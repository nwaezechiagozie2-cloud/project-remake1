import asyncio

from app.domain.models import ParsedInboundMessage
from app.services.agent_service import AgentService
from app.services.llm_service import IntentService
from app.services.webhook_service import WebhookService
from app.config import Settings


class _VendorRepo:
    async def get_by_phone_number_id(self, phone_number_id: str) -> dict | None:
        if phone_number_id != "phone-1":
            return None
        return {
            "id": 10,
            "name": "Demo Vendor",
            "whatsapp_number": "2347000000000",
            "whatsapp_phone_number_id": "phone-1",
            "bank_name": "Demo Bank",
            "account_name": "Demo Store",
            "account_number": "1234567890",
            "product_catalogue_url": None,
            "product_catalogue_media_id": None,
            "product_catalogue_caption": None,
        }


class _CustomerRepo:
    def __init__(self) -> None:
        self._ids: dict[str, int] = {}
        self._next_id = 1
        self.order_states: list[dict] = []

    async def get_or_create_by_whatsapp(self, whatsapp_number: str, display_name: str | None = None) -> dict:
        if whatsapp_number not in self._ids:
            self._ids[whatsapp_number] = self._next_id
            self._next_id += 1
        return {"id": self._ids[whatsapp_number], "name": display_name, "whatsapp_number": whatsapp_number}

    async def upsert_vendor_customer(self, vendor_id: int, customer_id: int) -> None:
        return None

    async def upsert_conversation_state(self, vendor_id: int, customer_id: int, last_message: str | None) -> None:
        return None

    async def record_message(self, **kwargs) -> None:
        return None

    async def upsert_order_lifecycle_state(self, **kwargs) -> None:
        self.order_states.append(kwargs)

    async def get_order_lifecycle_state(self, *, vendor_id: int, customer_id: int) -> dict | None:
        return None

    async def get_google_contact_saved(self, *, vendor_id: int, customer_id: int) -> bool:
        return False

    async def set_google_contact_saved(self, *, vendor_id: int, customer_id: int, saved: bool = True) -> None:
        return None


class _ProductRepo:
    PRODUCTS = [
        {
            "id": 1,
            "vendor_id": 10,
            "name": "Retro Analog Clock",
            "description": "Walnut",
            "extra_details": "2-year warranty",
            "price": 14500,
            "currency": "NGN",
            "in_stock": True,
        }
    ]

    async def list_for_vendor(self, vendor_id: int, *, limit: int = 50, offset: int = 0, in_stock: bool | None = None, search: str | None = None) -> list[dict]:
        results = self.PRODUCTS
        if search and search.strip():
            term = search.strip().lower()
            results = [
                p for p in results
                if term in (p.get("name") or "").lower() or term in (p.get("description") or "").lower()
            ]
        return results


class _Contacts:
    async def save_if_new(self, vendor_id: int, display_name: str, whatsapp_number: str) -> bool:
        return True


class _WhatsApp:
    def __init__(self) -> None:
        self.sent_text: list[dict] = []
        self.sent_buttons: list[dict] = []

    async def send_text(self, vendor: dict, to: str, body: str) -> None:
        self.sent_text.append({"to": to, "body": body})

    async def send_buttons(self, vendor: dict, to: str, body: str, buttons: list[dict]) -> None:
        self.sent_buttons.append({"to": to, "body": body, "buttons": buttons})


def _payload_text(from_number: str, body: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "User"}}],
                            "messages": [{"id": "wamid.x", "from": from_number, "type": "text", "text": {"body": body}}],
                        }
                    }
                ]
            }
        ],
    }


def _payload_interactive(from_number: str, button_id: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "Vendor"}}],
                            "messages": [
                                {
                                    "id": "wamid.y",
                                    "from": from_number,
                                    "type": "interactive",
                                    "interactive": {"button_reply": {"id": button_id, "title": "Approve"}},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }


class _IntentMock:
    async def classify(self, incoming_message: str, ad_context: dict | None = None) -> str:
        return "purchase_intent"

    async def generate_dynamic_response(self, context: str, instruction: str) -> str | None:
        if "bank details" in instruction.lower():
            return "Here are the payment details."
        if "approve checkout" in instruction.lower() or "vendors" in instruction.lower():
            return "Please approve checkout."
        return "Generating generic mock state."

    async def match_product_from_catalogue(self, incoming_message: str, products: list[dict]) -> int | None:
        if not products:
            return None
        # In test, always match the first product
        return products[0]["id"]

    async def extract_search_terms(self, incoming_message: str) -> list[str]:
        # In test, extract simple words as search terms
        words = incoming_message.lower().split()
        return [w for w in words if len(w) > 3 and w not in ("want", "this", "that", "have")]


class _KnowledgeRepo:
    async def list_for_vendor(self, vendor_id: int) -> list[dict]:
        return []

    async def search(self, vendor_id: int, query: str, allowed_types: list[str] | None = None) -> dict | None:
        return None


class _SettingsRepo:
    async def get(self, vendor_id: int) -> dict:
        return {
            "confirm_before_sending_account_details": False,
            "enable_knowledge_base_answers": True,
            "allow_product_qa": True,
            "allow_office_qa": True,
        }

    async def upsert(self, vendor_id: int, payload: dict) -> dict:
        return payload

def test_purchase_intent_to_vendor_approval_integration() -> None:
    customers = _CustomerRepo()
    whatsapp = _WhatsApp()
    agent = AgentService(
        intent_service=_IntentMock(),
        products=_ProductRepo(),
        knowledge=_KnowledgeRepo(),
        settings=_SettingsRepo(),
    )
    service = WebhookService(
        vendors=_VendorRepo(),
        customers=customers,
        contacts=_Contacts(),
        agent=agent,
        whatsapp=whatsapp,
    )

    customer_number = "2348011111111"
    vendor_number = "2347000000000"

    first = asyncio.run(service.handle_payload(_payload_text(customer_number, "I want to buy this")))
    second = asyncio.run(service.handle_payload(_payload_interactive(vendor_number, f"btn_approve::{customer_number}")))

    assert first == {"status": "ok", "messages_received": 1}
    assert second == {"status": "ok", "messages_received": 1}

    # Verify vendor got the approval prompt
    assert any("approve checkout" in entry["body"].lower() for entry in whatsapp.sent_buttons)
    # Verify customer got the payment details
    assert any(entry["to"] == customer_number and "payment details" in entry["body"].lower() for entry in whatsapp.sent_text)
    
    assert any(state.get("status") == "WAITING_VENDOR_CHECKOUT_APPROVAL" for state in customers.order_states)
    assert any(state.get("status") == "ACCOUNT_DETAILS_SENT" for state in customers.order_states)
