import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import database, models, auth, schemas
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(select(models.User).where(models.User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    refresh_token_str = auth.create_refresh_token()
    await auth.create_refresh_token_record(user.id, refresh_token_str, db)

    logger.info(f"User {user.email} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token_str}


@router.post("/token/refresh", response_model=schemas.Token)
async def refresh_access_token(
    body: schemas.TokenRefresh,
    db: AsyncSession = Depends(database.get_db),
):
    record = await auth.validate_refresh_token(body.refresh_token, db)

    result = await db.execute(select(models.User).where(models.User.id == record.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    await auth.revoke_refresh_token(body.refresh_token, db)

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    new_refresh_token = auth.create_refresh_token()
    await auth.create_refresh_token_record(user.id, new_refresh_token, db)

    logger.info(f"Token refreshed for user {user.email}")
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": new_refresh_token}


@router.post("/logout")
async def logout(
    body: schemas.TokenRefresh,
    db: AsyncSession = Depends(database.get_db),
):
    await auth.revoke_refresh_token(body.refresh_token, db)
    return {"message": "Logged out successfully"}
