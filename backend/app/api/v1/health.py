"""Health endpoint: liveness plus a real database round-trip."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health(session: Session = Depends(get_session)) -> HealthResponse:
    """Report service and database status; the check really queries Postgres."""
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok")
