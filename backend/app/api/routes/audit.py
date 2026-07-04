"""
Audit trail routes.

Handles audit log retrieval for compliance and traceability.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.responses import AuditTrailResponse, AuditEntryResponse

router = APIRouter()


# In-memory audit storage for MVP
_audit_storage = []


@router.get("/{amendment_id}", response_model=AuditTrailResponse)
async def get_audit_trail(amendment_id: str):
    """
    Get audit trail for a specific amendment.

    Returns all actions related to the amendment for FDA compliance.
    """
    try:
        uuid_id = UUID(amendment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid amendment ID format",
        )

    # Filter audit entries for this amendment
    entries = [
        e for e in _audit_storage
        if str(e.get("entity_id")) == str(uuid_id)
    ]

    return AuditTrailResponse(
        entries=[
            AuditEntryResponse(
                timestamp=e["timestamp"],
                user_email=e.get("user_email"),
                action=e["action"],
                entity_type=e["entity_type"],
                entity_id=str(e["entity_id"]) if e.get("entity_id") else None,
                details=e.get("details"),
            )
            for e in entries
        ],
        total=len(entries),
    )


@router.get("/", response_model=AuditTrailResponse)
async def list_audit_entries(
    limit: int = 100,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """List recent audit entries across the system."""
    entries = _audit_storage[-limit:]

    if start_date:
        start = datetime.fromisoformat(start_date)
        entries = [e for e in entries if e["timestamp"] >= start]

    if end_date:
        end = datetime.fromisoformat(end_date)
        entries = [e for e in entries if e["timestamp"] <= end]

    return AuditTrailResponse(
        entries=[
            AuditEntryResponse(
                timestamp=e["timestamp"],
                user_email=e.get("user_email"),
                action=e["action"],
                entity_type=e["entity_type"],
                entity_id=str(e["entity_id"]) if e.get("entity_id") else None,
                details=e.get("details"),
            )
            for e in entries
        ],
        total=len(entries),
    )


def log_audit_entry(
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    user_email: str | None = None,
    details: dict | None = None,
) -> None:
    """Log an audit entry."""
    _audit_storage.append({
        "timestamp": datetime.utcnow(),
        "user_email": user_email,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
    })
