# TODO — code-grounded issues to fix later

Each entry cites the file:line so future-me can jump straight in. Only includes things I actually observed in the source, not claims from stale docs.

## Scope read so far
- `app/main.py`
- `app/config.py`
- `app/agent/agent.py`
- `app/agent/tools.py`
- `app/services/agent_service.py`

Frontend, routes, repositories, schemas, and other services not yet reviewed — add to this list as those are read.

---

## Bugs / correctness

### 1. Thread-unsafe globals in `app/agent/tools.py`
`tools.py:16-20` declares module-level globals (`_products_repo`, `_business_info_repo`, `_vendor_id`, `_vendor_dict`, `_vendor_settings`) which `create_agent_tools` mutates on every request (`tools.py:34-39`). Two concurrent requests for different vendors will clobber each other's context mid-flight — vendor A's tool call can read vendor B's repo/ID. Move state into a per-request closure or pass via LangChain's `RunnableConfig.configurable`.

### 2. History truncation can break tool-call/tool-response pairing
`agent.py:98-100` slices `state["messages"]` to the last 10 entries with no awareness of tool-call structure. If the cut lands between an AI message with `tool_calls` and its matching `ToolMessage`, the next LLM call will reject the prompt (Gemini in particular is strict). Truncate by conversation turns, or walk backward and keep tool-call pairs together.

### 3. Guardrail silently overrides the LLM without telling it
`agent.py:220-241` resets `order_status` to `INQUIRY` if the customer's last human message lacks payment keywords — but the AI's response (already generated assuming checkout succeeded) is still sent verbatim. Result: customer reads "you'll get the account details shortly" while the system says no checkout happened. Either rewrite the AI message when the guardrail fires, or feed the rejection back through the graph so the model can reply correctly.

### 4. Guardrail keyword matching is naive
`agent.py:220` — `payment_keywords` contains "transfer" twice (dup), and uses substring matching, so "send me a picture" trips "send" and "how to" trips on innocuous phrases. Tighten to whole-word matching or use the LLM with a guard-prompt instead of a keyword list.

### 5. `order_status` on `AgentState` is declared but never written through the graph
`agent.py:21` adds `order_status` to `AgentState`, and `run_customer_agent` seeds it (`agent.py:205-207`), but no node ever updates it. The actual status mutation lives in post-hoc message inspection at lines 218-241. Either remove the field from state, or actually update it inside a node so the checkpointer persists it correctly.

### 6. CORS misconfiguration
`main.py:50-56` sets `allow_origins=["*"]` together with `allow_credentials=True`. Browsers reject this combination, and it's a security problem in production regardless. Pin allowed origins (frontend URL from `settings.frontend_base_url`).

### 7. Provider detection by string sniffing
`agent.py:108` — `"Google" in str(model)` to label which provider is being tried. Fragile across LangChain version bumps. Track provider name explicitly alongside the model instance.

---

## Dead code / inefficiency

### 8. Unused `_get_checkpointer` + unused import
`agent_service.py:7` imports `SqliteSaver` and `agent_service.py:29-35` defines `_get_checkpointer` storing a `SqliteSaver` instance — neither is ever called. The live path at `agent_service.py:67` uses `AsyncSqliteSaver.from_conn_string(...)` as a context manager per request. Delete the dead code; consider whether opening/closing the sqlite checkpointer per inbound message is the right lifecycle (probably hoist to app lifespan).

### 9. `ad_context` accepted but unused
`run_customer_agent(ad_context=...)` at `agent.py:188` and `agent_service.py:98` is plumbed through but never passed into the prompt or tools. Either wire it into the system prompt / a tool, or drop the param.

### 10. Tools and provider list rebuilt per turn
`create_nodes -> call_model` (`agent.py:76-92`) re-imports `create_agent_tools` and re-binds tools to providers on every model call. Functionally fine, but the rebind happens twice per request (once in `create_customer_agent` for `ToolNode`, once per `call_model`). Either build once at request entry and pass via config, or accept the cost knowingly.

### 11. `print()` instead of structured logger
`agent.py:110, 116, 119, 123, 240` use `print` while `app/logging.py` configures a real logger. Swap to logger so production logs are structured and respect log levels.

---

## Cosmetic / content

### 12. System prompt has a typo / placeholder
`agent.py:25` — `"production-grade autonomous agent for an o store"`. "an o store" looks like a leftover placeholder. Replace with the vendor's store name (already on `vendor_dict`) or a generic phrase.

### 13. Default NVIDIA model is old
`config.py:65` defaults `nvidia_model` to `meta/llama-3.1-70b-instruct`. Worth re-checking what NVIDIA currently serves and whether a newer Llama or Nemotron is a better default.

---

## 15. Google login userinfo call times out under slow network
`oauth_login_service.py:67` creates an `httpx.AsyncClient(timeout=20)` for both the token exchange and the userinfo call. Observed in the wild on 2026-05-24: TLS handshake to `openidconnect.googleapis.com` took ~7.4s, and a prior attempt blew past 20s and 500'd with `httpx.ReadTimeout` at line 84. The bug presents as "Google login randomly fails" and gets misattributed to account / duplicate-email issues.

Fix: bump the timeout (e.g. `httpx.Timeout(30.0, connect=10.0, read=30.0)`) and retry the userinfo call once on `httpx.TimeoutException`. Same treatment for `complete_instagram` at line 125 and the long-lived-token / subscribe-apps calls at 174/186.

## 16. ~~Three of five `bot_settings` fields are wired to nothing~~ (resolved 2026-05-24)
Removed `allow_product_qa` and `allow_office_qa` everywhere (model, schemas, repo, frontend type + UI rows, migration `20260524_01`). Implemented `confirm_before_sending_account_details` in `agent_service.py` — when OFF, bank details are sent immediately on checkout intent and the vendor is just notified (no approval buttons); when ON, the existing approve/deny flow runs. Tightened `enable_knowledge_base_answers` so the `search_business_info` tool is no longer exposed to the LLM when disabled (instead of returning a "disabled" string after a wasted tool call).

## Documentation hygiene

### 14. Stale top-level docs contradict the code
The Explore agent's summary parroted these and I shipped wrong claims as a result. Each of these needs reconciliation against the current code or a "STALE — see code" banner:
- `issues.md` claims Gemini tool-calling isn't wired — it is (`agent.py:54-55`).
- `issues.md` claims address-collector / payment confirmation / vendor approval are missing — vendor approval and bank-detail dispatch exist (`agent_service.py:107-153`).
- `README.md`, `HANDOFF.md`, `IMPLEMENTATION_HANDOFF.md`, `PRODUCT_STRATEGY.md`, `project state.md` reference a ReAct agent built with `create_react_agent`. Current code is a hand-built LangGraph `StateGraph` (`agent.py:164-174`).
- Several docs say the system uses OpenAI; it uses Gemini + NVIDIA (via OpenAI-compatible base URL).
- Tool names in docs: `search_knowledge_base` is referenced, actual tool is `search_business_info` (`tools.py:82`).

---

## Not yet reviewed (next pass)
- `app/api/routes/*` — webhook, instagram_webhook, vendor_admin, auth, profile, health
- `app/repositories/*` — sql.py, models.py, base.py
- `app/services/*` — webhook_service, whatsapp_service, instagram_service, google_*, catalogue_ingestion_service, oauth_login_service, auth_service
- `app/schemas/api.py`, `app/domain/*`, `app/security.py`, `app/observability.py`, `app/exception_handler.py`
- `frontend/src/**`
- Alembic migrations vs current `app/repositories/models.py`
