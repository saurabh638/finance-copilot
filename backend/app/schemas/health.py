"""Response shapes for the health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check result. `database` reflects a live query, not a guess."""

    status: str
    database: str
