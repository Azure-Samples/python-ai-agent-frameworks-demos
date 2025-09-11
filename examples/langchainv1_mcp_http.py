"""LangChain v1 agent + MCP HTTP itinerary server example.

Prerequisite:
  Start the local MCP server defined in `mcp_server_basic.py` on port 8000:
      python examples/mcp_server_basic.py
"""
import asyncio
import logging
import os

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("lang_itinerary")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    base_model = AzureChatOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version=os.environ.get("AZURE_OPENAI_VERSION"),
        azure_ad_token_provider=token_provider,
    )
elif API_HOST == "github":
    base_model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ.get("GITHUB_TOKEN"),
    )
elif API_HOST == "ollama":
    base_model = ChatOpenAI(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
    )
else:
    base_model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


async def run_agent():
    client = MultiServerMCPClient(
        {
            "itinerary": {
                # Make sure you start your itinerary server on port 8000
                "url": "http://localhost:8000/mcp/",
                "transport": "streamable_http",
            }
        }
    )

    tools = await client.get_tools()
    agent = create_agent(base_model, tools)

    user_query = (
        "Find me a hotel in San Francisco for 2 nights starting from 2026-01-01. "
        "I need a hotel with free WiFi and a pool."
    )

    response = await agent.ainvoke({"messages": [HumanMessage(content=user_query)]})
    final = response["messages"][-1].content
    print(final)


def main():
    asyncio.run(run_agent())


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
