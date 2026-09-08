# Products as Context (Hybrid) for the AI Agent

## Context

Today the AI sales agent only sees products by calling the `search_products` LangChain tool — every product question costs an extra LLM round-trip (tool call → result → reply), which adds latency and lets the model miss items that don't match its search keywords. The change: embed the vendor's product catalogue directly in the system prompt so the agent answers product questions from context in one step.

**Decided behavior:**
- **Hybrid threshold**: catalogue ≤ 40 products → embed in system prompt; larger → tool-only (prompt stays small).
- **`search_products` tool is kept in all cases** as fallback (item not in list / freshness).
- Business info stays tool-based (`search_business_info` unchanged).
- Checkout tool and catalogue-media tool unchanged.

**Approach**: fetch products **once per inbound message** in `AgentService._handle_customer_message`, pass the raw list through `config["configurable"]` (same pattern the repos already use), format + threshold-check in `agent.py`. No signature changes to `create_customer_agent`; no interface/repo/migration changes.

## Changes

### 1. `app/agent/agent.py` — formatting + prompt

**Add after `SYSTEM_PROMPT_CHECKOUT_RULES` (~line 43):**

```python
PRODUCTS_CONTEXT_LIMIT = 40  # embed catalogue in prompt when vendor has at most this many products
_DESC_TRUNCATE = 200         # per-field char cap for description/extra_details

def _truncate(text: str | None, limit: int = _DESC_TRUNCATE) -> str: ...

def format_products_context(products: list[dict], vendor_settings: dict | None) -> str:
    """Mirrors the search_products tool output format (tools.py lines 64-80) for consistency."""
```

`format_products_context` builds one line per product, exactly the tool's format:
`- {name} | {currency} {price:,.0f}` + `" | Available"`/`" | Not available"` (gated on `vendor_settings["use_product_availability"]`, default True) + ` | {desc}` + ` | {extra}` — with description/extra_details truncated to 200 chars. Price `None` → `"Price not listed"`.

**Replace `build_system_prompt` (line 45)** with `build_system_prompt(vendor_settings, products_context: str | None = None)`:
- New `catalogue_section` = `"Product Catalogue (the store's full product list, authoritative):\n" + products_context + "\n\n"`, inserted after `SYSTEM_PROMPT_BASE`.
- Product line branches: with context → "The catalogue above is the store's authoritative product list. Answer product questions (names, prices, availability, details) directly from it without calling tools. Use the search_products tool only if the customer asks about an item not in the list above, or if you need fresher results." Without → existing `"- Use search_products to search for items."` line.
- KB line (`enable_knowledge_base_answers` branching) unchanged, but decoupled from the product line.
- `SYSTEM_PROMPT_BASE` untouched (its "If a product is missing, say its not available." rule pairs with the embedded list).

### 2. `app/agent/agent.py` — wire through the graph

**In `call_model` (line 96), replace the prompt build at line 122:**

```python
catalogue_products = config["configurable"].get("catalogue_products")
products_context = None
if catalogue_products and len(catalogue_products) <= PRODUCTS_CONTEXT_LIMIT:
    products_context = format_products_context(catalogue_products, config["configurable"].get("vendor_settings"))

prompt = [SystemMessage(content=build_system_prompt(config["configurable"].get("vendor_settings"), products_context=products_context))] + all_messages
```

The `len(...) <= limit` check is the overflow detection — agent_service fetches `limit=PRODUCTS_CONTEXT_LIMIT + 1` (41), so an over-threshold vendor fails the check. No extra DB work. The tools rebuild at lines 103–110 is untouched — `search_products` stays bound every step.

**In `run_customer_agent` (line 197):** add optional kwarg `catalogue_products: list[dict] | None = None` and store it in `config["configurable"]` (line 211–222).

`create_customer_agent` signature: **unchanged** (catalogue never touches the ToolNode).

### 3. `app/services/agent_service.py` — fetch once per message

Extend import (line 12): `from app.agent.agent import PRODUCTS_CONTEXT_LIMIT, create_customer_agent, run_customer_agent`.

In `_handle_customer_message`, after `vendor_settings` fetch (line 71), before the `AsyncSqliteSaver` block:

```python
try:
    catalogue_products = await self._products.list_for_vendor(vendor["id"], limit=PRODUCTS_CONTEXT_LIMIT + 1)
except Exception:
    catalogue_products = None  # degrade to tool-only path
```

Pass `catalogue_products=catalogue_products` to `run_customer_agent` (line 93).

`list_for_vendor` already exists on the `ProductRepository` protocol and in both SQL and in-memory repos; SQL ordering (`in_stock DESC, id ASC` — `sql.py:370`) puts in-stock items first in the embedded list.

### 4. `scripts/simulate_chat.py` — fix pre-existing breakage

Line ~382 passes `knowledge=knowledge` to `AgentService(...)`, which accepts no such kwarg — the script currently raises `TypeError`. Remove the kwarg and the `knowledge` variable (~line 375); delete the now-dead `MemoryKnowledgeRepo` class (lines 97–167).

### 5. `app/agent/tools.py` — no changes

All four tools and `create_agent_tools` stay exactly as-is.

## Verification

1. **Prompt check (no LLM/DB):**
   `python -c` snippet calling `build_system_prompt` + `format_products_context` with a sample product — confirm catalogue block, availability suffix, checkout rules present; and with `products_context=None` the old tool-only shape.
2. **Full harness:** `python -m scripts.test_agent` — seeded vendor has 4 products (≤40), so catalogue is embedded. All cases should pass; product price/out-of-stock/not-in-catalog/multi-product cases should now answer **without** console printing `AI calling tool: search_products`; business-info cases still call `search_business_info`; checkout cases still trigger `SIGNAL:CHECKOUT_REQUESTED`.
3. **Tool-only branch:** temporarily set `PRODUCTS_CONTEXT_LIMIT = 2` and rerun — cases still pass with `search_products` calls reappearing. Revert.
4. **Simulator:** `python scripts/simulate_chat.py` (now fixed) — ask about a seeded product (expect direct answer, no tool call), then an item not in `MemoryProductRepo` (expect not-available answer).
5. **Prompt-size sanity:** build a fake 40-product list and check `len(format_products_context(...))` fits comfortably (200-char field caps keep it bounded).
