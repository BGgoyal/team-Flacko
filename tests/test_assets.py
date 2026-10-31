from unittest.mock import patch


def test_assets_disconnected_without_angel_credentials(authed_client):
    fake_btc = {
        "status": "provider_error",
        "message": "Could not reach CoinGecko. Bitcoin price not invented.",
        "inr": None,
        "change_24h_pct": None,
        "source": "CoinGecko",
        "last_successful_update": None,
    }
    fake_metals = {
        "status": "unavailable",
        "message": "Live gold and silver prices are unavailable.",
        "gold": {"price_usd": None},
        "silver": {"price_usd": None},
        "last_successful_update": None,
    }
    fake_fx = {
        "status": "unavailable",
        "usd_to_inr": None,
        "source": "ExchangeRate-API open endpoint",
        "provider_updated_at": None,
        "last_successful_update": None,
        "message": "Live USD/INR conversion rate is unavailable.",
    }
    with patch("app.routers.assets.fetch_bitcoin", return_value=fake_btc), patch(
        "app.routers.assets.fetch_metals", return_value=fake_metals
    ), patch("app.routers.assets.fetch_usd_inr_rate", return_value=fake_fx):
        r = authed_client.get("/api/assets")
    assert r.status_code == 200
    body = r.json()
    assert body["holdings"]["status"] == "disconnected"
    assert body["currency"]["usd_to_inr"] is None
    assert "password" in body["holdings"]["message"].lower()
    assert any("invent" in s.lower() for s in body["safety"])


def test_assets_exposes_dollar_equivalents_and_direction(authed_client):
    fake_holdings = {
        "status": "ok",
        "message": "Read-only holdings.",
        "holdings": [{
            "latest_price": 250,
            "average_price": 270,
            "current_value": 500,
            "overall_pnl": -40,
            "movement_since_previous_close": 10,
            "missing_fields": [],
        }],
        "last_successful_update": "2026-10-30T12:00:00+00:00",
    }
    fake_btc = {
        "status": "ok",
        "message": "Quote from CoinGecko.",
        "inr": 8000,
        "usd": 100,
        "change_24h_pct": 2.5,
        "change_24h_usd_pct": 2,
        "change_24h_inr": 200,
        "change_24h_usd": 2,
        "source": "CoinGecko",
        "last_successful_update": "2026-10-30T12:00:00+00:00",
    }
    fake_metals = {
        "status": "ok",
        "message": "Spot prices.",
        "gold": {"price_usd": 2000, "price_inr": None},
        "silver": {"price_usd": 25, "price_inr": None},
        "last_successful_update": "2026-10-30T12:00:00+00:00",
    }
    fake_fx = {
        "status": "ok",
        "usd_to_inr": 80,
        "source": "test FX source",
        "provider_updated_at": None,
        "last_successful_update": "2026-10-30T12:00:00+00:00",
        "message": "Indicative rate.",
    }
    with patch("app.routers.assets.fetch_holdings", return_value=fake_holdings), patch(
        "app.routers.assets.fetch_bitcoin", return_value=fake_btc
    ), patch("app.routers.assets.fetch_metals", return_value=fake_metals), patch(
        "app.routers.assets.fetch_usd_inr_rate", return_value=fake_fx
    ):
        response = authed_client.get("/api/assets")

    assert response.status_code == 200
    body = response.json()
    assert body["holdings"]["holdings"][0]["current_value_usd"] == 6.25
    assert body["holdings"]["holdings"][0]["average_price_usd"] == 3.38
    assert body["holdings"]["holdings"][0]["latest_price_usd"] == 3.12
    assert body["holdings"]["holdings"][0]["movement_since_previous_close_usd"] == 0.12
    assert body["metals"]["gold"]["price_inr"] == 160000
    assert body["bitcoin"]["change_24h_usd"] == 2
