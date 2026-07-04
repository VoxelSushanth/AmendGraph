"""
Impact analysis routes.

Handles impact analysis execution and retrieval.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.responses import (
    ImpactAnalysisResponse,
    ImpactSummaryResponse,
)
from app.domain.models.entities import RiskLevel
from app.domain.repositories.interfaces import AmendmentRepository
from app.infrastructure.neo4j.driver import Neo4jRepository
from app.domain.services.impact_service import ImpactService

router = APIRouter()


def get_impact_service() -> ImpactService:
    """Get impact service instance."""
    amendment_repo = InMemoryAmendmentRepository()
    graph_repo = Neo4jRepository()
    impact_repo = InMemoryImpactRepository()

    return ImpactService(amendment_repo, graph_repo, impact_repo)


class InMemoryAmendmentRepository(AmendmentRepository):
    """In-memory amendment repository for MVP."""
    _storage = {}

    async def create(self, amendment):
        self._storage[str(amendment.id)] = amendment
        return amendment

    async def get_by_id(self, amendment_id: UUID):
        return self._storage.get(str(amendment_id))

    async def update(self, amendment):
        self._storage[str(amendment.id)] = amendment
        return amendment

    async def get_by_protocol(self, protocol_id: UUID):
        return [a for a in self._storage.values() if a.protocol_id == protocol_id]

    async def get_recent(self, limit: int = 50):
        return list(self._storage.values())[-limit:]


class InMemoryImpactRepository:
    """In-memory impact result storage."""
    _storage = {}

    async def create(self, result):
        self._storage[str(result.amendment_id)] = result
        return result

    async def get_by_amendment(self, amendment_id: UUID):
        return self._storage.get(str(amendment_id))

    async def exists(self, amendment_id: UUID) -> bool:
        return str(amendment_id) in self._storage


@router.post("/{amendment_id}/analyze", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    amendment_id: str,
    service: ImpactService = Depends(get_impact_service),
):
    """
    Perform impact analysis for an amendment.

    This endpoint triggers Steps 3-6:
    1. Graph traversal to find downstream dependencies
    2. Risk scoring for each impacted node
    3. LLM explanation generation
    4. Aggregation of results
    """
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    # Get amendment
    amendment_repo = InMemoryAmendmentRepository()
    amendment = await amendment_repo.get_by_id(uuid_id)

    if not amendment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Amendment {amendment_id} not found",
        )

    if not amendment.semantic_diff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Semantic diff not yet computed. Call /compare first.",
        )

    # Perform analysis
    result = await service.analyze_impact(uuid_id, amendment.semantic_diff)

    return ImpactAnalysisResponse(
        amendment_id=str(result.amendment_id),
        semantic_diff=result.semantic_diff,
        total_impacted_nodes=result.total_impacted_nodes,
        risk_summary={k.value: v for k, v in result.risk_summary.items()},
        impacted_nodes=result.impacted_nodes,
        recommendations=result.recommendations,
        generated_at=result.generated_at,
        processing_time_ms=result.processing_time_ms,
    )


@router.get("/{amendment_id}", response_model=ImpactAnalysisResponse)
async def get_impact_analysis(
    amendment_id: str,
    service: ImpactService = Depends(get_impact_service),
):
    """Get existing impact analysis result."""
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    impact_repo = InMemoryImpactRepository()
    result = await impact_repo.get_by_amendment(uuid_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Impact analysis for {amendment_id} not found",
        )

    return ImpactAnalysisResponse(
        amendment_id=str(result.amendment_id),
        semantic_diff=result.semantic_diff,
        total_impacted_nodes=result.total_impacted_nodes,
        risk_summary={k.value: v for k, v in result.risk_summary.items()},
        impacted_nodes=result.impacted_nodes,
        recommendations=result.recommendations,
        generated_at=result.generated_at,
        processing_time_ms=result.processing_time_ms,
    )


@router.get("/{amendment_id}/summary", response_model=ImpactSummaryResponse)
async def get_impact_summary(
    amendment_id: str,
    service: ImpactService = Depends(get_impact_service),
):
    """Get brief impact summary for dashboard."""
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    impact_repo = InMemoryImpactRepository()
    result = await impact_repo.get_by_amendment(uuid_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Impact analysis for {amendment_id} not found",
        )

    return ImpactSummaryResponse(
        amendment_id=str(result.amendment_id),
        total_impacted_nodes=result.total_impacted_nodes,
        critical_count=result.risk_summary.get(RiskLevel.CRITICAL, 0),
        high_count=result.risk_summary.get(RiskLevel.HIGH, 0),
        medium_count=result.risk_summary.get(RiskLevel.MEDIUM, 0),
        low_count=result.risk_summary.get(RiskLevel.LOW, 0),
        status="completed",
    )
