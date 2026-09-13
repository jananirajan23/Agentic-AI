"""
End-to-end integration tests against the FastAPI app (Ch.11.2:
"Integration Testing... PDF Upload -> Extraction -> Literature Agent ->
Aggregator" and "End-to-End Testing... complete workflow... from report
upload through final report generation").

Runs with GROQ_API_KEY forced empty (see conftest.py) so this is fast,
free, and deterministic — LLM-dependent sub-scores come back as 0 with an
explanatory flag rather than crashing, exactly as documented in the
project README's "Validation performed" section. OCR and the local
embedding model still run for real (no network/API key needed for
either), so the architecture/alignment pipeline is genuinely exercised.
"""

import io
import os

from tests.make_dummy_report import build_dummy_pdf


def _upload_dummy_report(client, headers, tmp_path):
    pdf_path = os.path.join(tmp_path, "dummy.pdf")
    build_dummy_pdf(pdf_path)
    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/api/review",
            headers=headers,
            files={"file": ("dummy.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200, resp.text
    return resp.json()["job_id"]


def test_register_then_login(client):
    reg = client.post(
        "/api/auth/register",
        json={"name": "Prof A", "email": "profa@example.edu", "password": "password123"},
    )
    assert reg.status_code == 200
    assert reg.json()["user"]["email"] == "profa@example.edu"

    login = client.post("/api/auth/login", json={"email": "profa@example.edu", "password": "password123"})
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Prof A", "email": "dup@example.edu", "password": "password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 200
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={"name": "Prof A", "email": "wrongpass@example.edu", "password": "password123"},
    )
    resp = client.post("/api/auth/login", json={"email": "wrongpass@example.edu", "password": "nope"})
    assert resp.status_code == 401


def test_review_endpoints_require_auth(client):
    assert client.get("/api/reviews").status_code == 401
    assert client.post("/api/review", files={"file": ("x.pdf", b"", "application/pdf")}).status_code == 401


def test_only_pdf_files_accepted(client, auth_headers):
    resp = client.post(
        "/api/review",
        headers=auth_headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_full_review_pipeline_and_dashboard(client, auth_headers, tmp_path):
    job_id = _upload_dummy_report(client, auth_headers, tmp_path)

    status = client.get(f"/api/review/{job_id}/status", headers=auth_headers)
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "done"
    assert body["result"]["composite_score"] is not None

    # Dashboard should list the job.
    listing = client.get("/api/reviews", headers=auth_headers)
    assert listing.status_code == 200
    ids = [r["id"] for r in listing.json()]
    assert job_id in ids

    detail = client.get(f"/api/review/{job_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "done"
    assert detail.json()["report_ready"] is True
    assert detail.json()["final_report_ready"] is False


def test_review_belongs_to_owner_only(client, tmp_path):
    r1 = client.post(
        "/api/auth/register", json={"name": "A", "email": "a@example.edu", "password": "password123"}
    )
    r2 = client.post(
        "/api/auth/register", json={"name": "B", "email": "b@example.edu", "password": "password123"}
    )
    headers_a = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    headers_b = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    job_id = _upload_dummy_report(client, headers_a, tmp_path)

    # B cannot see A's review.
    assert client.get(f"/api/review/{job_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/review/{job_id}/status", headers=headers_b).status_code == 404


def test_approve_flow_filters_excluded_items_and_generates_final_report(client, auth_headers, tmp_path):
    job_id = _upload_dummy_report(client, auth_headers, tmp_path)

    detail = client.get(f"/api/review/{job_id}", headers=auth_headers).json()
    all_flags = detail["all_flags"]
    suggestions = detail["suggestions"]
    assert len(all_flags) >= 1

    # Exclude the first flag, keep the rest; keep all suggestions.
    for f in all_flags:
        f["included"] = False
    if all_flags:
        all_flags[0]["included"] = True

    approve = client.post(
        f"/api/review/{job_id}/approve",
        headers=auth_headers,
        json={
            "all_flags": all_flags,
            "suggestions": suggestions,
            "research_gap_summary": "Edited by faculty.",
        },
    )
    assert approve.status_code == 200, approve.text
    approved = approve.json()
    assert approved["status"] == "approved"
    assert approved["final_report_ready"] is True
    assert approved["research_gap_summary"] == "Edited by faculty."

    download = client.get(f"/api/report/{job_id}", headers=auth_headers)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert b"PK" == download.content[:2]  # .docx is a zip archive


def test_approve_before_processing_done_is_rejected(client, auth_headers):
    # A job id that was never created should 404, not 400/500.
    resp = client.post(
        "/api/review/does-not-exist/approve",
        headers=auth_headers,
        json={"all_flags": [], "suggestions": [], "research_gap_summary": ""},
    )
    assert resp.status_code == 404
