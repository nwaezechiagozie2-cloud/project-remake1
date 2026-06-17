"""
Agent service — the bridge between the webhook and the AI agent.

Customer messages → AI agent with tools (decides autonomously)
Vendor button taps → Structured handler (system-level, not AI)
"""
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.config import Settings
from app.domain.interfaces import BusinessInfoRepository, ProductRepository, VendorSettingsRepository, CustomerRepository
from app.domain.models import AgentDecision, ParsedInboundMessage
from app.agent.agent import create_customer_agent, run_customer_agent


class AgentService:
    def __init__(
        self,
        settings: Settings,
        products: ProductRepository,
        business_info: BusinessInfoRepository,
        customers: CustomerRepository,
        vendor_settings: VendorSettingsRepository,
    ) -> None:
        self._settings = settings
        self._products = products
        self._business_info = business_info
        self._customers = customers
        self._vendor_settings = vendor_settings
        self._checkpointer = None

    async def _get_checkpointer(self):
        if self._checkpointer is None:
            # Persistent sqlite checkpointer
            self._checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
        return self._checkpointer

    async def decide(self, vendor: dict, message: ParsedInboundMessage, is_vendor_sender: bool) -> AgentDecision:
        text = message.text.strip()
        text_lower = text.lower()

        # --- SYSTEM-LEVEL: Vendor button taps ---
        if is_vendor_sender and "btn_" in text_lower:
            return await self._handle_vendor_button(vendor, text)

        # --- AI-LEVEL: Customer natural language ---
        if not is_vendor_sender or message.platform == "telegram":
            return await self._handle_customer_message(vendor, message)

        # --- SYSTEM-LEVEL: Vendor sends a free-text message ---
        return AgentDecision(
            customer_text=text,
            order_status="INQUIRY"
        )

    async def _handle_customer_message(self, vendor: dict, message: ParsedInboundMessage) -> AgentDecision:
        if message.platform == "instagram":
            customer = await self._customers.get_or_create_by_instagram(message.from_number, message.profile_name)
        elif message.platform == "telegram":
            customer = await self._customers.get_or_create_by_telegram(
                telegram_id=message.from_number,
                chat_id=str((message.raw.get("chat") or {}).get("id") or message.from_number),
                display_name=message.profile_name,
            )
        else:
            customer = await self._customers.get_or_create_by_whatsapp(message.from_number, message.profile_name)
        customer_id = customer["id"]
        
        state = await self._customers.get_order_lifecycle_state(vendor_id=vendor["id"], customer_id=customer_id)
        order_status = state["status"] if state else "INQUIRY"
        
        vendor_settings = await self._vendor_settings.get(vendor["id"])

        async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
            agent = create_customer_agent(
                settings=self._settings,
                products_repo=self._products,
                business_info_repo=self._business_info,
                vendor_id=vendor["id"],
                vendor_dict=vendor,
                vendor_settings=vendor_settings,
                checkpointer=checkpointer,
            )

            if not agent:
                return AgentDecision(
                    customer_text="Thanks for your message! The store will get back to you shortly.",
                    order_status="INQUIRY",
                )

            platform_prefix = {"instagram": "ig", "telegram": "tg"}.get(message.platform, "wa")
            thread_id = f"{vendor['id']}_{platform_prefix}_{message.from_number}"

            result = await run_customer_agent(
                agent=agent,
                incoming_message=message.text,
                vendor_id=vendor["id"],
                thread_id=thread_id,
                products_repo=self._products,
                business_info_repo=self._business_info,
                vendor_dict=vendor,
                vendor_settings=vendor_settings,
                settings=self._settings,
                order_status=order_status,
                ad_context=message.ad_context,
            )

            decision = AgentDecision(
                customer_text=result["response_text"],
                customer_media=result["customer_media"],
                order_status=result["order_status"],
            )

            if result["order_status"] == "WAITING_VENDOR_CHECKOUT_APPROVAL":
                confirm = bool(vendor_settings.get("confirm_before_sending_account_details", False))
                if confirm:
                    decision.vendor_text = f"Customer {message.from_number} wants to make a purchase. Approve checkout?"
                    decision.vendor_buttons = [
                        {"id": f"btn_approve::{message.from_number}", "title": "✅ YES"},
                        {"id": f"btn_deny::{message.from_number}", "title": "❌ NO"},
                    ]
                else:
                    decision.customer_text = self._build_payment_message(vendor)
                    decision.order_status = "ACCOUNT_DETAILS_SENT"
                    decision.vendor_text = f"Customer {message.from_number} requested checkout — bank details sent automatically."

            return decision

    @staticmethod
    def _build_payment_message(vendor: dict) -> str:
        bank = vendor.get("bank_name") or ""
        name = vendor.get("account_name") or ""
        acct = vendor.get("account_number") or ""
        if bank and acct:
            return (
                "Your order has been approved. Here are the account details:\n\n"
                f"Bank: {bank}\nAccount Name: {name}\nAccount Number: {acct}\n\n"
                "Please share the payment receipt once you've made the transfer!"
            )
        return "Your order has been approved! I'll share the account details with you in a moment."

    async def _handle_vendor_button(self, vendor: dict, text: str) -> AgentDecision:
        """Handle vendor button taps (approve/deny). Pure system logic, no AI needed."""
        customer_target = None
        if "::" in text:
            _, customer_target = text.split("::", 1)
            customer_target = customer_target.strip() or None

        text_lower = text.lower()

        if any(term in text_lower for term in ["btn_approve", "approve", "yes"]):
            if not customer_target:
                return AgentDecision(vendor_text="Could not identify the customer.", order_status="VENDOR_RESPONSE")

            payment_msg = self._build_payment_message(vendor)

            return AgentDecision(
                customer_text=payment_msg,
                customer_target_number=customer_target,
                vendor_text=f"Approved. Payment details sent to {customer_target}.",
                order_status="ACCOUNT_DETAILS_SENT",
            )

        if any(term in text_lower for term in ["btn_deny", "deny", "no"]):
            return AgentDecision(
                customer_text="Thanks for your interest! We're still checking on that for you. We'll update you soon." if customer_target else None,
                customer_target_number=customer_target,
                vendor_text="Checkout denied.",
                order_status="CHECKOUT_DENIED",
            )

        return AgentDecision(vendor_text="Response noted.", order_status="VENDOR_RESPONSE")
