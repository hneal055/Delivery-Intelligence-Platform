import os
from typing import List

class Settings:
    PROJECT_NAME: str = "Delivery Intelligence Platform"
    
    # SECURITY
    # Default to a weak key for dev, but WARN or fail in prod if not set.
    # In a real app, we might raise an error if SECRET_KEY is missing in production.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_SUPER_SECRET_KEY_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    # Comma-separated list of origins
    BACKEND_CORS_ORIGINS: List[str] = os.getenv(
        "BACKEND_CORS_ORIGINS", 
        "http://localhost:8081,http://localhost:8082,http://127.0.0.1:8081,http://127.0.0.1:8082,*"
    ).split(",")

settings = Settings()

