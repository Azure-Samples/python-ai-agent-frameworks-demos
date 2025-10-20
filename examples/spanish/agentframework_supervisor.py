import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field
from rich import print
from rich.logging import RichHandler

# Configuración de logging
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("demo_supervisor")

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

# ----------------------------------------------------------------------------------
# Subagente 1 herramientas: planificación del fin de semana
# ----------------------------------------------------------------------------------


def get_weather(
    city: Annotated[str, Field(description="Ciudad para obtener el clima.")],
    date: Annotated[str, Field(description="Fecha (YYYY-MM-DD) para la que se quiere el clima.")],
) -> dict:
    """Devuelve datos meteorológicos para una ciudad y fecha dadas."""
    logger.info(f"Obteniendo el clima para {city} en {date}")
    if random.random() < 0.05:
        return {"temperature": 72, "description": "Soleado"}
    else:
        return {"temperature": 60, "description": "Lluvioso"}


def get_activities(
    city: Annotated[str, Field(description="Ciudad para obtener actividades.")],
    date: Annotated[str, Field(description="Fecha (YYYY-MM-DD) para obtener actividades.")],
) -> list[dict]:
    """Devuelve una lista de actividades para la ciudad y la fecha indicadas."""
    logger.info(f"Obteniendo actividades para {city} en {date}")
    return [
        {"name": "Senderismo", "location": city},
        {"name": "Playa", "location": city},
        {"name": "Museo", "location": city},
    ]


def get_current_date() -> str:
    """Obtiene la fecha actual del sistema (YYYY-MM-DD)."""
    logger.info("Obteniendo la fecha actual")
    return datetime.now().strftime("%Y-%m-%d")


weekend_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "Ayudas a las personas a planear su fin de semana y elegir las mejores actividades según el clima. "
        "Si una actividad sería desagradable con el clima previsto, no la sugieras. "
        "Incluye la fecha del fin de semana en tu respuesta."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


async def plan_weekend(query: str) -> str:
    """Planifica un fin de semana según la consulta del usuario y devuelve la respuesta final."""
    logger.info("Herramienta: plan_weekend invocada")
    response = await weekend_agent.run(query)
    return response.text


# ----------------------------------------------------------------------------------
# Subagente 2 herramientas: planificación de comidas
# ----------------------------------------------------------------------------------


def find_recipes(
    query: Annotated[str, Field(description="Consulta del usuario o comida/ingrediente deseado")],
) -> list[dict]:
    """Devuelve recetas (JSON) basadas en una consulta."""
    logger.info(f"Buscando recetas para '{query}'")
    if "pasta" in query.lower():
        recipes = [
            {
                "title": "Pasta Primavera",
                "ingredients": ["pasta", "verduras", "aceite de oliva"],
                "steps": ["Cocinar la pasta.", "Saltear las verduras."],
            }
        ]
    elif "tofu" in query.lower():
        recipes = [
            {
                "title": "Salteado de Tofu",
                "ingredients": ["tofu", "salsa de soja", "verduras"],
                "steps": ["Cortar el tofu en cubos.", "Saltear las verduras y el tofu."],
            }
        ]
    else:
        recipes = [
            {
                "title": "Sándwich de Queso a la Plancha",
                "ingredients": ["pan", "queso", "mantequilla"],
                "steps": [
                    "Untar mantequilla en el pan.",
                    "Colocar el queso entre las rebanadas.",
                    "Cocinar hasta que esté dorado.",
                ],
            }
        ]
    return recipes


def check_fridge() -> list[str]:
    """Devuelve una lista JSON de ingredientes actualmente en el refrigerador."""
    logger.info("Revisando los ingredientes del refrigerador")
    if random.random() < 0.5:
        items = ["pasta", "salsa de tomate", "pimientos", "aceite de oliva"]
    else:
        items = ["tofu", "salsa de soja", "brócoli", "zanahorias"]
    return items


meal_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "Ayudas a las personas a planear comidas y elegir las mejores recetas. "
        "Incluye los ingredientes e instrucciones de cocina en tu respuesta. "
        "Indica lo que la persona necesita comprar cuando falten ingredientes en su refrigerador."
    ),
    tools=[find_recipes, check_fridge],
)


async def plan_meal(query: str) -> str:
    """Planifica una comida según la consulta del usuario y devuelve la respuesta final."""
    logger.info("Herramienta: plan_meal invocada")
    response = await meal_agent.run(query)
    return response.text


# ----------------------------------------------------------------------------------
# Agente supervisor orquestando subagentes
# ----------------------------------------------------------------------------------

supervisor_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "Eres un supervisor que gestiona dos agentes especialistas: uno de "
        "planificación de fin de semana y otro de planificación de comidas. "
        "Divide la solicitud de la persona, decide qué especialista (o ambos) "
        "invocar mediante las herramientas disponibles, y sintetiza una "
        "respuesta final útil. Al invocar una herramienta, proporciona "
        "consultas claras y concisas."
    ),
    tools=[plan_weekend, plan_meal],
)


async def main():
    user_query = "mis hijos quieren pasta para la cena"
    response = await supervisor_agent.run(user_query)
    print(response.text)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
