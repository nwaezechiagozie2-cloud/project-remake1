from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import logging

from app.api.deps import get_auth_service, get_google_oauth_service
from app.exceptions import ValidationError
from app.observability import get_metrics_registry
from app.schemas.api import AuthResponse, ErrorResponse, GoogleOAuthStatusResponse, VendorLoginRequest, VendorRegisterRequest
from app.security import rate_limit_dependency
from app.services.auth_service import AuthService
from app.services.google_oauth_service import GoogleOAuthService

logger = logging.getLogger(__name__)

STANDARD_ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Validation error",
        "content": {"application/json": {"example": {"error": {"code": "validation_error", "message": "Missing OAuth callback parameters", "details": {}}}}},
    },
    401: {
        "model": ErrorResponse,
        "description": "Authentication error",
        "content": {"application/json": {"example": {"error": {"code": "authentication_error", "message": "Invalid or expired token", "details": {}}}}},
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource not found",
        "content": {"application/json": {"example": {"error": {"code": "resource_not_found", "message": "Vendor not found", "details": {}}}}},
    },
    409: {
        "model": ErrorResponse,
        "description": "Conflict",
        "content": {"application/json": {"example": {"error": {"code": "conflict", "message": "Email already registered", "details": {}}}}},
    },
    429: {
        "model": ErrorResponse,
        "description": "Rate limit exceeded",
        "content": {"application/json": {"example": {"error": {"code": "too_many_requests", "message": "Rate limit exceeded", "details": {}}}}},
    },
}


router = APIRouter(tags=["auth"], responses=STANDARD_ERROR_RESPONSES)


@router.post("/auth/register", response_model=AuthResponse, status_code=201, dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def register(payload: VendorRegisterRequest, auth_service: AuthService = Depends(get_auth_service)) -> dict:
    result = await auth_service.register(name=payload.name, email=payload.email, password=payload.password)
    logger.info("auth_register_succeeded | vendor_id=%s", result.get("vendor_id"))
    return result


@router.post("/auth/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def login(payload: VendorLoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> dict:
    result = await auth_service.login(email=payload.email, password=payload.password)
    logger.info("auth_login_succeeded | vendor_id=%s", result.get("vendor_id"))
    return result


@router.get("/auth/google", dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def auth_google(vendor_id: int, oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)):
    authorization_url = await oauth_service.build_authorization_url(vendor_id)
    logger.info("google_oauth_authorization_redirect | vendor_id=%s", vendor_id)
    return RedirectResponse(url=authorization_url)


@router.get("/auth/google/status", response_model=GoogleOAuthStatusResponse, dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def auth_google_status(vendor_id: int, oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)) -> dict:
    status_payload = await oauth_service.get_vendor_oauth_status(vendor_id)
    logger.info("google_oauth_status_checked | vendor_id=%s | status=%s", vendor_id, status_payload.get("status"))
    return status_payload


@router.get("/auth/google/callback")
async def auth_google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service),
) -> HTMLResponse:
    if not code or not state:
        raise ValidationError("Missing OAuth callback parameters")

    vendor_id = await oauth_service.complete_callback(
        code=code,
        state=state,
        authorization_response=str(request.url),
    )
    get_metrics_registry().increment("oauth_callbacks_total")
    logger.info("google_oauth_callback_completed | vendor_id=%s", vendor_id)

    return HTMLResponse(
        content=(
            "<html><body><h3>Google OAuth completed successfully.</h3>"
            f"<p>Token saved for vendor <code>{vendor_id}</code>.</p>"
            "<p>You can close this tab now.</p>"
            "</body></html>"
        )
    )
