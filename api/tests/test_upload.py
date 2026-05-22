"""Smoke tests del router /upload (validaciones de extensión, tamaño, idempotencia)."""

from __future__ import annotations


def test_upload_valid_txt(auth_client, tsv_path):
    with tsv_path.open("rb") as f:
        resp = auth_client.post(
            "/upload",
            files={"file": ("sample.txt", f, "text/plain")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "file_id" in body
    assert "validation_summary" in body
    assert body["already_processed"] is False
    assert body["validation_summary"]["rows_new"] == 5


def test_upload_duplicate_returns_already_processed(auth_client, tsv_path):
    """Segundo upload del mismo archivo → `already_processed=True` (`01 §8`)."""
    with tsv_path.open("rb") as f:
        first = auth_client.post(
            "/upload", files={"file": ("sample.txt", f, "text/plain")}
        )
    assert first.status_code == 200
    with tsv_path.open("rb") as f:
        second = auth_client.post(
            "/upload", files={"file": ("sample.txt", f, "text/plain")}
        )
    assert second.status_code == 200
    assert second.json()["already_processed"] is True
    assert second.json()["file_id"] == first.json()["file_id"]


def test_upload_invalid_extension(auth_client, tmp_path):
    bad = tmp_path / "evil.exe"
    bad.write_bytes(b"not a real binary, just bytes")
    with bad.open("rb") as f:
        resp = auth_client.post(
            "/upload",
            files={"file": ("evil.exe", f, "application/octet-stream")},
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_extension"


def test_upload_file_too_large(auth_client, tmp_path):
    """Stream > 50 MB → 400 con `code='file_too_large'`."""
    big = tmp_path / "big.txt"
    chunk = b"X" * (1024 * 1024)  # 1 MB
    with big.open("wb") as f:
        for _ in range(51):
            f.write(chunk)
    with big.open("rb") as f:
        resp = auth_client.post(
            "/upload", files={"file": ("big.txt", f, "text/plain")}
        )
    assert resp.status_code == 400
    assert resp.json()["code"] == "file_too_large"


def test_upload_status_done(auth_client, tsv_path):
    with tsv_path.open("rb") as f:
        resp = auth_client.post(
            "/upload", files={"file": ("sample.txt", f, "text/plain")}
        )
    file_id = resp.json()["file_id"]
    status_resp = auth_client.get(f"/upload/{file_id}/status")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "done"
    assert body["file_id"] == file_id


def test_upload_status_unknown_file(auth_client):
    resp = auth_client.get("/upload/9999/status")
    assert resp.status_code == 404
    assert resp.json()["code"] == "file_not_found"


def test_upload_requires_auth(client, tsv_path):
    with tsv_path.open("rb") as f:
        resp = client.post(
            "/upload", files={"file": ("sample.txt", f, "text/plain")}
        )
    assert resp.status_code == 401
