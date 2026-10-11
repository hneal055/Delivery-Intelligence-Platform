"""
Create a login account (operator tool).

Prompts for the password without echoing it. Run inside the backend container:

    docker exec -it delivery_backend python -m src.scripts.create_user <username> <role> [email]

role: driver | dispatcher | manager | admin. A driver also becomes assignable
in the dashboard the first time they log in on the phone.
"""
import asyncio
import getpass
import sys

from src.backend.core.database import AsyncSessionLocal
from src.backend.models.domain import UserCreate, UserRole
from src.backend.services.driver_profile import ensure_driver_profile
from src.backend.services.user_service import create_user, get_user_by_username

MIN_LENGTH = 10


async def create(username: str, role: UserRole, email: str, password: str) -> bool:
    async with AsyncSessionLocal() as db:
        if await get_user_by_username(db, username):
            return False
        await create_user(db, UserCreate(username=username, email=email, password=password), role=role)
        if role == UserRole.DRIVER:
            await ensure_driver_profile(db, username)
        return True


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("Usage: python -m src.scripts.create_user <username> <driver|dispatcher|manager|admin> [email]")
        return 2
    username, role_name = sys.argv[1], sys.argv[2].lower()
    try:
        role = UserRole(role_name)
    except ValueError:
        print(f"Unknown role {role_name!r}; use driver, dispatcher, manager or admin.")
        return 2
    email = sys.argv[3] if len(sys.argv) == 4 else f"{username}@example.invalid"

    password = getpass.getpass(f"Password for {username}: ")
    if len(password) < MIN_LENGTH:
        print(f"Password must be at least {MIN_LENGTH} characters.")
        return 1
    if getpass.getpass("Repeat password: ") != password:
        print("Passwords do not match.")
        return 1

    if not asyncio.run(create(username, role, email, password)):
        print(f"A user named {username} already exists. To change the password use set_user_password.")
        return 1
    print(f"Created {role.value} account {username}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
