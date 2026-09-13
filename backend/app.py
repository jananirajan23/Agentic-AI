"""
Reviewer-Lens FastAPI application.

Implements job-polling rather than a synchronous request/response for
POST /api/review: the pipeline runs several LLM + vision calls and can
take a while, so the frontend polls a status endpoint and can show real
per-stage progress instead of a bare spinner.

Every review job is owned by a logged-in faculty account and persisted in
SQLite (see database.py / models_db.py) rather than kept in an in-memory
dict — that's what makes GET /api/reviews (the dashboard) and the
faculty-approval workflow (POST /api/review/{id}/approve) possible across
backend restarts and multiple reviewers.
"""

import os
import shutil
import uuid
from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import config
import models_db as models
import schemas
from auth import create_access_token, get_current_user, hash_password, verify_password
from database import SessionLocal, get_db, init_db
from graph import build_graph

app = FastAPI(title="Reviewer-Lens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup():
    init_db()


NODE_TO_STAGE = {
    "parse": "parsing",
    "literature": "literature",
    "architecture": "architecture",
    "alignment": "alignment",
    "aggregate": "aggregating",
}


def _collect_tagged_flags(state: dict) -> list:
    tagged = []
    for f in state.get("parse_warnings") or []:
        tagged.append({"text": f, "source": "parsing", "included": True})
    for f in state.get("literature_flags") or []:
        tagged.append({"text": f, "source": "literature", "included": True})
    for f in state.get("architecture_flags") or []:
        tagged.append({"text": f, "source": "architecture", "included": True})
    for f in state.get("alignment_flags") or []:
        tagged.append({"text": f, "source": "alignment", "included": True})
    return tagged


def _run_review_job(job_id: str, pdf_path: str):
    """Runs in a BackgroundTasks thread, outside any request's DB session
    — opens its own SessionLocal() and always closes it."""
    output_path = os.path.join(config.REPORTS_DIR, f"{job_id}.docx")
    db: Session = SessionLocal()
    try:
        job = db.get(models.ReviewJob, job_id)
        if job is None:
            return

        graph = build_graph(output_path)
        final_state: dict = {}

        for step in graph.stream({"pdf_path": pdf_path}, stream_mode="updates"):
            for node_name, node_output in step.items():
                final_state.update(node_output or {})
                stage = NODE_TO_STAGE.get(node_name)
                if stage:
                    job.stage = stage
                    db.commit()

        job.status = "done"
        job.stage = None
        job.composite_score = final_state.get("composite_score", 0)
        job.literature_score = final_state.get("literature_score", 0)
        job.architecture_score = final_state.get("architecture_score", 0)
        job.alignment_score = final_state.get("alignment_score", 0)
        job.citation_resolution_rate = final_state.get("citation_resolution_rate", 0)
        job.embedding_alignment_score = final_state.get("embedding_alignment_score", 0)
        job.literature_flags = final_state.get("literature_flags", [])
        job.architecture_flags = final_state.get("architecture_flags", [])
        job.alignment_flags = final_state.get("alignment_flags", [])
        job.parse_warnings = final_state.get("parse_warnings", [])
        job.research_gap_summary = final_state.get("research_gap_summary", "")
        job.all_flags = _collect_tagged_flags(final_state)
        job.suggestions = [{"text": s, "included": True} for s in final_state.get("suggestions", [])]
        job.report_path = final_state.get("report_path", output_path)
        db.commit()
    except Exception as e:
        job = db.get(models.ReviewJob, job_id)
        if job is not None:
            job.status = "error"
            job.stage = None
            job.error = str(e)
            db.commit()
    finally:
        db.close()


# --- Auth ---------------------------------------------------------------


def _is_valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[-1] and len(email) <= 200


@app.post("/api/auth/register", response_model=schemas.TokenResponse)
async def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if not _is_valid_email(payload.email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = models.User(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return {"access_token": token, "user": _user_out(user)}


@app.post("/api/auth/login", response_model=schemas.TokenResponse)
async def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower().strip()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = create_access_token(user)
    return {"access_token": token, "user": _user_out(user)}


@app.get("/api/auth/me", response_model=schemas.UserOut)
async def me(current_user: models.User = Depends(get_current_user)):
    return _user_out(current_user)


def _user_out(user: models.User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


# --- Review pipeline ------------------------------------------------------


@app.post("/api/review")
async def start_review(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    job_id = uuid.uuid4().hex
    pdf_path = os.path.join(config.UPLOAD_DIR, f"{job_id}.pdf")

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = models.ReviewJob(
        id=job_id,
        user_id=current_user.id,
        filename=file.filename,
        status="processing",
        stage="parsing",
    )
    db.add(job)
    db.commit()

    background_tasks.add_task(_run_review_job, job_id, pdf_path)

    return {"job_id": job_id}


def _get_owned_job(job_id: str, current_user: models.User, db: Session) -> models.ReviewJob:
    job = db.get(models.ReviewJob, job_id)
    if job is None or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    return job


@app.get("/api/review/{job_id}/status")
async def review_status(
    job_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)
    result = None
    if job.status in ("done", "approved"):
        result = _job_to_result(job)
    return {
        "status": job.status,
        "stage": job.stage,
        "result": result,
        "error": job.error,
    }


def _job_to_result(job: models.ReviewJob) -> dict:
    return {
        "report_id": job.id,
        "composite_score": job.composite_score,
        "literature_score": job.literature_score,
        "architecture_score": job.architecture_score,
        "alignment_score": job.alignment_score,
        "citation_resolution_rate": job.citation_resolution_rate or 0,
        "embedding_alignment_score": job.embedding_alignment_score or 0,
        "all_flags": [f["text"] for f in (job.all_flags or [])],
        "literature_flags": job.literature_flags or [],
        "architecture_flags": job.architecture_flags or [],
        "alignment_flags": job.alignment_flags or [],
        "suggestions": [s["text"] for s in (job.suggestions or [])],
        "parse_warnings": job.parse_warnings or [],
        "research_gap_summary": job.research_gap_summary or "",
    }


@app.get("/api/reviews", response_model=list[schemas.ReviewSummary])
async def list_reviews(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = (
        db.query(models.ReviewJob)
        .filter(models.ReviewJob.user_id == current_user.id)
        .order_by(models.ReviewJob.created_at.desc())
        .all()
    )
    return [_job_to_summary(j) for j in jobs]


def _job_to_summary(job: models.ReviewJob) -> dict:
    return {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "stage": job.stage,
        "composite_score": job.composite_score or 0,
        "created_at": job.created_at.isoformat() if job.created_at else "",
        "approved_at": job.approved_at.isoformat() if job.approved_at else None,
    }


@app.get("/api/review/{job_id}", response_model=schemas.ReviewDetail)
async def get_review_detail(
    job_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)
    approver_name = None
    if job.approved_by:
        approver = db.get(models.User, job.approved_by)
        approver_name = approver.name if approver else None

    return {
        **_job_to_summary(job),
        "error": job.error,
        "literature_score": job.literature_score or 0,
        "architecture_score": job.architecture_score or 0,
        "alignment_score": job.alignment_score or 0,
        "citation_resolution_rate": job.citation_resolution_rate or 0,
        "embedding_alignment_score": job.embedding_alignment_score or 0,
        "literature_flags": job.literature_flags or [],
        "architecture_flags": job.architecture_flags or [],
        "alignment_flags": job.alignment_flags or [],
        "parse_warnings": job.parse_warnings or [],
        "research_gap_summary": job.research_gap_summary or "",
        "all_flags": job.all_flags or [],
        "suggestions": job.suggestions or [],
        "report_ready": bool(job.report_path),
        "final_report_ready": bool(job.final_report_path),
        "approved_by_name": approver_name,
    }


@app.post("/api/review/{job_id}/approve", response_model=schemas.ReviewDetail)
async def approve_review(
    job_id: str,
    payload: schemas.ApproveRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(job_id, current_user, db)
    if job.status not in ("done", "approved"):
        raise HTTPException(
            status_code=400,
            detail=f"This review is not ready to approve yet (status: {job.status}).",
        )

    job.all_flags = [f.model_dump() for f in payload.all_flags]
    job.suggestions = [s.model_dump() for s in payload.suggestions]
    job.research_gap_summary = payload.research_gap_summary

    included_flags = [f.text for f in payload.all_flags if f.included]
    included_suggestions = [s.text for s in payload.suggestions if s.included]

    approved_at = datetime.utcnow()
    final_path = os.path.join(config.REPORTS_DIR, f"{job_id}_final.docx")

    state = {
        "composite_score": job.composite_score,
        "literature_score": job.literature_score,
        "architecture_score": job.architecture_score,
        "alignment_score": job.alignment_score,
        "citation_resolution_rate": job.citation_resolution_rate,
        "embedding_alignment_score": job.embedding_alignment_score,
    }

    from agents.report_aggregator import build_final_report

    build_final_report(
        state,
        final_path,
        included_flags,
        included_suggestions,
        payload.research_gap_summary,
        approved_by=current_user.name,
        approved_at=approved_at.strftime("%Y-%m-%d %H:%M UTC"),
    )

    job.final_report_path = final_path
    job.approved_at = approved_at
    job.approved_by = current_user.id
    job.status = "approved"
    db.commit()

    return await get_review_detail(job_id, current_user, db)


@app.get("/api/report/{report_id}")
async def download_report(
    report_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _get_owned_job(report_id, current_user, db)

    report_path = job.final_report_path or job.report_path
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found.")

    suffix = "final" if job.final_report_path else "draft"
    return FileResponse(
        report_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"reviewer_lens_{suffix}_{report_id[:8]}.docx",
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "groq_configured": bool(config.GROQ_API_KEY),
    }
