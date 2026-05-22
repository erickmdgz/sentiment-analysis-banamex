"""Configuración de la API (lee `.env` con pydantic-settings).

Referencias: 00_decisiones_tecnicas.md §18 (auth JWT), §25 (logging),
Anexo A (variables de entorno), 06_M4_api.md (Settings).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_secret: str = "demo-secret-change-in-prod"
    jwt_expiration_hours: int = 24
    database_url: str = "sqlite:///./data/processed/banamex.db"
    api_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

__all__ = ["Settings", "settings"]
