"""
Repository interfaces for the domain layer.

These are abstract base classes that define the contract for data access.
Infrastructure layer provides concrete implementations.
This follows the Repository Pattern for dependency inversion.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.domain.models.entities import (
    Amendment,
    ImpactAnalysisResult,
    DependencyGraph,
)
from app.domain.models.value_objects import AuditEntry


class AmendmentRepository(ABC):
    """
    Repository interface for Amendment persistence.

    Abstracts away whether data is stored in PostgreSQL, Neo4j, or elsewhere.
    """

    @abstractmethod
    async def create(self, amendment: Amendment) -> Amendment:
        """Create a new amendment."""
        pass

    @abstractmethod
    async def get_by_id(self, amendment_id: UUID) -> Optional[Amendment]:
        """Retrieve an amendment by ID."""
        pass

    @abstractmethod
    async def update(self, amendment: Amendment) -> Amendment:
        """Update an existing amendment."""
        pass

    @abstractmethod
    async def get_by_protocol(self, protocol_id: UUID) -> list[Amendment]:
        """Get all amendments for a protocol."""
        pass

    @abstractmethod
    async def get_recent(self, limit: int = 50) -> list[Amendment]:
        """Get recent amendments across all protocols."""
        pass


class ImpactAnalysisRepository(ABC):
    """
    Repository interface for Impact Analysis results.
    """

    @abstractmethod
    async def create(self, result: ImpactAnalysisResult) -> ImpactAnalysisResult:
        """Store impact analysis result."""
        pass

    @abstractmethod
    async def get_by_amendment(
        self, amendment_id: UUID
    ) -> Optional[ImpactAnalysisResult]:
        """Get impact analysis for an amendment."""
        pass

    @abstractmethod
    async def exists(self, amendment_id: UUID) -> bool:
        """Check if impact analysis exists for an amendment."""
        pass


class GraphRepository(ABC):
    """
    Repository interface for the dependency graph.

    This is typically implemented using Neo4j.
    All graph traversals and queries go through this repository.
    """

    @abstractmethod
    async def initialize_graph(self) -> bool:
        """Initialize the graph with default clinical trial structure."""
        pass

    @abstractmethod
    async def find_downstream_dependencies(
        self, node_id: str, max_depth: int = 10
    ) -> list[str]:
        """
        Find all nodes that depend on the given node.

        This is the core query for impact analysis.
        Traverses downstream from the changed node.
        """
        pass

    @abstractmethod
    async def get_subgraph(
        self, node_ids: list[str], include_upstream: bool = False
    ) -> DependencyGraph:
        """
        Get a subgraph containing specified nodes and their relationships.

        Used for visualization.
        """
        pass

    @abstractmethod
    async def get_full_graph(self) -> DependencyGraph:
        """Get the complete dependency graph for visualization."""
        pass

    @abstractmethod
    async def add_node(self, node_data: dict) -> bool:
        """Add a node to the graph."""
        pass

    @abstractmethod
    async def add_relationship(
        self, source_id: str, target_id: str, relationship_type: str
    ) -> bool:
        """Add a relationship between two nodes."""
        pass

    @abstractmethod
    async def get_node_by_id(self, node_id: str) -> Optional[dict]:
        """Get a node by its ID."""
        pass

    @abstractmethod
    async def search_nodes(
        self, node_type: Optional[str] = None, search_term: Optional[str] = None
    ) -> list[dict]:
        """Search for nodes by type or name."""
        pass


class AuditRepository(ABC):
    """
    Repository interface for audit trail entries.

    All audit entries must be immutable and append-only for compliance.
    """

    @abstractmethod
    async def log(self, entry: AuditEntry) -> AuditEntry:
        """Log an audit entry."""
        pass

    @abstractmethod
    async def get_by_entity(
        self, entity_type: str, entity_id: UUID
    ) -> list[AuditEntry]:
        """Get audit trail for a specific entity."""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> list[AuditEntry]:
        """Get all actions by a specific user."""
        pass

    @abstractmethod
    async def get_recent(self, limit: int = 100) -> list[AuditEntry]:
        """Get recent audit entries across the system."""
        pass

    @abstractmethod
    async def get_by_date_range(
        self, start_date: str, end_date: str
    ) -> list[AuditEntry]:
        """Get audit entries within a date range."""
        pass
