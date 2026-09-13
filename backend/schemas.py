"""
Pydantic request/response models for the FastAPI layer.

Plain `str` is used for email fields rather than pydantic's `EmailStr` to
avoid pulling in the extra `email-validator` dependency for what is, for
this app's scope, a single lightweight format check (done in app.py).
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class FlagItem(BaseModel):
    text: str
    source: str = "general"
    included: bool = True


class SuggestionItem(BaseModel):
    text: str
    included: bool = True


class ReviewSummary(BaseModel):
    id: str
    filename: str
    status: str
    stage: Optional[str] = None
    composite_score: float = 0
    created_at: str
    approved_at: Optional[str] = None


class ReviewDetail(ReviewSummary):
    error: Optional[str] = None
    literature_score: float = 0
    architecture_score: float = 0
    alignment_score: float = 0
    citation_resolution_rate: float = 0
    embedding_alignment_score: float = 0
    literature_flags: List[str] = []
    architecture_flags: List[str] = []
    alignment_flags: List[str] = []
    parse_warnings: List[str] = []
    research_gap_summary: str = ""
    all_flags: List[FlagItem] = []
    suggestions: List[SuggestionItem] = []
    report_ready: bool = False
    final_report_ready: bool = False
    approved_by_name: Optional[str] = None


class ApproveRequest(BaseModel):
    all_flags: List[FlagItem]
    suggestions: List[SuggestionItem]
    research_gap_summary: str = ""
