from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorBody


class VendorRegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Acme Studio",
                "email": "owner@acme.com",
                "password": "supersecurepassword",
            }
        }
    )


    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class VendorLoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "owner@acme.com",
                "password": "supersecurepassword",
            }
        }
    )

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": 12,
                "token": "<jwt-token>",
            }
        }
    )

    vendor_id: int
    token: str
    email_verified: bool | None = None
    email_verification: dict[str, Any] | None = None


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationConfirmRequest(BaseModel):
    token: str = Field(min_length=16)


class EmailChangeRequest(BaseModel):
    new_email: EmailStr


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class VendorProfileAuthResponse(BaseModel):
    vendor_id: int
    name: str
    email: str
    email_verified: bool
    email_verified_at: datetime | None = None
    pending_email: str | None = None
    providers: dict[str, bool] = Field(default_factory=dict)


class VendorProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class StatusResponse(BaseModel):
    status: str


class GoogleOAuthStatusResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "vendor_id": 12,
                "has_credentials": True,
                "status": "connected",
                "is_expired": False,
                "has_refresh_token": True,
                "last_error": None,
            }
        }
    )

    vendor_id: int
    has_credentials: bool
    status: str
    is_expired: bool
    has_refresh_token: bool
    last_error: str | None = None


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Retro Analog Clock",
                "price": 14500.0,
                "description": "A handmade walnut desk clock",
                "extra_details": "2-year warranty",
                "currency": "NGN",
                "image_url": "https://cdn.example.com/clock.jpg",
                "video_url": "https://cdn.example.com/clock.mp4",
                "in_stock": True,
            }
        }
    )

    name: str = Field(min_length=2, max_length=255)
    price: float = Field(ge=0.01, le=100_000_000)
    description: str | None = None
    extra_details: str | None = None
    currency: str = Field(default="NGN", pattern=r"^[A-Z]{3}$", min_length=3, max_length=3)
    image_url: HttpUrl | None = None
    video_url: HttpUrl | None = None
    in_stock: bool = True


class ProductUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": 15000.0,
                "currency": "NGN",
                "in_stock": False,
            }
        }
    )

    name: str | None = Field(default=None, min_length=2, max_length=255)
    price: float | None = Field(default=None, ge=0.01, le=100_000_000)
    description: str | None = None
    extra_details: str | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$", min_length=3, max_length=3)
    image_url: HttpUrl | None = None
    video_url: HttpUrl | None = None
    in_stock: bool | None = None


class ProductAvailabilityUpdateRequest(BaseModel):
    in_stock: bool


class ProductResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    price: float
    description: str | None = None
    extra_details: str | None = None
    currency: str
    image_url: str | None = None
    video_url: str | None = None
    in_stock: bool


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    limit: int
    offset: int
    has_more: bool


class VendorSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "confirm_before_sending_account_details": True,
                "enable_knowledge_base_answers": True,
                "use_product_availability": True,
            }
        }
    )

    confirm_before_sending_account_details: bool | None = None
    enable_knowledge_base_answers: bool | None = None
    use_product_availability: bool | None = None


class VendorSettingsResponse(BaseModel):
    confirm_before_sending_account_details: bool
    enable_knowledge_base_answers: bool
    use_product_availability: bool


class VendorCatalogueUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product_catalogue_url": "https://cdn.example.com/catalogue.pdf",
                "product_catalogue_media_id": "media_123",
                "product_catalogue_caption": "Latest products",
            }
        }
    )

    product_catalogue_url: HttpUrl | None = None
    product_catalogue_media_id: str | None = None
    product_catalogue_caption: str | None = None


class VendorCatalogueResponse(BaseModel):
    product_catalogue_url: str | None = None
    product_catalogue_media_id: str | None = None
    product_catalogue_caption: str | None = None


class CatalogueUploadResponse(BaseModel):
    id: int
    vendor_id: int
    file_name: str
    mime_type: str | None = None
    source_url: str | None = None
    status: str
    extracted_text: str | None = None
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None


class CatalogueUploadCreateRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str | None = Field(default=None, max_length=120)
    content_base64: str = Field(min_length=1)


class CatalogueImportItemResponse(BaseModel):
    id: int
    upload_id: int
    vendor_id: int
    name: str
    description: str | None = None
    price: float | None = None
    currency: str
    in_stock: bool
    raw_text: str | None = None
    status: str
    product_id: int | None = None
    created_at: datetime


class CatalogueBulkImportItemRequest(BaseModel):
    id: int
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    price: float = Field(ge=0.01, le=100_000_000)
    currency: str = Field(default="NGN", pattern=r"^[A-Z]{3}$", min_length=3, max_length=3)
    in_stock: bool = True


class CatalogueBulkImportRequest(BaseModel):
    items: list[CatalogueBulkImportItemRequest] = Field(min_length=1)


class VendorProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    whatsapp_number: str | None = None
    whatsapp_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    instagram_page_id: str | None = None
    instagram_connected: bool = False
    account_number: str | None = None
    bank_name: str | None = None
    account_name: str | None = None
    product_catalogue_url: str | None = None
    product_catalogue_media_id: str | None = None
    product_catalogue_caption: str | None = None


class BusinessInfoCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    content: str = Field(min_length=10)
    source_type: str = Field(default="TEXT")


class BusinessInfoResponse(BaseModel):
    id: int
    title: str
    content: str
    source_type: str
    updated_at: datetime


class VendorDashboardResponse(BaseModel):
    vendor: VendorProfileResponse
    settings: VendorSettingsResponse
    products: list[ProductResponse]
    business_info: list[BusinessInfoResponse]
    catalogue: VendorCatalogueResponse


class DeleteResponse(BaseModel):
    status: Literal["deleted"]


class WebhookReceiveResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "messages_received": 1,
            }
        }
    )

    status: str
    messages_received: int


class InstagramCredentialsRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "instagram_page_id": "17841400123456789",
                "instagram_page_token": "EAABwzLixn...",
            }
        }
    )

    instagram_page_id: str = Field(min_length=1, max_length=100)
    instagram_page_token: str = Field(min_length=1)


class InstagramCredentialsResponse(BaseModel):
    instagram_page_id: str | None = None
    connected: bool = False
    message: str = ""


class WhatsAppCredentialsRequest(BaseModel):
    whatsapp_number: str | None = Field(default=None, min_length=1, max_length=50)
    whatsapp_token: str | None = Field(default=None, min_length=1)
    whatsapp_phone_number_id: str | None = Field(default=None, min_length=1, max_length=100)


class WhatsAppCredentialsResponse(BaseModel):
    whatsapp_number: str | None = None
    whatsapp_phone_number_id: str | None = None
    has_access_token: bool = False
    connected: bool = False
    webhook_url: str
    message: str = ""


class TelegramCredentialsRequest(BaseModel):
    telegram_bot_token: str | None = Field(default=None, min_length=1)
    telegram_vendor_chat_id: str | None = Field(default=None, min_length=1, max_length=100)


class TelegramCredentialsResponse(BaseModel):
    telegram_vendor_chat_id: str | None = None
    has_bot_token: bool = False
    connected: bool = False
    webhook_url: str
    message: str = ""
