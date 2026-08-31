import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User


async def main():
    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(User)
        )

        users = result.scalars().all()

        role_counts = {}

        for user in users:
            role = user.role

            if role not in role_counts:
                role_counts[role] = 0

            role_counts[role] += 1

        print("\nUSER ROLE AUDIT")
        print("=" * 40)
        print(f"Total Users: {len(users)}")
        print("=" * 40)

        for role in sorted(role_counts):
            print(
                f"{role.upper():<15} : "
                f"{role_counts[role]}"
            )

        print("=" * 40)

        print("\nUSER DETAILS")
        print("=" * 40)

        for user in sorted(users, key=lambda x: x.username.lower()):
            print(
                f"{user.username:<35} "
                f"{user.role:<15} "
                f"{'ACTIVE' if user.is_active else 'INACTIVE'}"
            )


if __name__ == "__main__":
    asyncio.run(main())