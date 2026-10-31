from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..security import current_user
from ..services.markets import (
    EDUCATION,
    PLATFORM_NOTE,
    fetch_bitcoin,
    fetch_holdings,
    fetch_metals,
    fetch_usd_inr_rate,
)

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("")
def assets(request: Request, db: Session = Depends(get_db), refresh: bool = False):
    current_user(db, request)
    settings = get_settings()
    holdings = fetch_holdings(settings, db, force=refresh)
    btc = fetch_bitcoin(settings, db, force=refresh)
    metals = fetch_metals(settings, db, force=refresh)
    fx = fetch_usd_inr_rate(db)
    rate = fx["usd_to_inr"] if fx["status"] == "ok" else None
    for holding in holdings.get("holdings", []):
        holding["average_price_usd"] = round(holding["average_price"] / rate, 2) if rate else None
        holding["latest_price_usd"] = round(holding["latest_price"] / rate, 2) if rate and holding["latest_price"] is not None else None
        holding["current_value_usd"] = round(holding["current_value"] / rate, 2) if rate and holding["current_value"] is not None else None
        holding["overall_pnl_usd"] = round(holding["overall_pnl"] / rate, 2) if rate and holding["overall_pnl"] is not None else None
        holding["movement_since_previous_close_usd"] = (
            round(holding["movement_since_previous_close"] / rate, 2)
            if rate and holding["movement_since_previous_close"] is not None
            else None
        )
    for metal in (metals.get("gold", {}), metals.get("silver", {})):
        usd_price = metal.get("price_usd")
        metal["price_inr"] = round(usd_price * rate, 2) if rate and usd_price is not None else None
    return {
        "holdings": holdings,
        "bitcoin": btc,
        "metals": metals,
        "currency": fx,
        "education": EDUCATION,
        "platform_note": PLATFORM_NOTE,
        "safety": [
            "Read-only view. FinCoach cannot place trades.",
            "Overall P&L is since purchase. Daily movement is versus previous close.",
            "Missing, stale, or failed quotes are shown as states. Prices are never invented.",
            "USD conversions are approximate and use the separately displayed indicative USD/INR rate.",
            "This is not a recommendation of any stock, metal, or cryptocurrency.",
        ],
    }
