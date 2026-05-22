"""Dependencias FastAPI: sesión SQLAlchemy y usuario actual.

Patrón `yield` para `get_db` (cierra la sesión en `finally`). Patrón `Bearer`
para `get_current_user` (decodifica el JWT vía `api.auth.decode_token`).
"""

from __future__ import annotations

from collections.abc import Iterator

from core.db import get_session
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auth import TokenError, decode_token
from .models_api import UserInfo


def get_db() -> Iterator[Session]:
    """Sesión SQLAlchemy por request, cerrada al final."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "detail": "Token ausente.",
                "code": "token_missing",
                "hint": "Incluye 'Authorization: Bearer <token>' en la solicitud.",
            },
        )
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "detail": "Formato de Authorization inválido.",
                "code": "token_invalid",
                "hint": "Usa el esquema 'Bearer <token>'.",
            },
        )
    return parts[1]


def get_current_user(request: Request) -> UserInfo:
    """Decodifica el JWT del header Authorization. 401 si inválido o expirado."""
    token = _extract_bearer(request)
    try:
        payload = decode_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "detail": "Token inválido o expirado.",
                "code": "token_invalid",
                "hint": str(exc),
            },
        ) from exc
    return UserInfo(username=str(payload["sub"]))


CurrentUser = Depends(get_current_user)
DBSession = Depends(get_db)


__all__ = ["CurrentUser", "DBSession", "get_current_user", "get_db"]
