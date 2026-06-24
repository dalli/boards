"""Auth & user routes (AC1). HTTP-layer only — delegates to AuthService (§5)."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.deps import AdminUser, CurrentUser, DbSession
from app.schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.service.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def signup(payload: SignupRequest, db: DbSession) -> UserResponse:
    user = AuthService(db).signup(email=payload.email, password=payload.password)
    return UserResponse.model_validate(user)


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    token = AuthService(db).authenticate(email=payload.email, password=payload.password)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/admin/users/{user_id}/promote", response_model=UserResponse)
def promote_user(user_id: int, db: DbSession, admin: AdminUser) -> UserResponse:
    """Y-02: an existing ADMIN promotes a USER to ADMIN."""
    user = AuthService(db).promote_to_admin(actor=admin, target_user_id=user_id)
    return UserResponse.model_validate(user)
