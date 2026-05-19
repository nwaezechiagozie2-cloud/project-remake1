import logging
from datetime import datetime, timedelta, timezone

from app.domain.models import ParsedInboundMessage
from app.domain.interfaces import AgentOrchestrator, ContactsAdapter, CustomerRepository, VendorRepository, WhatsAppAdapter, InstagramAdapter

logger = logging.getLogger(__name__)


class WebhookService:
    VENDOR_APPROVAL_TIMEOUT_MINUTES = 30
    PAYMENT_CONFIRMATION_TIMEOUT_MINUTES = 120

    def __init__(
        self,
        vendors: VendorRepository,
        customers: CustomerRepository,
        contacts: ContactsAdapter,
        agent: AgentOrchestrator,
        whatsapp: WhatsAppAdapter,
        instagram: InstagramAdapter | None = None,
    ) -> None:
        self.vendors = vendors
        self.customers = customers
        self.contacts = contacts
        self.agent = agent
        self.whatsapp = whatsapp
        self.instagram = instagram

    async def handle_payload(self, payload: dict) -> dict:
        obj_type = payload.get("object", "")
        if obj_type == "whatsapp_business_account":
            inbound_messages = self._extract_inbound_messages(payload)
        elif obj_type == "instagram":
            inbound_messages = self._extract_instagram_messages(payload)
        else:
            inbound_messages = []

        for message in inbound_messages:
            await self._handle_inbound_message(message)
        return {
            "status": "ok",
            "messages_received": len(inbound_messages),
        }

    async def _handle_inbound_message(self, message: ParsedInboundMessage) -> None:
        # --- Resolve vendor based on platform ---
        if message.platform == "instagram":
            vendor = await self.vendors.get_by_instagram_page_id(message.phone_number_id)
        else:
            vendor = await self.vendors.get_by_phone_number_id(message.phone_number_id)

        if not vendor:
            logger.warning("Unknown vendor for platform=%s id=%s", message.platform, message.phone_number_id)
            return

        # --- Resolve customer based on platform ---
        if message.platform == "instagram":
            customer = await self.customers.get_or_create_by_instagram(message.from_number, display_name=message.profile_name)
        else:
            customer = await self.customers.get_or_create_by_whatsapp(message.from_number, display_name=message.profile_name)
        await self.customers.upsert_vendor_customer(vendor_id=vendor["id"], customer_id=customer["id"])
        await self.customers.upsert_conversation_state(
            vendor_id=vendor["id"],
            customer_id=customer["id"],
            last_message=message.text,
        )
        await self.customers.record_message(
            vendor_id=vendor["id"],
            customer_id=customer["id"],
            direction="INBOUND",
            message_type=message.message_type,
            body_text=message.text,
            whatsapp_message_id=message.message_id,
            sender_number=message.from_number,
            recipient_number=vendor.get("whatsapp_number"),
        )

        if message.profile_name:
            contact_saved = await self.customers.get_google_contact_saved(vendor_id=vendor["id"], customer_id=customer["id"])
            if not contact_saved:
                saved_now = await self.contacts.save_if_new(vendor["id"], message.profile_name, message.from_number)
                if saved_now:
                    await self.customers.set_google_contact_saved(vendor_id=vendor["id"], customer_id=customer["id"], saved=True)

        is_vendor_sender = bool(vendor.get("whatsapp_number") and message.from_number == vendor["whatsapp_number"])

        # Determine which messaging adapter to use for this conversation
        _messenger = self.instagram if message.platform == "instagram" and self.instagram else self.whatsapp

        if await self._check_and_handle_timeout(vendor=vendor, customer=customer, message=message, is_vendor_sender=is_vendor_sender, messenger=_messenger):
            return

        decision = await self.agent.decide(vendor=vendor, message=message, is_vendor_sender=is_vendor_sender)

        if decision.order_status:
            await self.customers.upsert_order_lifecycle_state(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                status=decision.order_status,
                last_event_text=message.text,
            )

        if decision.customer_text:
            customer_target = decision.customer_target_number or message.from_number
            await _messenger.send_text(vendor=vendor, to=customer_target, body=decision.customer_text)
            await self.customers.record_message(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                direction="OUTBOUND",
                message_type="text",
                body_text=decision.customer_text,
                sender_number=vendor.get("whatsapp_number"),
                recipient_number=customer_target,
            )

        if decision.vendor_buttons:
            vendor_target = vendor.get("whatsapp_number") or message.from_number
            if message.platform == "instagram" and self.instagram:
                # Instagram uses quick replies instead of interactive buttons
                replies = [{"title": b["title"], "payload": b["id"]} for b in decision.vendor_buttons]
                await self.instagram.send_quick_replies(
                    vendor=vendor,
                    to=vendor_target,
                    body=decision.vendor_text or "Please confirm action",
                    replies=replies,
                )
            else:
                await self.whatsapp.send_buttons(
                    vendor=vendor,
                    to=vendor_target,
                    body=decision.vendor_text or "Please confirm action",
                    buttons=decision.vendor_buttons,
                )
            await self.customers.record_message(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                direction="OUTBOUND",
                message_type="interactive",
                body_text=decision.vendor_text or "Please confirm action",
                sender_number=vendor.get("whatsapp_number"),
                recipient_number=vendor_target,
            )
        elif decision.vendor_text:
            vendor_target = vendor.get("whatsapp_number") or message.from_number
            await _messenger.send_text(vendor=vendor, to=vendor_target, body=decision.vendor_text)
            await self.customers.record_message(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                direction="OUTBOUND",
                message_type="text",
                body_text=decision.vendor_text,
                sender_number=vendor.get("whatsapp_number"),
                recipient_number=vendor_target,
            )

    async def _check_and_handle_timeout(
        self,
        *,
        vendor: dict,
        customer: dict,
        message: ParsedInboundMessage,
        is_vendor_sender: bool,
        messenger=None,
    ) -> bool:
        if is_vendor_sender:
            return False

        state = await self.customers.get_order_lifecycle_state(vendor_id=vendor["id"], customer_id=customer["id"])
        if not state:
            return False

        updated_at = state.get("updated_at")
        if not isinstance(updated_at, datetime):
            return False

        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age = now - updated_at
        status = (state.get("status") or "").upper()

        if status == "WAITING_VENDOR_CHECKOUT_APPROVAL" and age >= timedelta(minutes=self.VENDOR_APPROVAL_TIMEOUT_MINUTES):
            customer_text = "Thanks for your patience. The store has not approved checkout yet; we’ve reminded them now."
            vendor_text = f"Approval timeout: customer {message.from_number} is still waiting. Please approve or deny checkout."
            await self._send_and_record_timeout_messages(
                vendor=vendor,
                customer=customer,
                customer_target=message.from_number,
                customer_text=customer_text,
                vendor_text=vendor_text,
                messenger=messenger,
            )
            await self.customers.upsert_order_lifecycle_state(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                status="TIMEOUT_VENDOR_CHECKOUT_APPROVAL",
                last_event_text=message.text,
            )
            return True

        if status == "ACCOUNT_DETAILS_SENT" and age >= timedelta(minutes=self.PAYMENT_CONFIRMATION_TIMEOUT_MINUTES):
            customer_text = "We haven’t received payment confirmation yet. Please share your proof of payment if you’ve completed transfer."
            vendor_text = f"Payment confirmation timeout: customer {message.from_number} may need follow-up."
            await self._send_and_record_timeout_messages(
                vendor=vendor,
                customer=customer,
                customer_target=message.from_number,
                customer_text=customer_text,
                vendor_text=vendor_text,
                messenger=messenger,
            )
            await self.customers.upsert_order_lifecycle_state(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                status="TIMEOUT_PAYMENT_CONFIRMATION",
                last_event_text=message.text,
            )
            return True

        return False

    async def _send_and_record_timeout_messages(
        self,
        *,
        vendor: dict,
        customer: dict,
        customer_target: str,
        customer_text: str,
        vendor_text: str,
        messenger=None,
    ) -> None:
        vendor_target = vendor.get("whatsapp_number") or customer_target
        _messenger = messenger or self.whatsapp

        await _messenger.send_text(vendor=vendor, to=customer_target, body=customer_text)
        await self.customers.record_message(
            vendor_id=vendor["id"],
            customer_id=customer["id"],
            direction="OUTBOUND",
            message_type="text",
            body_text=customer_text,
            sender_number=vendor.get("whatsapp_number"),
            recipient_number=customer_target,
        )

        await _messenger.send_text(vendor=vendor, to=vendor_target, body=vendor_text)
        await self.customers.record_message(
            vendor_id=vendor["id"],
            customer_id=customer["id"],
            direction="OUTBOUND",
            message_type="text",
            body_text=vendor_text,
            sender_number=vendor.get("whatsapp_number"),
            recipient_number=vendor_target,
        )

    def _extract_inbound_messages(self, payload: dict) -> list[ParsedInboundMessage]:
        if payload.get("object") != "whatsapp_business_account":
            return []

        parsed: list[ParsedInboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")
                contacts = value.get("contacts") or []
                profile_name = ((contacts[0] or {}).get("profile") or {}).get("name") if contacts else None

                for message in value.get("messages", []):
                    msg_type = message.get("type") or "unknown"
                    text = self._message_text(message)
                    parsed.append(
                        ParsedInboundMessage(
                            from_number=message.get("from", ""),
                            phone_number_id=phone_number_id or "",
                            message_id=message.get("id"),
                            text=text,
                            message_type=msg_type,
                            profile_name=profile_name,
                            ad_context=message.get("referral") or value.get("referral"),
                            raw=message,
                        )
                    )
        return parsed

    @staticmethod
    def _message_text(message: dict) -> str:
        msg_type = message.get("type")
        if msg_type == "text":
            return ((message.get("text") or {}).get("body") or "").strip()
        if msg_type == "interactive":
            interactive = message.get("interactive") or {}
            button_reply = interactive.get("button_reply") or {}
            list_reply = interactive.get("list_reply") or {}
            return (button_reply.get("id") or button_reply.get("title") or list_reply.get("id") or list_reply.get("title") or "").strip()
        return ""

    # ---- Instagram webhook parsing ----

    def _extract_instagram_messages(self, payload: dict) -> list[ParsedInboundMessage]:
        """
        Parse Instagram webhook payload into ParsedInboundMessages.

        Instagram structure:
            {"object": "instagram", "entry": [{"id": "PAGE_ID", "messaging": [
                {"sender": {"id": "IGSID"}, "recipient": {"id": "PAGE_ID"},
                 "message": {"mid": "...", "text": "Hello"}}
            ]}]}
        """
        parsed: list[ParsedInboundMessage] = []
        for entry in payload.get("entry", []):
            page_id = entry.get("id", "")
            for event in entry.get("messaging", []):
                sender_id = (event.get("sender") or {}).get("id", "")
                message = event.get("message")
                if not message:
                    # Could be a delivery/read receipt — skip
                    continue

                text = self._instagram_message_text(message)
                msg_type = "quick_reply" if message.get("quick_reply") else "text"

                parsed.append(
                    ParsedInboundMessage(
                        from_number=sender_id,
                        phone_number_id=page_id,
                        message_id=message.get("mid"),
                        text=text,
                        message_type=msg_type,
                        platform="instagram",
                        profile_name=None,  # IG doesn't include name in webhook
                        ad_context=event.get("referral"),
                        raw=event,
                    )
                )
        return parsed

    @staticmethod
    def _instagram_message_text(message: dict) -> str:
        """Extract text from an Instagram message, preferring quick_reply payload."""
        quick_reply = message.get("quick_reply")
        if quick_reply:
            return (quick_reply.get("payload") or message.get("text") or "").strip()
        return (message.get("text") or "").strip()
