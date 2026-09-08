import logging
import operator
import re
from typing import Annotated, Sequence, TypedDict

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END, add_messages
from langgraph.prebuilt import ToolNode

from app.config import Settings
from app.agent.tools import create_agent_tools

logger = logging.getLogger(__name__)


# 1. Define the Graph State
class AgentState(TypedDict):
    # Use add_messages reducer for idiomatic LangGraph message handling
    messages: Annotated[list[BaseMessage], add_messages]
    vendor_id: int
    order_status: str


SYSTEM_PROMPT_BASE = (
    "You are a helpful Sales Assistant, a production-grade autonomous agent for an online store. "
    "Your goal is to be helpful, professional, and efficient. Write plain text (no markdown).\n\n"
    "Core Principles:\n"
    "- Ensure end-to-end usable and coherent interactions.\n"
    "- Handle edge cases and invalid queries gracefully.\n"
    "- Prioritize clarity and correctness over cleverness.\n\n"
    "- Be nice to customers-\n\n"
    "Operational Rules:\n"
    "- If a product is missing, say its not available.\n"
)

SYSTEM_PROMPT_CHECKOUT_RULES = (
    "- CRITICAL FORBIDDEN ACTION: Never call the request_bank_details_and_vendor_approval tool just because a customer says they 'want' to buy, are 'interested', or 'will take' a product. These are still inquiries.\n"
    "- ONLY CALL request_bank_details_and_vendor_approval when the customer explicitly asks 'How do I pay?', 'What is your account number?', or says 'I am ready to transfer the money now'.\n"
    "- If they just say they want to buy, provide product info and ask: 'Do you want to pay so I can send the details?'\n"
    "- Once you call request_bank_details_and_vendor_approval, tell the customer that the store is being notified to approve the order."
)


def build_system_prompt(vendor_settings: dict | None) -> str:
    enable_kb = (vendor_settings or {}).get("enable_knowledge_base_answers", True)
    if enable_kb:
        tools_line = (
            "- Use search_products to search for items and search_business_info for store policies, "
            "delivery info, location, and other business details.\n"
        )
    else:
        tools_line = (
            "- Use search_products to search for items. "
            "You do not have access to any business-info, policy, delivery, or store-hours data — "
            "if a customer asks about those topics, tell them the store hasn't published that info "
            "and offer to share what you do know about products.\n"
        )
    return SYSTEM_PROMPT_BASE + tools_line + SYSTEM_PROMPT_CHECKOUT_RULES


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
def create_nodes(tools: list):
    async def call_model(state: AgentState, config: RunnableConfig):
        """The AI reasoning node. Manual failover for production-grade resilience."""
        settings = config["configurable"].get("settings")
        if not settings:
            from app.config import get_settings
            settings = get_settings()

        providers = get_chat_providers(settings, tools=tools)
        if not providers:
            raise ValueError("No LLM providers configured.")

        # Truncate history to stay within speed/context limits (last 10 messages)
        # Following ANTIGRAVITY.md production efficiency rule.
        all_messages = state["messages"]
        if len(all_messages) > 10:
            slice_start = len(all_messages) - 10
            for idx in range(slice_start, len(all_messages)):
                if isinstance(all_messages[idx], HumanMessage):
                    slice_start = idx
                    break
            all_messages = all_messages[slice_start:]

        prompt = [SystemMessage(content=build_system_prompt(config["configurable"].get("vendor_settings")))] + all_messages
        
        import asyncio
        last_error = None
        for i, model in enumerate(providers):
            # Better provider identification
            p_name = "Gemini" if "Google" in str(model) else "NVIDIA/Llama"
            try:
                logger.info("Attempting LLM provider: %s", p_name)
                # 30 second timeout for production resilience during multi-step reasoning
                response = await asyncio.wait_for(model.ainvoke(prompt), timeout=30.0)

                if response.tool_calls:
                    for tc in response.tool_calls:
                        logger.info("Agent calling tool: %s", tc['name'])
                return {"messages": [response]}
            except asyncio.TimeoutError:
                logger.warning("LLM provider %s timed out.", p_name)
                last_error = ValueError(f"{p_name} timed out.")
                continue
            except Exception as e:
                logger.warning("LLM provider %s failed: %s", p_name, e)
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
    call_model_node = create_nodes(tools)

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
        },
        "recursion_limit": 12,
    }

    inputs = {
        "messages": [HumanMessage(content=incoming_message)],
        "vendor_id": vendor_id,
        "order_status": order_status or "INQUIRY"
    }

    final_state = await agent.ainvoke(inputs, config=config)

    messages = final_state["messages"]
    ai_msg = next((m for m in reversed(messages) if m.type == "ai" and not m.tool_calls), None)

    customer_text = _strip_markdown(ai_msg.content if ai_msg else "")
    if not customer_text.strip():
        customer_text = "I'm here — could you tell me a bit more about what you're looking for?"

    new_order_status = final_state.get("order_status") or order_status or "INQUIRY"
    checkout_requested = False
    order_details = None

    # Inspect ONLY the messages generated in the current turn (from the latest HumanMessage onwards)
    latest_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            latest_human_idx = i
            break

    current_turn_messages = messages[latest_human_idx:] if latest_human_idx != -1 else messages

    for m in reversed(current_turn_messages):
        if m.type == "tool" and isinstance(m.content, str):
            if "SIGNAL:CHECKOUT_REQUESTED" in m.content:
                new_order_status = "WAITING_VENDOR_CHECKOUT_APPROVAL"
                checkout_requested = True
                order_details = _extract_order_details(m.content) or incoming_message.strip()
                break

    return {
        "response_text": customer_text,
        "order_status": new_order_status,
        "checkout_requested": checkout_requested,
        "order_details": order_details if checkout_requested else None,
    }


def _extract_order_details(tool_content: str) -> str | None:
    """Pull the ORDER:{...} segment the checkout tool echoes back, if present."""
    for part in tool_content.split("|"):
        if part.startswith("ORDER:"):
            return part[len("ORDER:"):].strip() or None
    return None


_MD_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_BOLD_UNDERSCORE = re.compile(r"__(.+?)__", re.DOTALL)
_MD_ITALIC_STAR = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?!\w)")
_MD_ITALIC_UNDERSCORE = re.compile(r"(?<![_\w])_([^_\n]+?)_(?!\w)")
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_MD_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s+", re.MULTILINE)
_MD_INLINE_CODE = re.compile(r"`([^`\n]+)`")


def _strip_markdown(text: str) -> str:
    """Best-effort removal of markdown so WhatsApp/Instagram don't render literal asterisks."""
    if not text:
        return text
    text = _MD_BOLD.sub(r"\1", text)
    text = _MD_BOLD_UNDERSCORE.sub(r"\1", text)
    text = _MD_ITALIC_STAR.sub(r"\1", text)
    text = _MD_ITALIC_UNDERSCORE.sub(r"\1", text)
    text = _MD_INLINE_CODE.sub(r"\1", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_BLOCKQUOTE.sub("", text)
    return text
