"""
Tools that the AI agent can call to answer customer questions.

These are real LangChain tools — the LLM decides when to call them
based on the customer's message. No hardcoded routing.
"""
from typing import Optional

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# These closures are populated at runtime by create_agent_tools() below,
# binding the actual repository instances so the @tool functions can use them.
# ---------------------------------------------------------------------------
_products_repo = None
_knowledge_repo = None
_vendor_id: int | None = None
_vendor_dict: dict | None = None
_vendor_settings: dict | None = None


def create_agent_tools(
    products_repo,
    knowledge_repo,
    vendor_id: int,
    vendor_dict: dict,
    vendor_settings: dict,
) -> list:
    """
    Create tool instances bound to the current vendor's data.
    Called per-request so each invocation has the right vendor context.
    """
    global _products_repo, _knowledge_repo, _vendor_id, _vendor_dict, _vendor_settings
    _products_repo = products_repo
    _knowledge_repo = knowledge_repo
    _vendor_id = vendor_id
    _vendor_dict = vendor_dict
    _vendor_settings = vendor_settings

    return [search_products, search_knowledge_base, get_store_catalogue, request_bank_details_and_vendor_approval]


@tool
async def search_products(query: str) -> str:
    """Search the store's product database for items matching the query.
    Use this when the customer asks about a specific product, price, or item.
    Returns a list of matching products with names, prices, and descriptions."""
    if not _products_repo or not _vendor_id:
        return "No products available."

    results = await _products_repo.list_for_vendor(_vendor_id, search=query)

    if not results:
        # Try without search filter as fallback
        results = await _products_repo.list_for_vendor(_vendor_id)

    if not results:
        return "The store has no products listed right now."

    lines = []
    for p in results[:6]:
        price = p.get("price")
        currency = p.get("currency") or "NGN"
        price_str = f"{currency} {price:,.0f}" if price is not None else "Price not listed"
        desc = p.get("description") or ""
        extra = p.get("extra_details") or ""
        lines.append(
            f"- {p.get('name')} | {price_str}"
            + (f" | {desc}" if desc else "")
            + (f" | {extra}" if extra else "")
        )

    return "Products found:\n" + "\n".join(lines)


@tool
async def search_knowledge_base(query: str) -> str:
    """Search the store's FAQ and knowledge base for answers about delivery, payment,
    returns, store hours, location, policies, etc.
    IMPORTANT: Provide 1-2 simple keywords as the query (e.g. 'delivery'), NOT the full question."""
    if not _knowledge_repo or not _vendor_id:
        return "No knowledge base available."

    settings = _vendor_settings or {}
    if not settings.get("enable_knowledge_base_answers", True):
        return "Knowledge base is disabled for this store."

    # Build allowed entry types from vendor settings
    allowed_types = ["FAQ"]
    if settings.get("allow_product_qa", True):
        allowed_types.append("PRODUCT")
    if settings.get("allow_office_qa", True):
        allowed_types.append("OFFICE")

    entry = await _knowledge_repo.search(_vendor_id, query, allowed_types=allowed_types)
    if entry:
        question = entry.get("question", "")
        answer = entry.get("answer", "")
        return f"FAQ Match:\nQuestion: {question}\nAnswer: {answer}"

    return "No matching FAQ found for this question."


@tool
async def get_store_catalogue() -> str:
    """Get the store's uploaded catalogue file (PDF or image) to share with the customer.
    Use this when they didnt ask for a specific product, so the customer can browse the full catalogue."""
    if not _vendor_dict:
        return "No catalogue available."

    media_id = _vendor_dict.get("product_catalogue_media_id")
    url = _vendor_dict.get("product_catalogue_url")
    caption = _vendor_dict.get("product_catalogue_caption") or "Product catalogue"

    if media_id:
        return f"CATALOGUE_MEDIA|document|{media_id}|{caption}"
    if url:
        return f"CATALOGUE_MEDIA|image|{url}|{caption}"

    return "The store has not uploaded a catalogue."


@tool
def request_bank_details_and_vendor_approval():
    """
    Call this tool ONLY when the customer explicitly asks for payment details, 
    bank account numbers, or says 'I am ready to transfer/pay right now'.
    CRITICAL: Do not call this for 'I want to buy', 'I'm interested', or 'I'll take it'. 
    Wait for the customer to ask for the payment step.
    """
    return "SIGNAL:CHECKOUT_REQUESTED"
