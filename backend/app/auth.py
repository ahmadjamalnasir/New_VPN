import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import database, models, schemas
from app.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(database.get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None or payload.get("type") != "access":
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(models.User).where(models.User.email == token_data.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(database.get_db),
) -> Optional[models.User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None or payload.get("type") != "access":
            return None
        result = await db.execute(select(models.User).where(models.User.email == email))
        return result.scalar_one_or_none()
    except JWTError:
        return None


async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user


async def revoke_refresh_token(token: str, db: AsyncSession) -> None:
    result = await db.execute(select(models.RefreshToken).where(models.RefreshToken.token == token))
    refresh_token = result.scalar_one_or_none()
    if refresh_token:
        refresh_token.revoked = True
        await db.commit()
        logger.info(f"Refresh token revoked for user_id={refresh_token.user_id}")


async def create_refresh_token_record(user_id: int, token: str, db: AsyncSession) -> models.RefreshToken:
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    record = models.RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def validate_refresh_token(token: str, db: AsyncSession) -> models.RefreshToken:
    result = await db.execute(
        select(models.RefreshToken)
        .where(models.RefreshToken.token == token)
        .where(models.RefreshToken.revoked.is_(False))
        .where(models.RefreshToken.expires_at > datetime.now(timezone.utc))
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return record
