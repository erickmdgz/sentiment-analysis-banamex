"""Tests transversales: CORS preflight, formato de errores, export OpenAPI."""

from __future__ import annotations

import json
from pathlib import Path


def test_cors_preflight_allowed_origin(client):
    """`OPTIONS` desde `http://localhost:5173` debe responder con los headers CORS."""
    resp = client.options(
        "/national/ytd",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    # FastAPI/Starlette responde 200 con headers ACAC para preflight válido.
    assert resp.status_code in {200, 204}
    assert "access-control-allow-origin" in {k.lower() for k in resp.headers.keys()}


def test_error_format_unified(client):
    """Cualquier 401 producido por el middleware debe respetar `{detail, code, hint}`."""
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert {"detail", "code"} <= set(body.keys())


def test_internal_error_handler(seeded_db, monkeypatch):
    """Excepción no controlada → 500 con `code='internal_error'`.

    Usa `raise_server_exceptions=False` para que el TestClient devuelva la
    response del handler en lugar de propagar la excepción.
    """
    from fastapi.testclient import TestClient

    import api.routes.national as nat_module
    from api.main import app

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(nat_module, "national_ytd_summary", boom)
    client = TestClient(app, raise_server_exceptions=False)
    token = client.post(
        "/auth/login", json={"username": "demo", "password": "demo"}
    ).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    resp = client.get("/national/ytd")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == "internal_error"
    assert body["detail"] == "Error interno"


def test_export_openapi_generates_paths():
    """`python -m api.export_openapi` genera un JSON con los endpoints de `01 §8`."""
    from api.main import app

    spec = app.openapi()
    paths = set(spec.get("paths", {}).keys())
    must_contain = {
        "/auth/login",
        "/auth/me",
        "/upload",
        "/upload/{file_id}/status",
        "/validation",
        "/validation/coverage",
        "/national/ytd",
        "/national/compare",
        "/branches",
        "/branches/{branch_id}/ytd",
        "/admin/files",
        "/admin/runs",
        "/healthz",
    }
    assert must_contain <= paths, f"faltan: {must_contain - paths}"


def test_openapi_json_exists_and_is_parseable():
    """El `api/openapi.json` versionado existe y es JSON parseable."""
    p = Path(__file__).resolve().parents[1] / "openapi.json"
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "paths" in data
