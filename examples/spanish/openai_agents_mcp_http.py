"""Ejemplo de framework OpenAI Agents + MCP HTTP.

Prerrequisito:
Inicia el servidor MCP local definido en `mcp_server_basic.py` en el puerto 8000:
    python examples/mcp_server_basic.py
"""

import asyncio
import logging
import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp.server import MCPServerStreamableHttp
from agents.model_settings import ModelSettings
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI

logging.basicConfig(level=logging.WARNING)
# Desactivar tracing ya que no estamos conectados a un proveedor de tracing soportado
set_tracing_disabled(disabled=True)

# Configuración del cliente OpenAI para usar Azure OpenAI o GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

async_credential = None
if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default")
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1",
        api_key=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
elif API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    MODEL_NAME = os.getenv("GITHUB_MODEL", "gpt-4o")
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    MODEL_NAME = os.environ["OLLAMA_MODEL"]
else:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4o")


mcp_server = MCPServerStreamableHttp(name="weather", params={"url": "http://localhost:8000/mcp/"})

agent = Agent(
    name="Asistente",
    instructions="Usa las herramientas para lograr la tarea",
    mcp_servers=[mcp_server],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    model_settings=ModelSettings(tool_choice="required"),
)


async def main():
    await mcp_server.connect()
    message = "Encuéntrame un hotel en SF para 2 noches comenzando el 2024-01-01. Necesito WiFi gratis y piscina."
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    await mcp_server.cleanup()

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
