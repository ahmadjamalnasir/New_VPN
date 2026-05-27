import asyncio
import os
import logging

from app.database import AsyncSessionLocal
from app import models, auth

logger = logging.getLogger(__name__)


async def register_and_promote(email: str, password: str):
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            models.User.__table__.select().where(models.User.email == email)
        )
        if existing.scalar_one_or_none():
            logger.info(f"Admin user {email} already exists")
            return

        hashed_password = auth.get_password_hash(password)
        user = models.User(
            email=email,
            hashed_password=hashed_password,
            role="admin",
            tier="premium",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    logger.info(f"Admin user {email} registered successfully")


if __name__ == "__main__":
    admin_email = os.getenv("ADMIN_EMAIL", "admin@primevpn.local")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_password:
        raise RuntimeError("Missing required environment variable: ADMIN_PASSWORD")

    asyncio.run(register_and_promote(admin_email, admin_password))
