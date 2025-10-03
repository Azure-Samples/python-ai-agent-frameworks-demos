import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Annotated

from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field
from rich import print
from rich.logging import RichHandler

# Configuración de logging con rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("planificador_fin_de_semana")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    client = AzureOpenAIChatClient(
        credential=DefaultAzureCredential(),
        deployment_name=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_version=os.environ.get("AZURE_OPENAI_VERSION"),
    )
elif API_HOST == "github":
    client = OpenAIChatClient(
        base_url="https://models.github.ai/inference",
        api_key=os.environ["GITHUB_TOKEN"],
        model_id=os.getenv("GITHUB_MODEL", "openai/gpt-4o"),
    )
elif API_HOST == "ollama":
    client = OpenAIChatClient(
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
        model_id=os.environ.get("OLLAMA_MODEL", "llama3.1:latest"),
    )
else:
    client = OpenAIChatClient(
        api_key=os.environ.get("OPENAI_API_KEY"), model_id=os.environ.get("OPENAI_MODEL", "gpt-4o")
    )


def get_weather(
    city: Annotated[str, Field(description="La ciudad para obtener el clima.")],
) -> dict:
    """Devuelve datos meteorológicos para una ciudad: temperatura y descripción."""
    logger.info(f"Obteniendo el clima para {city}")
    if random.random() < 0.05:
        return {
            "temperature": 72,
            "description": "Soleado",
        }
    else:
        return {
            "temperature": 60,
            "description": "Lluvioso",
        }


def get_activities(
    city: Annotated[str, Field(description="La ciudad para obtener actividades.")],
    date: Annotated[str, Field(description="La fecha (YYYY-MM-DD) para obtener actividades.")],
) -> list[dict]:
    """Devuelve una lista de actividades para una ciudad y fecha dadas."""
    logger.info(f"Obteniendo actividades para {city} en {date}")
    return [
        {"name": "Senderismo", "location": city},
        {"name": "Playa", "location": city},
        {"name": "Museo", "location": city},
    ]


def get_current_date() -> str:
    """Obtiene la fecha actual del sistema en formato YYYY-MM-DD."""
    logger.info("Obteniendo la fecha actual")
    return datetime.now().strftime("%Y-%m-%d")


agent = client.create_agent(
    instructions=(
        "Ayudas a las personas a planear su fin de semana y elegir las mejores actividades según el clima. "
        "Si una actividad sería desagradable con el clima previsto, no la sugieras. "
        "Incluye la fecha del fin de semana en tu respuesta."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


async def main():
    response = await agent.run("Hola, ¿qué puedo hacer este fin de semana en San Francisco?")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
