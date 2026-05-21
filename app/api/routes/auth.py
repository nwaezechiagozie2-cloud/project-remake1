from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
import logging

from app.api.deps import get_auth_service, get_google_oauth_service, get_instagram_oauth_service, get_oauth_login_service
from app.exceptions import ValidationError
from app.observability import get_metrics_registry
from app.schemas.api import (
    AuthResponse,
    EmailVerificationConfirmRequest,
    EmailVerificationRequest,
    ErrorResponse,
    GoogleOAuthStatusResponse,
    VendorLoginRequest,
    VendorRegisterRequest,
)
from app.security import rate_limit_dependency
from app.services.auth_service import AuthService
from app.services.google_oauth_service import GoogleOAuthService
from app.services.instagram_oauth_service import InstagramOAuthService
from app.services.oauth_login_service import OAuthLoginService

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
    result = await auth_service.register(email=payload.email, password=payload.password)
    logger.info("auth_register_succeeded | vendor_id=%s", result.get("vendor_id"))
    return result


@router.post("/auth/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def login(payload: VendorLoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> dict:
    result = await auth_service.login(email=payload.email, password=payload.password)
    logger.info("auth_login_succeeded | vendor_id=%s", result.get("vendor_id"))
    return result


@router.post("/auth/verify-email/request", dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def request_email_verification(payload: EmailVerificationRequest, auth_service: AuthService = Depends(get_auth_service)) -> dict:
    result = await auth_service.request_registration_verification(payload.email)
    logger.info("email_verification_requested | email=%s", payload.email)
    return result


@router.post("/auth/verify-email/confirm", response_model=dict, dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def confirm_email_verification(payload: EmailVerificationConfirmRequest, auth_service: AuthService = Depends(get_auth_service)) -> dict:
    result = await auth_service.confirm_registration_email(payload.token)
    logger.info("email_verification_confirmed | vendor_id=%s", result.get("vendor_id"))
    return result


@router.get("/auth/login/google", dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def login_google(oauth_login: OAuthLoginService = Depends(get_oauth_login_service)):
    authorization_url = await oauth_login.build_google_url()
    logger.info("google_login_authorization_redirect")
    return RedirectResponse(url=authorization_url)


@router.get("/auth/login/google/callback")
async def login_google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_login: OAuthLoginService = Depends(get_oauth_login_service),
):
    if error:
        raise ValidationError("Google login failed", details={"error": error})
    if not code or not state:
        raise ValidationError("Missing Google login callback parameters")
    frontend_url = await oauth_login.complete_google(code=code, state=state)
    get_metrics_registry().increment("oauth_callbacks_total")
    logger.info("google_login_callback_completed")
    return RedirectResponse(url=frontend_url)


@router.get("/auth/login/instagram", dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def login_instagram(oauth_login: OAuthLoginService = Depends(get_oauth_login_service)):
    authorization_url = await oauth_login.build_instagram_url()
    logger.info("instagram_login_authorization_redirect")
    return RedirectResponse(url=authorization_url)


@router.get("/auth/login/instagram/callback")
async def login_instagram_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    oauth_login: OAuthLoginService = Depends(get_oauth_login_service),
):
    if error:
        raise ValidationError("Instagram login failed", details={"error": error, "description": error_description})
    if not code or not state:
        raise ValidationError("Missing Instagram login callback parameters")
    frontend_url = await oauth_login.complete_instagram(code=code, state=state)
    get_metrics_registry().increment("oauth_callbacks_total")
    logger.info("instagram_login_callback_completed")
    return RedirectResponse(url=frontend_url)


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
) -> RedirectResponse:
    if not code or not state:
        raise ValidationError("Missing OAuth callback parameters")

    vendor_id = await oauth_service.complete_callback(
        code=code,
        state=state,
        authorization_response=str(request.url),
    )
    get_metrics_registry().increment("oauth_callbacks_total")
    logger.info("google_oauth_callback_completed | vendor_id=%s", vendor_id)

    return RedirectResponse(url=f"{oauth_service.settings.frontend_base_url.rstrip('/')}/settings?google=connected")


@router.get("/auth/instagram", dependencies=[Depends(rate_limit_dependency(scope="auth"))])
async def auth_instagram(vendor_id: int, oauth_service: InstagramOAuthService = Depends(get_instagram_oauth_service)):
    authorization_url = await oauth_service.build_authorization_url(vendor_id)
    logger.info("instagram_oauth_authorization_redirect | vendor_id=%s", vendor_id)
    return RedirectResponse(url=authorization_url)


@router.get("/auth/instagram/callback")
async def auth_instagram_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    oauth_service: InstagramOAuthService = Depends(get_instagram_oauth_service),
) -> RedirectResponse:
    if error:
        raise ValidationError("Instagram OAuth failed", details={"error": error, "description": error_description})
    if not code or not state:
        raise ValidationError("Missing OAuth callback parameters")

    result = await oauth_service.complete_callback(code=code, state=state)
    get_metrics_registry().increment("oauth_callbacks_total")
    logger.info("instagram_oauth_callback_completed | vendor_id=%s", result["vendor_id"])

    return RedirectResponse(url=f"{oauth_service.settings.frontend_base_url.rstrip('/')}/settings?instagram=connected")
