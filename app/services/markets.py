import json
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import MarketCache

MIN_REFRESH_SECONDS = 60

EDUCATION = {
    "stocks": {
        "title": "Stocks (shares)",
        "summary": (
            "A share is a small ownership slice of a listed company. Prices change through the trading day "
            "when markets are open. Overall P&L compares current value with what you paid (average price × quantity). "
            "Daily movement compares the latest price with the previous close — a different number from overall P&L."
        ),
        "risks": (
            "Share prices can fall, sometimes sharply. Company news, sector trends, and market mood all matter. "
            "Past performance is not a guarantee. FinCoach does not recommend any stock."
        ),
    },
    "gold": {
        "title": "Gold",
        "summary": (
            "Gold is a commodity. Learners often meet it as jewellery, coins, or exchange-traded products. "
            "Its price is quoted globally and converted into rupees. This app does not tell you to buy gold."
        ),
        "risks": (
            "Gold can lose value in rupee terms for long stretches. Making charges, spreads, and storage matter. "
            "Live quotes may be missing if the public source is down."
        ),
    },
    "silver": {
        "title": "Silver",
        "summary": (
            "Silver is also a commodity, often more volatile than gold. Industrial demand can add extra swings. "
            "Educational only — not a purchase suggestion."
        ),
        "risks": "Silver prices can move quickly. Spreads and product costs can be large relative to small quantities.",
    },
    "bitcoin": {
        "title": "Bitcoin",
        "summary": (
            "Bitcoin is a digital asset with no cash flow like a company dividend. Quotes on this screen, when available, "
            "come from CoinGecko and are for learning how a quote looks — not a signal to buy or sell."
        ),
        "risks": (
            "Bitcoin can drop a large percentage in a short time. It is not a bank deposit, is not insured like a savings "
            "account, and can be hard to value. Never use invented prices if the feed fails."
        ),
    },
}

PLATFORM_NOTE = {
    "as_of": "2026-10-30",
    "text": (
        "Groww’s holdings page is login-protected. FinCoach does not scrape it and will never ask for a Groww or "
        "Angel One password in this app. Public, dated context: Indian securities trading for retail investors typically "
        "requires a SEBI-registered broker and a demat account (see SEBI investor education materials). "
        "Fee schedules change; compare them on each broker’s public disclosures, not via scraped private dashboards."
    ),
    "sources": [
        "SEBI investor education (public): https://investor.sebi.gov.in/",
        "NSE investor education (public): https://www.nseindia.com/invest/investors-home",
    ],
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _age_seconds(fetched: datetime) -> float:
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (_utcnow() - fetched).total_seconds()


def _get_cache(db: Session, key: str) -> MarketCache | None:
    return db.get(MarketCache, key)


def _set_cache(db: Session, key: str, payload: dict, status: str, message: str) -> MarketCache:
    row = db.get(MarketCache, key)
    raw = json.dumps(payload)
    if row:
        row.payload_json = raw
        row.fetched_at = _utcnow()
        row.status = status
        row.message = message
    else:
        row = MarketCache(
            cache_key=key,
            payload_json=raw,
            fetched_at=_utcnow(),
            status=status,
            message=message,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _fresh(row: MarketCache | None) -> bool:
    return bool(row and _age_seconds(row.fetched_at) < MIN_REFRESH_SECONDS)


def _angel_headers(settings: Settings, jwt: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": settings.angel_one_api_key,
    }


def _refresh_angel_jwt(settings: Settings) -> str | None:
    if not settings.angel_one_refresh_token or not settings.angel_one_api_key:
        return None
    url = "https://apiconnect.angelone.in/rest/auth/angelbroking/jwt/v1/generateTokens"
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                url,
                headers=_angel_headers(settings, settings.angel_one_jwt_token),
                json={"refreshToken": settings.angel_one_refresh_token},
            )
        if response.status_code >= 400:
            return None
        data = response.json()
        return (data.get("data") or {}).get("jwtToken")
    except httpx.HTTPError:
        return None


def _map_holding(item: dict[str, Any], quote: dict[str, Any] | None) -> dict[str, Any]:
    symbol = item.get("tradingsymbol") or item.get("symbol") or item.get("tradingSymbol") or ""
    qty = float(item.get("quantity") or item.get("qty") or 0)
    avg = float(item.get("averageprice") or item.get("avgPrice") or item.get("averagePrice") or 0)
    ltp = None
    prev_close = None
    if quote:
        ltp_raw = quote.get("ltp") or quote.get("LTP") or quote.get("lastPrice")
        prev_raw = quote.get("close") or quote.get("previousClose") or quote.get("prevClose")
        try:
            ltp = float(ltp_raw) if ltp_raw is not None else None
        except (TypeError, ValueError):
            ltp = None
        try:
            prev_close = float(prev_raw) if prev_raw is not None else None
        except (TypeError, ValueError):
            prev_close = None
    if ltp is None:
        for key in ("ltp", "Ltp", "lastPrice"):
            if item.get(key) is not None:
                try:
                    ltp = float(item[key])
                except (TypeError, ValueError):
                    ltp = None
    if prev_close is None and item.get("close") is not None:
        try:
            prev_close = float(item["close"])
        except (TypeError, ValueError):
            prev_close = None
    current_value = round(qty * ltp, 2) if ltp is not None else None
    overall_pnl = round(current_value - (qty * avg), 2) if current_value is not None else None
    daily_move = round(ltp - prev_close, 2) if ltp is not None and prev_close is not None else None
    daily_move_pct = (
        round(((ltp - prev_close) / prev_close) * 100, 2)
        if ltp is not None and prev_close not in (None, 0)
        else None
    )
    return {
        "symbol": symbol,
        "quantity": qty,
        "average_price": avg,
        "latest_price": ltp,
        "current_value": current_value,
        "overall_pnl": overall_pnl,
        "overall_pnl_note": "Overall P&L is since purchase (latest value minus quantity × average price).",
        "movement_since_previous_close": daily_move,
        "movement_since_previous_close_pct": daily_move_pct,
        "movement_note": "Daily movement is latest price minus previous close — not the same as overall P&L.",
        "missing_fields": [
            name
            for name, val in [
                ("latest_price", ltp),
                ("previous_close", prev_close),
            ]
            if val is None
        ],
    }


def _fetch_holding_quotes(
    settings: Settings, jwt: str, holdings: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    exchange_tokens: dict[str, list[str]] = {}
    for holding in holdings:
        token = holding.get("symboltoken") or holding.get("symbolToken")
        exchange = holding.get("exchange")
        if token and exchange:
            exchange_tokens.setdefault(str(exchange).upper(), []).append(str(token))
    if not exchange_tokens:
        return {}

    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
    try:
        with httpx.Client(timeout=25.0) as client:
            response = client.post(
                url,
                headers=_angel_headers(settings, jwt),
                json={"mode": "FULL", "exchangeTokens": exchange_tokens},
            )
        if response.status_code >= 400:
            return {}
    except httpx.HTTPError:
        return {}

    try:
        payload = response.json()
    except ValueError:
        return {}
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}
    fetched = data.get("fetched")
    if not isinstance(fetched, list):
        return {}
    return {
        str(quote["symbolToken"]): quote
        for quote in fetched
        if isinstance(quote, dict) and quote.get("symbolToken")
    }


def fetch_usd_inr_rate(db: Session) -> dict[str, Any]:
    cached = _get_cache(db, "usd_inr")
    if cached and _fresh(cached):
        payload = json.loads(cached.payload_json)
        payload["cached"] = True
        return payload

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get("https://open.er-api.com/v6/latest/USD")
        if response.status_code >= 400:
            return _unavailable_usd_inr(db, cached)
        data = response.json()
        if not isinstance(data, dict):
            return _unavailable_usd_inr(db, cached)
        rate = (data.get("rates") or {}).get("INR")
        if data.get("result") != "success" or not isinstance(rate, (int, float)) or rate <= 0:
            return _unavailable_usd_inr(db, cached)
        body = {
            "status": "ok",
            "usd_to_inr": rate,
            "source": "ExchangeRate-API open endpoint",
            "provider_updated_at": data.get("time_last_update_utc"),
            "last_successful_update": _utcnow().isoformat(),
            "message": "Indicative conversion rate; not a trading quote.",
        }
        _set_cache(db, "usd_inr", body, "ok", body["message"])
        return body
    except (httpx.HTTPError, ValueError, TypeError):
        return _unavailable_usd_inr(db, cached)


def _unavailable_usd_inr(db: Session, cached: MarketCache | None) -> dict[str, Any]:
    body = {
        "status": "unavailable",
        "usd_to_inr": None,
        "source": "ExchangeRate-API open endpoint",
        "provider_updated_at": None,
        "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
        "message": "Live USD/INR conversion rate is unavailable. Currency equivalents are not shown.",
    }
    _set_cache(db, "usd_inr", body, "unavailable", body["message"])
    return body


def fetch_holdings(settings: Settings, db: Session, force: bool = False) -> dict[str, Any]:
    cached = _get_cache(db, "angel_holdings")
    if cached and _fresh(cached):
        payload = json.loads(cached.payload_json)
        payload["cached"] = True
        payload["last_successful_update"] = cached.fetched_at.isoformat() if cached.status == "ok" else payload.get("last_successful_update")
        payload["status"] = cached.status
        payload["message"] = cached.message
        return payload

    if not settings.angel_configured:
        body = {
            "status": "disconnected",
            "message": (
                "Angel One SmartAPI is not configured. Add ANGEL_ONE_API_KEY and ANGEL_ONE_JWT_TOKEN "
                "on the server. FinCoach never asks for a broker password in this app."
            ),
            "holdings": [],
            "last_successful_update": None,
            "min_refresh_seconds": MIN_REFRESH_SECONDS,
        }
        _set_cache(db, "angel_holdings", body, "disconnected", body["message"])
        return body

    jwt = settings.angel_one_jwt_token
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/portfolio/v1/getHolding"
    try:
        with httpx.Client(timeout=25.0) as client:
            response = client.get(url, headers=_angel_headers(settings, jwt))
            if response.status_code in (401, 403) and settings.angel_one_refresh_token:
                new_jwt = _refresh_angel_jwt(settings)
                if new_jwt:
                    jwt = new_jwt
                    response = client.get(url, headers=_angel_headers(settings, jwt))
                else:
                    body = {
                        "status": "expired_token",
                        "message": "Angel One session token expired and refresh failed. Update tokens in server environment.",
                        "holdings": [],
                        "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
                        "min_refresh_seconds": MIN_REFRESH_SECONDS,
                    }
                    _set_cache(db, "angel_holdings", body, "expired_token", body["message"])
                    return body
            elif response.status_code in (401, 403):
                body = {
                    "status": "expired_token",
                    "message": "Angel One rejected the session token. Update ANGEL_ONE_JWT_TOKEN on the server.",
                    "holdings": [],
                    "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
                    "min_refresh_seconds": MIN_REFRESH_SECONDS,
                }
                _set_cache(db, "angel_holdings", body, "expired_token", body["message"])
                return body
            if response.status_code >= 400:
                body = {
                    "status": "provider_error",
                    "message": f"Angel One returned HTTP {response.status_code}. No prices were invented.",
                    "holdings": [],
                    "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
                    "min_refresh_seconds": MIN_REFRESH_SECONDS,
                }
                _set_cache(db, "angel_holdings", body, "provider_error", body["message"])
                return body
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        body = {
            "status": "provider_error",
            "message": "Could not reach Angel One. Showing no invented holdings.",
            "holdings": [],
            "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
            "min_refresh_seconds": MIN_REFRESH_SECONDS,
        }
        _set_cache(db, "angel_holdings", body, "provider_error", body["message"])
        return body

    if not isinstance(data, dict):
        body = {
            "status": "provider_error",
            "message": "Angel One returned an unexpected holdings response. No prices were invented.",
            "holdings": [],
            "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
            "min_refresh_seconds": MIN_REFRESH_SECONDS,
        }
        _set_cache(db, "angel_holdings", body, "provider_error", body["message"])
        return body

    status_flag = str(data.get("status", "")).lower()
    if status_flag in {"false", "error"} or data.get("errorcode"):
        msg = data.get("message") or data.get("errorcode") or "Angel One reported an error."
        lowered = str(msg).lower()
        state = "expired_token" if "token" in lowered or "jwt" in lowered else "provider_error"
        if "market" in lowered and "clos" in lowered:
            state = "market_closed"
        body = {
            "status": state,
            "message": str(msg),
            "holdings": [],
            "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
            "min_refresh_seconds": MIN_REFRESH_SECONDS,
        }
        _set_cache(db, "angel_holdings", body, state, body["message"])
        return body

    raw_holdings = data.get("data") or []
    if raw_holdings is None:
        raw_holdings = []
    quotes = _fetch_holding_quotes(settings, jwt, raw_holdings)
    holdings = [
        _map_holding(item, quotes.get(str(item.get("symboltoken") or item.get("symbolToken") or "")))
        for item in raw_holdings
    ]
    quotes_complete = all(not holding["missing_fields"] for holding in holdings)
    body = {
        "status": "ok",
        "message": (
            "Read-only holdings from Angel One SmartAPI. FinCoach cannot place trades."
            if quotes_complete
            else "Holdings loaded, but latest price or previous-close quote data is missing for one or more symbols."
        ),
        "holdings": holdings,
        "last_successful_update": _utcnow().isoformat(),
        "min_refresh_seconds": MIN_REFRESH_SECONDS,
        "quote_data_status": "ok" if quotes_complete else "partial",
        "market_hours_note": (
            "If the market is closed, last traded price may be stale. Daily movement still uses previous close; "
            "it is not overall P&L."
        ),
    }
    _set_cache(db, "angel_holdings", body, "ok", body["message"])
    return body


def fetch_bitcoin(settings: Settings, db: Session, force: bool = False) -> dict[str, Any]:
    cached = _get_cache(db, "btc")
    if cached and _fresh(cached):
        payload = json.loads(cached.payload_json)
        payload["cached"] = True
        return payload
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "inr,usd",
        "include_24hr_change": "true",
    }
    headers = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, params=params, headers=headers)
        if response.status_code >= 400:
            body = {
                "status": "provider_error",
                "message": f"CoinGecko returned HTTP {response.status_code}. Bitcoin price not invented.",
                "inr": None,
                "usd": None,
                "change_24h_pct": None,
                "change_24h_usd_pct": None,
                "change_24h_inr": None,
                "change_24h_usd": None,
                "source": "CoinGecko",
                "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
            }
            _set_cache(db, "btc", body, "provider_error", body["message"])
            return body
        data = response.json()
        if not isinstance(data, dict):
            data = {}
        quote = data.get("bitcoin", {})
        if not isinstance(quote, dict):
            quote = {}
        inr = quote.get("inr")
        usd = quote.get("usd")
        inr_change_pct = quote.get("inr_24h_change")
        usd_change_pct = quote.get("usd_24h_change")
        if not isinstance(inr, (int, float)) or not isinstance(usd, (int, float)):
            inr_valid = isinstance(inr, (int, float))
            body = {
                "status": "partial" if inr_valid else "missing_data",
                "message": (
                    "CoinGecko did not provide a valid USD quote."
                    if inr_valid
                    else "CoinGecko did not provide a valid INR quote."
                ),
                "inr": inr if inr_valid else None,
                "usd": usd if isinstance(usd, (int, float)) else None,
                "change_24h_pct": None,
                "change_24h_usd_pct": usd_change_pct if isinstance(usd_change_pct, (int, float)) else None,
                "change_24h_inr": None,
                "change_24h_usd": (
                    round(usd * usd_change_pct / 100, 2)
                    if isinstance(usd, (int, float)) and isinstance(usd_change_pct, (int, float))
                    else None
                ),
                "source": "CoinGecko",
                "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
            }
            _set_cache(db, "btc", body, "missing_data", body["message"])
            return body
        body = {
            "status": "ok",
            "message": "Quote from CoinGecko. Not a recommendation.",
            "inr": inr,
            "usd": usd,
            "change_24h_pct": inr_change_pct,
            "change_24h_usd_pct": usd_change_pct if isinstance(usd_change_pct, (int, float)) else None,
            "change_24h_inr": (
                round(inr * inr_change_pct / 100, 2)
                if isinstance(inr_change_pct, (int, float))
                else None
            ),
            "change_24h_usd": (
                round(usd * usd_change_pct / 100, 2)
                if isinstance(usd, (int, float)) and isinstance(usd_change_pct, (int, float))
                else None
            ),
            "source": "CoinGecko",
            "last_successful_update": _utcnow().isoformat(),
        }
        _set_cache(db, "btc", body, "ok", body["message"])
        return body
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        body = {
            "status": "provider_error",
            "message": "Could not reach CoinGecko. Bitcoin price not invented.",
            "inr": None,
            "usd": None,
            "change_24h_pct": None,
            "change_24h_usd_pct": None,
            "change_24h_inr": None,
            "change_24h_usd": None,
            "source": "CoinGecko",
            "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
        }
        _set_cache(db, "btc", body, "provider_error", body["message"])
        return body


def fetch_metals(settings: Settings, db: Session, force: bool = False) -> dict[str, Any]:
    cached = _get_cache(db, "metals")
    if cached and _fresh(cached):
        payload = json.loads(cached.payload_json)
        payload["cached"] = True
        return payload

    def one(symbol: str) -> dict[str, Any]:
        url = f"{settings.metals_api_base.rstrip('/')}/price/{symbol}"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url)
            if response.status_code >= 400:
                return {"status": "unavailable", "price_usd": None, "symbol": symbol}
            data = response.json()
            if not isinstance(data, dict):
                return {"status": "unavailable", "price_usd": None, "symbol": symbol}
            price = data.get("price")
            if not isinstance(price, (int, float)):
                return {"status": "unavailable", "price_usd": None, "symbol": symbol}
            return {
                "status": "ok",
                "price_usd": price,
                "symbol": symbol,
                "name": data.get("name"),
                "updatedAt": data.get("updatedAt"),
                "source": "gold-api.com (public documented metal spot feed)",
            }
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return {"status": "unavailable", "price_usd": None, "symbol": symbol}

    gold = one("XAU")
    silver = one("XAG")
    if gold["status"] != "ok" and silver["status"] != "ok":
        body = {
            "status": "unavailable",
            "message": "Live gold and silver prices are unavailable from the documented public source (gold-api.com). No prices were invented.",
            "gold": gold,
            "silver": silver,
            "last_successful_update": cached.fetched_at.isoformat() if cached and cached.status == "ok" else None,
        }
        _set_cache(db, "metals", body, "unavailable", body["message"])
        return body
    body = {
        "status": "ok" if gold["status"] == "ok" and silver["status"] == "ok" else "partial",
        "message": "Spot prices in USD per troy ounce from gold-api.com. INR equivalents use a separately labeled indicative USD/INR rate. Not a buy/sell call.",
        "gold": gold,
        "silver": silver,
        "last_successful_update": _utcnow().isoformat(),
    }
    _set_cache(db, "metals", body, body["status"], body["message"])
    return body
