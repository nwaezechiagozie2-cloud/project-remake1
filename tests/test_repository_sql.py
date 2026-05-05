import asyncio
import uuid

from sqlalchemy import delete

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
from app.repositories.sql import (
    SQLCustomerRepository,
    SQLGoogleTokenRepository,
    SQLProductRepository,
    SQLVendorRepository,
)


async def _reset_tables() -> None:
    async with get_session() as session:
        await session.execute(delete(Message))
        await session.execute(delete(OrderLifecycleState))
        await session.execute(delete(ConversationState))
        await session.execute(delete(VendorCustomer))
        await session.execute(delete(Product))
        await session.execute(delete(VendorGoogleToken))
        await session.execute(delete(Customer))
        await session.execute(delete(Vendor))


def test_vendor_and_product_repository_flow() -> None:
    asyncio.run(_reset_tables())
    vendors = SQLVendorRepository()
    products = SQLProductRepository()

    email = f"repo-{uuid.uuid4().hex[:8]}@example.com"
    vendor = asyncio.run(vendors.create_vendor(name="Repo Vendor", email=email, password_hash="hash"))

    created_1 = asyncio.run(
        products.create_for_vendor(
            vendor["id"],
            {
                "name": "Retro Analog Clock",
                "description": "Walnut",
                "extra_details": "2-year warranty",
                "price": 14500,
                "currency": "NGN",
                "in_stock": True,
            },
        )
    )
    created_2 = asyncio.run(
        products.create_for_vendor(
            vendor["id"],
            {
                "name": "Desk Lamp",
                "description": "LED",
                "extra_details": "Matte black",
                "price": 25000,
                "currency": "NGN",
                "in_stock": False,
            },
        )
    )

    page = asyncio.run(products.list_for_vendor(vendor["id"], limit=1, offset=0, in_stock=None, search="Desk"))
    in_stock_only = asyncio.run(products.list_for_vendor(vendor["id"], limit=10, offset=0, in_stock=True, search=None))

    assert created_1["id"] != created_2["id"]
    assert len(page) == 1
    assert page[0]["name"] == "Desk Lamp"
    assert len(in_stock_only) == 1
    assert in_stock_only[0]["name"] == "Retro Analog Clock"


def test_customer_and_token_repositories_flow() -> None:
    asyncio.run(_reset_tables())
    vendors = SQLVendorRepository()
    customers = SQLCustomerRepository()
    tokens = SQLGoogleTokenRepository()

    vendor = asyncio.run(vendors.create_vendor(name="Repo Vendor", email=f"repo-{uuid.uuid4().hex[:8]}@example.com", password_hash="hash"))
    customer = asyncio.run(customers.get_or_create_by_whatsapp("2348011111111", "Sarah"))

    asyncio.run(customers.upsert_vendor_customer(vendor_id=vendor["id"], customer_id=customer["id"]))
    asyncio.run(customers.upsert_conversation_state(vendor_id=vendor["id"], customer_id=customer["id"], last_message="Hi"))
    asyncio.run(customers.set_google_contact_saved(vendor_id=vendor["id"], customer_id=customer["id"], saved=True))

    saved = asyncio.run(customers.get_google_contact_saved(vendor_id=vendor["id"], customer_id=customer["id"]))

    asyncio.run(tokens.upsert_token_json(vendor_id=vendor["id"], token_json='{"token":"abc"}'))
    token = asyncio.run(tokens.get_token_json(vendor_id=vendor["id"]))

    assert saved is True
    assert token == '{"token":"abc"}'
