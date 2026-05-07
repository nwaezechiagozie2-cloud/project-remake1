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


    name: str = Field(min_length=2, max_length=255)
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
                "allow_product_qa": True,
                "allow_office_qa": True,
            }
        }
    )

    confirm_before_sending_account_details: bool | None = None
    enable_knowledge_base_answers: bool | None = None
    allow_product_qa: bool | None = None
    allow_office_qa: bool | None = None


class VendorSettingsResponse(BaseModel):
    confirm_before_sending_account_details: bool
    enable_knowledge_base_answers: bool
    allow_product_qa: bool
    allow_office_qa: bool


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


class VendorProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    whatsapp_number: str | None = None
    whatsapp_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    account_number: str | None = None
    bank_name: str | None = None
    account_name: str | None = None
    product_catalogue_url: str | None = None
    product_catalogue_media_id: str | None = None
    product_catalogue_caption: str | None = None


class KnowledgeEntryResponse(BaseModel):
    id: int
    entry_type: str
    title: str | None = None
    question: str | None = None
    answer: str
    keywords: str | None = None
    is_active: bool


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
    knowledge_entries: list[KnowledgeEntryResponse]
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
