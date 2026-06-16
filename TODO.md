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

## Scan findings — 2026-06-01

### 17. README test instructions are intentionally out of date
`README.md` references `pytest -q tests`, but the `tests/` directory has been removed intentionally. Either remove that command from the README, replace it with the current script-based checks, or add a short note that automated tests are temporarily absent.

Current available validation scripts:
- `scripts/smoke_test.py`
- `scripts/post_deploy_smoke.py`
- `scripts/test_agent.py`
- `scripts/test_fallback.py`
- `scripts/simulate_chat.py`

### 18. Heroku deployment needs `$PORT` support
`Dockerfile` currently runs `uvicorn ... --port 8001`. Heroku web dynos must bind to the runtime-assigned `$PORT`, so either use a `Procfile`/buildpack deployment with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, or update the container command / `heroku.yml` to use `$PORT`.

### 19. Frontend and backend need separate deployment decisions
The repo contains both a FastAPI backend at the root and a Next app under `frontend/`. Heroku can deploy them as separate apps, but the frontend must have `NEXT_PUBLIC_API_URL` set to the deployed backend URL. Alternatively, deploy only the backend to Heroku and put the frontend on Vercel/Netlify.

### 20. Production CORS should be pinned before deploy
`app/main.py` currently allows all origins while also allowing credentials. For production, use `settings.frontend_base_url` or an explicit allowed-origin list so browser auth requests from the deployed frontend behave predictably.

### 21. Database choice must be settled for Heroku
`app/config.py` defaults to MySQL-style settings and `docker-compose.yml` uses MySQL locally. Heroku's first-party managed SQL add-on is typically Postgres, but this code does not include `asyncpg` or a Postgres URL path. For the lowest-change Heroku deploy, use a managed MySQL provider and set `DATABASE_URL=mysql+aiomysql://...`.

### 22. Runtime SQLite checkpoint file is not durable on Heroku
`app/services/agent_service.py` and `app/agent/agent.py` use `checkpoints.db` for LangGraph memory. Heroku dyno filesystems are ephemeral, so agent checkpoint memory can disappear on restart/redeploy. Move this to a durable store before depending on conversation memory in production.

---

## Not yet reviewed (next pass)
- Alembic migrations vs current `app/repositories/models.py`
- Full production deploy rehearsal on Heroku

---

## Scan findings - 2026-06-13

### 23. Registration contract regressed: backend no longer accepts `name`, but UI and schema example still imply it
Observed across:
- `app/schemas/api.py:17`
- `app/api/routes/auth.py:57`
- `app/services/auth_service.py:77`
- `frontend/src/app/register/page.tsx:9`

`VendorRegisterRequest` only accepts `email` and `password`, but its schema example still includes `name`. The frontend register page also only stores `{ email, password }`, and `AuthService.register()` now derives `name` from the email prefix (`email.split("@", 1)[0]`). Result: vendor records are created with synthetic names even though the product/UI contract still suggests the user should choose a business name. This is a real behavior change, not just a doc typo.

Impact:
- New vendor records get poor default names.
- API docs and product expectations are misleading.
- If the intended product flow still requires a business/store name at signup, that capability is currently gone.

Fix options:
- Restore a required `name` field end to end in the backend and frontend.
- Or explicitly make name collection a later profile-completion step and remove the stale schema example / UI assumptions.

### 24. Instagram vendor messages are misclassified as customer messages
Observed at:
- `app/services/webhook_service.py:218`

`WebhookService._is_vendor_sender()` handles Telegram specially, then falls back to comparing `message.from_number` against `vendor["whatsapp_number"]` for every other platform. That means Instagram messages from the vendor account are never recognized as vendor-originated, because Instagram sender IDs are compared against a WhatsApp phone number.

Impact:
- Vendor Instagram replies can be treated as customer messages.
- The bot can respond to the vendor as if they were the customer.
- Contact-save side effects, conversation-state updates, and order-state transitions can be applied to the wrong actor.

Fix:
- Add an Instagram-specific sender check using Instagram identifiers.
- Avoid using the WhatsApp fallback for non-WhatsApp platforms.

### 25. Instagram approval prompts are addressed to the page/account itself, not to a reachable vendor recipient
Observed at:
- `app/services/webhook_service.py:129`
- `app/services/webhook_service.py:210`

For Instagram, `_vendor_recipient_id()` returns `vendor["instagram_page_id"]`. Later, vendor approval prompts (`decision.vendor_buttons` / `decision.vendor_text`) are sent to that value. But Instagram messaging targets a user/IGSID conversation recipient, not the business page/account ID as an approval inbox. There is no separate vendor-recipient concept stored for Instagram, so these approval prompts have no valid destination.

Impact:
- Checkout approval requests for Instagram conversations will not reach the vendor correctly.
- The system appears to support vendor approval on Instagram, but the routing target is wrong.

Fix options:
- Introduce a real vendor recipient/channel for Instagram approvals.
- Or disable vendor-approval prompts on Instagram until there is a valid approval destination.

### 26. Telegram "connected" status is misleading because it ignores missing vendor chat binding
Observed at:
- `app/api/routes/vendor_admin.py:429`

`_telegram_credentials_response()` marks Telegram as connected when `telegram_bot_token` exists. But outbound vendor-side notifications and approval prompts still depend on `telegram_vendor_chat_id`. If only the token is saved, the UI reports success while real approval flows can still fail or be skipped.

Impact:
- Vendors can believe Telegram is fully configured when only half the setup is done.
- Approval prompts and vendor notifications may silently never arrive.

Fix:
- Make `connected` reflect the minimum configuration actually needed for the supported flows.
- At minimum, distinguish between "bot token saved" and "vendor chat linked".

### 27. Settings UI cannot clear saved WhatsApp or Telegram credentials
Observed across:
- `frontend/src/app/(main)/settings/page.tsx:145`
- `frontend/src/app/(main)/settings/page.tsx:168`
- `app/repositories/sql.py:251`
- `app/repositories/sql.py:287`

The settings page only sends non-empty fields when saving. Blank values are omitted from the request payload. On the backend, the repository update methods only write fields when the incoming value is not `None`. Combined effect: once a WhatsApp token, WhatsApp phone number ID, Telegram bot token, or Telegram vendor chat ID is saved, this UI/API path cannot remove it.

Impact:
- Credentials cannot be revoked or corrected through the current admin UI if the user needs to clear a wrong value first.
- Operational cleanup and provider switching are harder than they should be.

Fix options:
- Allow explicit null/empty-field clearing semantics in the API.
- Add dedicated disconnect/clear actions in the UI for sensitive credentials.
