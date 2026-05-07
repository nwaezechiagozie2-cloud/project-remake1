# Known Issues

_Last updated: 7 May 2026_

---

## ⚠️ Architecture / Code Quality

- [ ] **`tools.py` uses global mutable state (not thread-safe)** — The tool functions rely on module-level globals (`_products_repo`, `_vendor_id`, etc.) that are overwritten on each call via `create_agent_tools()`. If two vendors are served concurrently, one vendor's repo/context could bleed into another's request.

- [ ] **Gemini tool-calling not fully wired** — The Gemini provider is configured via `langchain-google-genai`, but native tool calling through the Gemini SDK isn't set up. The OpenAI-compatible wrapper used for NVIDIA NIM doesn't translate cleanly to Gemini's tool format.

## 🚧 Incomplete Features

- [ ] **`address_collector` node not implemented** — After vendor approval, there's no step to capture the customer's delivery address before sending bank details.

- [ ] **`vendor_payment_confirmation` node not implemented** — No receipt verification flow exists. The order lifecycle currently stops at `ACCOUNT_DETAILS_SENT` / `PAYMENT_CONFIRMED` without actually verifying proof of payment.

- [ ] **Frontend ↔ Backend not fully wired** — The Next.js pages (dashboard, inbox, products, knowledge, settings) exist but aren't fully connected to the FastAPI API endpoints.

- [ ] **Live WhatsApp webhook not tested** — The simulator works end-to-end, but no live test has been run against the real Meta WhatsApp Business API sandbox via ngrok.
