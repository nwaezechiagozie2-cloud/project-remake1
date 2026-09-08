"""Google Sheets order sync — unit tests (no Google credentials needed).

Covers: order creation on the ACCOUNT_DETAILS_SENT transition (via
WebhookService with stub repos), duplicate-transition dedup, append success,
transient-error retry, failure recording, the retry duplicate guard, reauth
handling, validation errors, extract_spreadsheet_id forms, and the
agent-side order-details extraction.
"""
import asyncio
from datetime import datetime, timedelta

import pytest
from googleapiclient.errors import HttpError

from app.agent.agent import run_customer_agent, _extract_order_details
from app.agent.tools import create_agent_tools
from app.services.google_sheets_service import GoogleSheetsService
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage


# --------------------------------------------------------------------- fakes

class FakeTokenRepo:
    def __init__(self, token_json=None):
        self.token_json = token_json

    async def get_token_json(self, vendor_id):
        return self.token_json

    async def upsert_token_json(self, vendor_id, token_json):
        self.token_json = token_json

    async def delete_for_vendor(self, vendor_id):
        had = self.token_json is not None
        self.token_json = None
        return had


class FakeOrderRepo:
    def __init__(self):
        self.orders = []
        self._next_id = 1

    async def create_order(self, vendor_id, payload):
        order = {
            "id": self._next_id,
            "vendor_id": vendor_id,
            "status": payload.get("status", "ACCOUNT_DETAILS_SENT"),
            "order_ref": f"ORD-{self._next_id:06d}",
            "customer_name": payload.get("customer_name"),
            "customer_phone": payload.get("customer_phone"),
            "customer_platform": payload.get("customer_platform", "whatsapp"),
            "customer_handle": payload.get("customer_handle"),
            "order_details": payload.get("order_details"),
            "sheets_synced": False,
            "sheets_sync_attempts": 0,
            "sheets_synced_at": None,
            "sheets_last_error": None,
            "next_attempt_at": None,
            "created_at": datetime.utcnow(),
        }
        self._next_id += 1
        self.orders.append(order)
        return order

    async def mark_synced(self, order_id):
        for o in self.orders:
            if o["id"] == order_id:
                o["sheets_synced"] = True
                o["sheets_synced_at"] = datetime.utcnow()
                o["sheets_last_error"] = None

    async def record_sync_failure(self, order_id, error, retry_delay_seconds):
        for o in self.orders:
            if o["id"] == order_id:
                o["sheets_sync_attempts"] += 1
                o["sheets_last_error"] = error
                o["next_attempt_at"] = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)

    async def claim_pending(self, limit=50):
        now = datetime.utcnow()
        return [o for o in self.orders if not o["sheets_synced"]][:limit]

    async def list_pending_for_vendor(self, vendor_id):
        return [o for o in self.orders if o["vendor_id"] == vendor_id and not o["sheets_synced"]]

    async def count_for_vendor(self, vendor_id, synced):
        return sum(1 for o in self.orders if o["vendor_id"] == vendor_id and o["sheets_synced"] == synced)


class FakeSettingsRepo:
    def __init__(self, settings=None):
        self.settings = settings or {}

    async def get(self, vendor_id):
        base = {
            "confirm_before_sending_account_details": False,
            "enable_knowledge_base_answers": True,
            "use_product_availability": True,
            "sheets_sync_enabled": True,
            "sheets_spreadsheet_id": "sheet123",
            "sheets_spreadsheet_title": "Orders",
            "sheets_tab_name": "Sheet1",
        }
        base.update(self.settings)
        return base

    async def upsert(self, vendor_id, payload):
        self.settings.update(payload)
        return await self.get(vendor_id)


class FakeHttpError(HttpError):
    def __init__(self, status):
        class FakeResp:
            pass
        resp = FakeResp()
        resp.status = status
        resp.reason = "fake reason"
        super().__init__(resp, b"fake error")


# Monkeypatch target: GoogleSheetsService._get_credentials
def _make_service(token_json="fake", settings=None):
    tokens = FakeTokenRepo(token_json)
    orders = FakeOrderRepo()
    settings_repo = FakeSettingsRepo(settings)
    service = GoogleSheetsService(settings=None, tokens=tokens, orders=orders, settings_repo=settings_repo)
    return service, orders, tokens, settings_repo


# ------------------------------------------------------------------- tests

def test_extract_spreadsheet_id_forms():
    extract = GoogleSheetsService.extract_spreadsheet_id
    full = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0"
    assert extract(full) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert extract("https://docs.google.com/spreadsheets/d/abc123XYZ456def789ghi012/edit") == "abc123XYZ456def789ghi012"
    assert extract("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms") == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"


def test_extract_spreadsheet_id_rejects_invalid():
    from app.exceptions import ValidationError
    with pytest.raises(ValidationError):
        GoogleSheetsService.extract_spreadsheet_id("https://docs.google.com/spreadsheets/new")
    with pytest.raises(ValidationError):
        GoogleSheetsService.extract_spreadsheet_id("")
    with pytest.raises(ValidationError):
        GoogleSheetsService.extract_spreadsheet_id("not a url at all")


@pytest.mark.asyncio
async def test_sync_order_success(monkeypatch):
    service, orders, _, _ = _make_service()
    appended = []
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))
    monkeypatch.setattr(service, "_first_cell_sync", lambda *a, **k: "Timestamp")  # header exists
    monkeypatch.setattr(service, "_append_row_sync", lambda *a, **k: appended.append(a))

    order = await orders.create_order(1, {"customer_id": 5, "customer_name": "Ada", "order_details": "2x shoes"})
    result = await service.sync_order(order)

    assert result is True
    assert order["sheets_synced"] is True
    assert len(appended) == 1  # header skipped, one data row


@pytest.mark.asyncio
async def test_sync_order_writes_header_when_empty(monkeypatch):
    service, orders, _, _ = _make_service()
    appended = []
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))
    monkeypatch.setattr(service, "_first_cell_sync", lambda *a, **k: None)  # empty sheet
    monkeypatch.setattr(service, "_append_row_sync", lambda *a, **k: appended.append(a))

    order = await orders.create_order(1, {"customer_id": 5})
    await service.sync_order(order)

    assert len(appended) == 2  # header + data row
    assert appended[0][3][0] == "Timestamp"


@pytest.mark.asyncio
async def test_sync_order_disabled_leaves_pending(monkeypatch):
    service, orders, _, _ = _make_service(settings={"sheets_sync_enabled": False})
    called = []
    monkeypatch.setattr(service, "_get_credentials", lambda vid: called.append(1) or asyncio.sleep(0, {}))

    order = await orders.create_order(1, {"customer_id": 5})
    result = await service.sync_order(order)

    assert result is False
    assert order["sheets_synced"] is False
    assert called == []  # never even touched Google


@pytest.mark.asyncio
async def test_sync_order_no_token_records_reauth():
    service, orders, _, _ = _make_service(token_json=None)

    order = await orders.create_order(1, {"customer_id": 5})
    result = await service.sync_order(order)

    assert result is False
    assert order["sheets_last_error"] == "reauth_needed"
    assert order["sheets_sync_attempts"] == 1


@pytest.mark.asyncio
async def test_sync_order_403_records_spreadsheet_unavailable(monkeypatch):
    service, orders, _, _ = _make_service()
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))
    monkeypatch.setattr(service, "_first_cell_sync", lambda *a, **k: "Timestamp")

    def raise_403(*a, **k):
        raise FakeHttpError(403)
    monkeypatch.setattr(service, "_append_row_sync", raise_403)

    order = await orders.create_order(1, {"customer_id": 5})
    result = await service.sync_order(order)

    assert result is False
    assert "spreadsheet_unavailable" in order["sheets_last_error"]
    assert order["next_attempt_at"] is not None


@pytest.mark.asyncio
async def test_sync_order_transient_retry_then_success(monkeypatch):
    service, orders, _, _ = _make_service()
    attempts = []

    async def fake_creds(vid):
        return {"ok": True}
    monkeypatch.setattr(service, "_get_credentials", fake_creds)
    monkeypatch.setattr(service, "_first_cell_sync", lambda *a, **k: "Timestamp")

    def flaky_append(creds, spreadsheet_id, tab, row):
        attempts.append(1)
        if len(attempts) < 2:
            raise FakeHttpError(429)
        return None

    monkeypatch.setattr(service, "_append_row_sync", flaky_append)
    # speed the test up: no real backoff sleeps
    async def no_sleep(delay):
        return None
    monkeypatch.setattr("app.services.google_sheets_service.asyncio.sleep", no_sleep)

    order = await orders.create_order(1, {"customer_id": 5})
    result = await service.sync_order(order)

    assert result is True
    assert len(attempts) == 2  # failed once, retried, succeeded
    assert order["sheets_synced"] is True


@pytest.mark.asyncio
async def test_duplicate_guard_on_retry(monkeypatch):
    service, orders, _, _ = _make_service()
    appended = []
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))
    monkeypatch.setattr(
        service, "_read_column_a_sync",
        lambda creds, sid, tab: [["ORD-000001"], ["ORD-000002"]],
    )
    monkeypatch.setattr(service, "_append_row_sync", lambda *a, **k: appended.append(a))

    order = await orders.create_order(1, {"customer_id": 5})
    assert order["order_ref"] == "ORD-000001"
    # Simulate a previous failed attempt (append succeeded, response lost)
    order["sheets_sync_attempts"] = 1

    result = await service.sync_order(order)

    assert result is True
    assert order["sheets_synced"] is True
    assert appended == []  # duplicate guard: no re-append


@pytest.mark.asyncio
async def test_validate_spreadsheet_no_token():
    from app.exceptions import ValidationError
    service, _, _, _ = _make_service(token_json=None)
    with pytest.raises(ValidationError):
        await service.validate_spreadsheet(1, "https://docs.google.com/spreadsheets/d/abc123XYZ456def789ghi012/edit")


@pytest.mark.asyncio
async def test_validate_spreadsheet_404(monkeypatch):
    from app.exceptions import ValidationError
    service, _, _, _ = _make_service()
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))

    def raise_404(*a, **k):
        raise FakeHttpError(404)
    monkeypatch.setattr(service, "_get_metadata_sync", raise_404)

    with pytest.raises(ValidationError):
        await service.validate_spreadsheet(1, "https://docs.google.com/spreadsheets/d/abc123XYZ456def789ghi012/edit")


@pytest.mark.asyncio
async def test_validate_spreadsheet_success(monkeypatch):
    service, _, _, _ = _make_service()
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))
    monkeypatch.setattr(service, "_get_metadata_sync", lambda creds, sid: {
        "properties": {"title": "My Orders"},
        "sheets": [{"properties": {"title": "Sheet1"}}],
    })

    result = await service.validate_spreadsheet(1, "https://docs.google.com/spreadsheets/d/abc123XYZ456def789ghi012/edit")
    assert result == {"spreadsheet_id": "abc123XYZ456def789ghi012", "spreadsheet_title": "My Orders", "tab_name": "Sheet1"}


# ----------------------------------------------------- agent order details

def test_extract_order_details():
    assert _extract_order_details("SIGNAL:CHECKOUT_REQUESTED|ORDER:2x Ankara gown, NGN 45000") == "2x Ankara gown, NGN 45000"
    assert _extract_order_details("SIGNAL:CHECKOUT_REQUESTED|ORDER:") is None
    assert _extract_order_details("SIGNAL:CHECKOUT_REQUESTED") is None


def test_checkout_tool_echoes_order():
    tools = create_agent_tools(products_repo=None, business_info_repo=None, vendor_id=1, vendor_dict={}, vendor_settings={})
    checkout = tools[2]
    result = asyncio.run(checkout.ainvoke({"order_description": "1x sneakers, NGN 12000"}))
    assert result == "SIGNAL:CHECKOUT_REQUESTED|ORDER:1x sneakers, NGN 12000"


class DummyAgent:
    """Returns one turn: checkout tool called with an order description."""
    def __init__(self, final_messages):
        self.final_messages = final_messages
        self.calls = 0

    async def ainvoke(self, inputs, config=None):
        self.calls += 1
        return {"messages": self.final_messages, "order_status": "WAITING_VENDOR_CHECKOUT_APPROVAL"}


@pytest.mark.asyncio
async def test_run_customer_agent_extracts_order_details():
    messages = [
        HumanMessage(content="I want to pay for 2 gowns"),
        AIMessage(content="", tool_calls=[{"name": "request_bank_details_and_vendor_approval", "args": {"order_description": "2x Ankara gowns, NGN 90000"}, "id": "call_1"}]),
        ToolMessage(content="SIGNAL:CHECKOUT_REQUESTED|ORDER:2x Ankara gowns, NGN 90000", tool_call_id="call_1"),
        AIMessage(content="Notifying the store now."),
    ]
    agent = DummyAgent(messages)
    result = await run_customer_agent(
        agent=agent,
        incoming_message="I want to pay for 2 gowns",
        vendor_id=1,
        thread_id="t1",
        products_repo=None,
        business_info_repo=None,
        vendor_dict={"id": 1},
        vendor_settings={},
        settings=None,
        order_status="INQUIRY",
    )
    assert result["checkout_requested"] is True
    assert result["order_details"] == "2x Ankara gowns, NGN 90000"


@pytest.mark.asyncio
async def test_run_customer_agent_order_details_falls_back_to_message():
    messages = [
        HumanMessage(content="I am ready to pay now"),
        AIMessage(content="", tool_calls=[{"name": "request_bank_details_and_vendor_approval", "args": {}, "id": "call_1"}]),
        ToolMessage(content="SIGNAL:CHECKOUT_REQUESTED|ORDER:", tool_call_id="call_1"),
        AIMessage(content="Notifying the store now."),
    ]
    agent = DummyAgent(messages)
    result = await run_customer_agent(
        agent=agent,
        incoming_message="I am ready to pay now",
        vendor_id=1,
        thread_id="t1",
        products_repo=None,
        business_info_repo=None,
        vendor_dict={"id": 1},
        vendor_settings={},
        settings=None,
        order_status="INQUIRY",
    )
    assert result["checkout_requested"] is True
    assert result["order_details"] == "I am ready to pay now"


# ----------------------------------------------------------- webhook hook

class FakeCustomerRepo:
    def __init__(self):
        self.lifecycle = {}
        self.customer = {"id": 5, "name": "Ada", "whatsapp_number": "+2348000000000", "instagram_id": None, "telegram_id": None}

    async def get_or_create_by_whatsapp(self, number, display_name=None):
        return self.customer

    async def upsert_vendor_customer(self, vendor_id, customer_id):
        pass

    async def upsert_conversation_state(self, vendor_id, customer_id, last_message):
        pass

    async def record_message(self, **kwargs):
        pass

    async def get_google_contact_saved(self, *, vendor_id, customer_id):
        return True  # skip the contacts adapter

    async def set_google_contact_saved(self, *, vendor_id, customer_id, saved=True):
        pass

    async def get_order_lifecycle_state(self, *, vendor_id, customer_id):
        return self.lifecycle.get((vendor_id, customer_id))

    async def upsert_order_lifecycle_state(self, *, vendor_id, customer_id, status, last_event_text):
        self.lifecycle[(vendor_id, customer_id)] = {"status": status, "last_event_text": last_event_text}


class FakeAgentDecider:
    def __init__(self, decision):
        self.decision = decision

    async def decide(self, vendor, message, is_vendor_sender):
        return self.decision


class FakeMessenger:
    async def send_text(self, vendor, to, body):
        pass


@pytest.mark.asyncio
async def test_webhook_creates_order_on_account_details_sent():
    from app.domain.models import AgentDecision, ParsedInboundMessage
    from app.services.webhook_service import WebhookService

    customers = FakeCustomerRepo()
    orders = FakeOrderRepo()
    synced = []

    class FakeSheets:
        async def sync_order(self, order):
            synced.append(order["order_ref"])
            return True

    decision = AgentDecision(
        customer_text="Here are the account details...",
        order_status="ACCOUNT_DETAILS_SENT",
        order_details="2x Ankara gowns, NGN 90000",
    )
    service = WebhookService(
        vendors=None, customers=customers, contacts=None, agent=FakeAgentDecider(decision),
        whatsapp=FakeMessenger(), orders=orders, sheets=FakeSheets(),
    )
    message = ParsedInboundMessage(
        from_number="+2348000000000", phone_number_id="pid", message_id="mid1",
        text="I am ready to pay", message_type="text", platform="whatsapp",
        profile_name="Ada", raw={},
    )

    # Vendor resolution: stub get_by_phone_number_id
    class FakeVendors:
        async def get_by_phone_number_id(self, pid):
            return {"id": 1, "name": "Store"}
    service.vendors = FakeVendors()

    await service._handle_inbound_message(message)
    await asyncio.sleep(0)  # let the fire-and-forget sync task run

    assert len(orders.orders) == 1
    order = orders.orders[0]
    assert order["customer_name"] == "Ada"
    assert order["customer_phone"] == "+2348000000000"
    assert order["order_details"] == "2x Ankara gowns, NGN 90000"
    assert synced == ["ORD-000001"]


@pytest.mark.asyncio
async def test_webhook_duplicate_transition_no_second_order():
    from app.domain.models import AgentDecision, ParsedInboundMessage
    from app.services.webhook_service import WebhookService

    customers = FakeCustomerRepo()
    customers.lifecycle[(1, 5)] = {"status": "ACCOUNT_DETAILS_SENT", "last_event_text": "already sent"}
    orders = FakeOrderRepo()

    decision = AgentDecision(customer_text="Details again", order_status="ACCOUNT_DETAILS_SENT")
    service = WebhookService(
        vendors=None, customers=customers, contacts=None, agent=FakeAgentDecider(decision),
        whatsapp=FakeMessenger(), orders=orders, sheets=None,
    )

    class FakeVendors:
        async def get_by_phone_number_id(self, pid):
            return {"id": 1, "name": "Store"}
    service.vendors = FakeVendors()

    message = ParsedInboundMessage(
        from_number="+2348000000000", phone_number_id="pid", message_id="mid2",
        text="resend details", message_type="text", platform="whatsapp",
        profile_name="Ada", raw={},
    )
    await service._handle_inbound_message(message)

    assert len(orders.orders) == 0  # previous status already ACCOUNT_DETAILS_SENT → dedup


@pytest.mark.asyncio
async def test_webhook_no_order_for_inquiry_status():
    from app.domain.models import AgentDecision, ParsedInboundMessage
    from app.services.webhook_service import WebhookService

    customers = FakeCustomerRepo()
    orders = FakeOrderRepo()
    decision = AgentDecision(customer_text="Hi!", order_status="INQUIRY")
    service = WebhookService(
        vendors=None, customers=customers, contacts=None, agent=FakeAgentDecider(decision),
        whatsapp=FakeMessenger(), orders=orders, sheets=None,
    )

    class FakeVendors:
        async def get_by_phone_number_id(self, pid):
            return {"id": 1, "name": "Store"}
    service.vendors = FakeVendors()

    message = ParsedInboundMessage(
        from_number="+2348000000000", phone_number_id="pid", message_id="mid3",
        text="hello", message_type="text", platform="whatsapp",
        profile_name="Ada", raw={},
    )
    await service._handle_inbound_message(message)

    assert len(orders.orders) == 0


@pytest.mark.asyncio
async def test_sweep_pending_processes_claimed_orders(monkeypatch):
    service, orders, _, _ = _make_service()
    monkeypatch.setattr(service, "_get_credentials", lambda vid: asyncio.sleep(0, {"ok": True}))
    monkeypatch.setattr(service, "_first_cell_sync", lambda *a, **k: "Timestamp")
    monkeypatch.setattr(service, "_append_row_sync", lambda *a, **k: None)

    await orders.create_order(1, {"customer_id": 5})
    await orders.create_order(1, {"customer_id": 6})
    await service.sweep_pending()

    assert all(o["sheets_synced"] for o in orders.orders)
