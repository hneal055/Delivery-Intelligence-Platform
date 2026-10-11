"""
Set a user's password (operator tool).

Prompts for the new password without echoing it, so it never appears in
shell history or process listings. Run inside the backend container:

    docker exec -it delivery_backend python -m src.scripts.set_user_password driver2
"""
import asyncio
import getpass
import sys

from sqlalchemy import update

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.sql_models import User
from src.backend.utils.security import get_password_hash

MIN_LENGTH = 10


async def set_password(username: str, password: str) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(User)
            .where(User.username == username)
            .values(hashed_password=get_password_hash(password))
        )
        await db.commit()
        return result.rowcount


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m src.scripts.set_user_password <username>")
        return 2
    username = sys.argv[1]

    password = getpass.getpass(f"New password for {username}: ")
    if len(password) < MIN_LENGTH:
        print(f"Password must be at least {MIN_LENGTH} characters.")
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.")
        return 1

    if asyncio.run(set_password(username, password)) == 0:
        print(f"No user named {username}.")
        return 1
    print(f"Password updated for {username}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
