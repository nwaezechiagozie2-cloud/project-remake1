import asyncio
from datetime import datetime, timedelta, timezone

from app.domain.models import AgentDecision, ParsedInboundMessage
from app.services.agent_service import AgentService
from app.services.webhook_service import WebhookService


class _VendorRepo:
    async def get_by_phone_number_id(self, phone_number_id: str) -> dict | None:
        if phone_number_id != "phone-1":
            return None
        return {
            "id": 7,
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
        self.recorded_messages: list[dict] = []
        self.order_states: list[dict] = []
        self.google_contact_saved = False

    async def get_or_create_by_whatsapp(self, whatsapp_number: str, display_name: str | None = None) -> dict:
        return {"id": 99, "name": display_name or "Customer", "whatsapp_number": whatsapp_number}

    async def upsert_vendor_customer(self, vendor_id: int, customer_id: int) -> None:
        return None

    async def upsert_conversation_state(self, vendor_id: int, customer_id: int, last_message: str | None) -> None:
        return None

    async def record_message(self, **kwargs) -> None:
        self.recorded_messages.append(kwargs)

    async def upsert_order_lifecycle_state(self, **kwargs) -> None:
        self.order_states.append(kwargs)

    async def get_order_lifecycle_state(self, *, vendor_id: int, customer_id: int) -> dict | None:
        return None

    async def get_google_contact_saved(self, *, vendor_id: int, customer_id: int) -> bool:
        return self.google_contact_saved

    async def set_google_contact_saved(self, *, vendor_id: int, customer_id: int, saved: bool = True) -> None:
        self.google_contact_saved = saved


class _Contacts:
    async def save_if_new(self, vendor_id: int, display_name: str, whatsapp_number: str) -> bool:
        return True


class _Agent:
    async def decide(self, vendor: dict, message: ParsedInboundMessage, is_vendor_sender: bool) -> AgentDecision:
        return AgentDecision(
            customer_text="I’m confirming with the store, I’ll update you shortly.",
            vendor_text="Customer is ready to checkout. Approve?",
            vendor_buttons=[
                {"id": "btn_approve::2348011111111", "title": "✅ APPROVE"},
                {"id": "btn_deny::2348011111111", "title": "❌ DENY"},
            ],
            order_status="WAITING_VENDOR_CHECKOUT_APPROVAL",
        )


class _WhatsApp:
    async def send_text(self, vendor: dict, to: str, body: str) -> None:
        return None

    async def send_buttons(self, vendor: dict, to: str, body: str, buttons: list[dict]) -> None:
        return None


def test_webhook_persists_inbound_and_outbound_messages() -> None:
    customers = _CustomerRepo()
    service = WebhookService(
        vendors=_VendorRepo(),
        customers=customers,
        contacts=_Contacts(),
        agent=_Agent(),
        whatsapp=_WhatsApp(),
    )

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "Chi"}}],
                            "messages": [
                                {
                                    "id": "wamid.inbound.1",
                                    "from": "2348011111111",
                                    "type": "text",
                                    "text": {"body": "I want to buy this"},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }

    result = asyncio.run(service.handle_payload(payload))

    assert result == {"status": "ok", "messages_received": 1}
    assert len(customers.recorded_messages) == 3
    assert customers.recorded_messages[0]["direction"] == "INBOUND"
    assert customers.recorded_messages[1]["direction"] == "OUTBOUND"
    assert customers.recorded_messages[1]["message_type"] == "text"
    assert customers.recorded_messages[2]["direction"] == "OUTBOUND"
    assert customers.recorded_messages[2]["message_type"] == "interactive"
    assert customers.order_states[-1]["status"] == "WAITING_VENDOR_CHECKOUT_APPROVAL"


class _IntentService:
    async def classify(self, incoming_message: str, ad_context: dict | None = None) -> str:
        return "inquiry"

    async def generate_dynamic_response(self, context: str, instruction: str) -> str | None:
        instruction_lower = instruction.lower()
        if "bank details" in instruction_lower or "payment receipt" in instruction_lower:
            return "Here are the payment details."
        if "account details have been securely sent" in instruction_lower:
            return "Account details were sent."
        if "customer confirmed payment" in instruction_lower:
            return "Customer 2348011111111 confirmed payment."
        if "acknowledge the payment confirmation" in instruction_lower:
            return "Payment confirmation received. The store has been notified."
        return "Mock response"
    async def match_product_from_catalogue(self, incoming_message: str, products: list[dict]) -> int | None:
        return None

    async def extract_search_terms(self, incoming_message: str) -> list[str]:
        return []


class _ProductRepo:
    async def list_for_vendor(self, vendor_id: int, *, limit: int = 50, offset: int = 0, in_stock=None, search=None) -> list[dict]:
        return []


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

def test_agent_vendor_button_updates_checkout_state() -> None:
    service = AgentService(intent_service=_IntentService(), products=_ProductRepo(), knowledge=_KnowledgeRepo(), settings=_SettingsRepo())
    vendor = {
        "id": 7,
        "whatsapp_number": "2347000000000",
        "bank_name": "Demo Bank",
        "account_name": "Demo Store",
        "account_number": "1234567890",
    }
    decision = asyncio.run(service.decide(
        vendor,
        ParsedInboundMessage(
            from_number="2347000000000",
            phone_number_id="phone-1",
            message_id="wamid.vendor.1",
            text="btn_approve::2348011111111",
            message_type="interactive",
        ),
        is_vendor_sender=True
    ))

    assert decision.order_status == "ACCOUNT_DETAILS_SENT"
    assert decision.customer_target_number == "2348011111111"
    assert "payment details" in (decision.customer_text or "").lower()


def test_agent_payment_confirmation_transitions_state() -> None:
    service = AgentService(intent_service=_IntentService(), products=_ProductRepo(), knowledge=_KnowledgeRepo(), settings=_SettingsRepo())
    decision = asyncio.run(
        service.decide(
            vendor={"id": 7, "name": "Demo Vendor", "whatsapp_number": "2347000000000"},
            message=ParsedInboundMessage(
                from_number="2348011111111",
                phone_number_id="phone-1",
                message_id="wamid.customer.2",
                text="I have paid",
                message_type="text",
            ),
            is_vendor_sender=False,
        )
    )

    assert decision.order_status == "PAYMENT_CONFIRMED"
    assert "confirmation" in (decision.customer_text or "").lower()
    assert "customer 2348011111111" in (decision.vendor_text or "").lower()


def test_agent_vendor_approve_handles_missing_account_details() -> None:
    service = AgentService(intent_service=_IntentService(), products=_ProductRepo(), knowledge=_KnowledgeRepo(), settings=_SettingsRepo())
    vendor = {
        "id": 7,
        "whatsapp_number": "2347000000000",
        "bank_name": "",
        "account_name": "Demo Store",
        "account_number": None,
    }

    decision = asyncio.run(service.decide(
        vendor,
        ParsedInboundMessage(
            from_number="2347000000000",
            phone_number_id="phone-1",
            message_id="wamid.vendor.2",
            text="btn_approve::2348011111111",
            message_type="interactive",
        ),
        is_vendor_sender=True
    ))

    assert decision.order_status == "ACCOUNT_DETAILS_SENT"
    assert decision.customer_target_number == "2348011111111"
    assert "payment details" in (decision.customer_text or "").lower()
    assert "account details were sent" in (decision.vendor_text or "").lower()


class _TimeoutCustomerRepo(_CustomerRepo):
    async def get_order_lifecycle_state(self, *, vendor_id: int, customer_id: int) -> dict | None:
        return {
            "vendor_id": vendor_id,
            "customer_id": customer_id,
            "status": "WAITING_VENDOR_CHECKOUT_APPROVAL",
            "last_event_text": "I want to buy this",
            "updated_at": datetime.now(timezone.utc) - timedelta(minutes=45),
        }


def test_webhook_transitions_stale_approval_to_timeout() -> None:
    customers = _TimeoutCustomerRepo()
    service = WebhookService(
        vendors=_VendorRepo(),
        customers=customers,
        contacts=_Contacts(),
        agent=_Agent(),
        whatsapp=_WhatsApp(),
    )

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "Chi"}}],
                            "messages": [
                                {
                                    "id": "wamid.inbound.timeout.1",
                                    "from": "2348011111111",
                                    "type": "text",
                                    "text": {"body": "Any update?"},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }

    result = asyncio.run(service.handle_payload(payload))

    assert result == {"status": "ok", "messages_received": 1}
    assert customers.order_states[-1]["status"] == "TIMEOUT_VENDOR_CHECKOUT_APPROVAL"
    outbound_messages = [item for item in customers.recorded_messages if item.get("direction") == "OUTBOUND"]
    assert len(outbound_messages) == 2
    assert "not approved checkout" in (outbound_messages[0].get("body_text") or "").lower()
    assert "approval timeout" in (outbound_messages[1].get("body_text") or "").lower()


def test_webhook_skips_contact_write_when_already_saved() -> None:
    class _CountingContacts(_Contacts):
        def __init__(self) -> None:
            self.calls = 0

        async def save_if_new(self, vendor_id: int, display_name: str, whatsapp_number: str) -> bool:
            self.calls += 1
            return True

    customers = _CustomerRepo()
    customers.google_contact_saved = True
    contacts = _CountingContacts()
    service = WebhookService(
        vendors=_VendorRepo(),
        customers=customers,
        contacts=contacts,
        agent=_Agent(),
        whatsapp=_WhatsApp(),
    )

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "Chi"}}],
                            "messages": [
                                {
                                    "id": "wamid.inbound.idempotent.1",
                                    "from": "2348011111111",
                                    "type": "text",
                                    "text": {"body": "Hi again"},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }

    result = asyncio.run(service.handle_payload(payload))

    assert result == {"status": "ok", "messages_received": 1}
    assert contacts.calls == 0