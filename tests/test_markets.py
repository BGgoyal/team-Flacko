from app.config import Settings
from app.services.markets import (
    _angel_headers,
    _fetch_holding_quotes,
    _map_holding,
    fetch_bitcoin,
    fetch_metals,
    fetch_usd_inr_rate,
)


def test_holding_metrics_separate_daily_move_from_overall_pnl():
    holding = _map_holding(
        {"tradingsymbol": "DEMO", "quantity": 2, "averageprice": 10},
        {"ltp": 13, "close": 12},
    )

    assert holding["current_value"] == 26
    assert holding["overall_pnl"] == 6
    assert holding["movement_since_previous_close"] == 1
    assert holding["missing_fields"] == []


def test_angel_authorization_uses_server_jwt():
    headers = _angel_headers(Settings(angel_one_api_key="server-api-key"), "server-jwt")

    assert headers["Authorization"] == "Bearer server-jwt"
    assert headers["X-PrivateKey"] == "server-api-key"


def test_holding_quotes_use_smartapi_read_only_quote_endpoint(monkeypatch):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "data": {
                    "fetched": [
                        {"symbolToken": "123", "ltp": 13, "close": 12},
                    ]
                }
            }

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, **kwargs):
            assert url.endswith("/market/v1/quote/")
            assert kwargs["json"] == {"mode": "FULL", "exchangeTokens": {"NSE": ["123"]}}
            assert kwargs["headers"]["Authorization"] == "Bearer server-jwt"
            return Response()

    monkeypatch.setattr("app.services.markets.httpx.Client", Client)
    quotes = _fetch_holding_quotes(
        Settings(angel_one_api_key="server-api-key"),
        "server-jwt",
        [{"exchange": "NSE", "symboltoken": "123"}],
    )

    assert quotes["123"]["ltp"] == 13


def test_usd_inr_rate_requires_live_provider_data(monkeypatch, db_session):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "result": "success",
                "rates": {"INR": 83.5},
                "time_last_update_utc": "Fri, 30 Oct 2026 00:00:01 +0000",
            }

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url):
            assert url == "https://open.er-api.com/v6/latest/USD"
            return Response()

    monkeypatch.setattr("app.services.markets.httpx.Client", Client)
    rate = fetch_usd_inr_rate(db_session)

    assert rate["status"] == "ok"
    assert rate["usd_to_inr"] == 83.5


def test_bitcoin_returns_changes_in_both_quote_currencies(monkeypatch, db_session):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {
                "bitcoin": {
                    "inr": 8000,
                    "usd": 100,
                    "inr_24h_change": -2.5,
                    "usd_24h_change": -2,
                }
            }

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, _url, **kwargs):
            assert kwargs["params"]["vs_currencies"] == "inr,usd"
            return Response()

    monkeypatch.setattr("app.services.markets.httpx.Client", Client)
    quote = fetch_bitcoin(Settings(), db_session)

    assert quote["inr"] == 8000
    assert quote["usd"] == 100
    assert quote["change_24h_inr"] == -200
    assert quote["change_24h_usd"] == -2


def test_currency_and_quote_providers_handle_malformed_payloads(monkeypatch, db_session):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return ["unexpected", "shape"]

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr("app.services.markets.httpx.Client", Client)

    rate = fetch_usd_inr_rate(db_session)
    bitcoin = fetch_bitcoin(Settings(), db_session)
    metals = fetch_metals(Settings(), db_session)

    assert rate["status"] == "unavailable"
    assert rate["usd_to_inr"] is None
    assert bitcoin["status"] == "missing_data"
    assert bitcoin["inr"] is None
    assert metals["status"] == "unavailable"
    assert metals["gold"]["price_usd"] is None
