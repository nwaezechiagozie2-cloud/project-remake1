"""
Tools that the AI agent can call to answer customer questions.

These are real LangChain tools — the LLM decides when to call them
based on the customer's message. No hardcoded routing.

Each call to create_agent_tools() returns fresh tool instances bound to
that request's vendor context via closures, so concurrent requests for
different vendors can never read each other's data.
"""
from langchain_core.tools import tool


def create_agent_tools(
    products_repo,
    business_info_repo,
    vendor_id: int,
    vendor_dict: dict,
    vendor_settings: dict,
) -> list:
    """
    Create tool instances bound to the current vendor's data.
    Called per-request so each invocation has the right vendor context.
    """
    @tool
    async def search_products(query: str) -> str:
        """Search the store's product database for items matching the query.
        Use this when the customer asks about a specific product, price, or item.
        Returns a list of matching products with names, prices, and descriptions."""
        if not products_repo or not vendor_id:
            return "No products available."

        results = await products_repo.list_for_vendor(vendor_id, search=query)

        if not results:
            # Try without search filter as fallback
            results = await products_repo.list_for_vendor(vendor_id)

        if not results:
            return "The store has no products listed right now."

        lines = []
        include_availability = (vendor_settings or {}).get("use_product_availability", True)
        for p in results[:6]:
            price = p.get("price")
            currency = p.get("currency") or "NGN"
            price_str = f"{currency} {price:,.0f}" if price is not None else "Price not listed"
            desc = p.get("description") or ""
            extra = p.get("extra_details") or ""
            availability = ""
            if include_availability:
                availability = " | Available" if p.get("in_stock") else " | Not available"
            lines.append(
                f"- {p.get('name')} | {price_str}"
                + availability
                + (f" | {desc}" if desc else "")
                + (f" | {extra}" if extra else "")
            )

        return "Products found:\n" + "\n".join(lines)

    @tool
    async def search_business_info(query: str) -> str:
        """Search the store's business information for answers about delivery, payment,
        returns, store hours, location, policies, etc.
        IMPORTANT: Provide 1-2 simple keywords as the query (e.g. 'delivery'), NOT the full question."""
        if not business_info_repo or not vendor_id:
            return "No business information available."

        content = await business_info_repo.search(vendor_id, query)
        if content:
            return f"Business Info Match:\n{content}"

        return "No matching business information found for this query."

    tools = [search_products, request_bank_details_and_vendor_approval]
    if (vendor_settings or {}).get("enable_knowledge_base_answers", True):
        tools.insert(1, search_business_info)
    return tools


@tool
def request_bank_details_and_vendor_approval():
    """
    Call this tool ONLY when the customer explicitly asks for payment details,
    bank account numbers, or says 'I am ready to transfer/pay right now'.
    CRITICAL: Do not call this for 'I want to buy', 'I'm interested', or 'I'll take it'.
    Wait for the customer to ask for the payment step.
    """
    return "SIGNAL:CHECKOUT_REQUESTED"
