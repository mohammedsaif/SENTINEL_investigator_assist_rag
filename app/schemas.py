from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    transaction_id: str


class Action(str, Enum):
    APPROVE = "APPROVE"
    STEP_UP_AUTH = "STEP_UP_AUTH"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW"
    BLOCK = "BLOCK"


class ReasonCode(BaseModel):
    code: str
    description: str
    evidence: str  # the actual value that tripped the rule, e.g. "amount=48210 > 10000"
    source: str  # "features" | "graph"


class Citation(BaseModel):
    document: str
    chunk_id: str
    quote: str = Field(description="Short phrase from the chunk that supports the decision")


class PolicyChunk(BaseModel):
    document: str
    title: str = ""
    chunk_id: str
    text: str
    score: float


class ExplainResponse(BaseModel):
    transaction_id: str
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    risk_summary: str
    reason_codes: list[ReasonCode]
    recommended_action: Action
    action_rationale: str
    cited_sources: list[Citation]
    context_gaps: list[str] = []  # data sources that failed or were empty
    debug: dict[str, Any] = {}  # retrieved chunk ids, model, latency
