#!/usr/bin/env python3
"""
Interactive Chat Simulator for the One-Tap Closer Agent.

Drives the full LangGraph pipeline with real LLM calls.
No database or WhatsApp connection needed — everything runs in-memory.

Usage:
    python scripts/simulate_chat.py
"""

import asyncio
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.domain.models import ParsedInboundMessage, AgentDecision
from app.services.agent_service import AgentService


# ── In-memory product catalogue ──────────────────────────────────────────────

class MemoryProductRepo:
    """Fake product repository with sample products."""

    PRODUCTS = [
        {
            "id": 1,
            "vendor_id": 1,
            "name": "Retro Analog Clock",
            "description": "Beautiful walnut-finish analog clock",
            "extra_details": "2-year warranty, battery included",
            "price": 14500,
            "currency": "NGN",
            "in_stock": True,
        },
        {
            "id": 2,
            "vendor_id": 1,
            "name": "Wireless Earbuds Pro",
            "description": "Noise-cancelling Bluetooth earbuds",
            "extra_details": "8hr battery, IPX5 water resistant",
            "price": 28000,
            "currency": "NGN",
            "in_stock": True,
        },
        {
            "id": 3,
            "vendor_id": 1,
            "name": "Leather Messenger Bag",
            "description": "Genuine leather laptop bag, fits 15-inch",
            "extra_details": "Adjustable strap, multiple compartments",
            "price": 45000,
            "currency": "NGN",
            "in_stock": True,
        },
        {
            "id": 4,
            "vendor_id": 1,
            "name": "Smart LED Desk Lamp",
            "description": "Touch-controlled desk lamp with 3 color modes",
            "extra_details": "USB-C charging port built in",
            "price": 9500,
            "currency": "NGN",
            "in_stock": True,
        },
    ]

    async def list_for_vendor(self, vendor_id: int, *, limit: int = 50, offset: int = 0, in_stock=None, search=None):
        results = self.PRODUCTS
        if search and search.strip():
            term = search.strip().lower()
            results = [
                p for p in results
                if term in (p.get("name") or "").lower() or term in (p.get("description") or "").lower()
            ]
        return results[:limit]

    async def get_for_vendor(self, vendor_id: int, product_id: int):
        return next((p for p in self.PRODUCTS if p["id"] == product_id), None)

    async def create_for_vendor(self, vendor_id: int, payload: dict):
        return payload

    async def update_for_vendor(self, vendor_id: int, product_id: int, payload: dict):
        return payload

    async def delete_for_vendor(self, vendor_id: int, product_id: int):
        return True


# ── In-memory knowledge base ─────────────────────────────────────────────────

class MemoryKnowledgeRepo:
    """Fake knowledge base with sample FAQ entries."""

    ENTRIES = [
        {
            "id": 1, "vendor_id": 1, "entry_type": "FAQ",
            "title": "Delivery", "question": "Do you deliver?",
            "answer": "Yes, we deliver nationwide! Delivery within Lagos takes 1-2 business days, outside Lagos takes 3-5 days. Delivery fee starts from NGN 1,500.",
            "keywords": "deliver delivery shipping ship send", "is_active": True,
        },
        {
            "id": 2, "vendor_id": 1, "entry_type": "FAQ",
            "title": "Payment methods", "question": "How can I pay?",
            "answer": "We accept bank transfer (GTBank, Access Bank), and cash on delivery within Lagos.",
            "keywords": "pay payment transfer cash bank how pay", "is_active": True,
        },
        {
            "id": 3, "vendor_id": 1, "entry_type": "FAQ",
            "title": "Returns and refunds", "question": "Can I return an item?",
            "answer": "You can return items within 7 days of delivery if they are in original condition. Refunds are processed within 3 business days.",
            "keywords": "return refund exchange warranty", "is_active": True,
        },
        {
            "id": 4, "vendor_id": 1, "entry_type": "OFFICE",
            "title": "Store hours", "question": "What are your opening hours?",
            "answer": "We're open Monday to Saturday, 9AM to 7PM. Closed on Sundays and public holidays.",
            "keywords": "open close hours time when available", "is_active": True,
        },
        {
            "id": 5, "vendor_id": 1, "entry_type": "OFFICE",
            "title": "Location", "question": "Where is your store?",
            "answer": "Our store is at 15 Admiralty Way, Lekki Phase 1, Lagos. You're welcome to visit anytime during business hours!",
            "keywords": "where location address shop store visit", "is_active": True,
        },
        {
            "id": 6, "vendor_id": 1, "entry_type": "FAQ",
            "title": "Discounts", "question": "Do you offer discounts?",
            "answer": "Our prices are fixed to ensure the best quality, but we occasionally run seasonal sales. Keep an eye on our WhatsApp status!",
            "keywords": "discount price reduction sales promo cheaper", "is_active": True,
        },
    ]

    async def list_for_vendor(self, vendor_id: int) -> list[dict]:
        return self.ENTRIES

    async def search(self, vendor_id: int, query: str, allowed_types: list[str] | None = None) -> dict | None:
        normalized = query.strip().lower()
        if not normalized:
            return None
            
        # Try exact/phrase match first
        for entry in self.ENTRIES:
            if allowed_types and entry["entry_type"] not in allowed_types:
                continue
            if not entry["is_active"]:
                continue
            searchable = f"{entry.get('title', '')} {entry.get('question', '')} {entry.get('answer', '')} {entry.get('keywords', '')}".lower()
            if normalized in searchable:
                return entry
                
        # Try word-by-word match
        query_words = [w for w in normalized.split() if len(w) > 2]
        for entry in self.ENTRIES:
            if allowed_types and entry["entry_type"] not in allowed_types:
                continue
            searchable = f"{entry.get('title', '')} {entry.get('question', '')} {entry.get('answer', '')} {entry.get('keywords', '')}".lower()
            for word in query_words:
                if word in searchable:
                    return entry
                    
        return None


class MemoryBusinessInfoRepo:
    """Fake business info repository for agent policy/tool search."""

    ENTRIES = [
        {
            "id": 1,
            "title": "Delivery",
            "content": "We deliver nationwide. Lagos delivery takes 1-2 business days, outside Lagos takes 3-5 days. Delivery fee starts from NGN 1,500.",
            "source_type": "TEXT",
        },
        {
            "id": 2,
            "title": "Payment",
            "content": "We accept bank transfer. Account details are sent after checkout is approved.",
            "source_type": "TEXT",
        },
        {
            "id": 3,
            "title": "Opening Hours",
            "content": "We are open Monday to Saturday, 9AM to 7PM.",
            "source_type": "TEXT",
        },
    ]

    async def list_for_vendor(self, vendor_id: int) -> list[dict]:
        return self.ENTRIES

    async def create_for_vendor(self, vendor_id: int, payload: dict) -> dict:
        row = {"id": len(self.ENTRIES) + 1, **payload}
        self.ENTRIES.append(row)
        return row

    async def delete_for_vendor(self, vendor_id: int, info_id: int) -> bool:
        original_count = len(self.ENTRIES)
        self.ENTRIES = [entry for entry in self.ENTRIES if entry["id"] != info_id]
        return len(self.ENTRIES) != original_count

    async def search(self, vendor_id: int, query: str) -> str | None:
        normalized = query.strip().lower()
        if not normalized:
            return None
        for entry in self.ENTRIES:
            searchable = f"{entry.get('title', '')} {entry.get('content', '')}".lower()
            if normalized in searchable:
                return entry["content"]
        return None


# ── In-memory vendor settings ────────────────────────────────────────────────

class MemorySettingsRepo:
    async def get(self, vendor_id: int) -> dict:
        return {
            "confirm_before_sending_account_details": False,
            "enable_knowledge_base_answers": True,
            "allow_product_qa": True,
            "allow_office_qa": True,
        }

    async def upsert(self, vendor_id: int, payload: dict) -> dict:
        return payload


class MemoryCustomerRepo:
    def __init__(self):
        self.messages = []
        self.order_state = None

    async def get_or_create_by_whatsapp(self, whatsapp_number: str, display_name: str | None = None) -> dict:
        return {"id": 1, "name": "Test Customer", "whatsapp_number": whatsapp_number}

    async def upsert_vendor_customer(self, vendor_id: int, customer_id: int) -> None:
        pass

    async def upsert_conversation_state(self, vendor_id: int, customer_id: int, last_message: str | None) -> None:
        pass

    async def record_message(self, **kwargs) -> None:
        # Translate keys to match SQL repo expectations if needed, but for memory it's fine
        self.messages.append(kwargs)

    async def upsert_order_lifecycle_state(self, **kwargs) -> None:
        self.order_state = kwargs

    async def get_order_lifecycle_state(self, **kwargs) -> dict | None:
        return self.order_state

    async def list_messages(self, vendor_id: int, customer_id: int, limit: int = 10) -> list[dict]:
        # Filter and return in format agent expects
        return [
            {"direction": m["direction"], "body_text": m["body_text"]}
            for m in self.messages[-limit:]
        ]

    async def get_google_contact_saved(self, **kwargs) -> bool:
        return False

    async def set_google_contact_saved(self, **kwargs) -> None:
        pass


# ── Fake vendor data ─────────────────────────────────────────────────────────

DEMO_VENDOR = {
    "id": 1,
    "name": "Demo Store",
    "email": "demo@store.com",
    "whatsapp_number": "2347000000000",
    "whatsapp_phone_number_id": "phone-1",
    "whatsapp_access_token": "fake-token",
    "bank_name": "GTBank",
    "account_name": "Demo Store Ltd",
    "account_number": "0123456789",
}

CUSTOMER_NUMBER = "2348011111111"


# ── ANSI colors ──────────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    BG_DARK = "\033[48;5;236m"


def banner():
    print(f"""
{C.CYAN}{C.BOLD}╔══════════════════════════════════════════════════════════════╗
║           ONE-TAP CLOSER — Agent Chat Simulator              ║
╠══════════════════════════════════════════════════════════════╣
║  Type messages to simulate a WhatsApp conversation.          ║
║                                                              ║
║  Commands:                                                   ║
║    /vendor <msg>   — Send as the vendor (e.g. /vendor yes)   ║
║    /btn approve    — Vendor taps ✅ YES for a customer       ║
║    /btn deny       — Vendor taps ❌ NO for a customer        ║
║    /products       — Show the product catalogue              ║
║    /state          — Show current order state                ║
║    /quit           — Exit                                    ║
║                                                              ║
║  Everything else is sent as the CUSTOMER.                    ║
╚══════════════════════════════════════════════════════════════╝{C.RESET}
""")


def print_decision(decision: AgentDecision, label: str = ""):
    print(f"\n{C.DIM}{'─' * 60}{C.RESET}")
    print(f"  {C.BOLD}{C.YELLOW}📊 Agent Decision{C.RESET}" + (f"  {C.DIM}({label}){C.RESET}" if label else ""))
    print(f"  {C.DIM}{'─' * 56}{C.RESET}")

    if decision.customer_text:
        print(f"  {C.GREEN}💬 To Customer:{C.RESET}")
        for line in decision.customer_text.strip().split("\n"):
            print(f"     {C.WHITE}{line}{C.RESET}")

    if decision.vendor_text:
        print(f"  {C.BLUE}🏪 To Vendor:{C.RESET}")
        for line in decision.vendor_text.strip().split("\n"):
            print(f"     {C.WHITE}{line}{C.RESET}")

    if decision.vendor_buttons:
        print(f"  {C.MAGENTA}🔘 Vendor Buttons:{C.RESET}")
        for btn in decision.vendor_buttons:
            print(f"     [{btn['id']}] {btn['title']}")

    if decision.customer_target_number:
        print(f"  {C.CYAN}🎯 Target Customer: {decision.customer_target_number}{C.RESET}")

    print(f"  {C.YELLOW}📋 Order Status: {decision.order_status}{C.RESET}")
    print(f"{C.DIM}{'─' * 60}{C.RESET}\n")


async def main():
    banner()

    settings = get_settings()
    provider = settings.active_llm_provider
    print(f"  {C.DIM}LLM Provider: {C.CYAN}{provider}{C.RESET}")
    if provider == "nvidia":
        print(f"  {C.DIM}Model: {C.CYAN}{settings.nvidia_model}{C.RESET}")
    else:
        print(f"  {C.DIM}Model: {C.CYAN}{settings.gemini_model}{C.RESET}")

    products = MemoryProductRepo()
    knowledge = MemoryKnowledgeRepo()
    business_info = MemoryBusinessInfoRepo()
    vendor_settings_repo = MemorySettingsRepo()
    customers = MemoryCustomerRepo()
    agent = AgentService(
        settings=settings,
        products=products,
        knowledge=knowledge,
        business_info=business_info,
        customers=customers,
        vendor_settings=vendor_settings_repo,
    )

    print(f"\n  {C.GREEN}✓ Agent ready. Start chatting!{C.RESET}\n")

    order_status = "INQUIRY"

    while True:
        try:
            raw = input(f"{C.BOLD}{C.WHITE}You ▸ {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}Goodbye!{C.RESET}")
            break

        if not raw:
            continue

        # ── Commands ──────────────────────────────────────────────
        if raw.lower() == "/quit":
            print(f"{C.DIM}Goodbye!{C.RESET}")
            break

        if raw.lower() == "/products":
            print(f"\n  {C.BOLD}{C.CYAN}📦 Product Catalogue:{C.RESET}")
            for p in MemoryProductRepo.PRODUCTS:
                price = f"₦{p['price']:,.0f}" if p.get("price") else "N/A"
                print(f"    {p['id']}. {C.WHITE}{p['name']}{C.RESET} — {C.GREEN}{price}{C.RESET}")
                print(f"       {C.DIM}{p.get('description', '')}{C.RESET}")
            print()
            continue

        if raw.lower() == "/state":
            print(f"\n  {C.YELLOW}📋 Current Order Status: {order_status}{C.RESET}\n")
            continue

        # Determine sender
        is_vendor = False
        text = raw

        if raw.lower().startswith("/vendor "):
            is_vendor = True
            text = raw[8:].strip()
            print(f"  {C.DIM}(Sending as VENDOR){C.RESET}")

        elif raw.lower().startswith("/btn "):
            is_vendor = True
            btn_action = raw[5:].strip().lower()
            if btn_action in ("approve", "yes"):
                text = f"btn_approve::{CUSTOMER_NUMBER}"
            elif btn_action in ("deny", "no"):
                text = f"btn_deny::{CUSTOMER_NUMBER}"
            else:
                print(f"  {C.RED}Unknown button. Use: /btn approve  or  /btn deny{C.RESET}")
                continue
            print(f"  {C.DIM}(Vendor pressed: {btn_action}){C.RESET}")

        # Build the message
        from_number = DEMO_VENDOR["whatsapp_number"] if is_vendor else CUSTOMER_NUMBER
        message = ParsedInboundMessage(
            from_number=from_number,
            phone_number_id="phone-1",
            message_id=f"wamid.sim.{id(raw)}",
            text=text,
            message_type="interactive" if text.startswith("btn_") else "text",
            profile_name="Vendor" if is_vendor else "Customer",
            ad_context=None,
            raw={},
        )

        # Run the agent
        label = "vendor" if is_vendor else "customer"
        try:
            print(f"  {C.DIM}⏳ Thinking...{C.RESET}", end="", flush=True)
            # Record customer message
            await customers.record_message(
                vendor_id=DEMO_VENDOR["id"],
                customer_id=1,
                direction="INBOUND",
                message_type="text",
                body_text=message.text
            )

            decision = await agent.decide(
                vendor=DEMO_VENDOR,
                message=message,
                is_vendor_sender=is_vendor,
            )

            # Record agent response
            if decision.customer_text:
                await customers.record_message(
                    vendor_id=DEMO_VENDOR["id"],
                    customer_id=1,
                    direction="OUTBOUND",
                    message_type="text",
                    body_text=decision.customer_text
                )
            
            if decision.order_status:
                await customers.upsert_order_lifecycle_state(
                    vendor_id=DEMO_VENDOR["id"],
                    customer_id=1,
                    status=decision.order_status,
                    last_event_text=message.text
                )
            print(f"\r  {C.DIM}             {C.RESET}", end="\r")  # clear "Thinking..."
            order_status = decision.order_status or order_status
            print_decision(decision, label=label)
        except Exception as exc:
            print(f"\r  {C.RED}❌ Error: {exc}{C.RESET}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
