"""Request and response shapes for authentication."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials sent to POST /auth/login."""

    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class UserResponse(BaseModel):
    """The signed-in user. Never includes the password hash."""

    id: int
    email: str
