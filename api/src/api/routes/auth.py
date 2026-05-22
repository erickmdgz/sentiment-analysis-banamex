"""Router de autenticación: `/auth/login`, `/auth/me`."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import create_token
from ..deps import get_current_user
from ..models_api import LoginRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """Devuelve un JWT firmado HS256. Cualquier `{username, password}` es válido (`00 §18`)."""
    token, expires_at = create_token(payload.username)
    return TokenResponse(token=token, expires_at=expires_at.isoformat())


@router.get("/me", response_model=UserInfo)
def me(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Devuelve el `username` decodificado del JWT. 401 si el token es inválido."""
    return user
