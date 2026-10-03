"""Login, logout and the current user."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, get_current_user
from app.config import get_settings
from app.db import get_session
from app.models import User
from app.schemas.auth import LoginRequest, UserResponse
from app.services.auth import authenticate, create_session, revoke_session

router = APIRouter(prefix="/auth", tags=["auth"])

_SECONDS_PER_DAY = 24 * 60 * 60


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_session),
) -> UserResponse:
    """Verify credentials, start a session and set the session cookie."""
    settings = get_settings()
    user = authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_session(db, user, datetime.now(UTC), settings.session_ttl_days)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.session_ttl_days * _SECONDS_PER_DAY,
        path="/",
    )
    return UserResponse(id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_session)) -> Response:
    """End the session and clear the cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    if token is not None:
        revoke_session(db, token)

    cleared = Response(status_code=status.HTTP_204_NO_CONTENT)
    cleared.delete_cookie(SESSION_COOKIE, path="/")
    return cleared


@router.get("/me", response_model=UserResponse)
def read_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the signed-in user."""
    return UserResponse(id=user.id, email=user.email)
