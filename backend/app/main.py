"""FastAPI application factory and router registration."""

from fastapi import FastAPI

from app.api.v1 import health


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="Finance Co-pilot API", version="0.1.0")
    app.include_router(health.router, prefix="/api/v1")
    return app


app = create_app()
