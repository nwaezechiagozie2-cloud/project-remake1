class AppError(Exception):
    code = "app_error"
    status_code = 500

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    code = "validation_error"
    status_code = 400


class AuthenticationError(AppError):
    code = "authentication_error"
    status_code = 401


class AuthorizationError(AppError):
    code = "authorization_error"
    status_code = 403


class ResourceNotFoundError(AppError):
    code = "resource_not_found"
    status_code = 404


class ConflictError(AppError):
    code = "conflict"
    status_code = 409


class TooManyRequestsError(AppError):
    code = "too_many_requests"
    status_code = 429
