import asyncio

from sqlalchemy import select

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User


USER_ID = "41a246e5-baa5-4d2f-836c-3bbc7a5c4b92"
NEW_ROLE = "manager"


async def main():
    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User).where(
                User.id == USER_ID
            )
        )

        user = result.scalars().first()

        if not user:
            print(f"User not found: {USER_ID}")
            return

        print(f"Found user: {user.username}")
        print(f"Current role: {user.role}")

        user.role = NEW_ROLE

        await db.commit()
        await db.refresh(user)

        print(f"Role updated to: {user.role}")


if __name__ == "__main__":
    asyncio.run(main())