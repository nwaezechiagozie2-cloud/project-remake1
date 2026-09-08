from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedInboundMessage:
    from_number: str
    phone_number_id: str
    message_id: str | None
    text: str
    message_type: str
    platform: str = "whatsapp"
    profile_name: str | None = None
    ad_context: dict | None = None
    raw: dict = field(default_factory=dict)


@dataclass(slots=True)
class AgentDecision:
    customer_text: str | None = None
    vendor_text: str | None = None
    customer_target_number: str | None = None
    vendor_buttons: list[dict] | None = None
    order_status: str = "INQUIRY"

