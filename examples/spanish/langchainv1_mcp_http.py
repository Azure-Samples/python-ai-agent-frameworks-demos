"""Ejemplo de agente LangChain v1 + servidor MCP HTTP de itinerarios.

Prerrequisito:
  Inicia el servidor MCP local definido en `mcp_server_basic.py` en el puerto 8000:
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
from langchain_openai import ChatOpenAI
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("itinerario_lang")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    base_model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
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
                # Asegúrate de iniciar tu servidor de itinerarios en el puerto 8000
                "url": "http://localhost:8000/mcp/",
                "transport": "streamable_http",
            }
        }
    )

    tools = await client.get_tools()
    agent = create_agent(base_model, tools)

    user_query = "Encuéntrame un hotel en San Francisco para 2 noches comenzando el 2026-01-01. " "Necesito un hotel con WiFi gratis y piscina."

    response = await agent.ainvoke({"messages": [HumanMessage(content=user_query)]})
    final = response["messages"][-1].content
    print(final)


def main():
    asyncio.run(run_agent())


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
