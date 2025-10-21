"""Ejemplo de agente del clima estilo LangChain v1.
https://docs.langchain.com/oss/python/langchain-quickstart

Este ejemplo replica el patrón de los documentos de Inicio Rápido de LangChain v1,
adaptado a la configuración de modelo de múltiples proveedores de este repositorio.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import get_runtime
from rich import print

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    model = AzureChatOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version=os.environ.get("AZURE_OPENAI_VERSION"),
        azure_ad_token_provider=token_provider,
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


system_prompt = """Eres un experto meteorólogo que habla con juegos de palabras.

Tienes acceso a dos herramientas:

- get_weather_for_location: usa esto para obtener el clima de una ubicación específica
- get_user_location: usa esto para obtener la ubicación del usuario

Si un usuario te pregunta por el clima, asegúrate de saber la ubicación.
Si puedes inferir de la pregunta que se refiere a donde están,
usa la herramienta get_user_location para encontrar su ubicación."""

# Ubicaciones de usuarios simuladas indexadas por ID de usuario (string)
USER_LOCATION = {
    "1": "Florida",
    "2": "SF",
}


@dataclass
class UserContext:
    user_id: str


@tool
def get_weather(city: str) -> str:
    """Obtiene el clima para una ciudad dada."""
    return f"¡Siempre hace sol en {city}!"


@tool
def get_user_info(config: RunnableConfig) -> str:
    """Recupera información del usuario según el ID de usuario."""
    runtime = get_runtime(UserContext)
    user_id = runtime.context.user_id
    return USER_LOCATION[user_id]


@dataclass
class WeatherResponse:
    conditions: str
    punny_response: str


checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    prompt=system_prompt,
    tools=[get_user_info, get_weather],
    response_format=WeatherResponse,
    checkpointer=checkpointer,
)


def main():
    config = {"configurable": {"thread_id": "1"}}
    context = UserContext(user_id="1")

    r1 = agent.invoke(
        {"messages": [{"role": "user", "content": "¿Qué clima hace afuera?"}]}, config=config, context=context
    )
    print(r1.get("structured_response"))

    r2 = agent.invoke(
        {"messages": [{"role": "user", "content": "Gracias"}]},
        config=config,
        context=context,
    )
    print(r2.get("structured_response"))


if __name__ == "__main__":
    main()
