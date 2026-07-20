import os
import sys
from typing import List


def _parse_origins(raw: str) -> List[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings:
    PROJECT_NAME: str = "Delivery Intelligence Platform"

    # ENVIRONMENT: "development" (default) or "production"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    IS_PRODUCTION: bool = ENVIRONMENT == "production"

    # SECURITY
    DEV_SECRET_PLACEHOLDER: str = "dev-only-secret-do-not-use-in-production"
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEV_SECRET_PLACEHOLDER)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
    )

    # CORS
    # No wildcard default. In development we allow common local dev ports.
    # In production, BACKEND_CORS_ORIGINS MUST be set explicitly
    # (comma-separated, e.g. "https://dispatch.example.com").
    _DEV_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8081,http://127.0.0.1:8081,"
        "http://localhost:8082,http://127.0.0.1:8082,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    BACKEND_CORS_ORIGINS: List[str] = _parse_origins(
        os.getenv("BACKEND_CORS_ORIGINS", _DEV_ORIGINS)
    )

    # DATABASE
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/delivery_db",
    )

    # CLOUDFLARE R2 (proof-of-delivery photo storage)
    # When all four are set, the R2 backend is used automatically.
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "")

    @property
    def r2_configured(self) -> bool:
        return bool(
            self.R2_ACCOUNT_ID
            and self.R2_ACCESS_KEY_ID
            and self.R2_SECRET_ACCESS_KEY
            and self.R2_BUCKET_NAME
        )


settings = Settings()


# ---------------------------------------------------------------------------
# Production fail-fast checks.
# The app REFUSES to start in production with unsafe configuration.
# ---------------------------------------------------------------------------
if settings.IS_PRODUCTION:
    _problems = []

    if (
        settings.SECRET_KEY == Settings.DEV_SECRET_PLACEHOLDER
        or len(settings.SECRET_KEY) < 32
    ):
        _problems.append(
            "SECRET_KEY must be set to a strong random value (32+ characters)."
        )

    if not os.getenv("BACKEND_CORS_ORIGINS"):
        _problems.append(
            "BACKEND_CORS_ORIGINS must be set to your dashboard URL(s)."
        )

    if "*" in settings.BACKEND_CORS_ORIGINS:
        _problems.append("BACKEND_CORS_ORIGINS must not contain '*'.")

    if not os.getenv("DATABASE_URL"):
        _problems.append("DATABASE_URL must be set.")

    if not settings.r2_configured:
        # Warning only: local disk is EPHEMERAL on Railway. Proof photos
        # will be LOST on every redeploy until R2 is configured.
        sys.stderr.write(
            "WARNING: R2 storage is not configured. Proof-of-delivery photos "
            "will be stored on ephemeral local disk and lost on redeploy. "
            "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, "
            "and R2_BUCKET_NAME.\n"
        )

    if _problems:
        sys.stderr.write(
            "FATAL: refusing to start in production with unsafe settings:\n"
        )
        for _p in _problems:
            sys.stderr.write("  - " + _p + "\n")
        sys.exit(1)
