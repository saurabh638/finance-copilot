"""FastAPI application factory and router registration."""

from fastapi import Depends, FastAPI

from app.api.deps import enforce_auth
from app.api.v1 import accounts, auth, categories, health, recurring, transactions


def create_app() -> FastAPI:
    """Build and return the FastAPI application.

    Every route requires a session except the paths allow-listed in deps.py, so a
    router added later is protected by default.
    """
    app = FastAPI(
        title="Finance Co-pilot API",
        version="0.1.0",
        dependencies=[Depends(enforce_auth)],
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(accounts.router, prefix="/api/v1")
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(categories.router, prefix="/api/v1")
    app.include_router(recurring.router, prefix="/api/v1")
    return app


app = create_app()
