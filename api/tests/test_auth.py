"""Smoke tests del router /auth y del middleware Bearer."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from jose import jwt


def test_login_returns_token(client):
    resp = client.post("/auth/login", json={"username": "demo", "password": "demo"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body and isinstance(body["token"], str)
    assert "expires_at" in body


def test_login_any_credentials_valid(client):
    """`00 §18`: cualquier `{username, password}` es válido en MVP."""
    resp = client.post("/auth/login", json={"username": "x", "password": "y"})
    assert resp.status_code == 200


def test_me_with_valid_token(auth_client):
    resp = auth_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "demo"


def test_me_without_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] in {"token_missing", "token_invalid"}


def test_me_invalid_token(client):
    client.headers.update({"Authorization": "Bearer not-a-real-jwt"})
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "token_invalid"


def test_me_expired_token(client):
    """Token expirado → 401 con `code='token_invalid'`."""
    from api.settings import settings

    past = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {"sub": "demo", "exp": int(past.timestamp())}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    client.headers.update({"Authorization": f"Bearer {token}"})
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "token_invalid"
