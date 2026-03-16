"""
Unit tests for JWT / password-hashing utilities.
These are pure-function tests — no DB or HTTP required.
"""
import pytest
from datetime import timedelta
from jose import jwt

from src.backend.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from src.backend.core.config import settings


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = get_password_hash("secret123")
        assert hashed != "secret123"

    def test_correct_password_verifies(self):
        hashed = get_password_hash("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_wrong_password_fails(self):
        hashed = get_password_hash("rightpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_does_not_match_non_empty_hash(self):
        hashed = get_password_hash("notempty")
        assert verify_password("", hashed) is False


class TestJWT:
    def test_token_contains_subject_and_role(self):
        token = create_access_token(subject="alice", role="driver", expires_delta=timedelta(hours=1))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "alice"
        assert payload["role"] == "driver"

    def test_token_expires_is_set(self):
        token = create_access_token(subject="bob", role="manager", expires_delta=timedelta(minutes=10))
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_expired_token_raises(self):
        from jose import ExpiredSignatureError
        token = create_access_token(subject="carol", role="driver", expires_delta=timedelta(seconds=-1))
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def test_tampered_token_raises(self):
        from jose import JWTError
        token = create_access_token(subject="dave", role="admin", expires_delta=timedelta(hours=1))
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            jwt.decode(tampered, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
