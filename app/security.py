import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from .models import AuthSession, User

COOKIE_NAME = "fincoach_session"
SESSION_DAYS = 14


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_session(db: Session, user: User, response: Response, secure: bool) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.add(AuthSession(token=token, user_id=user.id, expires_at=expires))
    db.commit()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=SESSION_DAYS * 24 * 3600,
        path="/",
    )


def clear_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.get(AuthSession, token)
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")


def current_user(db: Session, request: Request) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required.")
    session = db.get(AuthSession, token)
    now = datetime.now(timezone.utc)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Sign in again.")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Sign in again.")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found.")
    return user
