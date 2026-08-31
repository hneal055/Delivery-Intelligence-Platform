import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User


SOURCE_ROLE = "driver"
TARGET_ROLE = "manager"


async def main():
    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User).where(
                User.role == SOURCE_ROLE
            )
        )

        users = result.scalars().all()

        print(f"Found {len(users)} users with role '{SOURCE_ROLE}'")

        if not users:
            return

        for user in users:
            print(
                f"Updating {user.username}: "
                f"{user.role} -> {TARGET_ROLE}"
            )

            user.role = TARGET_ROLE

        await db.commit()

        print(
            f"\nSuccessfully updated {len(users)} users."
        )


if __name__ == "__main__":
    asyncio.run(main())