"""
Domain entities for the Protocol Amendment Dependency Graph Engine.

These are the core business objects that represent the domain.
All entities use Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Types of protocol changes that can be detected."""

    ENDPOINT = "endpoint"
    VISIT = "visit"
    POPULATION = "population"
    VARIABLE = "variable"
    TIMING = "timing"
    METHOD = "method"
    SCHEDULE = "schedule"
    CRITERIA = "criteria"


class RiskLevel(str, Enum):
    """Risk levels for impact assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NodeType(str, Enum):
    """Types of nodes in the dependency graph."""

    ENDPOINT = "Endpoint"
    VISIT = "Visit"
    POPULATION = "Population"
    DATASET = "Dataset"
    VARIABLE = "Variable"
    TABLE = "Table"
    FIGURE = "Figure"
    VALIDATION_RULE = "ValidationRule"
    DEFINE_XML = "DefineXML"
    REVIEW_TASK = "ReviewTask"
    TLF = "TLF"
    CSR = "CSR"
    PROTOCOL = "Protocol"
    SAP = "SAP"


class User(BaseModel):
    """User entity for authentication and authorization."""

    id: UUID = Field(default_factory=uuid4)
    email: str
    role: str = "viewer"  # admin, reviewer, programmer, viewer
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Protocol(BaseModel):
    """Protocol entity representing a clinical trial protocol."""

    id: UUID = Field(default_factory=uuid4)
    protocol_number: str
    title: str
    therapeutic_area: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Amendment(BaseModel):
    """
    Amendment entity representing a protocol change.

    This is the primary input to the impact analysis engine.
    """

    id: UUID = Field(default_factory=uuid4)
    protocol_id: Optional[UUID] = None
    old_text: str = Field(..., description="Original protocol/SAP text")
    new_text: str = Field(..., description="Amended protocol/SAP text")
    change_type: Optional[ChangeType] = None
    change_description: Optional[str] = None
    semantic_diff: Optional["SemanticDiff"] = None
    status: str = "pending"  # pending, processing, completed, failed
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SemanticDiff(BaseModel):
    """
    Structured representation of semantic differences between old and new text.

    This is produced by the semantic difference detection agent (Step 1).
    Never output free-form text - always structured JSON.
    """

    endpoints_changed: list[str] = Field(
        default_factory=list,
        description="List of endpoint names that changed"
    )
    visits_changed: Optional[dict[str, str]] = Field(
        default=None,
        description="Dictionary with 'old' and 'new' visit values"
    )
    populations_changed: list[str] = Field(
        default_factory=list,
        description="List of population names that changed"
    )
    variables_changed: list[str] = Field(
        default_factory=list,
        description="List of variable names that changed"
    )
    methods_changed: list[str] = Field(
        default_factory=list,
        description="List of statistical methods that changed"
    )
    timing_changes: Optional[dict[str, Any]] = Field(
        default=None,
        description="Timing-related changes"
    )
    change_type: ChangeType
    change_description: str
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of the detection"
    )
    raw_extraction: Optional[dict[str, Any]] = Field(
        default=None,
        description="Raw LLM extraction before structuring"
    )


class ImpactedNode(BaseModel):
    """
    Represents a node in the dependency graph that is impacted by an amendment.

    This includes risk scoring and explanation (Steps 4-6).
    """

    node_id: str = Field(..., description="Unique identifier of the node")
    node_type: NodeType = Field(..., description="Type of the node")
    name: str = Field(..., description="Human-readable name")
    risk_score: int = Field(
        ge=0,
        le=100,
        description="Risk score from 0-100"
    )
    priority: RiskLevel = Field(..., description="Priority level")
    reason: str = Field(..., description="Why this node is impacted")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the impact assessment"
    )
    estimated_rework_hours: float = Field(
        ge=0.0,
        description="Estimated hours of rework required"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="LLM-generated human-readable explanation"
    )
    downstream_dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of nodes that depend on this node"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImpactAnalysisResult(BaseModel):
    """
    Complete result of an impact analysis.

    This aggregates all information from Steps 1-9.
    """

    amendment_id: UUID
    semantic_diff: SemanticDiff
    total_impacted_nodes: int
    risk_summary: dict[RiskLevel, int] = Field(
        default_factory=lambda: {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 0,
            RiskLevel.HIGH: 0,
            RiskLevel.CRITICAL: 0,
        }
    )
    impacted_nodes: list[ImpactedNode] = Field(default_factory=list)
    recommendations: list[str] = Field(
        default_factory=list,
        description="Validation recommendations (Step 9)"
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = None


class ReviewTask(BaseModel):
    """
    Review task generated from impact analysis (Step 8).

    These tasks are assigned to team members for remediation.
    """

    task_id: Optional[UUID] = Field(default_factory=uuid4)
    task_name: str
    owner_role: str = Field(
        ...,
        description="Role responsible for completing this task"
    )
    priority: RiskLevel
    estimated_hours: float = Field(ge=0.0)
    dependencies: list[str] = Field(
        default_factory=list,
        description="Task IDs that must be completed first"
    )
    due_date: Optional[datetime] = None
    status: str = "open"  # open, in_progress, completed, blocked
    related_node_ids: list[str] = Field(default_factory=list)
    instructions: Optional[str] = None


class GraphNode(BaseModel):
    """
    Node representation for graph visualization (Step 10).

    Optimized for React Flow consumption.
    """

    id: str
    label: str
    type: NodeType
    risk_level: Optional[RiskLevel] = None
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    metadata: dict[str, Any] = Field(default_factory=dict)
    style: Optional[dict[str, Any]] = None


class GraphEdge(BaseModel):
    """
    Edge representation for graph visualization.

    Represents relationships between nodes.
    """

    source: str
    target: str
    relationship: str = Field(
        ...,
        description="Type of relationship (e.g., MEASURED_AT, USES_DATASET)"
    )
    directed: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    label: Optional[str] = None


class DependencyGraph(BaseModel):
    """
    Complete dependency graph for visualization.

    Contains all nodes and edges needed for React Flow rendering.
    """

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# Forward reference resolution
SemanticDiff.model_rebuild()
