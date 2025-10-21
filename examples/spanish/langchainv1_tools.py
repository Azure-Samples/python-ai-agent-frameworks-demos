import logging
import os
import random
from datetime import datetime

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from rich import print
from rich.logging import RichHandler

# Configuración de logging con rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("planificador_fin_de_semana")

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


agent = create_agent(
    model=model,
    prompt="Ayudas a las personas a planear su fin de semana y elegir las mejores actividades según el clima. Si una actividad sería desagradable con el clima previsto, no la sugieras. Incluye la fecha del fin de semana en tu respuesta.",
    tools=[get_weather, get_activities, get_current_date],
)


def main():
    response = agent.invoke({"messages": [{"role": "user", "content": "Hola, ¿qué puedo hacer este fin de semana en San Francisco?"}]})
    latest_message = response["messages"][-1]
    print(latest_message.content)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
