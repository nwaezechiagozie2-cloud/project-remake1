import logging
from datetime import datetime, timedelta, timezone

from app.domain.models import ParsedInboundMessage
from app.domain.interfaces import AgentOrchestrator, ContactsAdapter, CustomerRepository, VendorRepository, WhatsAppAdapter, InstagramAdapter, TelegramAdapter

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
        telegram: TelegramAdapter | None = None,
    ) -> None:
        self.vendors = vendors
        self.customers = customers
        self.contacts = contacts
        self.agent = agent
        self.whatsapp = whatsapp
        self.instagram = instagram
        self.telegram = telegram

    async def handle_payload(self, payload: dict) -> dict:
        obj_type = payload.get("object", "")
        if obj_type == "whatsapp_business_account":
            inbound_messages = self._extract_inbound_messages(payload)
        elif obj_type == "instagram":
            inbound_messages = self._extract_instagram_messages(payload)
        elif obj_type == "telegram":
            inbound_messages = self._extract_telegram_messages(payload.get("update") or payload)
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
        elif message.platform == "telegram":
            vendor = await self._resolve_telegram_vendor(message)
        else:
            vendor = await self.vendors.get_by_phone_number_id(message.phone_number_id)

        if not vendor:
            logger.warning("Unknown vendor for platform=%s id=%s", message.platform, message.phone_number_id)
            return

        # --- Resolve customer based on platform ---
        if message.platform == "instagram":
            customer = await self.customers.get_or_create_by_instagram(message.from_number, display_name=message.profile_name)
        elif message.platform == "telegram":
            customer = await self.customers.get_or_create_by_telegram(
                telegram_id=message.from_number,
                chat_id=str((message.raw.get("chat") or {}).get("id") or message.from_number),
                display_name=message.profile_name,
            )
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
            recipient_number=self._vendor_recipient_id(vendor, message.platform),
        )

        if message.profile_name:
            contact_saved = await self.customers.get_google_contact_saved(vendor_id=vendor["id"], customer_id=customer["id"])
            if not contact_saved:
                saved_now = await self.contacts.save_if_new(vendor["id"], message.profile_name, message.from_number)
                if saved_now:
                    await self.customers.set_google_contact_saved(vendor_id=vendor["id"], customer_id=customer["id"], saved=True)

        is_vendor_sender = self._is_vendor_sender(vendor, message)

        # Determine which messaging adapter to use for this conversation
        _messenger = self._messenger_for_platform(message.platform)

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
            customer_target = decision.customer_target_number or self._customer_reply_target(message)
            await _messenger.send_text(vendor=vendor, to=customer_target, body=decision.customer_text)
            await self.customers.record_message(
                vendor_id=vendor["id"],
                customer_id=customer["id"],
                direction="OUTBOUND",
                message_type="text",
                body_text=decision.customer_text,
                sender_number=self._vendor_recipient_id(vendor, message.platform),
                recipient_number=customer_target,
            )

        if decision.vendor_buttons:
            vendor_target = self._vendor_recipient_id(vendor, message.platform)
            if not vendor_target and message.platform != "telegram":
                vendor_target = message.from_number
            if message.platform == "instagram" and self.instagram:
                # Instagram uses quick replies instead of interactive buttons
                replies = [{"title": b["title"], "payload": b["id"]} for b in decision.vendor_buttons]
                await self.instagram.send_quick_replies(
                    vendor=vendor,
                    to=vendor_target,
                    body=decision.vendor_text or "Please confirm action",
                    replies=replies,
                )
            elif message.platform == "telegram":
                if vendor_target:
                    # Telegram MVP sends approval prompts as plain text; button callbacks can be added later.
                    button_text = "\n".join(f"{button['title']}: {button['id']}" for button in decision.vendor_buttons)
                    await _messenger.send_text(
                        vendor=vendor,
                        to=vendor_target,
                        body=f"{decision.vendor_text or 'Please confirm action'}\n\n{button_text}",
                    )
                else:
                    logger.warning("Skipped Telegram vendor buttons because vendor chat is not configured | vendor_id=%s", vendor["id"])
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
                sender_number=self._vendor_recipient_id(vendor, message.platform),
                recipient_number=vendor_target,
            )
        elif decision.vendor_text:
            vendor_target = self._vendor_recipient_id(vendor, message.platform)
            if not vendor_target and message.platform != "telegram":
                vendor_target = message.from_number
            if vendor_target:
                await _messenger.send_text(vendor=vendor, to=vendor_target, body=decision.vendor_text)
                await self.customers.record_message(
                    vendor_id=vendor["id"],
                    customer_id=customer["id"],
                    direction="OUTBOUND",
                    message_type="text",
                    body_text=decision.vendor_text,
                    sender_number=self._vendor_recipient_id(vendor, message.platform),
                    recipient_number=vendor_target,
                )
            elif message.platform == "telegram":
                logger.warning("Skipped Telegram vendor text because vendor chat is not configured | vendor_id=%s", vendor["id"])

    async def _resolve_telegram_vendor(self, message: ParsedInboundMessage) -> dict | None:
        chat = message.raw.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        if chat_id:
            vendor = await self.vendors.get_by_telegram_vendor_chat_id(chat_id)
            if vendor:
                return vendor

        if message.text.startswith("/start"):
            parts = message.text.split(maxsplit=1)
            if len(parts) == 2 and parts[1].strip().isdigit():
                return await self.vendors.get_by_id(int(parts[1].strip()))
        if chat_id:
            return await self.vendors.get_by_telegram_customer_chat_id(chat_id)
        return None

    def _messenger_for_platform(self, platform: str):
        if platform == "instagram" and self.instagram:
            return self.instagram
        if platform == "telegram" and self.telegram:
            return self.telegram
        return self.whatsapp

    @staticmethod
    def _vendor_recipient_id(vendor: dict, platform: str) -> str | None:
        if platform == "instagram":
            return vendor.get("instagram_page_id")
        if platform == "telegram":
            return vendor.get("telegram_vendor_chat_id")
        return vendor.get("whatsapp_number")

    @staticmethod
    def _is_vendor_sender(vendor: dict, message: ParsedInboundMessage) -> bool:
        if message.platform == "telegram":
            chat_id = str((message.raw.get("chat") or {}).get("id") or "")
            return bool(vendor.get("telegram_vendor_chat_id") and chat_id == vendor["telegram_vendor_chat_id"])
        return bool(vendor.get("whatsapp_number") and message.from_number == vendor["whatsapp_number"])

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
                customer_target=self._customer_reply_target(message),
                platform=message.platform,
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
                customer_target=self._customer_reply_target(message),
                platform=message.platform,
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
        platform: str,
        customer_text: str,
        vendor_text: str,
        messenger=None,
    ) -> None:
        vendor_target = self._vendor_recipient_id(vendor, platform) or customer_target
        _messenger = messenger or self.whatsapp

        await _messenger.send_text(vendor=vendor, to=customer_target, body=customer_text)
        await self.customers.record_message(
            vendor_id=vendor["id"],
            customer_id=customer["id"],
            direction="OUTBOUND",
            message_type="text",
            body_text=customer_text,
            sender_number=self._vendor_recipient_id(vendor, platform),
            recipient_number=customer_target,
        )

        await _messenger.send_text(vendor=vendor, to=vendor_target, body=vendor_text)
        await self.customers.record_message(
            vendor_id=vendor["id"],
            customer_id=customer["id"],
            direction="OUTBOUND",
            message_type="text",
            body_text=vendor_text,
            sender_number=self._vendor_recipient_id(vendor, platform),
            recipient_number=vendor_target,
        )

    @staticmethod
    def _customer_reply_target(message: ParsedInboundMessage) -> str:
        if message.platform == "telegram":
            return str((message.raw.get("chat") or {}).get("id") or message.from_number)
        return message.from_number

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

    # ---- Telegram webhook parsing ----

    def _extract_telegram_messages(self, update: dict) -> list[ParsedInboundMessage]:
        message = update.get("message") or update.get("edited_message")
        if not message:
            callback_query = update.get("callback_query") or {}
            message = callback_query.get("message")
            if not message:
                return []
            callback_data = callback_query.get("data") or ""
            sender = callback_query.get("from") or {}
            chat = message.get("chat") or {}
            return [
                ParsedInboundMessage(
                    from_number=str(sender.get("id") or ""),
                    phone_number_id=str(chat.get("id") or ""),
                    message_id=str(callback_query.get("id") or message.get("message_id") or ""),
                    text=callback_data.strip(),
                    message_type="callback_query",
                    platform="telegram",
                    profile_name=self._telegram_display_name(sender),
                    raw={**message, "callback_query": callback_query},
                )
            ]

        sender = message.get("from") or {}
        chat = message.get("chat") or {}
        text = self._telegram_message_text(message)
        if not text:
            return []
        return [
            ParsedInboundMessage(
                from_number=str(sender.get("id") or chat.get("id") or ""),
                phone_number_id=str(chat.get("id") or ""),
                message_id=str(message.get("message_id") or ""),
                text=text,
                message_type="text",
                platform="telegram",
                profile_name=self._telegram_display_name(sender),
                raw=message,
            )
        ]

    @staticmethod
    def _telegram_message_text(message: dict) -> str:
        return (
            message.get("text")
            or message.get("caption")
            or ""
        ).strip()

    @staticmethod
    def _telegram_display_name(sender: dict) -> str | None:
        first_name = sender.get("first_name") or ""
        last_name = sender.get("last_name") or ""
        username = sender.get("username")
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()
        return full_name or username
