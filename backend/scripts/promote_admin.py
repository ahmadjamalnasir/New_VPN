import asyncio
import sys
from app.database import AsyncSessionLocal
from app.models import User
from sqlalchemy.future import select

async def promote_user(email: str):
    async with AsyncSessionLocal() as db:
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User with email {email} not found.")
            return
            
        user.role = "admin"
        await db.commit()
        print(f"User {email} successfully promoted to ADMIN.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_admin.py <email>")
    else:
        asyncio.run(promote_user(sys.argv[1]))
