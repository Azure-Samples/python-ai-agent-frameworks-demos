"""Semantic Kernel + MCP HTTP example.

Prerequisite:
Start the local MCP server defined in `mcp_server_basic.py` on port 8000:
    python examples/mcp_server_basic.py
"""

import asyncio
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")
if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    chat_client = AsyncAzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )
    chat_completion_service = OpenAIChatCompletion(
        ai_model_id=os.environ["AZURE_OPENAI_CHAT_MODEL"], async_client=chat_client
    )
else:
    chat_client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    chat_completion_service = OpenAIChatCompletion(
        ai_model_id=os.getenv("GITHUB_MODEL", "gpt-4o"), async_client=chat_client
    )


async def main():
    async with MCPStreamableHttpPlugin(
        name="TravelServer",
        description="Search hotels and flights",
        url="http://localhost:8000/mcp",
    ) as mcp_http_plugin:
        agent = ChatCompletionAgent(
            name="travel_agent",
            instructions="You are a travel planning agent. You can help users find hotels.",
            service=chat_completion_service,
            plugins=[mcp_http_plugin],
        )
        response = await agent.get_response(
            messages="Find me a hotel in San Francisco for 2 nights starting from 2024-01-01. I need a hotel with free WiFi and a pool."
        )
        print(response.content)


if __name__ == "__main__":
    asyncio.run(main())
