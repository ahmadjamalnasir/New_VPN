import asyncio
from app.database import engine, Base
from app import models

async def recreate_db():
    async with engine.begin() as conn:
        # Warning: This will drop all data!
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables recreated successfully.")

if __name__ == "__main__":
    asyncio.run(recreate_db())
