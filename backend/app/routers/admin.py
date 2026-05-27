import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import database, models, schemas, auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[schemas.UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()


@router.patch("/users/{user_id}/tier", response_model=schemas.UserResponse)
async def update_user_tier(
    user_id: int,
    tier: str,
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    if tier not in ("free", "premium"):
        raise HTTPException(status_code=400, detail="Invalid tier")

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.tier = tier
    await db.commit()
    await db.refresh(user)
    logger.info(f"Admin {admin.email} updated user {user.email} tier to {tier}")
    return user


@router.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
async def update_user_role(
    user_id: int,
    role: str,
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    if role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    await db.commit()
    await db.refresh(user)
    logger.info(f"Admin {admin.email} updated user {user.email} role to {role}")
    return user


@router.get("/servers", response_model=List[schemas.ServerResponse])
async def get_all_servers(
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    result = await db.execute(select(models.Server))
    return result.scalars().all()


@router.patch("/servers/{server_id}/toggle", response_model=schemas.ServerResponse)
async def toggle_server(
    server_id: int,
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    result = await db.execute(select(models.Server).where(models.Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.is_active = not server.is_active
    await db.commit()
    await db.refresh(server)
    logger.info(f"Admin {admin.email} toggled server {server.name} to active={server.is_active}")
    return server


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: int,
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    result = await db.execute(select(models.Server).where(models.Server.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    await db.delete(server)
    await db.commit()
    logger.info(f"Admin {admin.email} deleted server {server.name}")


@router.get("/vpn-keys", response_model=List[schemas.VPNKeyResponse])
async def list_all_keys(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(database.get_db),
    admin: models.User = Depends(auth.get_current_admin_user),
):
    result = await db.execute(
        select(models.VPNKey).offset(skip).limit(limit)
    )
    return result.scalars().all()
