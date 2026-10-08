import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.backend.services.auth import AuthService

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_valid_key_is_accepted():
    svc = AuthService(api_key="correct-key")
    assert await svc.validate_device_token(api_key="correct-key") is True


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, "", "wrong-key", "dev-secret-key-123"])
async def test_invalid_or_missing_token_is_rejected(token):
    svc = AuthService(api_key="correct-key")
    with pytest.raises(HTTPException) as exc_info:
        await svc.validate_device_token(api_key=token)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("token", [None, "", "dev-secret-key-123"])
async def test_unconfigured_key_rejects_everything(token):
    """With DIAD_API_KEY unset there is no fallback key to guess."""
    svc = AuthService(api_key="")
    with pytest.raises(HTTPException):
        await svc.validate_device_token(api_key=token)


def _start_production_config(diad_api_key: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "ENVIRONMENT": "production",
        "SECRET_KEY": "x" * 64,
        "BACKEND_CORS_ORIGINS": "https://dashboard.example.com",
        "DATABASE_URL": "postgresql://u:p@localhost/db",
        "DIAD_API_KEY": diad_api_key,
    }
    return subprocess.run(
        [sys.executable, "-c", "import src.backend.core.config"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("diad_api_key", ["", "dev-secret-key-123"])
def test_production_refuses_to_start_without_strong_device_key(diad_api_key):
    result = _start_production_config(diad_api_key)
    assert result.returncode == 1
    assert "DIAD_API_KEY must be set" in result.stderr


def test_production_starts_with_device_key():
    result = _start_production_config("a" * 64)
    assert result.returncode == 0, result.stderr
