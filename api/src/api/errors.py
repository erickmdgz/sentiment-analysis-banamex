"""Handlers globales que producen el formato unificado `{detail, code, hint}`.

Referencias: 01_contratos_compartidos.md §9 (convención de errores), 00 §25
(logging con structlog).
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


def _build_payload(detail: str, code: str, hint: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"detail": detail, "code": code}
    if hint is not None:
        body["hint"] = hint
    return body


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normaliza cualquier `HTTPException` al formato `{detail, code, hint}`.

    Acepta dos variantes en `exc.detail`:
      - `dict` con claves `detail`/`code`/`hint` (preformateado por el handler).
      - `str` plano (envuelto con `code` derivado del status).
    """
    raw = exc.detail
    if isinstance(raw, dict) and "detail" in raw and "code" in raw:
        body = _build_payload(
            detail=str(raw["detail"]),
            code=str(raw["code"]),
            hint=raw.get("hint"),
        )
    else:
        body = _build_payload(
            detail=str(raw) if raw else "Error",
            code=_default_code_for_status(exc.status_code),
        )
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


def _default_code_for_status(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "unauthorized",
        404: "not_found",
        422: "unprocessable_entity",
        500: "internal_error",
    }.get(status_code, f"http_{status_code}")


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 con mensaje legible, sin filtrar la estructura interna de Pydantic."""
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    msg = first.get("msg", "Datos inválidos")
    body = _build_payload(
        detail=f"Validación fallida: {msg}",
        code="validation_error",
        hint=f"campo: {loc}" if loc else None,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """422 para `ValueError` lanzados por la capa de analytics (e.g., mes inexistente)."""
    body = _build_payload(
        detail=str(exc) or "Argumento inválido.",
        code="invalid_argument",
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """500 con detalle genérico; log completo con structlog."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error_message=str(exc),
    )
    body = _build_payload(
        detail="Error interno",
        code="internal_error",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los handlers globales en la app FastAPI."""
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(ValueError, _value_error_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


__all__ = ["register_exception_handlers"]
