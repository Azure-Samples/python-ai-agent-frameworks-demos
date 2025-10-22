import logging
import os
import random

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
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
    model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
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
def get_weather(city: str) -> dict:
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


agent = create_agent(
    model=model,
    prompt="Eres un agente informativo. Responde a las preguntas con alegría.",
    tools=[get_weather],
)


def main():
    response = agent.invoke({"messages": [{"role": "user", "content": "¿Cómo está el clima hoy en San Francisco?"}]})
    latest_message = response["messages"][-1]
    print(latest_message.content)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
