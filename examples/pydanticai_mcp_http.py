"""PydanticAI + MCP HTTP example.

Prerequisite:
Start the local MCP server defined in `mcp_server_basic.py` on port 8000:
    python examples/mcp_server_basic.py
"""

import asyncio
import logging
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Setup the OpenAI client to use either Azure OpenAI or GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=token_provider,
    )
    model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))

server = MCPServerStreamableHTTP(url="http://localhost:8000/mcp")

agent: Agent[None, str] = Agent(model, system_prompt="You are a travel planning agent. You can help users find hotels.", output_type=str, toolsets=[server])


async def main():
    result = await agent.run("Find me a hotel in San Francisco for 2 nights starting from 2024-01-01. I need a hotel with free WiFi and a pool.")
    print(result.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main())
