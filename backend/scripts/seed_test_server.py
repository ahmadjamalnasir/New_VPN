import asyncio
from app.database import AsyncSessionLocal
from app.models import Server

async def seed_test_server():
    async with AsyncSessionLocal() as db:
        test_server = Server(
            name="Prime Test Canada",
            location="Montreal, Canada",
            ip_address="144.217.253.149",
            vpn_subnet="10.104.0.0/24",
            port=443,
            public_key="Iq0kTIp79YgI45+vVMOTfYZSbydVUoLnNe0mt88CViI=",
            is_active=True,
            is_premium=False
        )
        db.add(test_server)
        await db.commit()
        print(f"Added server: {test_server.name}")

if __name__ == "__main__":
    asyncio.run(seed_test_server())
