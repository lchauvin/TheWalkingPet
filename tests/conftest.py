"""Test configuration.

Every test here runs without a database, GPU or network: the aim is that
`pytest` is runnable on a clean checkout, which is what CI needs.
"""
import os

# Must be set before src.config is imported anywhere.
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("PASSWORD_MIN_LENGTH", "10")

import pytest


@pytest.fixture
def storage_tmp(tmp_path, monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    return tmp_path
