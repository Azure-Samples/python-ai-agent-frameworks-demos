"""PydanticAI + GitHub MCP example.

This example creates an MCP server adapter that points at the GitHub MCP
endpoint, lists available tools, filters them to a small set useful for
triaging issues, and then sends those tools to a PydanticAI Agent which
produces a structured IssueProposal.

Prerequisites:
- Set GITHUB_TOKEN in your environment or in a .env file.
- The GitHub MCP endpoint must be reachable from your environment.

Usage:
    python examples/pydanticai_mcp_github.py
"""

import asyncio
import json
import logging
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent, CallToolsNode, ModelRequestNode
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import (
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from rich import print
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("pydanticai_mcp_github")


load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")


if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=token_provider,
    )
    model = OpenAIChatModel(
        os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        provider=OpenAIProvider(openai_client=client),
    )
elif API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(
        os.environ.get("GITHUB_MODEL", "gpt-4o-mini"), provider=OpenAIProvider(openai_client=client)
    )
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ["OLLAMA_ENDPOINT"], api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))
else:
    client = AsyncOpenAI()
    model = OpenAIChatModel(
        os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), provider=OpenAIProvider(openai_client=client)
    )


class IssueProposal(BaseModel):
    """Structured proposal for closing an issue."""

    url: str = Field(description="URL of the issue")
    title: str = Field(description="Title of the issue")
    summary: str = Field(description="Brief summary of the issue and signals for closing")
    should_close: bool = Field(description="Whether the issue should be closed or not")
    reply_message: str = Field(description="Message to post when closing the issue, if applicable")


async def main():
    server = MCPServerStreamableHTTP(
        url="https://api.githubcopilot.com/mcp/", headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN', '')}"}
    )
    desired_tool_names = ("list_issues", "search_code", "search_issues", "search_pull_requests")
    filtered_tools = server.filtered(lambda ctx, tool_def: tool_def.name in desired_tool_names)

    agent: Agent[None, IssueProposal] = Agent(
        model,
        system_prompt=(
            "You are an issue triage assistant. Use the provided tools to find an issue that can be closed "
            "and produce an IssueProposal."
        ),
        output_type=IssueProposal,
        toolsets=[filtered_tools],
    )

    user_content = "Find an issue from Azure-samples azure-search-openai-demo that can be closed."
    async with agent.iter(user_content) as agent_run:
        async for node in agent_run:
            if isinstance(node, CallToolsNode):
                tool_call = node.model_response.parts[0]
                logger.info(f"Calling tool '{tool_call.tool_name}' with args:\n{tool_call.args}")
            elif isinstance(node, ModelRequestNode) and isinstance(node.request.parts[0], ToolReturnPart):
                tool_return_value = json.dumps(node.request.parts[0].content)
                logger.info(f"Got tool result:\n{tool_return_value[0:200]}...")

    print(agent_run.result.output)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
