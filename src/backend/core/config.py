import os
from typing import List

def get_secret(key: str, default: str = "") -> str:
    """
    Retrieve secret from environment variable or file.
    Prioritizes <KEY>_FILE environment variable which points to a file containing the secret.
    This is standard for Docker Swarm and Kubernetes secrets.
    """
    # 1. Check for file-based secret
    file_path = os.getenv(f"{key}_FILE")
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return f.read().strip()
        except Exception:
            pass # Fallback to env var if file read fails
    
    # 2. Check for standard env var
    return os.getenv(key, default)

class Settings:
    ENV: str = os.getenv("ENV", "development")
    PROJECT_NAME: str = "Delivery Intelligence Platform"

    # SECURITY
    SECRET_KEY: str = get_secret("SECRET_KEY", "CHANGE_THIS_TO_A_SUPER_SECRET_KEY_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = get_secret(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8081,http://localhost:8082,http://127.0.0.1:5173,http://127.0.0.1:8081,http://127.0.0.1:8082"
    ).split(",")

    # DATABASE
    DATABASE_URL: str = get_secret("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/delivery_db")

    # S3 / PROOF STORAGE
    PROOF_STORAGE: str = get_secret("PROOF_STORAGE", "local")  # "local" or "s3"
    AWS_ACCESS_KEY_ID: str = get_secret("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = get_secret("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = get_secret("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = get_secret("S3_BUCKET_NAME", "delivery-proofs")
    S3_ENDPOINT_URL: str = get_secret("S3_ENDPOINT_URL", "")  # For LocalStack

    # NOTIFICATIONS
    NOTIFICATIONS_ENABLED: bool = get_secret("NOTIFICATIONS_ENABLED", "false").lower() == "true"
    TWILIO_ACCOUNT_SID: str = get_secret("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = get_secret("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = get_secret("TWILIO_FROM_NUMBER", "")
    SENDGRID_API_KEY: str = get_secret("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = get_secret("SENDGRID_FROM_EMAIL", "noreply@example.com")

    # REDIS
    REDIS_URL: str = get_secret("REDIS_URL", "")  # Empty = disabled, fallback to in-memory

    # MAPBOX
    MAPBOX_ACCESS_TOKEN: str = get_secret("MAPBOX_ACCESS_TOKEN", "")  # Empty = disabled

    # FIREBASE CLOUD MESSAGING
    FIREBASE_CREDENTIALS_JSON: str = get_secret("FIREBASE_CREDENTIALS_JSON", "")

    # WEATHER
    OPENWEATHER_API_KEY: str = get_secret("OPENWEATHER_API_KEY", "")

    # OIDC (Auth0 / Keycloak)
    OIDC_ENABLED: bool = get_secret("OIDC_ENABLED", "false").lower() == "true"
    OIDC_ISSUER_URL: str = get_secret("OIDC_ISSUER_URL", "")
    OIDC_CLIENT_ID: str = get_secret("OIDC_CLIENT_ID", "")
    OIDC_CLIENT_SECRET: str = get_secret("OIDC_CLIENT_SECRET", "")
    OIDC_ROLE_CLAIM: str = get_secret("OIDC_ROLE_CLAIM", "roles")

    # TELEMATICS (Samsara / Geotab)
    TELEMATICS_PROVIDER: str = get_secret("TELEMATICS_PROVIDER", "none")
    TELEMATICS_API_KEY: str = get_secret("TELEMATICS_API_KEY", "")
    TELEMATICS_API_URL: str = get_secret("TELEMATICS_API_URL", "")

    # IMAGE VERIFICATION
    IMAGE_VERIFICATION_PROVIDER: str = get_secret("IMAGE_VERIFICATION_PROVIDER", "stub")

    # CUSTOMER TRACKING PORTAL
    PUBLIC_TRACKING_ENABLED: bool = get_secret("PUBLIC_TRACKING_ENABLED", "true").lower() == "true"
    PUBLIC_TRACKING_BASE_URL: str = get_secret("PUBLIC_TRACKING_BASE_URL", "http://localhost:5173/track")

settings = Settings()
