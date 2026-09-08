from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    pending_email: Mapped[str | None] = mapped_column(String(255), unique=True)
    google_subject_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    instagram_user_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    whatsapp_token: Mapped[str | None] = mapped_column(Text)
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    instagram_page_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    instagram_page_token: Mapped[str | None] = mapped_column(Text)
    telegram_bot_token: Mapped[str | None] = mapped_column(Text)
    telegram_vendor_chat_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    account_number: Mapped[str | None] = mapped_column(String(30))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    account_name: Mapped[str | None] = mapped_column(String(255))
    product_catalogue_url: Mapped[str | None] = mapped_column(Text)
    product_catalogue_media_id: Mapped[str | None] = mapped_column(String(255))
    product_catalogue_caption: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VendorBotSetting(Base):
    __tablename__ = "vendor_bot_settings"

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True)
    confirm_before_sending_account_details: Mapped[bool] = mapped_column(Boolean, server_default=text("0"))
    enable_knowledge_base_answers: Mapped[bool] = mapped_column(Boolean, server_default=text("1"))
    use_product_availability: Mapped[bool] = mapped_column(Boolean, server_default=text("1"))
    sheets_sync_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("0"))
    sheets_spreadsheet_id: Mapped[str | None] = mapped_column(String(100))
    sheets_spreadsheet_title: Mapped[str | None] = mapped_column(String(255))
    sheets_tab_name: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VendorBusinessInfo(Base):
    __tablename__ = "vendor_business_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), server_default=text("'TEXT'"))  # TEXT, PDF
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VendorCatalogueUpload(Base):
    __tablename__ = "vendor_catalogue_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), server_default=text("'PENDING'"))
    extracted_text: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)


class CatalogueImportItem(Base):
    __tablename__ = "catalogue_import_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("vendor_catalogue_uploads.id", ondelete="CASCADE"), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(10), server_default=text("'NGN'"))
    in_stock: Mapped[bool] = mapped_column(Boolean, server_default=text("1"))
    raw_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), server_default=text("'DRAFT'"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    extra_details: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), server_default=text("'NGN'"))
    image_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    in_stock: Mapped[bool] = mapped_column(Boolean, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    instagram_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    telegram_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    delivery_address: Mapped[str | None] = mapped_column(Text)


class VendorCustomer(Base):
    __tablename__ = "vendor_customers"
    __table_args__ = (UniqueConstraint("vendor_id", "customer_id", name="uq_vendor_customer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ConversationState(Base):
    __tablename__ = "conversation_states"

    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_message: Mapped[str | None] = mapped_column(Text)
    google_contact_saved: Mapped[bool] = mapped_column(Boolean, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(Enum("INBOUND", "OUTBOUND", name="message_direction", native_enum=False))
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(255))
    sender_number: Mapped[str | None] = mapped_column(String(50))
    recipient_number: Mapped[str | None] = mapped_column(String(50))
    body_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class OrderLifecycleState(Base):
    __tablename__ = "order_lifecycle_states"

    vendor_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    last_event_text: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VendorGoogleToken(Base):
    __tablename__ = "vendor_google_tokens"

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True)
    token_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VendorGoogleSheetsToken(Base):
    __tablename__ = "vendor_google_sheets_tokens"

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True)
    token_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False, server_default=text("'ACCOUNT_DETAILS_SENT'"))
    order_ref: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    # Denormalized customer snapshot so the row is self-contained for the sheet
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(50))
    customer_platform: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_handle: Mapped[str | None] = mapped_column(String(100))
    # AI-generated free-text order details (what the customer is buying)
    order_details: Mapped[str | None] = mapped_column(Text)
    # Sheets sync state
    sheets_synced: Mapped[bool] = mapped_column(Boolean, server_default=text("0"), index=True)
    sheets_sync_attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    sheets_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    sheets_last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    sync_claimed_until: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
