import asyncio
import sys
sys.path.append('.')

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User
from src.backend.utils.security import get_password_hash
from sqlalchemy.future import select

async def add_dispatcher():
    async with AsyncSessionLocal() as db:
        # Check if dispatcher1 exists
        result = await db.execute(select(User).where(User.username == "dispatcher1"))
        user = result.scalars().first()
        
        if user:
            print(f"dispatcher1 already exists with role: {user.role}")
            return
        
        # Create dispatcher1 user
        print("Creating dispatcher1 user...")
        new_user = User(
            username="dispatcher1",
            hashed_password=get_password_hash("dispatcherpassword"),
            role="manager",
            is_active=True
        )
        db.add(new_user)
        await db.commit()
        print("dispatcher1 created successfully!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(add_dispatcher())
