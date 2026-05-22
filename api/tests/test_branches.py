"""Smoke tests del router /branches (11 endpoints + búsqueda)."""

from __future__ import annotations


def test_branches_search(seeded_client):
    resp = seeded_client.get("/branches", params={"q": "A-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert all(b["branch_id"].startswith("A-1") for b in body)


def test_branches_search_no_filter(seeded_client):
    resp = seeded_client.get("/branches")
    assert resp.status_code == 200
    body = resp.json()
    branch_ids = {b["branch_id"] for b in body}
    assert {"A-101", "A-102", "A-103"} <= branch_ids


def test_branch_ytd_unknown(seeded_client):
    resp = seeded_client.get("/branches/A-9999/ytd")
    assert resp.status_code == 404
    assert resp.json()["code"] == "branch_not_found"


def test_branch_ytd_known(seeded_client):
    resp = seeded_client.get("/branches/A-101/ytd")
    assert resp.status_code == 200
    body = resp.json()
    expected = {
        "branch_id",
        "nps",
        "trend",
        "causes",
        "strengths",
        "actions",
        "insights",
        "top_words",
        "representatives",
        "personnel",
    }
    assert expected.issubset(body.keys())
    assert body["branch_id"] == "A-101"


def test_branch_trend(seeded_client):
    resp = seeded_client.get("/branches/A-101/trend")
    assert resp.status_code == 200
    assert "points" in resp.json()


def test_branch_causes(seeded_client):
    resp = seeded_client.get("/branches/A-101/causes")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_strengths(seeded_client):
    resp = seeded_client.get("/branches/A-101/strengths")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_words(seeded_client):
    resp = seeded_client.get("/branches/A-101/words", params={"top_n": 10})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_representatives(seeded_client):
    resp = seeded_client.get("/branches/A-101/representatives", params={"n_per_topic": 1})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_personnel(seeded_client):
    resp = seeded_client.get("/branches/A-101/personnel")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_actions(seeded_client):
    resp = seeded_client.get("/branches/A-101/actions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_insights(seeded_client):
    resp = seeded_client.get("/branches/A-101/insights")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_branch_compare(seeded_client):
    resp = seeded_client.get(
        "/branches/A-101/compare", params={"month_a": "2026-01", "month_b": "2026-02"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["month_a"] == "2026-01"


def test_branch_ytd_requires_auth(client):
    resp = client.get("/branches/A-101/ytd")
    assert resp.status_code == 401
