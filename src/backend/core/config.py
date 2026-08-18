import os
import sys
from typing import List


def _parse_origins(raw: str) -> List[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


class Settings:
    PROJECT_NAME: str = "Delivery Intelligence Platform"

    # ENVIRONMENT: "development" (default) or "production"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    ENV: str = ENVIRONMENT  # alias for compatibility
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
        "postgresql://postgres:[REDACTED]@localhost:5432/delivery_db",
    )

    # REDIS
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # NOTIFICATIONS
    NOTIFICATIONS_ENABLED: bool = os.getenv("NOTIFICATIONS_ENABLED", "false").lower() == "true"
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "noreply@diplatform.local")

    # OPENTELEMETRY
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "delivery-platform-backend")
    OTEL_SERVICE_VERSION: str = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    OTLP_ENDPOINT: str = os.getenv("OTLP_ENDPOINT", "")

    # MAPBOX
    MAPBOX_ACCESS_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", "")

    # TOMTOM (real-time traffic + routing)
    # When set, package creation uses real traffic-adjusted ETAs instead of
    # synthetic random values. Falls back gracefully to synthetic data if
    # unset or if the API call fails, so this is never a hard dependency.
    TOMTOM_API_KEY: str = os.getenv("TOMTOM_API_KEY", "")

    # Device token used for dev device secure-ping. In production provide DEVICE_TOKEN.
    DEVICE_TOKEN: str = os.getenv("DEVICE_TOKEN", "")

    # If true, the app will run init_data() at startup to create demo users/profiles.
    # Defaults to false for safety in production.
    INIT_SEED: bool = os.getenv("INIT_SEED", "false").lower() == "true"

    # OIDC (Optional)
    OIDC_ENABLED: bool = os.getenv("OIDC_ENABLED", "false").lower() == "true"
    OIDC_ISSUER_URL: str = os.getenv("OIDC_ISSUER_URL", "")
    OIDC_CLIENT_ID: str = os.getenv("OIDC_CLIENT_ID", "")

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

    @property
    def tomtom_configured(self) -> bool:
        return bool(self.TOMTOM_API_KEY)


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

    if not settings.tomtom_configured:
        # Warning only: traffic data falls back to synthetic values without it.
        sys.stderr.write(
            "WARNING: TOMTOM_API_KEY is not configured. Package ETAs and "
            "traffic conditions will use synthetic placeholder data instead "
            "of real traffic. Set TOMTOM_API_KEY to enable real traffic data.\n"
        )

    if _problems:
        sys.stderr.write(
            "FATAL: refusing to start in production with unsafe settings:\n"
        )
        for _p in _problems:
            sys.stderr.write("  - " + _p + "\n")
        sys.exit(1)
