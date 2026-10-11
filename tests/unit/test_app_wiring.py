"""Guards for app-level setup that a rewrite of main.py silently dropped once."""
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.backend.api.main import app
from src.backend.core.config import settings


def _middleware(cls):
    return next((m for m in app.user_middleware if m.cls is cls), None)


def test_rate_limit_exceeded_returns_429_not_500():
    assert app.state.limiter is not None
    assert RateLimitExceeded in app.exception_handlers


def test_session_middleware_installed_for_oidc():
    assert _middleware(SessionMiddleware) is not None


def test_cors_uses_validated_backend_cors_origins():
    cors = _middleware(CORSMiddleware)
    assert cors.kwargs["allow_origins"] == settings.BACKEND_CORS_ORIGINS
    assert "*" not in cors.kwargs["allow_origins"]


def test_metrics_endpoint_exposed():
    assert TestClient(app).get("/metrics").status_code == 200
