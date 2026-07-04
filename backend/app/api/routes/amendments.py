"""
Amendment routes.

Handles protocol amendment upload, retrieval, and management.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.responses import (
    AmendmentResponse,
    AmendmentListResponse,
    AmendmentUploadRequest,
)
from app.domain.models.entities import Amendment
from app.domain.repositories.interfaces import AmendmentRepository
from app.infrastructure.neo4j.driver import Neo4jRepository
from app.core.config import get_settings

settings = get_settings()

router = APIRouter()


def get_amendment_repo() -> AmendmentRepository:
    """Get amendment repository instance."""
    # For MVP, using in-memory storage
    # In production, this would use PostgreSQL
    return InMemoryAmendmentRepository()


class InMemoryAmendmentRepository(AmendmentRepository):
    """
    In-memory implementation for MVP.

    Will be replaced with PostgreSQL implementation in production.
    """

    _storage = {}

    async def create(self, amendment: Amendment) -> Amendment:
        self._storage[str(amendment.id)] = amendment
        return amendment

    async def get_by_id(self, amendment_id: UUID) -> Amendment | None:
        return self._storage.get(str(amendment_id))

    async def update(self, amendment: Amendment) -> Amendment:
        self._storage[str(amendment.id)] = amendment
        return amendment

    async def get_by_protocol(self, protocol_id: UUID) -> List[Amendment]:
        return [
            a for a in self._storage.values()
            if a.protocol_id == protocol_id
        ]

    async def get_recent(self, limit: int = 50) -> List[Amendment]:
        return list(self._storage.values())[-limit:]


@router.post("/upload", response_model=AmendmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_amendment(
    request: AmendmentUploadRequest,
    repo: AmendmentRepository = Depends(get_amendment_repo),
):
    """
    Upload a protocol amendment for analysis.

    This is the entry point for the impact analysis workflow.
    Accepts old and new protocol/SAP text sections.
    """
    amendment = Amendment(
        protocol_id=UUID(request.protocol_id) if request.protocol_id else None,
        old_text=request.old_text,
        new_text=request.new_text,
        change_type=request.change_type,
        change_description=request.change_description,
        status="pending",
    )

    created = await repo.create(amendment)

    return AmendmentResponse(
        id=str(created.id),
        protocol_id=str(created.protocol_id) if created.protocol_id else None,
        old_text=created.old_text,
        new_text=created.new_text,
        change_type=created.change_type,
        change_description=created.change_description,
        semantic_diff=created.semantic_diff,
        status=created.status,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@router.get("/{amendment_id}", response_model=AmendmentResponse)
async def get_amendment(
    amendment_id: str,
    repo: AmendmentRepository = Depends(get_amendment_repo),
):
    """Get an amendment by ID."""
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    amendment = await repo.get_by_id(uuid_id)
    if not amendment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Amendment {amendment_id} not found",
        )

    return AmendmentResponse(
        id=str(amendment.id),
        protocol_id=str(amendment.protocol_id) if amendment.protocol_id else None,
        old_text=amendment.old_text,
        new_text=amendment.new_text,
        change_type=amendment.change_type,
        change_description=amendment.change_description,
        semantic_diff=amendment.semantic_diff,
        status=amendment.status,
        created_at=amendment.created_at,
        updated_at=amendment.updated_at,
    )


@router.get("/", response_model=AmendmentListResponse)
async def list_amendments(
    limit: int = 50,
    repo: AmendmentRepository = Depends(get_amendment_repo),
):
    """List recent amendments."""
    amendments = await repo.get_recent(limit)

    return AmendmentListResponse(
        amendments=[
            AmendmentResponse(
                id=str(a.id),
                protocol_id=str(a.protocol_id) if a.protocol_id else None,
                old_text=a.old_text,
                new_text=a.new_text,
                change_type=a.change_type,
                change_description=a.change_description,
                semantic_diff=a.semantic_diff,
                status=a.status,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in amendments
        ],
        total=len(amendments),
    )


@router.post("/{amendment_id}/compare", response_model=AmendmentResponse)
async def compare_amendment(
    amendment_id: str,
    repo: AmendmentRepository = Depends(get_amendment_repo),
):
    """
    Trigger semantic difference detection for an amendment.

    This endpoint initiates Step 1 of the analysis pipeline.
    """
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    amendment = await repo.get_by_id(uuid_id)
    if not amendment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Amendment {amendment_id} not found",
        )

    # For MVP, perform simple diff detection
    # In production, this would call the LLM parser agent
    from app.agents.parsers.semantic_parser import SemanticDiffAgent

    agent = SemanticDiffAgent()
    semantic_diff = await agent.detect_differences(
        amendment.old_text,
        amendment.new_text,
        amendment.change_type,
    )

    amendment.semantic_diff = semantic_diff
    amendment.status = "processing"
    await repo.update(amendment)

    return AmendmentResponse(
        id=str(amendment.id),
        protocol_id=str(amendment.protocol_id) if amendment.protocol_id else None,
        old_text=amendment.old_text,
        new_text=amendment.new_text,
        change_type=amendment.change_type,
        change_description=amendment.change_description,
        semantic_diff=amendment.semantic_diff,
        status=amendment.status,
        created_at=amendment.created_at,
        updated_at=amendment.updated_at,
    )
