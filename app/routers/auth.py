import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import BudgetCategory, User
from ..schemas import EmailLogin, EmailRegister, OtpCheck, OtpStart
from ..security import clear_session, create_session, current_user, hash_password, verify_password
from ..services.sms import check_otp, normalize_in_phone, send_otp

router = APIRouter(prefix="/api/auth", tags=["auth"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _public_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "name": user.name,
        "has_profile": user.profile is not None,
    }


@router.get("/status")
def auth_status():
    settings = get_settings()
    return {
        "twilio_configured": settings.twilio_configured,
        "openai_configured": settings.openai_configured,
        "angel_one_configured": settings.angel_configured,
        "sms_setup_hint": None
        if settings.twilio_configured
        else (
            "Mobile OTP needs Twilio Verify on the server: TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_VERIFY_SERVICE_SID. FinCoach will not invent or show a fake OTP."
        ),
    }


@router.post("/register")
def register(body: EmailRegister, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(body.password), name=body.name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    create_session(db, user, response, secure=get_settings().app_env == "production")
    return _public_user(user)


@router.post("/login")
def login(body: EmailLogin, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    create_session(db, user, response, secure=get_settings().app_env == "production")
    return _public_user(user)


@router.post("/otp/start")
def otp_start(body: OtpStart):
    settings = get_settings()
    if not settings.twilio_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "SMS verification is not configured. Add Twilio Verify credentials on the server. "
                "A fake OTP will not be generated."
            ),
        )
    try:
        phone = normalize_in_phone(body.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        send_otp(settings, phone)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True, "phone": phone, "message": "If the number is valid, a verification SMS is on the way."}


@router.post("/otp/verify")
def otp_verify(body: OtpCheck, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.twilio_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMS verification is not configured. A fake OTP will not be accepted.",
        )
    try:
        phone = normalize_in_phone(body.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        approved = check_otp(settings, phone, body.code.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not approved:
        raise HTTPException(status_code=401, detail="That code was not approved. Request a new SMS and try again.")
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone, name=body.name.strip())
        db.add(user)
        db.commit()
        db.refresh(user)
    elif body.name.strip() and not user.name:
        user.name = body.name.strip()
        db.commit()
    create_session(db, user, response, secure=settings.app_env == "production")
    return _public_user(user)


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = current_user(db, request)
    return _public_user(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    clear_session(db, request, response)
    return {"ok": True}


# Keep a default category helper used after profile save
DEFAULT_CATEGORIES = [
    ("Rent / housing", 0.30),
    ("Food", 0.25),
    ("Transport", 0.10),
    ("Bills & mobile", 0.10),
    ("Learning", 0.10),
    ("Other", 0.15),
]


def seed_categories(db: Session, user: User, monthly_expenses: float) -> None:
    if user.categories:
        return
    for name, share in DEFAULT_CATEGORIES:
        db.add(BudgetCategory(user_id=user.id, name=name, planned_amount=round(monthly_expenses * share, 2)))
    db.commit()
