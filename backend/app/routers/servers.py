import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import auth, database, models, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/servers", tags=["Servers"])


@router.get("/", response_model=List[schemas.ServerResponse])
async def read_servers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    query = select(models.Server).filter(models.Server.is_active.is_(True))

    if current_user is None or current_user.tier == "free":
        query = query.filter(models.Server.is_premium.is_(False))

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
