"""Email/password auth (bcrypt + JWT) and per-user daily rate limiting (IST)."""
from datetime import date, datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import AnalysisUsage, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

IST = timezone(timedelta(hours=5, minutes=30))


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise cred_exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise cred_exc
    return user


def ist_today() -> date:
    return datetime.now(IST).date()


def next_ist_midnight_iso() -> str:
    now = datetime.now(IST)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return tomorrow.isoformat()


def get_usage(db: Session, user_id: int) -> AnalysisUsage:
    today = ist_today()
    usage = (
        db.query(AnalysisUsage)
        .filter(AnalysisUsage.user_id == user_id, AnalysisUsage.usage_date_ist == today)
        .first()
    )
    if not usage:
        usage = AnalysisUsage(user_id=user_id, usage_date_ist=today, count=0)
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def assert_quota(db: Session, user_id: int) -> AnalysisUsage:
    """Raise 429 if the user's daily limit is reached; else return the row."""
    usage = get_usage(db, user_id)
    if usage.count >= settings.daily_analysis_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI analysis limit reached. Resets at midnight IST.",
        )
    return usage


def consume_quota(db: Session, usage: AnalysisUsage) -> None:
    """Increment the counter — only call after a successful analysis."""
    usage.count += 1
    db.commit()
