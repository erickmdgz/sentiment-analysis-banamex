"""Healthz no requiere auth."""

from __future__ import annotations


def test_healthz_no_auth(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "db_path" in body
    assert "classifier_loaded" in body
