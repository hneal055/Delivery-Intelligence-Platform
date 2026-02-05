from typing import Dict, Optional
from src.backend.models.domain import User, UserCreate, UserRole
from src.backend.utils.security import get_password_hash

# In-memory database for Phase 1
fake_users_db: Dict[str, dict] = {}

def get_user_by_username(username: str) -> Optional[User]:
    if username in fake_users_db:
        return User(**fake_users_db[username])
    return None

def create_user(user: UserCreate, role: UserRole = UserRole.DRIVER) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = {
        "username": user.username,
        "email": user.email,
        "role": role,
        "password": hashed_password, # Storing hashed password
        "id": user.username, # Simple ID for now
        "is_active": True
    }
    fake_users_db[user.username] = db_user
    return User(**db_user)

# Initialize with a default admin
def init_db():
    if "admin" not in fake_users_db:
        create_user(UserCreate(username="admin", password="adminpassword", email="admin@diplatform.com"), role=UserRole.ADMIN)
    if "driver1" not in fake_users_db:
        create_user(UserCreate(username="driver1", password="driverpassword", email="driver1@diplatform.com"), role=UserRole.DRIVER)

init_db()
