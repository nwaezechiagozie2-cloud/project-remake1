import asyncio
from app.config import get_settings
from app.agent.agent import create_customer_agent, run_customer_agent
from app.agent.tools import create_agent_tools
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def test():
    settings = get_settings()
    products_repo = None # We'll see if it fails
    
    async with AsyncSqliteSaver.from_conn_string(":memory:") as saver:
        agent = create_customer_agent(
            settings=settings,
            products_repo=None,
            knowledge_repo=None,
            vendor_id=1,
            vendor_dict={},
            vendor_settings={},
            checkpointer=saver
        )
        
        print("Running agent...")
        result = await run_customer_agent(
            agent=agent,
            incoming_message="Hi, I want to buy the bag.",
            vendor_id=1,
            thread_id="test_thread",
            order_status="INQUIRY"
        )
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test())
