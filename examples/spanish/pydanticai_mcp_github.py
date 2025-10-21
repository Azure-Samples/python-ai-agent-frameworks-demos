"""Ejemplo de PydanticAI + MCP de GitHub.

Este ejemplo crea un adaptador de servidor MCP que apunta al endpoint MCP de GitHub,
lista las herramientas disponibles, las filtra a un conjunto pequeño útil para
triar issues, y luego envía esas herramientas a un Agente PydanticAI que
produce un IssueProposal estructurado.

Prerrequisitos:
- Establece GITHUB_TOKEN en tu entorno o en un archivo .env.
- El endpoint MCP de GitHub debe ser accesible desde tu entorno.

Uso:
    python examples/pydanticai_mcp_github.py
"""

import asyncio
import json
import logging
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI
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
    client = AsyncAzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
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
    """Propuesta estructurada para cerrar un issue."""

    url: str = Field(description="URL del issue")
    title: str = Field(description="Título del issue")
    summary: str = Field(description="Resumen breve del issue y señales para cerrarlo")
    should_close: bool = Field(description="Si el issue debe cerrarse o no")
    reply_message: str = Field(description="Mensaje para publicar al cerrar el issue, si aplica")


async def main():
    server = MCPServerStreamableHTTP(
        url="https://api.githubcopilot.com/mcp/", headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN', '')}"}
    )
    desired_tool_names = ("list_issues", "search_code", "search_issues", "search_pull_requests")
    filtered_tools = server.filtered(lambda ctx, tool_def: tool_def.name in desired_tool_names)

    agent: Agent[None, IssueProposal] = Agent(
        model,
        system_prompt=(
            "Eres un asistente de triaje de issues. Usa las herramientas proporcionadas para encontrar un issue que pueda cerrarse "
            "y produce un IssueProposal."
        ),
        output_type=IssueProposal,
        toolsets=[filtered_tools],
    )

    user_content = "Encuentra un issue de Azure-samples azure-search-openai-demo que pueda cerrarse."
    async with agent.iter(user_content) as agent_run:
        async for node in agent_run:
            if isinstance(node, CallToolsNode):
                tool_call = node.model_response.parts[0]
                logger.info(f"Llamando herramienta '{tool_call.tool_name}' con args:\n{tool_call.args}")
            elif isinstance(node, ModelRequestNode) and isinstance(node.request.parts[0], ToolReturnPart):
                tool_return_value = json.dumps(node.request.parts[0].content)
                logger.info(f"Resultado de la herramienta:\n{tool_return_value[0:200]}...")

    print(agent_run.result.output)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
