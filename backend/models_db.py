"""
SQLAlchemy ORM models for the auth + dashboard layer.

Two tables:
  - User: a faculty/reviewer account (email + password hash).
  - ReviewJob: one uploaded report's full pipeline run, owned by a User.
    Doubles as both the async-job record (status/stage/error, polled by
    the frontend while the LangGraph pipeline runs) and the persisted
    review result + faculty-approval state once it finishes.
"""

import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    # Single role today ("faculty") — kept as a column rather than a bare
    # assumption so a "coordinator" or "admin" role can be added later
    # (Ch.3.2 of the requirements lists several stakeholder roles) without
    # a schema migration.
    role = Column(String, nullable=False, default="faculty")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    reviews = relationship(
        "ReviewJob", back_populates="owner", foreign_keys="ReviewJob.user_id"
    )


class ReviewJob(Base):
    __tablename__ = "review_jobs"

    id = Column(String, primary_key=True)  # == job_id == report_id
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)

    # processing -> done -> approved, or processing -> error
    status = Column(String, nullable=False, default="processing")
    stage = Column(String, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    composite_score = Column(Float, default=0)
    literature_score = Column(Float, default=0)
    architecture_score = Column(Float, default=0)
    alignment_score = Column(Float, default=0)
    # Deterministic, non-LLM measurements (Ch.9.4/Ch.11.1 of the
    # requirements) — kept alongside the LLM-blended scores above so the
    # final approved report can quote them even after approval.
    citation_resolution_rate = Column(Float, default=0)
    embedding_alignment_score = Column(Float, default=0)

    literature_flags = Column(JSON, default=list)
    architecture_flags = Column(JSON, default=list)
    alignment_flags = Column(JSON, default=list)
    parse_warnings = Column(JSON, default=list)
    research_gap_summary = Column(Text, default="")

    # Editable-by-faculty items: [{"text": str, "source": str, "included": bool}]
    all_flags = Column(JSON, default=list)
    # [{"text": str, "included": bool}]
    suggestions = Column(JSON, default=list)

    # AI-draft report, generated as soon as the pipeline finishes.
    report_path = Column(String, nullable=True)
    # Faculty-approved report, generated only after /approve — this is the
    # one meant to reach students (Ch.3.3 / Ch.4.1 human-in-the-loop
    # requirement: AI findings must not become final feedback on their own).
    final_report_path = Column(String, nullable=True)

    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="reviews", foreign_keys=[user_id])
