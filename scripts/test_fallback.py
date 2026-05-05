import asyncio
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

@tool
def my_tool(query: str):
    """A tool."""
    return f"Result for {query}"

async def test():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    nvidia_key = os.environ.get("NVIDIA_API_KEY")
    
    gemini = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key).bind_tools([my_tool])
    nvidia = ChatOpenAI(model="openai/gpt-oss-20b", api_key=nvidia_key, base_url="https://integrate.api.nvidia.com/v1").bind_tools([my_tool])
    
    chain = gemini.with_fallbacks([nvidia])
    
    print("Invoking chain...")
    try:
        response = await chain.ainvoke([HumanMessage(content="Use the tool for 'hello'")])
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
