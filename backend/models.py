# ================================================
# Pydantic models — request/response shapes
# ================================================
from pydantic import BaseModel
from typing import Optional, List


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class AskRequest(BaseModel):
    question: str
    employee_type: Optional[str] = ""
    issue_category: Optional[str] = ""
    anonymous: Optional[bool] = False


class AskResponse(BaseModel):
    decision: str
    answer: str
    reasoning: Optional[str] = ""
    citation: Optional[str] = ""
    confidence: Optional[str] = ""
    top_score: Optional[float] = 0.0
    latency: Optional[float] = 0.0
    conflict_clause_a: Optional[str] = ""
    conflict_clause_b: Optional[str] = ""
    clarification_question: Optional[str] = ""
    session_id: Optional[str] = ""


class DocumentInfo(BaseModel):
    filename: str
    chunks: int
    path: Optional[str] = ""


class HealthScoreResponse(BaseModel):
    score: int
    grade: str
    color: str
    coverage_score: int
    freshness_score: int
    consistency_score: int
    insights: List[str]
    gaps: List[str]
    covered: List[str]
