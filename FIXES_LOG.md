# Bug Fixes Log

This document records bugs, their root causes, and the exact fixes implemented in the repository.

---

## [2026-07-31] Order Confirmation Message Loop on Multi-Turn Inbound Messages

### Problem Summary
When a customer expressed readiness to pay (e.g., "I am ready to pay now"), the agent invoked the `request_bank_details_and_vendor_approval` tool, returning `"SIGNAL:CHECKOUT_REQUESTED"`. However, on every subsequent message sent by the customer (e.g., "hello", "is this still available?"), the bot repeatedly resent the "order confirmed" / bank account details message instead of answering the customer's new inquiry.

### Root Cause
1. **Unbounded Historical Message Scanning in `run_customer_agent` ([`app/agent/agent.py`](file:///home/azureuser/remake/project-remake1/app/agent/agent.py))**:
   `run_customer_agent` inspected `final_state["messages"]` by walking backward through the entire conversation history saved in SQLite checkpoints. Because `ToolMessage(content="SIGNAL:CHECKOUT_REQUESTED")` remained in the conversation history from turn 1, every subsequent turn found the old `ToolMessage` and set `new_order_status = "WAITING_VENDOR_CHECKOUT_APPROVAL"`.

2. **Always-On Approval Logic in `AgentService` ([`app/services/agent_service.py`](file:///home/azureuser/remake/project-remake1/app/services/agent_service.py))**:
   `AgentService._handle_customer_message` checked `if result["order_status"] == "WAITING_VENDOR_CHECKOUT_APPROVAL"`. Because `order_status` was forced to `WAITING_VENDOR_CHECKOUT_APPROVAL` on every turn, `AgentService` continually re-overwrote the response text with bank account details or re-generated vendor approval prompts on every turn.

3. **Risk of Unsafe History Truncation**:
   In `agent.py`, truncating history blindly to the last 10 items could slice between an `AIMessage` with `tool_calls` and its corresponding `ToolMessage`, breaking LangChain/LangGraph model input contracts.

### Solution & What Was Done
1. **Isolated Current-Turn Tool Signals**:
   Updated [`run_customer_agent`](file:///home/azureuser/remake/project-remake1/app/agent/agent.py#L240-L260) to identify the starting index of the current turn (from the latest `HumanMessage` onward). Tool output signals (`SIGNAL:CHECKOUT_REQUESTED` and `CATALOGUE_MEDIA|`) are now scanned **only within the current turn's messages**.
2. **Explicit `checkout_requested` Flag**:
   Added a `checkout_requested: bool` flag to the dictionary returned by `run_customer_agent` so `AgentService` knows whether checkout was requested *in the current turn*.
3. **Turn-Scoped Vendor Prompting**:
   Updated [`AgentService._handle_customer_message`](file:///home/azureuser/remake/project-remake1/app/services/agent_service.py#L113) to check `if result.get("checkout_requested"):` instead of checking the persistent `order_status`. Payment details and vendor approval prompts are now dispatched only when checkout is newly requested in the active turn.
4. **Turn-Aware Context Window Truncation**:
   Updated history truncation in [`app/agent/agent.py`](file:///home/azureuser/remake/project-remake1/app/agent/agent.py#L118-L125) to align slice boundaries to `HumanMessage` instances, avoiding broken tool call/response pairs.
5. **Added Regression Test Suite**:
   Created [`tests/test_checkout_multiturn.py`](file:///home/azureuser/remake/project-remake1/tests/test_checkout_multiturn.py) to simulate multi-turn checkout interactions and verify that follow-up turns execute natural responses without looping order confirmation messages.

---
