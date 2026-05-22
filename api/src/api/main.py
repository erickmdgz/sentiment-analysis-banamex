"""App FastAPI: registra middlewares, handlers de error y todos los routers.

Referencias: 06_M4_api.md, 00_decisiones_tecnicas.md §18-§19, §25,
01_contratos_compartidos.md §8.
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import register_exception_handlers
from .models_api import HealthResponse
from .routes import admin, auth, branches, national, upload, validation
from .settings import settings


def _configure_logging() -> None:
    """Configura structlog con renderer JSON (`00 §25`)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _classifier_is_loaded() -> bool:
    """Indica si el clasificador supervisado (M2b) está disponible.

    TODO: cuando M2b se mergee, verificar `data/models/classifier.joblib`.
    Mientras tanto, el shim local (`api._classifier_shim`) está siempre disponible.
    """
    return False


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(title="Banamex CX MVP", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth.router)
    app.include_router(upload.router)
    app.include_router(validation.router)
    app.include_router(national.router)
    app.include_router(branches.router)
    app.include_router(admin.router)

    @app.get("/healthz", response_model=HealthResponse, tags=["health"])
    def healthz() -> HealthResponse:
        return HealthResponse(
            status="ok",
            db_path=settings.database_url,
            classifier_loaded=_classifier_is_loaded(),
        )

    return app


app = create_app()


__all__ = ["app", "create_app"]
