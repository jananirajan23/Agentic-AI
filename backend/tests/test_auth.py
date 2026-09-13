"""Unit tests for auth.py password hashing and JWT helpers."""

import jwt as pyjwt
import pytest

import config
from auth import create_access_token, hash_password, verify_password


class _FakeUser:
    def __init__(self, id_="u1", email="a@b.com"):
        self.id = id_
        self.email = email


def test_hash_password_is_salted_and_not_plaintext():
    h1 = hash_password("correct horse battery staple")
    h2 = hash_password("correct horse battery staple")
    assert h1 != h2  # different random salt each time
    assert "correct horse battery staple" not in h1


def test_verify_password_round_trip():
    stored = hash_password("my-secret-password")
    assert verify_password("my-secret-password", stored) is True
    assert verify_password("wrong-password", stored) is False


def test_verify_password_rejects_malformed_hash():
    assert verify_password("anything", "not-a-valid-hash") is False


def test_create_access_token_round_trips_claims():
    user = _FakeUser(id_="user-123", email="prof@example.edu")
    token = create_access_token(user)
    payload = pyjwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    assert payload["sub"] == "user-123"
    assert payload["email"] == "prof@example.edu"


def test_expired_or_tampered_token_fails_decode():
    user = _FakeUser()
    token = create_access_token(user)
    with pytest.raises(pyjwt.PyJWTError):
        pyjwt.decode(token + "tampered", config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
