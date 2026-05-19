from datetime import datetime

from sqlalchemy import or_, select

from app.repositories.base import get_session
from app.repositories.models import (
    CatalogueImportItem,
    ConversationState,
    Customer,
    Message,
    OrderLifecycleState,
    Product,
    Vendor,
    VendorBotSetting,
    VendorBusinessInfo,
    VendorCatalogueUpload,
    VendorCustomer,
    VendorGoogleToken,
)


def _vendor_dict(vendor: Vendor | None) -> dict | None:
    if not vendor:
        return None
    return {
        "id": vendor.id,
        "name": vendor.name,
        "email": vendor.email,
        "whatsapp_number": vendor.whatsapp_number,
        "whatsapp_token": vendor.whatsapp_token,
        "whatsapp_phone_number_id": vendor.whatsapp_phone_number_id,
        "instagram_page_id": vendor.instagram_page_id,
        "instagram_page_token": vendor.instagram_page_token,
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

    async def get_password_hash(self, email: str) -> str | None:
        async with get_session() as session:
            vendor = (await session.execute(select(Vendor).where(Vendor.email == email))).scalar_one_or_none()
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

    async def update_instagram_credentials(self, vendor_id: int, page_id: str, page_token: str) -> dict | None:
        async with get_session() as session:
            vendor = await session.get(Vendor, vendor_id)
            if not vendor:
                return None
            vendor.instagram_page_id = page_id
            vendor.instagram_page_token = page_token
            await session.flush()
            return _vendor_dict(vendor)


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
                    "allow_product_qa": True,
                    "allow_office_qa": True,
                    "use_product_availability": True,
                }
            return {
                "confirm_before_sending_account_details": bool(row.confirm_before_sending_account_details),
                "enable_knowledge_base_answers": bool(row.enable_knowledge_base_answers),
                "allow_product_qa": bool(row.allow_product_qa),
                "allow_office_qa": bool(row.allow_office_qa),
                "use_product_availability": bool(row.use_product_availability),
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
            return {
                "confirm_before_sending_account_details": bool(row.confirm_before_sending_account_details),
                "enable_knowledge_base_answers": bool(row.enable_knowledge_base_answers),
                "allow_product_qa": bool(row.allow_product_qa),
                "allow_office_qa": bool(row.allow_office_qa),
                "use_product_availability": bool(row.use_product_availability),
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
