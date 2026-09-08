from datetime import datetime, timedelta

from sqlalchemy import func, or_, select, update

from app.repositories.base import get_session
from app.repositories.models import (
    CatalogueImportItem,
    ConversationState,
    Customer,
    EmailVerificationToken,
    Message,
    Order,
    OrderLifecycleState,
    Product,
    Vendor,
    VendorBotSetting,
    VendorBusinessInfo,
    VendorCatalogueUpload,
    VendorCustomer,
    VendorGoogleSheetsToken,
    VendorGoogleToken,
)


def _vendor_dict(vendor: Vendor | None) -> dict | None:
    if not vendor:
        return None
    return {
        "id": vendor.id,
        "name": vendor.name,
        "email": vendor.email,
        "email_verified_at": vendor.email_verified_at,
        "pending_email": vendor.pending_email,
        "google_subject_id": vendor.google_subject_id,
        "instagram_user_id": vendor.instagram_user_id,
        "whatsapp_number": vendor.whatsapp_number,
        "whatsapp_token": vendor.whatsapp_token,
        "whatsapp_phone_number_id": vendor.whatsapp_phone_number_id,
        "instagram_page_id": vendor.instagram_page_id,
        "instagram_page_token": vendor.instagram_page_token,
        "telegram_bot_token": vendor.telegram_bot_token,
        "telegram_vendor_chat_id": vendor.telegram_vendor_chat_id,
        "account_number": vendor.account_number,
        "bank_name": vendor.bank_name,
        "account_name": vendor.account_name,
        "product_catalogue_url": vendor.product_catalogue_url,
        "product_catalogue_media_id": vendor.product_catalogue_media_id,
        "product_catalogue_caption": vendor.product_catalogue_caption,
    }


def _product_dict(product: Product | None) -> dict | None:
    if not product:
        return None
    return {
        "id": product.id,
        "vendor_id": product.vendor_id,
        "name": product.name,
        "description": product.description,
        "extra_details": product.extra_details,
        "price": float(product.price),
        "currency": product.currency,
        "image_url": product.image_url,
        "video_url": product.video_url,
        "in_stock": bool(product.in_stock),
    }


def _catalogue_upload_dict(upload: VendorCatalogueUpload | None) -> dict | None:
    if not upload:
        return None
    return {
        "id": upload.id,
        "vendor_id": upload.vendor_id,
        "file_name": upload.file_name,
        "mime_type": upload.mime_type,
        "source_url": upload.source_url,
        "status": upload.status,
        "extracted_text": upload.extracted_text,
        "error_message": upload.error_message,
        "created_at": upload.created_at,
        "processed_at": upload.processed_at,
    }


def _catalogue_item_dict(item: CatalogueImportItem | None) -> dict | None:
    if not item:
        return None
    return {
        "id": item.id,
        "upload_id": item.upload_id,
        "vendor_id": item.vendor_id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price) if item.price is not None else None,
        "currency": item.currency,
        "in_stock": bool(item.in_stock),
        "raw_text": item.raw_text,
        "status": item.status,
        "product_id": item.product_id,
        "created_at": item.created_at,
    }


class SQLVendorRepository:
    async def get_by_id(self, vendor_id: int) -> dict | None:
        async with get_session() as session:
            return _vendor_dict(await session.get(Vendor, vendor_id))

    async def get_by_email(self, email: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(select(Vendor).where(Vendor.email == email))).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def get_by_pending_email(self, email: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(select(Vendor).where(Vendor.pending_email == email))).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def get_by_google_subject_id(self, subject_id: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(select(Vendor).where(Vendor.google_subject_id == subject_id))).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def get_by_instagram_user_id(self, user_id: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(select(Vendor).where(Vendor.instagram_user_id == user_id))).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def get_password_hash(self, email: str) -> str | None:
        async with get_session() as session:
            vendor = (await session.execute(select(Vendor).where(Vendor.email == email))).scalar_one_or_none()
            return vendor.password_hash if vendor else None

    async def get_password_hash_by_id(self, vendor_id: int) -> str | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            return vendor.password_hash if vendor else None

    async def get_by_phone_number_id(self, phone_number_id: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(
                select(Vendor).where(Vendor.whatsapp_phone_number_id == phone_number_id)
            )).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def create_vendor(self, name: str, email: str, password_hash: str) -> dict:
        async with get_session() as session:
            vendor = Vendor(name=name, email=email, password_hash=password_hash)
            session.add(vendor)
            await session.flush()
            return _vendor_dict(vendor) or {}

    async def update_password_hash(self, vendor_id: int, password_hash: str) -> bool:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return False
            vendor.password_hash = password_hash
            await session.flush()
            return True

    async def set_email_verified(self, vendor_id: int) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            vendor.email_verified_at = datetime.utcnow()
            await session.flush()
            return _vendor_dict(vendor)

    async def set_pending_email(self, vendor_id: int, email: str | None) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            vendor.pending_email = email
            await session.flush()
            return _vendor_dict(vendor)

    async def apply_pending_email(self, vendor_id: int, email: str) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor or vendor.pending_email != email:
                return None
            vendor.email = email
            vendor.pending_email = None
            vendor.email_verified_at = datetime.utcnow()
            await session.flush()
            return _vendor_dict(vendor)

    async def update_profile(self, vendor_id: int, payload: dict) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            if "name" in payload:
                vendor.name = payload["name"]
            await session.flush()
            return _vendor_dict(vendor)

    async def link_google_subject(self, vendor_id: int, subject_id: str, mark_email_verified: bool = False) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            vendor.google_subject_id = subject_id
            if mark_email_verified:
                vendor.email_verified_at = vendor.email_verified_at or datetime.utcnow()
            await session.flush()
            return _vendor_dict(vendor)

    async def link_instagram_user(self, vendor_id: int, user_id: str) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            vendor.instagram_user_id = user_id
            await session.flush()
            return _vendor_dict(vendor)

    async def update_catalogue(self, vendor_id: int, payload: dict) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            for key in ("product_catalogue_url", "product_catalogue_media_id", "product_catalogue_caption"):
                if key in payload:
                    setattr(vendor, key, payload[key])
            await session.flush()
            return _vendor_dict(vendor)

    async def get_by_instagram_page_id(self, page_id: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(
                select(Vendor).where(Vendor.instagram_page_id == page_id)
            )).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def get_by_telegram_vendor_chat_id(self, chat_id: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(
                select(Vendor).where(Vendor.telegram_vendor_chat_id == chat_id)
            )).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def get_by_telegram_customer_chat_id(self, chat_id: str) -> dict | None:
        async with get_session() as session:
            vendor = (await session.execute(
                select(Vendor)
                .join(VendorCustomer, VendorCustomer.vendor_id == Vendor.id)
                .join(Customer, Customer.id == VendorCustomer.customer_id)
                .where(Customer.telegram_chat_id == chat_id)
                .order_by(VendorCustomer.last_seen_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            return _vendor_dict(vendor)

    async def update_instagram_credentials(self, vendor_id: int, page_id: str, page_token: str) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            vendor.instagram_page_id = page_id
            vendor.instagram_page_token = page_token
            await session.flush()
            return _vendor_dict(vendor)

    async def update_whatsapp_credentials(
        self,
        vendor_id: int,
        whatsapp_number: str | None = None,
        whatsapp_token: str | None = None,
        whatsapp_phone_number_id: str | None = None,
    ) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            if whatsapp_number is not None:
                vendor.whatsapp_number = whatsapp_number
            if whatsapp_token is not None:
                vendor.whatsapp_token = whatsapp_token
            if whatsapp_phone_number_id is not None:
                vendor.whatsapp_phone_number_id = whatsapp_phone_number_id
            await session.flush()
            return _vendor_dict(vendor)

    async def update_telegram_credentials(self, vendor_id: int, bot_token: str | None = None, vendor_chat_id: str | None = None) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            if bot_token is not None:
                vendor.telegram_bot_token = bot_token
            if vendor_chat_id is not None:
                vendor.telegram_vendor_chat_id = vendor_chat_id
            await session.flush()
            return _vendor_dict(vendor)


class SQLEmailVerificationRepository:
    async def create_token(self, vendor_id: int, token_hash: str, purpose: str, email: str, expires_at) -> dict:
        async with get_session() as session:
            row = EmailVerificationToken(
                vendor_id=vendor_id,
                token_hash=token_hash,
                purpose=purpose,
                email=email,
                expires_at=expires_at,
            )
            session.add(row)
            await session.flush()
            return {
                "id": row.id,
                "vendor_id": row.vendor_id,
                "purpose": row.purpose,
                "email": row.email,
                "expires_at": row.expires_at,
                "used_at": row.used_at,
            }

    async def consume_token(self, token_hash: str, purpose: str) -> dict | None:
        async with get_session() as session:
            now = datetime.utcnow()
            row = (await session.execute(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.token_hash == token_hash,
                    EmailVerificationToken.purpose == purpose,
                    EmailVerificationToken.used_at.is_(None),
                    EmailVerificationToken.expires_at > now,
                )
            )).scalar_one_or_none()
            if not row:
                return None
            row.used_at = now
            await session.flush()
            return {
                "id": row.id,
                "vendor_id": row.vendor_id,
                "purpose": row.purpose,
                "email": row.email,
                "expires_at": row.expires_at,
                "used_at": row.used_at,
            }


class SQLProductRepository:
    async def list_for_vendor(
        self,
        vendor_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
        in_stock: bool | None = None,
        search: str | None = None,
    ) -> list[dict]:
        async with get_session() as session:
            query = select(Product).where(Product.vendor_id == vendor_id)
            if in_stock is not None:
                query = query.where(Product.in_stock == in_stock)
            if search and search.strip():
                term = f"%{search.strip()}%"
                query = query.where(
                    or_(
                        Product.name.ilike(term),
                        Product.description.ilike(term),
                    )
                )

            rows = (await session.execute(
                query.order_by(Product.in_stock.desc(), Product.id.asc()).offset(offset).limit(limit)
            )).scalars().all()
            return [item for item in (_product_dict(row) for row in rows) if item]

    async def get_for_vendor(self, vendor_id: int, product_id: int) -> dict | None:
        async with get_session() as session:
            row = (await session.execute(
                select(Product).where(Product.vendor_id == vendor_id, Product.id == product_id)
            )).scalar_one_or_none()
            return _product_dict(row)

    async def create_for_vendor(self, vendor_id: int, payload: dict) -> dict:
        async with get_session() as session:
            row = Product(vendor_id=vendor_id, **payload)
            session.add(row)
            await session.flush()
            return _product_dict(row) or {}

    async def update_for_vendor(self, vendor_id: int, product_id: int, payload: dict) -> dict | None:
        async with get_session() as session:
            row = (await session.execute(
                select(Product).where(Product.vendor_id == vendor_id, Product.id == product_id)
            )).scalar_one_or_none()
            if not row:
                return None
            for key, value in payload.items():
                setattr(row, key, value)
            await session.flush()
            return _product_dict(row)

    async def delete_for_vendor(self, vendor_id: int, product_id: int) -> bool:
        async with get_session() as session:
            row = (await session.execute(
                select(Product).where(Product.vendor_id == vendor_id, Product.id == product_id)
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            return True


class SQLCatalogueRepository:
    async def create_upload(self, vendor_id: int, payload: dict) -> dict:
        async with get_session() as session:
            row = VendorCatalogueUpload(vendor_id=vendor_id, **payload)
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return _catalogue_upload_dict(row) or {}

    async def get_upload_for_vendor(self, vendor_id: int, upload_id: int) -> dict | None:
        async with get_session() as session:
            row = (await session.execute(
                select(VendorCatalogueUpload).where(
                    VendorCatalogueUpload.vendor_id == vendor_id,
                    VendorCatalogueUpload.id == upload_id,
                )
            )).scalar_one_or_none()
            return _catalogue_upload_dict(row)

    async def list_uploads_for_vendor(self, vendor_id: int) -> list[dict]:
        async with get_session() as session:
            rows = (await session.execute(
                select(VendorCatalogueUpload)
                .where(VendorCatalogueUpload.vendor_id == vendor_id)
                .order_by(VendorCatalogueUpload.id.desc())
            )).scalars().all()
            return [item for item in (_catalogue_upload_dict(row) for row in rows) if item]

    async def mark_upload_processed(self, vendor_id: int, upload_id: int, extracted_text: str, item_payloads: list[dict]) -> dict | None:
        async with get_session() as session:
            upload = (await session.execute(
                select(VendorCatalogueUpload).where(
                    VendorCatalogueUpload.vendor_id == vendor_id,
                    VendorCatalogueUpload.id == upload_id,
                )
            )).scalar_one_or_none()
            if not upload:
                return None

            upload.status = "PROCESSED"
            upload.extracted_text = extracted_text
            upload.error_message = None
            upload.processed_at = datetime.utcnow()

            for payload in item_payloads:
                session.add(CatalogueImportItem(vendor_id=vendor_id, upload_id=upload_id, **payload))

            if extracted_text.strip():
                session.add(
                    VendorBusinessInfo(
                        vendor_id=vendor_id,
                        title=f"Catalogue: {upload.file_name}",
                        content=extracted_text.strip(),
                        source_type="CATALOGUE",
                    )
                )

            await session.flush()
            return _catalogue_upload_dict(upload)

    async def mark_upload_failed(self, vendor_id: int, upload_id: int, error_message: str) -> dict | None:
        async with get_session() as session:
            upload = (await session.execute(
                select(VendorCatalogueUpload).where(
                    VendorCatalogueUpload.vendor_id == vendor_id,
                    VendorCatalogueUpload.id == upload_id,
                )
            )).scalar_one_or_none()
            if not upload:
                return None
            upload.status = "FAILED"
            upload.error_message = error_message
            upload.processed_at = datetime.utcnow()
            await session.flush()
            return _catalogue_upload_dict(upload)

    async def list_items_for_upload(self, vendor_id: int, upload_id: int) -> list[dict]:
        async with get_session() as session:
            rows = (await session.execute(
                select(CatalogueImportItem)
                .where(
                    CatalogueImportItem.vendor_id == vendor_id,
                    CatalogueImportItem.upload_id == upload_id,
                )
                .order_by(CatalogueImportItem.id.asc())
            )).scalars().all()
            return [item for item in (_catalogue_item_dict(row) for row in rows) if item]

    async def import_item_as_product(self, vendor_id: int, item_id: int) -> dict | None:
        async with get_session() as session:
            item = (await session.execute(
                select(CatalogueImportItem).where(
                    CatalogueImportItem.vendor_id == vendor_id,
                    CatalogueImportItem.id == item_id,
                )
            )).scalar_one_or_none()
            if not item:
                return None
            if item.product_id:
                product = await session.get(Product, item.product_id)
                return _product_dict(product)
            if item.price is None:
                return None

            product = Product(
                vendor_id=vendor_id,
                name=item.name,
                description=item.description,
                price=item.price,
                currency=item.currency,
                in_stock=item.in_stock,
            )
            session.add(product)
            await session.flush()
            item.product_id = product.id
            item.status = "IMPORTED"
            await session.flush()
            return _product_dict(product)

    async def import_items_as_products(self, vendor_id: int, item_payloads: list[dict]) -> list[dict]:
        if not item_payloads:
            return []

        async with get_session() as session:
            item_ids = [payload["id"] for payload in item_payloads]
            rows = (await session.execute(
                select(CatalogueImportItem).where(
                    CatalogueImportItem.vendor_id == vendor_id,
                    CatalogueImportItem.id.in_(item_ids),
                )
            )).scalars().all()
            items_by_id = {row.id: row for row in rows}
            products: list[dict] = []

            for payload in item_payloads:
                item = items_by_id.get(payload["id"])
                if not item:
                    continue

                item.name = payload["name"]
                item.description = payload.get("description")
                item.price = payload["price"]
                item.currency = payload.get("currency", "NGN")
                item.in_stock = payload.get("in_stock", True)

                if item.product_id:
                    product = await session.get(Product, item.product_id)
                    if product:
                        product.name = item.name
                        product.description = item.description
                        product.price = item.price
                        product.currency = item.currency
                        product.in_stock = item.in_stock
                        await session.flush()
                        product_dict = _product_dict(product)
                        if product_dict:
                            products.append(product_dict)
                    continue

                product = Product(
                    vendor_id=vendor_id,
                    name=item.name,
                    description=item.description,
                    price=item.price,
                    currency=item.currency,
                    in_stock=item.in_stock,
                )
                session.add(product)
                await session.flush()
                item.product_id = product.id
                item.status = "IMPORTED"
                product_dict = _product_dict(product)
                if product_dict:
                    products.append(product_dict)

            await session.flush()
            return products


class SQLCustomerRepository:
    async def get_or_create_by_whatsapp(self, whatsapp_number: str, display_name: str | None = None) -> dict:
        async with get_session() as session:
            customer = (await session.execute(
                select(Customer).where(Customer.whatsapp_number == whatsapp_number)
            )).scalar_one_or_none()
            if customer:
                if display_name and not customer.name:
                    customer.name = display_name
                    await session.flush()
                return {
                    "id": customer.id,
                    "name": customer.name,
                    "whatsapp_number": customer.whatsapp_number,
                }
            customer = Customer(whatsapp_number=whatsapp_number, name=display_name, phone=whatsapp_number)
            session.add(customer)
            await session.flush()
            return {
                "id": customer.id,
                "name": customer.name,
                "whatsapp_number": customer.whatsapp_number,
            }

    async def get_or_create_by_instagram(self, instagram_id: str, display_name: str | None = None) -> dict:
        async with get_session() as session:
            customer = (await session.execute(
                select(Customer).where(Customer.instagram_id == instagram_id)
            )).scalar_one_or_none()
            if customer:
                if display_name and not customer.name:
                    customer.name = display_name
                    await session.flush()
                return {
                    "id": customer.id,
                    "name": customer.name,
                    "instagram_id": customer.instagram_id,
                }
            customer = Customer(instagram_id=instagram_id, name=display_name)
            session.add(customer)
            await session.flush()
            return {
                "id": customer.id,
                "name": customer.name,
                "instagram_id": customer.instagram_id,
            }

    async def get_or_create_by_telegram(self, telegram_id: str, chat_id: str, display_name: str | None = None) -> dict:
        async with get_session() as session:
            customer = (await session.execute(
                select(Customer).where(
                    or_(
                        Customer.telegram_id == telegram_id,
                        Customer.telegram_chat_id == chat_id,
                    )
                )
            )).scalar_one_or_none()
            if customer:
                if display_name and not customer.name:
                    customer.name = display_name
                if not customer.telegram_id:
                    customer.telegram_id = telegram_id
                if not customer.telegram_chat_id:
                    customer.telegram_chat_id = chat_id
                await session.flush()
                return {
                    "id": customer.id,
                    "name": customer.name,
                    "telegram_id": customer.telegram_id,
                    "telegram_chat_id": customer.telegram_chat_id,
                }
            customer = Customer(telegram_id=telegram_id, telegram_chat_id=chat_id, name=display_name)
            session.add(customer)
            await session.flush()
            return {
                "id": customer.id,
                "name": customer.name,
                "telegram_id": customer.telegram_id,
                "telegram_chat_id": customer.telegram_chat_id,
            }

    async def upsert_vendor_customer(self, vendor_id: int, customer_id: int) -> None:
        async with get_session() as session:
            relation = (await session.execute(
                select(VendorCustomer).where(
                    VendorCustomer.vendor_id == vendor_id,
                    VendorCustomer.customer_id == customer_id,
                )
            )).scalar_one_or_none()
            if relation:
                return
            session.add(VendorCustomer(vendor_id=vendor_id, customer_id=customer_id))
            await session.flush()

    async def upsert_conversation_state(self, vendor_id: int, customer_id: int, last_message: str | None) -> None:
        async with get_session() as session:
            state = (await session.execute(
                select(ConversationState).where(
                    ConversationState.vendor_id == vendor_id,
                    ConversationState.customer_id == customer_id,
                )
            )).scalar_one_or_none()
            if state:
                state.last_message = last_message
            else:
                session.add(
                    ConversationState(vendor_id=vendor_id, customer_id=customer_id, last_message=last_message)
                )
            await session.flush()

    async def record_message(
        self,
        *,
        vendor_id: int,
        customer_id: int,
        direction: str,
        message_type: str,
        body_text: str | None,
        whatsapp_message_id: str | None = None,
        sender_number: str | None = None,
        recipient_number: str | None = None,
    ) -> None:
        async with get_session() as session:
            session.add(
                Message(
                    vendor_id=vendor_id,
                    customer_id=customer_id,
                    direction=direction,
                    message_type=message_type,
                    whatsapp_message_id=whatsapp_message_id,
                    sender_number=sender_number,
                    recipient_number=recipient_number,
                    body_text=body_text,
                )
            )
            await session.flush()

    async def list_messages(self, vendor_id: int, customer_id: int, limit: int = 10) -> list[dict]:
        async with get_session() as session:
            query = select(Message).where(
                Message.vendor_id == vendor_id,
                Message.customer_id == customer_id,
            ).order_by(Message.id.desc()).limit(limit)
            rows = (await session.execute(query)).scalars().all()
            return [
                {
                    "direction": row.direction,
                    "body_text": row.body_text,
                }
                for row in reversed(rows)
            ]

    async def upsert_order_lifecycle_state(
        self,
        *,
        vendor_id: int,
        customer_id: int,
        status: str,
        last_event_text: str | None,
    ) -> None:
        async with get_session() as session:
            row = (await session.execute(
                select(OrderLifecycleState).where(
                    OrderLifecycleState.vendor_id == vendor_id,
                    OrderLifecycleState.customer_id == customer_id,
                )
            )).scalar_one_or_none()
            if row:
                row.status = status
                row.last_event_text = last_event_text
            else:
                session.add(
                    OrderLifecycleState(
                        vendor_id=vendor_id,
                        customer_id=customer_id,
                        status=status,
                        last_event_text=last_event_text,
                    )
                )
            await session.flush()

    async def get_order_lifecycle_state(self, *, vendor_id: int, customer_id: int) -> dict | None:
        async with get_session() as session:
            row = (await session.execute(
                select(OrderLifecycleState).where(
                    OrderLifecycleState.vendor_id == vendor_id,
                    OrderLifecycleState.customer_id == customer_id,
                )
            )).scalar_one_or_none()
            if not row:
                return None
            return {
                "vendor_id": row.vendor_id,
                "customer_id": row.customer_id,
                "status": row.status,
                "last_event_text": row.last_event_text,
                "updated_at": row.updated_at,
            }

    async def get_google_contact_saved(self, *, vendor_id: int, customer_id: int) -> bool:
        async with get_session() as session:
            row = (await session.execute(
                select(ConversationState).where(
                    ConversationState.vendor_id == vendor_id,
                    ConversationState.customer_id == customer_id,
                )
            )).scalar_one_or_none()
            return bool(row and row.google_contact_saved)

    async def set_google_contact_saved(self, *, vendor_id: int, customer_id: int, saved: bool = True) -> None:
        async with get_session() as session:
            row = (await session.execute(
                select(ConversationState).where(
                    ConversationState.vendor_id == vendor_id,
                    ConversationState.customer_id == customer_id,
                )
            )).scalar_one_or_none()
            if not row:
                session.add(
                    ConversationState(
                        vendor_id=vendor_id,
                        customer_id=customer_id,
                        google_contact_saved=saved,
                    )
                )
            else:
                row.google_contact_saved = saved
            await session.flush()


class SQLVendorSettingsRepository:
    async def get(self, vendor_id: int) -> dict:
        async with get_session() as session:
            row = await session.get(VendorBotSetting, vendor_id)
            if not row:
                return {
                    "confirm_before_sending_account_details": False,
                    "enable_knowledge_base_answers": True,
                    "use_product_availability": True,
                    "sheets_sync_enabled": False,
                    "sheets_spreadsheet_id": None,
                    "sheets_spreadsheet_title": None,
                    "sheets_tab_name": None,
                }
            return {
                "confirm_before_sending_account_details": bool(row.confirm_before_sending_account_details),
                "enable_knowledge_base_answers": bool(row.enable_knowledge_base_answers),
                "use_product_availability": bool(row.use_product_availability),
                "sheets_sync_enabled": bool(row.sheets_sync_enabled),
                "sheets_spreadsheet_id": row.sheets_spreadsheet_id,
                "sheets_spreadsheet_title": row.sheets_spreadsheet_title,
                "sheets_tab_name": row.sheets_tab_name,
            }

    async def upsert(self, vendor_id: int, payload: dict) -> dict:
        async with get_session() as session:
            row = await session.get(VendorBotSetting, vendor_id)
            if not row:
                row = VendorBotSetting(vendor_id=vendor_id)
                session.add(row)
            for key, value in payload.items():
                setattr(row, key, value)
            await session.flush()
            await session.refresh(row)
            return {
                "confirm_before_sending_account_details": bool(row.confirm_before_sending_account_details),
                "enable_knowledge_base_answers": bool(row.enable_knowledge_base_answers),
                "use_product_availability": bool(row.use_product_availability),
                "sheets_sync_enabled": bool(row.sheets_sync_enabled),
                "sheets_spreadsheet_id": row.sheets_spreadsheet_id,
                "sheets_spreadsheet_title": row.sheets_spreadsheet_title,
                "sheets_tab_name": row.sheets_tab_name,
            }


class SQLGoogleTokenRepository:
    async def get_token_json(self, vendor_id: int) -> str | None:
        async with get_session() as session:
            row = await session.get(VendorGoogleToken, vendor_id)
            return row.token_json if row else None

    async def upsert_token_json(self, vendor_id: int, token_json: str) -> None:
        async with get_session() as session:
            row = await session.get(VendorGoogleToken, vendor_id)
            if row:
                row.token_json = token_json
            else:
                session.add(VendorGoogleToken(vendor_id=vendor_id, token_json=token_json))
            await session.flush()

    async def delete_for_vendor(self, vendor_id: int) -> bool:
        async with get_session() as session:
            row = await session.get(VendorGoogleToken, vendor_id)
            if not row:
                return False
            await session.delete(row)
            return True


class SQLGoogleSheetsTokenRepository:
    async def get_token_json(self, vendor_id: int) -> str | None:
        async with get_session() as session:
            row = await session.get(VendorGoogleSheetsToken, vendor_id)
            return row.token_json if row else None

    async def upsert_token_json(self, vendor_id: int, token_json: str) -> None:
        async with get_session() as session:
            row = await session.get(VendorGoogleSheetsToken, vendor_id)
            if row:
                row.token_json = token_json
            else:
                session.add(VendorGoogleSheetsToken(vendor_id=vendor_id, token_json=token_json))
            await session.flush()

    async def delete_for_vendor(self, vendor_id: int) -> bool:
        async with get_session() as session:
            row = await session.get(VendorGoogleSheetsToken, vendor_id)
            if not row:
                return False
            await session.delete(row)
            return True


class SQLOrderRepository:
    def _order_dict(self, row: Order) -> dict:
        return {
            "id": row.id,
            "vendor_id": row.vendor_id,
            "customer_id": row.customer_id,
            "status": row.status,
            "order_ref": row.order_ref,
            "customer_name": row.customer_name,
            "customer_phone": row.customer_phone,
            "customer_platform": row.customer_platform,
            "customer_handle": row.customer_handle,
            "order_details": row.order_details,
            "sheets_synced": bool(row.sheets_synced),
            "sheets_sync_attempts": row.sheets_sync_attempts,
            "sheets_synced_at": row.sheets_synced_at,
            "sheets_last_error": row.sheets_last_error,
            "next_attempt_at": row.next_attempt_at,
            "created_at": row.created_at,
        }

    async def create_order(self, vendor_id: int, payload: dict) -> dict:
        async with get_session() as session:
            # vendor_id + customer_id uniqueness is enforced at the call site via the
            # lifecycle-transition guard; here we just persist the snapshot.
            row = Order(
                vendor_id=vendor_id,
                customer_id=payload.get("customer_id"),
                status=payload.get("status") or "ACCOUNT_DETAILS_SENT",
                order_ref="PENDING",  # placeholder; replaced with ORD-{id} below
                customer_name=payload.get("customer_name"),
                customer_phone=payload.get("customer_phone"),
                customer_platform=payload.get("customer_platform") or "whatsapp",
                customer_handle=payload.get("customer_handle"),
                order_details=payload.get("order_details"),
            )
            session.add(row)
            await session.flush()
            row.order_ref = f"ORD-{row.id:06d}"
            await session.flush()
            await session.refresh(row)
            return self._order_dict(row)

    async def get_for_vendor(self, vendor_id: int, order_id: int) -> dict | None:
        async with get_session() as session:
            row = (await session.execute(
                select(Order).where(Order.vendor_id == vendor_id, Order.id == order_id)
            )).scalar_one_or_none()
            return self._order_dict(row) if row else None

    async def mark_synced(self, order_id: int) -> None:
        async with get_session() as session:
            row = await session.get(Order, order_id)
            if not row:
                return
            row.sheets_synced = True
            row.sheets_synced_at = datetime.utcnow()
            row.sheets_last_error = None
            row.next_attempt_at = None
            await session.flush()

    async def record_sync_failure(self, order_id: int, error: str, retry_delay_seconds: int) -> None:
        async with get_session() as session:
            row = await session.get(Order, order_id)
            if not row:
                return
            row.sheets_sync_attempts += 1
            row.sheets_last_error = error
            row.next_attempt_at = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)
            await session.flush()

    async def claim_pending(self, limit: int = 50) -> list[dict]:
        """Optimistic-lock claim: rows claimed by one worker get a distinct claim
        expiry, so two workers racing on the same row cannot both claim it."""
        now = datetime.utcnow()
        claim_expiry = now + timedelta(minutes=5)
        async with get_session() as session:
            await session.execute(
                update(Order)
                .where(
                    Order.sheets_synced == False,  # noqa: E712
                    or_(Order.next_attempt_at == None, Order.next_attempt_at <= now),  # noqa: E711
                    or_(Order.sync_claimed_until == None, Order.sync_claimed_until <= now),  # noqa: E711
                )
                .values(sync_claimed_until=claim_expiry)
                .execution_options(synchronize_session=False)
            )
            await session.flush()
            rows = (await session.execute(
                select(Order).where(
                    Order.sheets_synced == False,  # noqa: E712
                    Order.sync_claimed_until == claim_expiry,
                ).order_by(Order.id).limit(limit)
            )).scalars().all()
            return [self._order_dict(row) for row in rows]

    async def list_pending_for_vendor(self, vendor_id: int) -> list[dict]:
        async with get_session() as session:
            rows = (await session.execute(
                select(Order).where(
                    Order.vendor_id == vendor_id,
                    Order.sheets_synced == False,  # noqa: E712
                ).order_by(Order.id.desc())
            )).scalars().all()
            return [self._order_dict(row) for row in rows]

    async def count_for_vendor(self, vendor_id: int, synced: bool) -> int:
        async with get_session() as session:
            result = await session.execute(
                select(func.count()).select_from(Order).where(
                    Order.vendor_id == vendor_id,
                    Order.sheets_synced == synced,  # noqa: E712
                )
            )
            return int(result.scalar() or 0)


class SQLBusinessInfoRepository:
    async def list_for_vendor(self, vendor_id: int) -> list[dict]:
        async with get_session() as session:
            rows = (await session.execute(
                select(VendorBusinessInfo).where(VendorBusinessInfo.vendor_id == vendor_id)
            )).scalars().all()
            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "content": row.content,
                    "source_type": row.source_type,
                    "updated_at": row.updated_at,
                }
                for row in rows
            ]

    async def create_for_vendor(self, vendor_id: int, payload: dict) -> dict:
        async with get_session() as session:
            row = VendorBusinessInfo(vendor_id=vendor_id, **payload)
            session.add(row)
            await session.flush()
            await session.refresh(row)
            return {
                "id": row.id,
                "title": row.title,
                "content": row.content,
                "source_type": row.source_type,
                "updated_at": row.updated_at,
            }

    async def delete_for_vendor(self, vendor_id: int, info_id: int) -> bool:
        async with get_session() as session:
            row = (await session.execute(
                select(VendorBusinessInfo).where(
                    VendorBusinessInfo.vendor_id == vendor_id,
                    VendorBusinessInfo.id == info_id,
                )
            )).scalar_one_or_none()
            if not row:
                return False
            await session.delete(row)
            return True

    async def search(self, vendor_id: int, query: str) -> str | None:
        """Simple keyword search across business info content."""
        async with get_session() as session:
            normalized = query.strip().lower()
            if not normalized:
                return None
            
            term = f"%{normalized}%"
            row = (await session.execute(
                select(VendorBusinessInfo)
                .where(VendorBusinessInfo.vendor_id == vendor_id)
                .where(or_(
                    VendorBusinessInfo.title.ilike(term),
                    VendorBusinessInfo.content.ilike(term)
                ))
                .limit(1)
            )).scalar_one_or_none()
            
            return row.content if row else None
