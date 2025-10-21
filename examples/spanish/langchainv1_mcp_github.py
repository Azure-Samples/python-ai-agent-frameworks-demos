"""Ejemplo de LangChain v1 con herramientas MCP (adaptado de la versión LangGraph).

Este script demuestra cómo usar la sintaxis de agentes de LangChain v1 con herramientas MCP
expuestas por el endpoint MCP de GitHub. Preserva la lógica de selección de modelo
Azure OpenAI vs GitHub del ejemplo original basado en LangGraph.
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
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import BaseModel, Field
from rich import print
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("triaje_lang")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    base_model = AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        openai_api_version=os.environ["AZURE_OPENAI_VERSION"],
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


class IssueProposal(BaseModel):
    """Información de contacto de una persona."""

    url: str = Field(description="URL del issue")
    title: str = Field(description="Título del issue")
    summary: str = Field(description="Resumen breve del issue y señales para cerrarlo")
    should_close: bool = Field(description="Si el issue debe cerrarse o no")
    reply_message: str = Field(description="Mensaje para publicar al cerrar el issue, si aplica")


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

    prompt_path = Path(__file__).parent.parent / "triager.prompt.md"
    with prompt_path.open("r", encoding="utf-8") as f:
        prompt = f.read()
    agent = create_agent(base_model, prompt=prompt, tools=filtered_tools, response_format=IssueProposal)

    user_content = "Encuentra un issue abierto de Azure-samples azure-search-openai-demo que pueda cerrarse."
    async for step in agent.astream(
        {"messages": [HumanMessage(content=user_content)]}, stream_mode="updates", config={"recursion_limit": 100}
    ):
        for step_name, step_data in step.items():
            last_message = step_data["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                tool_name = last_message.tool_calls[0]["name"]
                tool_args = last_message.tool_calls[0]["args"]
                logger.info(f"Llamando herramienta '{tool_name}' con args:\n{tool_args}")
            elif isinstance(last_message, ToolMessage):
                logger.info(f"Resultado de la herramienta:\n{last_message.content[0:200]}...")
            if step_data.get("structured_response"):
                print(step_data["structured_response"])


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
