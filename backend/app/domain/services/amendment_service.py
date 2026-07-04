"""
Domain services for the Protocol Amendment Dependency Graph Engine.

Services contain business logic that doesn't fit naturally into entities.
They orchestrate between repositories and other services.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.models.entities import (
    Amendment,
    ChangeType,
    SemanticDiff,
)
from app.domain.repositories.interfaces import AmendmentRepository
from app.domain.models.value_objects import AuditEntry


class AmendmentService:
    """
    Service for managing amendments.

    Handles creation, retrieval, and lifecycle management of amendments.
    """

    def __init__(
        self,
        amendment_repo: AmendmentRepository,
    ):
        self.amendment_repo = amendment_repo

    async def create_amendment(
        self,
        old_text: str,
        new_text: str,
        protocol_id: Optional[UUID] = None,
        change_type: Optional[ChangeType] = None,
        change_description: Optional[str] = None,
        created_by: Optional[UUID] = None,
    ) -> Amendment:
        """
        Create a new amendment record.

        This is the entry point for the impact analysis workflow.
        """
        amendment = Amendment(
            protocol_id=protocol_id,
            old_text=old_text,
            new_text=new_text,
            change_type=change_type,
            change_description=change_description,
            created_by=created_by,
            status="pending",
        )

        return await self.amendment_repo.create(amendment)

    async def get_amendment(self, amendment_id: UUID) -> Optional[Amendment]:
        """Retrieve an amendment by ID."""
        return await self.amendment_repo.get_by_id(amendment_id)

    async def update_semantic_diff(
        self, amendment_id: UUID, semantic_diff: SemanticDiff
    ) -> Amendment:
        """
        Update an amendment with semantic diff results.

        Called after Step 1 (Semantic Difference Detection) completes.
        """
        amendment = await self.amendment_repo.get_by_id(amendment_id)
        if not amendment:
            raise ValueError(f"Amendment {amendment_id} not found")

        amendment.semantic_diff = semantic_diff
        amendment.status = "processing"
        amendment.updated_at = datetime.utcnow()

        return await self.amendment_repo.update(amendment)

    async def complete_amendment(self, amendment_id: UUID) -> Amendment:
        """Mark an amendment as completed."""
        amendment = await self.amendment_repo.get_by_id(amendment_id)
        if not amendment:
            raise ValueError(f"Amendment {amendment_id} not found")

        amendment.status = "completed"
        amendment.updated_at = datetime.utcnow()

        return await self.amendment_repo.update(amendment)

    async def fail_amendment(
        self, amendment_id: UUID, error_message: str
    ) -> Amendment:
        """Mark an amendment as failed."""
        amendment = await self.amendment_repo.get_by_id(amendment_id)
        if not amendment:
            raise ValueError(f"Amendment {amendment_id} not found")

        amendment.status = "failed"
        amendment.change_description = error_message
        amendment.updated_at = datetime.utcnow()

        return await self.amendment_repo.update(amendment)

    async def get_protocol_amendments(
        self, protocol_id: UUID
    ) -> list[Amendment]:
        """Get all amendments for a protocol."""
        return await self.amendment_repo.get_by_protocol(protocol_id)

    async def get_recent_amendments(self, limit: int = 50) -> list[Amendment]:
        """Get recent amendments across all protocols."""
        return await self.amendment_repo.get_recent(limit)
