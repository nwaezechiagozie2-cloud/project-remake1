import asyncio
import pytest
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from app.agent.agent import run_customer_agent
from app.domain.models import AgentDecision

class DummyAgent:
    def __init__(self, turns):
        self.turns = turns
        self.current_turn = 0

    async def ainvoke(self, inputs, config=None):
        turn_data = self.turns[self.current_turn]
        self.current_turn += 1
        return turn_data

@pytest.mark.asyncio
async def test_checkout_multiturn():
    print("--- Running multi-turn checkout bug test ---")

    # Turn 1: Customer says "I am ready to pay". LLM calls tool, tool returns SIGNAL:CHECKOUT_REQUESTED.
    turn1_state = {
        "messages": [
            HumanMessage(content="I am ready to pay now"),
            AIMessage(content="", tool_calls=[{"name": "request_bank_details_and_vendor_approval", "args": {}, "id": "call_1"}]),
            ToolMessage(content="SIGNAL:CHECKOUT_REQUESTED", tool_call_id="call_1"),
            AIMessage(content="Your order is confirmed! I have notified the store owner to approve your checkout.")
        ],
        "order_status": "INQUIRY"
    }

    # Turn 2: Customer says "Hello, any update?". LLM responds normally without tool calls.
    turn2_state = {
        "messages": [
            # Turn 1 messages preserved in thread checkpointer:
            HumanMessage(content="I am ready to pay now"),
            AIMessage(content="", tool_calls=[{"name": "request_bank_details_and_vendor_approval", "args": {}, "id": "call_1"}]),
            ToolMessage(content="SIGNAL:CHECKOUT_REQUESTED", tool_call_id="call_1"),
            AIMessage(content="Your order is confirmed! I have notified the store owner to approve your checkout."),
            # Turn 2 messages:
            HumanMessage(content="Hello, any update?"),
            AIMessage(content="We are still waiting for store confirmation. I'll notify you as soon as it's ready!")
        ],
        "order_status": "WAITING_VENDOR_CHECKOUT_APPROVAL"
    }

    agent = DummyAgent([turn1_state, turn2_state])

    # Run Turn 1
    res1 = await run_customer_agent(
        agent=agent,
        incoming_message="I am ready to pay now",
        vendor_id=1,
        thread_id="test_thread",
        products_repo=None,
        business_info_repo=None,
        vendor_dict={"id": 1},
        vendor_settings={},
        settings=None,
        order_status="INQUIRY"
    )

    print(f"Turn 1 Result: checkout_requested={res1.get('checkout_requested')}, status={res1.get('order_status')}")
    assert res1.get("checkout_requested") is True, "Turn 1 should request checkout"
    assert res1.get("order_status") == "WAITING_VENDOR_CHECKOUT_APPROVAL", "Turn 1 status should be WAITING_VENDOR_CHECKOUT_APPROVAL"

    # Run Turn 2
    res2 = await run_customer_agent(
        agent=agent,
        incoming_message="Hello, any update?",
        vendor_id=1,
        thread_id="test_thread",
        products_repo=None,
        business_info_repo=None,
        vendor_dict={"id": 1},
        vendor_settings={},
        settings=None,
        order_status="WAITING_VENDOR_CHECKOUT_APPROVAL"
    )

    print(f"Turn 2 Result: checkout_requested={res2.get('checkout_requested')}, status={res2.get('order_status')}")
    print(f"Turn 2 Response: '{res2.get('response_text')}'")

    assert res2.get("checkout_requested") is False, "Turn 2 should NOT request checkout again from old tool history!"
    assert res2.get("response_text") == "We are still waiting for store confirmation. I'll notify you as soon as it's ready!", "Turn 2 response text should be the AI response, not repeated checkout confirmation!"

    print("✅ MULTI-TURN CHECKOUT TEST PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(test_checkout_multiturn())
