"""Authentication guard: every route needs a session unless it is allow-listed.

Applied once in `main.create_app`, so a new router is protected by default and
cannot be exposed by forgetting a dependency.
"""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.services.auth import resolve_session

SESSION_COOKIE = "finance_session"

# The only paths that work without a session.
_PUBLIC_PATHS = frozenset({"/api/v1/health", "/api/v1/auth/login"})


def _unauthorised() -> HTTPException:
    """The single 401 raised for a missing or invalid session."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_current_user(request: Request, db: Session = Depends(get_session)) -> User:
    """Return the signed-in user, or raise 401 when there is no valid session."""
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        raise _unauthorised()

    user = resolve_session(db, token, datetime.now(UTC))
    if user is None:
        raise _unauthorised()
    return user


def enforce_auth(request: Request, db: Session = Depends(get_session)) -> None:
    """Guard applied to every route: allow only the public paths anonymously."""
    if request.url.path in _PUBLIC_PATHS:
        return
    get_current_user(request, db)
