"""Tests for auth utilities."""
import pytest

from src.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_round_trip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_type():
    token = create_access_token("user-id-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == "access"


def test_refresh_token_type():
    token = create_refresh_token("user-id-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-456"
    assert payload["type"] == "refresh"


def test_access_and_refresh_are_different():
    access = create_access_token("u1")
    refresh = create_refresh_token("u1")
    assert access != refresh
