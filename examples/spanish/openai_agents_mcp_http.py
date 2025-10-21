"""Ejemplo de framework OpenAI Agents + MCP HTTP.

Prerrequisito:
Inicia el servidor MCP local definido en `mcp_server_basic.py` en el puerto 8000:
    python examples/mcp_server_basic.py
"""

import asyncio
import logging
import os

import azure.identity
import openai
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp.server import MCPServerStreamableHttp
from agents.model_settings import ModelSettings
from dotenv import load_dotenv

logging.basicConfig(level=logging.WARNING)
# Desactivar tracing ya que no estamos conectados a un proveedor de tracing soportado
set_tracing_disabled(disabled=True)

# Configuración del cliente OpenAI para usar Azure OpenAI o GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")
if API_HOST == "github":
    client = openai.AsyncOpenAI(base_url="https://models.inference.ai.azure.com", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "gpt-4o")
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = openai.AsyncAzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
elif API_HOST == "ollama":
    client = openai.AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="none")
    MODEL_NAME = "llama3.1:latest"


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
    message = "Encuéntrame un hotel en San Francisco para 2 noches comenzando el 2024-01-01. Necesito un hotel con WiFi gratis y piscina."
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)
    await mcp_server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
