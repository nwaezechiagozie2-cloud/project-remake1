import asyncio
import sys
from pathlib import Path

import bcrypt
from sqlalchemy import delete

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.base import get_session
from app.repositories.models import (
    ConversationState,
    Customer,
    Message,
    OrderLifecycleState,
    Product,
    Vendor,
    VendorCustomer,
    VendorGoogleToken,
)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


async def seed() -> None:
    async with get_session() as session:
        await session.execute(delete(Message))
        await session.execute(delete(OrderLifecycleState))
        await session.execute(delete(ConversationState))
        await session.execute(delete(VendorCustomer))
        await session.execute(delete(Product))
        await session.execute(delete(VendorGoogleToken))
        await session.execute(delete(Customer))
        await session.execute(delete(Vendor))

        vendor = Vendor(
            name="Acme Home",
            email="owner@acmehome.com",
            password_hash=_hash_password("supersecurepassword"),
            whatsapp_number="2347000000000",
            whatsapp_phone_number_id="phone-1",
            whatsapp_token="demo-token",
            bank_name="Demo Bank",
            account_name="Acme Home Ltd",
            account_number="0123456789",
            product_catalogue_caption="Spring collection",
            product_catalogue_url="https://cdn.example.com/catalogue.pdf",
            product_catalogue_media_id="media_abc123",
        )
        session.add(vendor)
        await session.flush()

        products = [
            Product(
                vendor_id=vendor.id,
                name="Retro Analog Clock",
                description="Handmade walnut desk clock",
                price=14500,
                currency="NGN",
                in_stock=True,
            ),
            Product(
                vendor_id=vendor.id,
                name="Minimalist Desk Lamp",
                description="Soft-warm LED lamp",
                price=25000,
                currency="NGN",
                in_stock=True,
            ),
            Product(
                vendor_id=vendor.id,
                name="Ergonomic Chair",
                description="Lumbar support office chair",
                price=85000,
                currency="NGN",
                in_stock=False,
            ),
        ]
        session.add_all(products)

        customer = Customer(
            whatsapp_number="2348011111111",
            name="Sarah Jenkins",
            phone="2348011111111",
            delivery_address="12 Palm Avenue, Ikeja, Lagos",
        )
        session.add(customer)
        await session.flush()

        session.add(VendorCustomer(vendor_id=vendor.id, customer_id=customer.id))
        session.add(
            ConversationState(
                vendor_id=vendor.id,
                customer_id=customer.id,
                last_message="I want to buy the retro analog clock",
                google_contact_saved=True,
            )
        )
        session.add(
            OrderLifecycleState(
                vendor_id=vendor.id,
                customer_id=customer.id,
                status="WAITING_VENDOR_CHECKOUT_APPROVAL",
                last_event_text="I am ready to checkout",
            )
        )
        session.add_all(
            [
                Message(
                    vendor_id=vendor.id,
                    customer_id=customer.id,
                    direction="INBOUND",
                    message_type="text",
                    whatsapp_message_id="wamid.seed.1",
                    sender_number=customer.whatsapp_number,
                    recipient_number=vendor.whatsapp_number,
                    body_text="I am ready to checkout",
                ),
                Message(
                    vendor_id=vendor.id,
                    customer_id=customer.id,
                    direction="OUTBOUND",
                    message_type="interactive",
                    sender_number=vendor.whatsapp_number,
                    recipient_number=vendor.whatsapp_number,
                    body_text="Customer is ready to checkout. Approve?",
                ),
            ]
        )

        session.add(
            VendorGoogleToken(
                vendor_id=vendor.id,
                token_json='{"token": "demo-access-token", "refresh_token": "demo-refresh-token"}',
            )
        )

    print("Seed complete: 1 vendor, 3 products, 1 customer, messages/conversation/order state.")


if __name__ == "__main__":
    asyncio.run(seed())
