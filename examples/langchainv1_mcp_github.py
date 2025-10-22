"""LangChain v1 MCP tools example (ported from LangGraph version).

This script demonstrates how to use LangChain v1 agent syntax with MCP tools
exposed by the GitHub MCP endpoint. It preserves the Azure OpenAI vs GitHub
model selection logic from the original LangGraph based example.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from rich import print
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("lang_triage")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
    )
elif API_HOST == "github":
    model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ.get("GITHUB_TOKEN"),
    )
elif API_HOST == "ollama":
    model = ChatOpenAI(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
    )
else:
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


class IssueProposal(BaseModel):
    """Contact information for a person."""

    url: str = Field(description="URL of the issue")
    title: str = Field(description="Title of the issue")
    summary: str = Field(description="Brief summary of the issue and signals for closing")
    should_close: bool = Field(description="Whether the issue should be closed or not")
    reply_message: str = Field(description="Message to post when closing the issue, if applicable")


async def main():
    mcp_client = MultiServerMCPClient(
        {
            "github": {
                "url": "https://api.githubcopilot.com/mcp/",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
            }
        }
    )

    tools = await mcp_client.get_tools()
    desired_tool_names = ("list_issues", "search_code", "search_issues", "search_pull_requests")
    filtered_tools = [t for t in tools if t.name in desired_tool_names]

    prompt_path = Path(__file__).parent / "triager.prompt.md"
    with prompt_path.open("r", encoding="utf-8") as f:
        prompt = f.read()
    agent = create_agent(model, system_prompt=prompt, tools=filtered_tools, response_format=IssueProposal)

    user_content = "Find an open issue from Azure-samples azure-search-openai-demo that can be closed."
    async for step in agent.astream({"messages": [HumanMessage(content=user_content)]}, stream_mode="updates", config={"recursion_limit": 100}):
        for step_name, step_data in step.items():
            last_message = step_data["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                tool_name = last_message.tool_calls[0]["name"]
                tool_args = last_message.tool_calls[0]["args"]
                logger.info(f"Calling tool '{tool_name}' with args:\n{tool_args}")
            elif isinstance(last_message, ToolMessage):
                logger.info(f"Got tool result:\n{last_message.content[0:200]}...")
            if step_data.get("structured_response"):
                print(step_data["structured_response"])


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
