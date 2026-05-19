import operator
from typing import Annotated, Sequence, TypedDict

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import Settings
from app.agent.tools import create_agent_tools


# 1. Define the Graph State
class AgentState(TypedDict):
    # Use add_messages reducer for idiomatic LangGraph message handling
    messages: Annotated[list[BaseMessage], add_messages]
    vendor_id: int
    order_status: str


SYSTEM_PROMPT = (
    "You are a helpful Sales Assistant, a production-grade autonomous agent for an o store. "
    "Your goal is to be helpful, professional, and efficient. Write plain text (no markdown).\n\n"
    "Core Principles:\n"
    "- Ensure end-to-end usable and coherent interactions.\n"
    "- Handle edge cases and invalid queries gracefully.\n"
    "- Prioritize clarity and correctness over cleverness.\n\n"
    "- Be nice to customers-\n\n"
    "Operational Rules:\n"
    "- If a product is missing, say its not available.\n"
    "- Use search_products to search for items and search_business_info for store policies, delivery info, location, and other business details.\n"
    "- CRITICAL FORBIDDEN ACTION: Never call the request_bank_details_and_vendor_approval tool just because a customer says they 'want' to buy, are 'interested', or 'will take' a product. These are still inquiries.\n"
    "- ONLY CALL request_bank_details_and_vendor_approval when the customer explicitly asks 'How do I pay?', 'What is your account number?', or says 'I am ready to transfer the money now'.\n"
    "- If they just say they want to buy, provide product info and ask: 'Do you want to pay so I can send the details?'\n"
    "- Once you call request_bank_details_and_vendor_approval, tell the customer that the store is being notified to approve the order."
)


def get_chat_providers(settings: Settings, tools: list = None):
    """
    Returns a list of configured providers in order of preference.
    Binds tools to each model individually for production safety.
    """
    gemini = None
    if settings.gemini_api_key:
        gemini = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.7,
        )
        if tools:
            gemini = gemini.bind_tools(tools)

    nvidia = None
    if settings.nvidia_api_key:
        nvidia = ChatOpenAI(
            api_key=settings.nvidia_api_key,
            model=settings.nvidia_model,
            base_url=settings.nvidia_base_url,
            temperature=0.7,
        )
        if tools:
            nvidia = nvidia.bind_tools(tools)

    # Order by active provider
    if settings.active_llm_provider == "nvidia":
        return [p for p in [nvidia, gemini] if p]
    return [p for p in [gemini, nvidia] if p]


# 2. Define the Nodes
def create_nodes():
    async def call_model(state: AgentState, config: RunnableConfig):
        """The AI reasoning node. Manual failover for production-grade resilience."""
        settings = config["configurable"].get("settings")
        if not settings:
            from app.config import get_settings
            settings = get_settings()

        from app.agent.tools import create_agent_tools
        tools = create_agent_tools(
            products_repo=config["configurable"].get("products_repo"),
            business_info_repo=config["configurable"].get("business_info_repo"),
            vendor_id=config["configurable"].get("vendor_id"),
            vendor_dict=config["configurable"].get("vendor_dict"),
            vendor_settings=config["configurable"].get("vendor_settings"),
        )

        providers = get_chat_providers(settings, tools=tools)
        if not providers:
            raise ValueError("No LLM providers configured.")

        # Truncate history to stay within speed/context limits (last 10 messages)
        # Following ANTIGRAVITY.md production efficiency rule.
        all_messages = state["messages"]
        if len(all_messages) > 10:
            all_messages = all_messages[-10:]

        prompt = [SystemMessage(content=SYSTEM_PROMPT)] + all_messages
        
        import asyncio
        last_error = None
        for i, model in enumerate(providers):
            # Better provider identification
            p_name = "Gemini" if "Google" in str(model) else "NVIDIA/Llama"
            try:
                print(f"Attempting {p_name}...")
                # 30 second timeout for production resilience during multi-step reasoning
                response = await asyncio.wait_for(model.ainvoke(prompt), timeout=30.0)
                
                if response.tool_calls:
                    for tc in response.tool_calls:
                        print(f"AI calling tool: {tc['name']}")
                return {"messages": [response]}
            except asyncio.TimeoutError:
                print(f"{p_name} timed out.")
                last_error = ValueError(f"{p_name} timed out.")
                continue
            except Exception as e:
                print(f"{p_name} Error: {e}")
                last_error = e
                continue
        
        raise last_error or ValueError("All LLM providers failed.")

    return call_model


def should_continue(state: AgentState):
    """Conditional edge: tools or end."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# 3. Create the Graph
def create_customer_agent(
    settings: Settings,
    products_repo,
    business_info_repo,
    vendor_id: int,
    vendor_dict: dict,
    vendor_settings: dict,
    checkpointer,
):
    """
    Creates the LangGraph workflow. 
    Following ANTIGRAVITY.md, dependencies are injected via config at runtime.
    """
    # 1. Define tools (for the ToolNode)
    tools = create_agent_tools(
        products_repo=products_repo,
        business_info_repo=business_info_repo,
        vendor_id=vendor_id,
        vendor_dict=vendor_dict,
        vendor_settings=vendor_settings,
    )
    
    # 2. Setup the graph
    workflow = StateGraph(AgentState)
    call_model_node = create_nodes() # No longer takes model as argument

    workflow.add_node("agent", call_model_node)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=checkpointer)


async def run_customer_agent(
    agent,
    incoming_message: str,
    vendor_id: int,
    thread_id: str,
    products_repo,
    business_info_repo,
    vendor_dict: dict,
    vendor_settings: dict,
    settings: Settings,
    order_status: str | None = None,
    ad_context: dict | None = None,
) -> dict:
    """Run the explicit LangGraph with thread memory and injected dependencies."""
    config = {
        "configurable": {
            "thread_id": thread_id,
            "products_repo": products_repo,
            "business_info_repo": business_info_repo,
            "vendor_id": vendor_id,
            "vendor_dict": vendor_dict,
            "vendor_settings": vendor_settings,
            "settings": settings,
        }
    }
    
    inputs = {
        "messages": [HumanMessage(content=incoming_message)],
        "vendor_id": vendor_id,
        "order_status": order_status or "INQUIRY"
    }

    final_state = await agent.ainvoke(inputs, config=config)

    messages = final_state["messages"]
    ai_msg = next((m for m in reversed(messages) if m.type == "ai" and not m.tool_calls), None)
    
    customer_text = ai_msg.content if ai_msg else ""
    customer_media = None
    new_order_status = final_state.get("order_status") or "INQUIRY"
    
    # 3. Check for signals in tool outputs with STRICT GUARDRAILS
    # Following ANTIGRAVITY.md: Interface-driven and resilient logic.
    payment_keywords = ["pay", "account", "bank", "transfer", "details", "send", "give", "how to", "transfer", "checkout"]
    
    for m in reversed(final_state["messages"]):
        if m.type == "tool" and isinstance(m.content, str):
            if "CATALOGUE_MEDIA|" in m.content:
                parts = m.content.split("|")
                if len(parts) >= 3:
                    customer_media = {"kind": parts[1], "document_id": parts[2]}
            
            if "SIGNAL:CHECKOUT_REQUESTED" in m.content:
                # GUARDRAIL: Verify if the user actually asked for payment
                last_customer_msg = next((msg.content.lower() for msg in reversed(final_state["messages"]) if msg.type == "human"), "")
                has_intent = any(kw in last_customer_msg for kw in payment_keywords)
                
                if has_intent:
                    new_order_status = "WAITING_VENDOR_CHECKOUT_APPROVAL"
                else:
                    # REJECT: Reset status and add a warning for the next turn
                    # This ensures the UI doesn't show the checkout button
                    new_order_status = "INQUIRY"
                    print("Guardrail: Blocked premature checkout call.")
                break

    return {
        "response_text": customer_text,
        "customer_media": customer_media,
        "order_status": new_order_status
    }
