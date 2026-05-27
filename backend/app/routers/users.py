import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import database, models, schemas, auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(database.get_db),
):
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"New user registered: {user.email}")
    return db_user


@router.get("/me", response_model=schemas.UserResponse)
async def read_user_me(
    current_user: models.User = Depends(auth.get_current_user),
):
    return current_user
