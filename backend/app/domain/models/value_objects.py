"""
Value objects for the Protocol Amendment Dependency Graph Engine.

Value objects are immutable objects defined by their attributes rather than identity.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """
    Audit trail entry for compliance and traceability (Step 7).

    Every action in the system must be logged for FDA audit requirements.
    """

    id: UUID = Field(default_factory=lambda: UUID(int=0))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    action: str = Field(
        ...,
        description="Action performed (e.g., AMENDMENT_CREATED, IMPACT_ANALYZED)"
    )
    entity_type: str = Field(
        ...,
        description="Type of entity affected"
    )
    entity_id: Optional[UUID] = None
    old_value: Optional[dict[str, Any]] = None
    new_value: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context-specific details"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            UUID: lambda v: str(v) if v else None,
        }


class ValidationResult(BaseModel):
    """
    Result of a validation check on clinical trial assets.

    Used for validation recommendations (Step 9).
    """

    validation_type: str = Field(
        ...,
        description="Type of validation (e.g., SDTM, ADaM, DefineXML)"
    )
    asset_id: str
    asset_type: str
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    severity: str = "info"  # info, warning, error, critical
    recommendation: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class ChangeSummary(BaseModel):
    """
    Summary of changes detected in an amendment.

    Aggregates semantic diff results for quick review.
    """

    total_changes: int
    endpoints_affected: int
    visits_affected: int
    populations_affected: int
    variables_affected: int
    high_impact_changes: int
    summary_text: str


class RiskAssessment(BaseModel):
    """
    Risk assessment for a single impacted node.

    Encapsulates the risk scoring logic (Step 5).
    """

    node_id: str
    base_risk_score: int = Field(ge=0, le=100)
    adjustment_factors: dict[str, float] = Field(default_factory=dict)
    final_risk_score: int = Field(ge=0, le=100)
    priority: str  # low, medium, high, critical
    rationale: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class ProcessingStatus(BaseModel):
    """
    Status of an asynchronous processing job.

    Used for tracking Celery task progress.
    """

    job_id: str
    status: str  # pending, started, completed, failed
    progress: int = Field(ge=0, le=100, default=0)
    current_step: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
