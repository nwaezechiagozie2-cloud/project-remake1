from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_auth_service, get_vendor_repo
from app.exceptions import AuthorizationError, ResourceNotFoundError
from app.schemas.api import (
    EmailChangeRequest,
    EmailVerificationConfirmRequest,
    PasswordChangeRequest,
    StatusResponse,
    VendorProfileAuthResponse,
    VendorProfileUpdateRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/vendors", tags=["profile"])
security = HTTPBearer()


async def _ensure_vendor(vendor_id: int, vendors) -> dict:
    vendor = await vendors.get_by_id(vendor_id)
    if not vendor:
        raise ResourceNotFoundError("Vendor not found")
    return vendor


async def _vendor_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> int:
    return auth_service.decode_token(credentials.credentials)


async def _authorize_vendor_scope(vendor_id: int, token_vendor_id: int = Depends(_vendor_from_token)) -> int:
    if token_vendor_id != vendor_id:
        raise AuthorizationError("Token vendor cannot access this vendor resource")
    return token_vendor_id


@router.get("/{vendor_id}/profile", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorProfileAuthResponse)
async def get_profile(vendor_id: int, vendors=Depends(get_vendor_repo), auth_service: AuthService = Depends(get_auth_service)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await auth_service.get_profile(vendor_id)


@router.patch("/{vendor_id}/profile", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorProfileAuthResponse)
async def update_profile(vendor_id: int, payload: VendorProfileUpdateRequest, auth_service: AuthService = Depends(get_auth_service), vendors=Depends(get_vendor_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await auth_service.update_profile(vendor_id, payload.name)


@router.post("/{vendor_id}/profile/email-change/request", dependencies=[Depends(_authorize_vendor_scope)])
async def request_email_change(vendor_id: int, payload: EmailChangeRequest, auth_service: AuthService = Depends(get_auth_service), vendors=Depends(get_vendor_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await auth_service.request_email_change(vendor_id, payload.new_email)


@router.post("/{vendor_id}/profile/email-change/confirm", dependencies=[Depends(_authorize_vendor_scope)])
async def confirm_email_change(vendor_id: int, payload: EmailVerificationConfirmRequest, auth_service: AuthService = Depends(get_auth_service), vendors=Depends(get_vendor_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await auth_service.confirm_email_change(vendor_id, payload.token)


@router.post("/{vendor_id}/profile/password", dependencies=[Depends(_authorize_vendor_scope)], response_model=StatusResponse)
async def change_password(vendor_id: int, payload: PasswordChangeRequest, auth_service: AuthService = Depends(get_auth_service), vendors=Depends(get_vendor_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await auth_service.change_password(vendor_id, payload.current_password, payload.new_password)
