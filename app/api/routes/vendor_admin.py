from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import (
    get_auth_service,
    get_knowledge_repo,
    get_product_repo,
    get_settings_repo,
    get_vendor_repo,
)
from app.exceptions import AuthorizationError, ResourceNotFoundError
from app.schemas.api import (
    DeleteResponse,
    ErrorResponse,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
    VendorCatalogueResponse,
    VendorCatalogueUpdateRequest,
    VendorDashboardResponse,
    VendorSettingsResponse,
    VendorSettingsUpdateRequest,
)

STANDARD_ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Validation error",
        "content": {"application/json": {"example": {"error": {"code": "validation_error", "message": "Invalid request", "details": {}}}}},
    },
    401: {
        "model": ErrorResponse,
        "description": "Authentication error",
        "content": {"application/json": {"example": {"error": {"code": "authentication_error", "message": "Invalid or expired token", "details": {}}}}},
    },
    403: {
        "model": ErrorResponse,
        "description": "Authorization error",
        "content": {"application/json": {"example": {"error": {"code": "authorization_error", "message": "Access denied", "details": {}}}}},
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource not found",
        "content": {"application/json": {"example": {"error": {"code": "resource_not_found", "message": "Vendor not found", "details": {}}}}},
    },
    409: {
        "model": ErrorResponse,
        "description": "Conflict",
        "content": {"application/json": {"example": {"error": {"code": "conflict", "message": "Resource conflict", "details": {}}}}},
    },
    429: {
        "model": ErrorResponse,
        "description": "Rate limit exceeded",
        "content": {"application/json": {"example": {"error": {"code": "too_many_requests", "message": "Rate limit exceeded", "details": {}}}}},
    },
}


router = APIRouter(prefix="/vendors", tags=["vendor-admin"], responses=STANDARD_ERROR_RESPONSES)
security = HTTPBearer()


async def _vendor_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth=Depends(get_auth_service),
) -> int:
    return auth.decode_token(credentials.credentials)


async def _authorize_vendor_scope(vendor_id: int, token_vendor_id: int = Depends(_vendor_from_token)) -> int:
    if token_vendor_id != vendor_id:
        raise AuthorizationError("Token vendor cannot access this vendor resource")
    return token_vendor_id


async def _ensure_vendor(vendor_id: int, vendors) -> dict:
    vendor = await vendors.get_by_id(vendor_id)
    if not vendor:
        raise ResourceNotFoundError("Vendor not found")
    return vendor


@router.get("/{vendor_id}/dashboard", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorDashboardResponse)
async def dashboard(vendor_id: int, vendors=Depends(get_vendor_repo), settings_repo=Depends(get_settings_repo), knowledge_repo=Depends(get_knowledge_repo), products=Depends(get_product_repo)) -> dict:
    vendor = await _ensure_vendor(vendor_id, vendors)
    return {
        "vendor": vendor,
        "settings": await settings_repo.get(vendor_id),
        "products": await products.list_for_vendor(vendor_id),
        "knowledge_entries": await knowledge_repo.list_for_vendor(vendor_id),
        "catalogue": {
            "product_catalogue_url": vendor.get("product_catalogue_url"),
            "product_catalogue_media_id": vendor.get("product_catalogue_media_id"),
            "product_catalogue_caption": vendor.get("product_catalogue_caption"),
        },
    }


@router.get("/{vendor_id}/products", dependencies=[Depends(_authorize_vendor_scope)], response_model=ProductListResponse)
async def list_products(
    vendor_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    in_stock: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=120),
    vendors=Depends(get_vendor_repo),
    products=Depends(get_product_repo),
) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    rows = await products.list_for_vendor(
        vendor_id,
        limit=limit + 1,
        offset=offset,
        in_stock=in_stock,
        search=search,
    )
    has_more = len(rows) > limit
    return {
        "items": rows[:limit],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
    }


@router.post("/{vendor_id}/products", dependencies=[Depends(_authorize_vendor_scope)], status_code=201, response_model=ProductResponse)
async def create_product(vendor_id: int, payload: ProductCreateRequest, vendors=Depends(get_vendor_repo), products=Depends(get_product_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await products.create_for_vendor(vendor_id, payload.model_dump(mode="json"))


@router.patch("/{vendor_id}/products/{product_id}", dependencies=[Depends(_authorize_vendor_scope)], response_model=ProductResponse)
async def update_product(vendor_id: int, product_id: int, payload: ProductUpdateRequest, vendors=Depends(get_vendor_repo), products=Depends(get_product_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    updated = await products.update_for_vendor(vendor_id, product_id, payload.model_dump(exclude_unset=True, mode="json"))
    if not updated:
        raise ResourceNotFoundError("Product not found")
    return updated


@router.delete("/{vendor_id}/products/{product_id}", dependencies=[Depends(_authorize_vendor_scope)], response_model=DeleteResponse)
async def delete_product(vendor_id: int, product_id: int, vendors=Depends(get_vendor_repo), products=Depends(get_product_repo)) -> DeleteResponse:
    await _ensure_vendor(vendor_id, vendors)
    deleted = await products.delete_for_vendor(vendor_id, product_id)
    if not deleted:
        raise ResourceNotFoundError("Product not found")
    return DeleteResponse(status="deleted")


@router.get("/{vendor_id}/bot-settings", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorSettingsResponse)
async def get_bot_settings(vendor_id: int, vendors=Depends(get_vendor_repo), settings_repo=Depends(get_settings_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await settings_repo.get(vendor_id)


@router.put("/{vendor_id}/bot-settings", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorSettingsResponse)
async def upsert_bot_settings(vendor_id: int, payload: VendorSettingsUpdateRequest, vendors=Depends(get_vendor_repo), settings_repo=Depends(get_settings_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await settings_repo.upsert(vendor_id, payload.model_dump(exclude_unset=True))


@router.get("/{vendor_id}/catalogue", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorCatalogueResponse)
async def get_catalogue(vendor_id: int, vendors=Depends(get_vendor_repo)) -> VendorCatalogueResponse:
    vendor = await _ensure_vendor(vendor_id, vendors)
    return VendorCatalogueResponse(
        product_catalogue_url=vendor.get("product_catalogue_url"),
        product_catalogue_media_id=vendor.get("product_catalogue_media_id"),
        product_catalogue_caption=vendor.get("product_catalogue_caption"),
    )


@router.put("/{vendor_id}/catalogue", dependencies=[Depends(_authorize_vendor_scope)], response_model=VendorCatalogueResponse)
async def update_catalogue(vendor_id: int, payload: VendorCatalogueUpdateRequest, vendors=Depends(get_vendor_repo)) -> VendorCatalogueResponse:
    await _ensure_vendor(vendor_id, vendors)
    updated = await vendors.update_catalogue(vendor_id, payload.model_dump(exclude_unset=True, mode="json"))
    if not updated:
        raise ResourceNotFoundError("Vendor not found")
    return VendorCatalogueResponse(
        product_catalogue_url=updated.get("product_catalogue_url"),
        product_catalogue_media_id=updated.get("product_catalogue_media_id"),
        product_catalogue_caption=updated.get("product_catalogue_caption"),
    )
