import asyncio
import logging
import os
import random
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.identity.aio import get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from rich.logging import RichHandler

# Configuración de logging con rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("planificador_fin_de_semana")

# Configuración del cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "azure":
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1",
        api_key=token_provider,
    )
    model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))


def obtener_clima(ciudad: str, fecha: str) -> dict:
    """Devuelve un clima simulado según la ciudad y la fecha proporcionadas."""
    logger.info(f"Obteniendo clima para {ciudad}")
    if random.random() < 0.05:
        return {
            "ciudad": ciudad,
            "fecha": fecha,
            "temperatura": 22,
            "descripcion": "Soleado",
        }
    else:
        return {
            "ciudad": ciudad,
            "fecha": fecha,
            "temperatura": 16,
            "descripcion": "Lluvioso",
        }


def obtener_actividades(ciudad: str, fecha: str) -> list:
    """Devuelve una lista simulada de actividades disponibles según la ciudad y la fecha proporcionadas."""
    logger.info(f"Obteniendo actividades para {ciudad} en {fecha}")
    return [
        {"nombre": "Senderismo", "lugar": ciudad},
        {"nombre": "Playa", "lugar": ciudad},
        {"nombre": "Museo", "lugar": ciudad},
    ]


def obtener_fecha_actual() -> str:
    logger.info("Obteniendo fecha actual")
    return datetime.now().strftime("%Y-%m-%d")


agent = Agent(
    model,
    system_prompt=(
        "Ayuda al usuario a planificar su fin de semana y a elegir las "
        "mejores actividades según el clima proporcionado. No sugieras actividades que puedan "
        "resultar desagradables con ese clima. Incluye la fecha del fin de semana en tu respuesta."
    ),
    tools=[obtener_clima, obtener_actividades, obtener_fecha_actual],
)


async def main():
    consulta = "¿Qué puedo hacer este fin de semana en Barcelona para divertirme?"
    resultado = await agent.run(consulta)
    print(resultado.output)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
