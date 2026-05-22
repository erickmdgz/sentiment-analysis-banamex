"""Smoke tests del router /admin (solo lectura)."""

from __future__ import annotations


def test_admin_files(seeded_client):
    resp = seeded_client.get("/admin/files")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["filename"] == "seed.txt"


def test_admin_runs(seeded_client):
    resp = seeded_client.get("/admin/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert "annotation_runs" in body
    assert "classifier_runs" in body
    assert body["annotation_runs"] == []
    assert body["classifier_runs"] == []


def test_admin_requires_auth(client):
    resp = client.get("/admin/files")
    assert resp.status_code == 401
