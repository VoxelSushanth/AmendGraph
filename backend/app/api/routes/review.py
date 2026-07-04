"""
Review task routes.

Handles review task generation and management.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.responses import ReviewPlanResponse, ReviewTaskResponse
from app.domain.services.review_service import ReviewService
from app.infrastructure.neo4j.driver import Neo4jRepository
from app.domain.repositories.interfaces import AmendmentRepository

router = APIRouter()


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


@router.post("/{amendment_id}/plan", response_model=ReviewPlanResponse)
async def generate_review_plan(amendment_id: str):
    """
    Generate review tasks from impact analysis.

    This endpoint creates actionable tasks for all impacted nodes (Step 8).
    """
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    # Get impact analysis result
    impact_repo = InMemoryImpactRepository()
    impact_result = await impact_repo.get_by_amendment(uuid_id)

    if not impact_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Impact analysis for {amendment_id} not found",
        )

    # Generate tasks
    review_service = ReviewService()
    tasks = review_service.generate_tasks(impact_result)

    # Calculate effort by role
    effort_by_role = review_service.estimate_total_effort(tasks)
    total_hours = effort_by_role.pop("TOTAL", 0.0)

    return ReviewPlanResponse(
        tasks=[
            ReviewTaskResponse(
                task_id=str(task.task_id),
                task_name=task.task_name,
                owner_role=task.owner_role,
                priority=task.priority,
                estimated_hours=task.estimated_hours,
                dependencies=task.dependencies,
                due_date=task.due_date,
                status=task.status,
                instructions=task.instructions,
            )
            for task in tasks
        ],
        total_estimated_hours=total_hours,
        effort_by_role=effort_by_role,
    )


@router.get("/{amendment_id}/tasks", response_model=list[ReviewTaskResponse])
async def list_review_tasks(amendment_id: str):
    """List all review tasks for an amendment."""
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    # For MVP, return empty list
    # In production, fetch from database
    return []
