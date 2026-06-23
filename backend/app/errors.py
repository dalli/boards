"""Domain error types mapped to HTTP responses at the api layer.

Service layer raises these; api layer (or a global handler) translates to status codes.
Keeping HTTP out of the service layer preserves the api→service→repo boundary (§5).
"""
from __future__ import annotations


class AppError(Exception):
    status_code: int = 400
    detail: str = "Bad request"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class AuthenticationError(AppError):
    status_code = 401
    detail = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = 403
    detail = "Permission denied"


class NotFoundError(AppError):
    status_code = 404
    detail = "Not found"


class ConflictError(AppError):
    status_code = 409
    detail = "Conflict"


class ValidationFailedError(AppError):
    status_code = 422
    detail = "Validation failed"
