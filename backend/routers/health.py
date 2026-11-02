"""Health check router."""
from __future__ import annotations

from fastapi import APIRouter
from schemas import HealthResponse

router = APIRouter(tags=["System"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Service Health Check",
)
def health():
    """Verify backend API operational status."""
    return {"status": "ok"}
