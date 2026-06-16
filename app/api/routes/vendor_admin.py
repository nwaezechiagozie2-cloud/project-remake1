import base64

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx

from app.api.deps import (
    get_auth_service,
    get_business_info_repo,
    get_catalogue_repo,
    get_google_token_repo,
    get_product_repo,
    get_settings_repo,
    get_vendor_repo,
)
from app.config import get_settings
from app.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError
from app.schemas.api import (
    BusinessInfoCreateRequest,
    BusinessInfoResponse,
    CatalogueBulkImportRequest,
    CatalogueImportItemResponse,
    CatalogueUploadCreateRequest,
    CatalogueUploadResponse,
    DeleteResponse,
    ErrorResponse,
    InstagramCredentialsRequest,
    InstagramCredentialsResponse,
    ProductAvailabilityUpdateRequest,
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
    TelegramCredentialsRequest,
    TelegramCredentialsResponse,
    ProductUpdateRequest,
    VendorCatalogueResponse,
    VendorCatalogueUpdateRequest,
    VendorDashboardResponse,
    VendorSettingsResponse,
    VendorSettingsUpdateRequest,
    WhatsAppCredentialsRequest,
    WhatsAppCredentialsResponse,
)
from app.services.catalogue_ingestion_service import CatalogueIngestionService

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
async def dashboard(vendor_id: int, vendors=Depends(get_vendor_repo), settings_repo=Depends(get_settings_repo), business_info=Depends(get_business_info_repo), products=Depends(get_product_repo)) -> dict:
    vendor = await _ensure_vendor(vendor_id, vendors)
    return {
        "vendor": vendor,
        "settings": await settings_repo.get(vendor_id),
        "products": await products.list_for_vendor(vendor_id),
        "business_info": await business_info.list_for_vendor(vendor_id),
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


@router.patch("/{vendor_id}/products/{product_id}/availability", dependencies=[Depends(_authorize_vendor_scope)], response_model=ProductResponse)
async def update_product_availability(vendor_id: int, product_id: int, payload: ProductAvailabilityUpdateRequest, vendors=Depends(get_vendor_repo), products=Depends(get_product_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    updated = await products.update_for_vendor(vendor_id, product_id, {"in_stock": payload.in_stock})
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


@router.post("/{vendor_id}/catalogue/uploads", dependencies=[Depends(_authorize_vendor_scope)], status_code=201, response_model=CatalogueUploadResponse)
async def upload_catalogue_base64(vendor_id: int, payload: CatalogueUploadCreateRequest, vendors=Depends(get_vendor_repo), catalogue=Depends(get_catalogue_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except ValueError as exc:
        raise ValidationError("content_base64 must be valid base64") from exc
    service = CatalogueIngestionService(catalogue)
    return await service.ingest_file(vendor_id, payload.file_name, payload.mime_type, content)


@router.get("/{vendor_id}/catalogue/uploads", dependencies=[Depends(_authorize_vendor_scope)], response_model=list[CatalogueUploadResponse])
async def list_catalogue_uploads(vendor_id: int, vendors=Depends(get_vendor_repo), catalogue=Depends(get_catalogue_repo)) -> list[dict]:
    await _ensure_vendor(vendor_id, vendors)
    return await catalogue.list_uploads_for_vendor(vendor_id)


@router.get("/{vendor_id}/catalogue/uploads/{upload_id}/items", dependencies=[Depends(_authorize_vendor_scope)], response_model=list[CatalogueImportItemResponse])
async def list_catalogue_import_items(vendor_id: int, upload_id: int, vendors=Depends(get_vendor_repo), catalogue=Depends(get_catalogue_repo)) -> list[dict]:
    await _ensure_vendor(vendor_id, vendors)
    upload = await catalogue.get_upload_for_vendor(vendor_id, upload_id)
    if not upload:
        raise ResourceNotFoundError("Catalogue upload not found")
    return await catalogue.list_items_for_upload(vendor_id, upload_id)


@router.post("/{vendor_id}/catalogue/items/{item_id}/import", dependencies=[Depends(_authorize_vendor_scope)], status_code=201, response_model=ProductResponse)
async def import_catalogue_item(vendor_id: int, item_id: int, vendors=Depends(get_vendor_repo), catalogue=Depends(get_catalogue_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    product = await catalogue.import_item_as_product(vendor_id, item_id)
    if not product:
        raise ResourceNotFoundError("Catalogue item not found or missing price")
    return product


@router.post("/{vendor_id}/catalogue/items/import-bulk", dependencies=[Depends(_authorize_vendor_scope)], status_code=201, response_model=list[ProductResponse])
async def import_catalogue_items(vendor_id: int, payload: CatalogueBulkImportRequest, vendors=Depends(get_vendor_repo), catalogue=Depends(get_catalogue_repo)) -> list[dict]:
    await _ensure_vendor(vendor_id, vendors)
    products = await catalogue.import_items_as_products(vendor_id, [item.model_dump(mode="json") for item in payload.items])
    if not products:
        raise ResourceNotFoundError("No catalogue items were imported")
    return products


@router.get("/{vendor_id}/business-info", dependencies=[Depends(_authorize_vendor_scope)], response_model=list[BusinessInfoResponse])
async def list_business_info(vendor_id: int, vendors=Depends(get_vendor_repo), business_info=Depends(get_business_info_repo)) -> list[dict]:
    await _ensure_vendor(vendor_id, vendors)
    return await business_info.list_for_vendor(vendor_id)


@router.delete("/{vendor_id}/google-contacts", dependencies=[Depends(_authorize_vendor_scope)], response_model=DeleteResponse)
async def disconnect_google_contacts(vendor_id: int, vendors=Depends(get_vendor_repo), google_tokens=Depends(get_google_token_repo)) -> DeleteResponse:
    await _ensure_vendor(vendor_id, vendors)
    await google_tokens.delete_for_vendor(vendor_id)
    return DeleteResponse(status="deleted")


@router.post("/{vendor_id}/business-info", dependencies=[Depends(_authorize_vendor_scope)], status_code=201, response_model=BusinessInfoResponse)
async def create_business_info(vendor_id: int, payload: BusinessInfoCreateRequest, vendors=Depends(get_vendor_repo), business_info=Depends(get_business_info_repo)) -> dict:
    await _ensure_vendor(vendor_id, vendors)
    return await business_info.create_for_vendor(vendor_id, payload.model_dump(mode="json"))


@router.delete("/{vendor_id}/business-info/{info_id}", dependencies=[Depends(_authorize_vendor_scope)], response_model=DeleteResponse)
async def delete_business_info(vendor_id: int, info_id: int, vendors=Depends(get_vendor_repo), business_info=Depends(get_business_info_repo)) -> DeleteResponse:
    await _ensure_vendor(vendor_id, vendors)
    deleted = await business_info.delete_for_vendor(vendor_id, info_id)
    if not deleted:
        raise ResourceNotFoundError("Business info not found")
    return DeleteResponse(status="deleted")


@router.put("/{vendor_id}/instagram-credentials", dependencies=[Depends(_authorize_vendor_scope)], response_model=InstagramCredentialsResponse)
async def update_instagram_credentials(
    vendor_id: int,
    payload: InstagramCredentialsRequest,
    vendors=Depends(get_vendor_repo),
) -> InstagramCredentialsResponse:
    """Save Instagram page credentials for this vendor."""
    await _ensure_vendor(vendor_id, vendors)

    page_id = payload.instagram_page_id
    if not page_id.isdigit():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://graph.instagram.com/me",
                    params={
                        "fields": "id,username",
                        "access_token": payload.instagram_page_token,
                    },
                )
                response.raise_for_status()
                resolved_id = response.json().get("id")
        except Exception as exc:
            raise ValidationError(
                "instagram_page_id must be the numeric Instagram account ID, or the token must be valid so the app can resolve it.",
                details={"instagram_page_id": page_id},
            ) from exc

        if not resolved_id:
            raise ValidationError(
                "Could not resolve numeric Instagram account ID from the access token.",
                details={"instagram_page_id": page_id},
            )
        page_id = str(resolved_id)

    updated = await vendors.update_instagram_credentials(
        vendor_id,
        page_id=page_id,
        page_token=payload.instagram_page_token,
    )
    if not updated:
        raise ResourceNotFoundError("Vendor not found")
    return InstagramCredentialsResponse(
        instagram_page_id=updated.get("instagram_page_id"),
        connected=True,
        message="Instagram credentials saved successfully.",
    )


@router.get("/{vendor_id}/instagram-credentials", dependencies=[Depends(_authorize_vendor_scope)], response_model=InstagramCredentialsResponse)
async def get_instagram_credentials(
    vendor_id: int,
    vendors=Depends(get_vendor_repo),
) -> InstagramCredentialsResponse:
    """Check if Instagram is connected for this vendor."""
    vendor = await _ensure_vendor(vendor_id, vendors)
    page_id = vendor.get("instagram_page_id")
    return InstagramCredentialsResponse(
        instagram_page_id=page_id,
        connected=bool(page_id and vendor.get("instagram_page_token")),
        message="Instagram is connected." if page_id else "Instagram is not connected.",
    )


@router.put("/{vendor_id}/whatsapp-credentials", dependencies=[Depends(_authorize_vendor_scope)], response_model=WhatsAppCredentialsResponse)
async def update_whatsapp_credentials(
    vendor_id: int,
    payload: WhatsAppCredentialsRequest,
    vendors=Depends(get_vendor_repo),
) -> WhatsAppCredentialsResponse:
    if not any(
        value is not None
        for value in (
            payload.whatsapp_number,
            payload.whatsapp_token,
            payload.whatsapp_phone_number_id,
        )
    ):
        raise ValidationError("At least one WhatsApp credential field is required")

    await _ensure_vendor(vendor_id, vendors)
    updated = await vendors.update_whatsapp_credentials(
        vendor_id,
        whatsapp_number=payload.whatsapp_number,
        whatsapp_token=payload.whatsapp_token,
        whatsapp_phone_number_id=payload.whatsapp_phone_number_id,
    )
    if not updated:
        raise ResourceNotFoundError("Vendor not found")
    return _whatsapp_credentials_response(updated, "WhatsApp credentials saved successfully.")


@router.get("/{vendor_id}/whatsapp-credentials", dependencies=[Depends(_authorize_vendor_scope)], response_model=WhatsAppCredentialsResponse)
async def get_whatsapp_credentials(
    vendor_id: int,
    vendors=Depends(get_vendor_repo),
) -> WhatsAppCredentialsResponse:
    vendor = await _ensure_vendor(vendor_id, vendors)
    return _whatsapp_credentials_response(vendor)


def _whatsapp_credentials_response(vendor: dict, message: str | None = None) -> WhatsAppCredentialsResponse:
    phone_number = vendor.get("whatsapp_number")
    phone_number_id = vendor.get("whatsapp_phone_number_id")
    has_access_token = bool(vendor.get("whatsapp_token"))
    connected = bool(phone_number and phone_number_id and has_access_token)
    return WhatsAppCredentialsResponse(
        whatsapp_number=phone_number,
        whatsapp_phone_number_id=phone_number_id,
        has_access_token=has_access_token,
        connected=connected,
        webhook_url="/webhook",
        message=message or ("WhatsApp is connected." if connected else "WhatsApp is not connected."),
    )


@router.put("/{vendor_id}/telegram-credentials", dependencies=[Depends(_authorize_vendor_scope)], response_model=TelegramCredentialsResponse)
async def update_telegram_credentials(
    vendor_id: int,
    payload: TelegramCredentialsRequest,
    vendors=Depends(get_vendor_repo),
) -> TelegramCredentialsResponse:
    await _ensure_vendor(vendor_id, vendors)
    updated = await vendors.update_telegram_credentials(
        vendor_id,
        bot_token=payload.telegram_bot_token,
        vendor_chat_id=payload.telegram_vendor_chat_id,
    )
    if not updated:
        raise ResourceNotFoundError("Vendor not found")
    return _telegram_credentials_response(updated)


@router.get("/{vendor_id}/telegram-credentials", dependencies=[Depends(_authorize_vendor_scope)], response_model=TelegramCredentialsResponse)
async def get_telegram_credentials(
    vendor_id: int,
    vendors=Depends(get_vendor_repo),
) -> TelegramCredentialsResponse:
    vendor = await _ensure_vendor(vendor_id, vendors)
    return _telegram_credentials_response(vendor)


def _telegram_credentials_response(vendor: dict) -> TelegramCredentialsResponse:
    has_bot_token = bool(vendor.get("telegram_bot_token"))
    chat_id = vendor.get("telegram_vendor_chat_id")
    return TelegramCredentialsResponse(
        telegram_vendor_chat_id=chat_id,
        has_bot_token=has_bot_token,
        connected=has_bot_token,
        webhook_url="/telegram/webhook",
        message="Telegram is connected." if has_bot_token else "Telegram is not connected.",
    )


@router.post("/{vendor_id}/telegram-webhook", dependencies=[Depends(_authorize_vendor_scope)])
async def configure_telegram_webhook(
    vendor_id: int,
    vendors=Depends(get_vendor_repo),
) -> dict:
    vendor = await _ensure_vendor(vendor_id, vendors)
    token = vendor.get("telegram_bot_token") or get_settings().telegram_bot_token
    if not token:
        raise ValidationError("Telegram bot token is not configured")

    settings = get_settings()
    webhook_url = f"{settings.public_api_base_url.rstrip('/')}/telegram/webhook"
    if "localhost" in webhook_url or "127.0.0.1" in webhook_url:
        raise ValidationError("Set PUBLIC_API_BASE_URL to the public backend base URL before configuring Telegram webhook")

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={
                "url": webhook_url,
                "secret_token": settings.telegram_webhook_secret or None,
                "allowed_updates": ["message", "edited_message", "callback_query"],
            },
        )
    if response.status_code >= 400:
        raise ValidationError("Telegram setWebhook failed", details={"body": response.text[:500]})
    return {"status": "ok", "webhook_url": webhook_url}
