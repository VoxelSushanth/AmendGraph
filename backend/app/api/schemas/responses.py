"""
API Schemas for request/response validation.

These Pydantic models define the API contract.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.models.entities import (
    ChangeType,
    RiskLevel,
    NodeType,
    SemanticDiff,
    ImpactedNode,
    ImpactAnalysisResult,
    ReviewTask,
    GraphNode,
    GraphEdge,
    DependencyGraph,
)


# ============== Authentication Schemas ==============

class LoginRequest(BaseModel):
    """Login request schema."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    """User information response."""

    id: str
    email: str
    role: str


# ============== Amendment Schemas ==============

class AmendmentUploadRequest(BaseModel):
    """Request to upload a protocol amendment."""

    old_text: str = Field(..., description="Original protocol/SAP text")
    new_text: str = Field(..., description="Amended protocol/SAP text")
    protocol_id: Optional[str] = Field(None, description="Protocol ID if exists")
    change_type: Optional[ChangeType] = Field(None, description="Type of change")
    change_description: Optional[str] = Field(
        None, description="Human-readable description"
    )


class AmendmentResponse(BaseModel):
    """Amendment response schema."""

    id: str
    protocol_id: Optional[str]
    old_text: str
    new_text: str
    change_type: Optional[ChangeType]
    change_description: Optional[str]
    semantic_diff: Optional[SemanticDiff]
    status: str
    created_at: datetime
    updated_at: datetime


class AmendmentListResponse(BaseModel):
    """List of amendments."""

    amendments: List[AmendmentResponse]
    total: int


# ============== Impact Analysis Schemas ==============

class ImpactAnalysisResponse(BaseModel):
    """Impact analysis result response."""

    amendment_id: str
    semantic_diff: SemanticDiff
    total_impacted_nodes: int
    risk_summary: Dict[str, int]
    impacted_nodes: List[ImpactedNode]
    recommendations: List[str]
    generated_at: datetime
    processing_time_ms: Optional[int]


class ImpactSummaryResponse(BaseModel):
    """Brief impact summary for dashboard."""

    amendment_id: str
    total_impacted_nodes: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    status: str


# ============== Graph Schemas ==============

class DependencyGraphResponse(BaseModel):
    """Dependency graph response for React Flow."""

    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphNodeRequest(BaseModel):
    """Request to add a node to the graph."""

    id: str
    type: NodeType
    name: str
    metadata: Optional[Dict[str, Any]] = None


class GraphEdgeRequest(BaseModel):
    """Request to add an edge to the graph."""

    source_id: str
    target_id: str
    relationship: str


# ============== Review Task Schemas ==============

class ReviewTaskResponse(BaseModel):
    """Review task response."""

    task_id: str
    task_name: str
    owner_role: str
    priority: RiskLevel
    estimated_hours: float
    dependencies: List[str]
    due_date: Optional[datetime]
    status: str
    instructions: Optional[str]


class ReviewPlanResponse(BaseModel):
    """Complete review plan response."""

    tasks: List[ReviewTaskResponse]
    total_estimated_hours: float
    effort_by_role: Dict[str, float]


# ============== Audit Schemas ==============

class AuditEntryResponse(BaseModel):
    """Audit log entry response."""

    timestamp: datetime
    user_email: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[str]
    details: Optional[Dict[str, Any]]


class AuditTrailResponse(BaseModel):
    """Audit trail response."""

    entries: List[AuditEntryResponse]
    total: int


# ============== Health & Status Schemas ==============

class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    neo4j_connected: bool = False
    postgres_connected: bool = False
    redis_connected: bool = False


class ProcessingStatusResponse(BaseModel):
    """Processing job status."""

    job_id: str
    status: str
    progress: int
    current_step: Optional[str]
    result: Optional[Any]
    error: Optional[str]
