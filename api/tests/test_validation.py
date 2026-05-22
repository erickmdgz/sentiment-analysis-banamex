"""Smoke tests del router /validation."""

from __future__ import annotations


def test_validation_summary(seeded_client):
    resp = seeded_client.get("/validation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["files_processed"] == 1
    assert body["branches_detected"] == 3
    assert body["rows_loaded"] > 0
    assert "months_available" in body and len(body["months_available"]) > 0
    assert set(body["columns_detected"]) >= {
        "record_id",
        "response_date",
        "nps_group",
        "nps_rate",
        "verbatim",
        "branch_id",
    }


def test_validation_coverage(seeded_client):
    resp = seeded_client.get("/validation/coverage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["branches_detected"] == 3
    assert body["branches_with_target"] == 3
    assert body["branches_without_target"] == []
