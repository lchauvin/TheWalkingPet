"""Token and password handling."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError

from src.utils.security import (
    BCRYPT_MAX_BYTES,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip():
    hashed = hash_password("correct horse battery")
    assert verify_password("correct horse battery", hashed)
    assert not verify_password("wrong", hashed)


def test_password_over_bcrypt_limit_is_rejected():
    with pytest.raises(ValueError):
        hash_password("a" * (BCRYPT_MAX_BYTES + 1))


def test_overlong_password_never_verifies():
    # bcrypt truncates at 72 bytes: a longer string must not authenticate
    # against the hash of its own prefix.
    hashed = hash_password("a" * BCRYPT_MAX_BYTES)
    assert not verify_password("a" * (BCRYPT_MAX_BYTES + 1), hashed)


def test_access_token_carries_type_and_jti():
    payload = decode_token(create_access_token("user-123"))
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert uuid.UUID(payload["jti"])


def test_refresh_token_carries_supplied_jti():
    jti = uuid.uuid4()
    token, expires_at = create_refresh_token("user-456", jti)
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["jti"] == str(jti)
    assert expires_at > datetime.now(timezone.utc)


def test_tokens_of_different_types_differ():
    assert create_access_token("u1") != create_refresh_token("u1", uuid.uuid4())[0]


def test_tampered_token_is_rejected():
    token = create_access_token("u1")
    with pytest.raises(JWTError):
        decode_token(token[:-2] + ("aa" if not token.endswith("aa") else "bb"))


def test_expired_token_is_rejected(monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    with pytest.raises(JWTError):
        decode_token(create_access_token("u1"))
