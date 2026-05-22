"""Encode/decode de JWT mock (HS256).

Decisión `00 §18`: cualquier `{username, password}` es válido; el token expira
en `JWT_EXPIRATION_HOURS`. El secreto se lee de `settings.jwt_secret`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from .settings import settings

ALGORITHM = "HS256"


class TokenError(Exception):
    """Token ausente, malformado o expirado."""


def create_token(username: str) -> tuple[str, datetime]:
    """Crea un JWT firmado HS256. Devuelve `(token, expires_at_utc)`."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expires_at


def decode_token(token: str) -> dict:
    """Valida y decodifica un token. Lanza `TokenError` si es inválido."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError(str(exc)) from exc
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise TokenError("token sin 'sub'")
    return payload


__all__ = ["ALGORITHM", "TokenError", "create_token", "decode_token"]
