import logging
import os
import random
from datetime import datetime

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI, ChatOpenAI
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
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version=os.environ.get("AZURE_OPENAI_VERSION"),
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


# ----------------------------------------------------------------------------------
# SUBAGENTE 1: Agente de planificación de actividades
# ----------------------------------------------------------------------------------
@tool
def get_weather(city: str, date: str) -> dict:
    """Devuelve datos meteorológicos para una ciudad y fecha dadas."""
    logger.info(f"Obteniendo el clima para {city} en {date}")
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


@tool
def get_activities(city: str, date: str) -> list:
    """Devuelve una lista de actividades para una ciudad y fecha dadas."""
    logger.info(f"Obteniendo actividades para {city} en {date}")
    return [
        {"name": "Senderismo", "location": city},
        {"name": "Playa", "location": city},
        {"name": "Museo", "location": city},
    ]


@tool
def get_current_date() -> str:
    """Obtiene la fecha actual del sistema en formato YYYY-MM-DD."""
    logger.info("Obteniendo la fecha actual")
    return datetime.now().strftime("%Y-%m-%d")


weekend_agent = create_agent(
    model=base_model,
    prompt=(
        "Ayudas a las personas a planear su fin de semana y elegir las mejores actividades según el clima."
        "Si una actividad sería desagradable con el clima previsto, no la sugieras."
        "Incluye la fecha del fin de semana en tu respuesta."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


@tool
def plan_weekend(query: str) -> str:
    """Planifica un fin de semana según la consulta del usuario y devuelve la respuesta final."""
    logger.info("Herramienta: plan_weekend invocada")
    response = weekend_agent.invoke({"messages": [HumanMessage(content=query)]})
    final = response["messages"][-1].content
    return final


# ----------------------------------------------------------------------------------
# SUBAGENTE 2: Agente de planificación de recetas
# ----------------------------------------------------------------------------------


@tool
def find_recipes(query: str) -> list[dict]:
    """Devuelve recetas basadas en una consulta."""
    logger.info(f"Buscando recetas para '{query}'")
    if "pasta" in query.lower():
        return [
            {
                "title": "Pasta Primavera",
                "ingredients": ["pasta", "verduras", "aceite de oliva"],
                "steps": ["Cocinar la pasta.", "Saltear las verduras."],
            }
        ]
    elif "tofu" in query.lower():
        return [
            {
                "title": "Salteado de Tofu",
                "ingredients": ["tofu", "salsa de soja", "verduras"],
                "steps": ["Cortar el tofu en cubos.", "Saltear las verduras y el tofu."],
            }
        ]
    else:
        return [
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


@tool
def check_fridge() -> list[str]:
    """Devuelve una lista de ingredientes actualmente en el refrigerador."""
    logger.info("Revisando los ingredientes del refrigerador")
    if random.random() < 0.5:
        return ["pasta", "salsa de tomate", "pimientos", "aceite de oliva"]
    else:
        return ["tofu", "salsa de soja", "brócoli", "zanahorias"]


meal_agent = create_agent(
    model=base_model,
    prompt=(
        "Ayudas a las personas a planear comidas y elegir las mejores recetas."
        "Incluye los ingredientes e instrucciones de cocina en tu respuesta."
        "Indica lo que la persona necesita comprar cuando falten ingredientes en su refrigerador."
    ),
    tools=[find_recipes, check_fridge],
)


@tool
def plan_meal(query: str) -> str:
    """Planifica una comida según la consulta del usuario y devuelve la respuesta final."""
    logger.info("Herramienta: plan_meal invocada")
    response = meal_agent.invoke({"messages": [HumanMessage(content=query)]})
    final = response["messages"][-1].content
    return final


# ----------------------------------------------------------------------------------
# AGENTE SUPERVISOR: Gestiona los subagentes
# ----------------------------------------------------------------------------------
supervisor_agent = create_agent(
    model=base_model,
    prompt=(
        "Eres un supervisor que gestiona un agente de planificación de actividades y un agente de planificación de recetas."
        "Asígnales trabajo según sea necesario para responder la pregunta del usuario."
    ),
    tools=[plan_weekend, plan_meal],
)


def main():
    response = supervisor_agent.invoke({"messages": [{"role": "user", "content": "mis hijos quieren pasta para la cena"}]})
    latest_message = response["messages"][-1]
    print(latest_message.content)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
