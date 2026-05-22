"""Smoke tests del router /national (11 endpoints)."""

from __future__ import annotations


def test_national_ytd_structure(seeded_client):
    resp = seeded_client.get("/national/ytd")
    assert resp.status_code == 200
    body = resp.json()
    expected_keys = {
        "nps",
        "trend",
        "causes",
        "strengths",
        "critical_branches",
        "rankings",
        "actions",
        "impact",
        "insights",
        "branches_total",
        "branches_with_target",
    }
    assert expected_keys.issubset(body.keys())
    assert body["branches_total"] == 3
    assert body["branches_with_target"] == 3


def test_national_trend(seeded_client):
    resp = seeded_client.get("/national/trend")
    assert resp.status_code == 200
    assert "points" in resp.json()


def test_national_compare_valid(seeded_client):
    resp = seeded_client.get(
        "/national/compare", params={"month_a": "2026-01", "month_b": "2026-02"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["month_a"] == "2026-01"
    assert body["month_b"] == "2026-02"


def test_national_compare_month_inexistente(seeded_client):
    """Mes fuera del rango → 422 (`ValueError` desde M3)."""
    resp = seeded_client.get(
        "/national/compare", params={"month_a": "2030-01", "month_b": "2026-02"}
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] in {"invalid_argument", "validation_error"}


def test_national_compare_formato_invalido(seeded_client):
    """Formato no `YYYY-MM` → 422."""
    resp = seeded_client.get(
        "/national/compare", params={"month_a": "abril", "month_b": "2026-02"}
    )
    assert resp.status_code == 422


def test_national_critical_branches(seeded_client):
    resp = seeded_client.get("/national/critical-branches", params={"limit": 5})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_national_rankings(seeded_client):
    resp = seeded_client.get("/national/rankings")
    assert resp.status_code == 200
    body = resp.json()
    for k in ("worst_nps", "worst_gap", "most_detractors", "worsened", "improved"):
        assert k in body


def test_national_causes(seeded_client):
    resp = seeded_client.get("/national/causes", params={"group": "Detractor"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_national_strengths(seeded_client):
    resp = seeded_client.get("/national/strengths")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_national_actions(seeded_client):
    resp = seeded_client.get("/national/actions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_national_impact(seeded_client):
    resp = seeded_client.get("/national/impact")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_national_insights(seeded_client):
    resp = seeded_client.get("/national/insights")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_national_passive_analysis(seeded_client):
    resp = seeded_client.get("/national/passive-analysis")
    assert resp.status_code == 200
    body = resp.json()
    assert "near_promoter" in body
    assert "near_detractor" in body


def test_national_ytd_requires_auth(client):
    resp = client.get("/national/ytd")
    assert resp.status_code == 401
