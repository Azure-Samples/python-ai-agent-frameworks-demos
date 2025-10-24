import asyncio
import logging
import os
import random
from datetime import datetime

from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI
from rich.logging import RichHandler

# Configuración de logging con rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("weekend_planner")

# Desactivamos el rastreo ya que no estamos conectados a un proveedor compatible
set_tracing_disabled(disabled=True)

# Configuramos el cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
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


@function_tool
def get_weather(city: str) -> str:
    logger.info(f"Obteniendo el clima para {city}")
    if random.random() < 0.05:
        weather = f"El clima en {city}: 72°F, Soleado"
    else:
        weather = f"El clima en {city}: 60°F, Lluvioso"
    return weather


@function_tool
def get_activities(city: str, date: str) -> str:
    logger.info(f"Obteniendo actividades para {city} el {date}")
    activities_text = f"Actividades disponibles en {city} para {date}: Senderismo, Playa, Museo"
    return activities_text


@function_tool
def get_current_date() -> str:
    """Obtiene la fecha actual y la devuelve como string en formato YYYY-MM-DD."""
    logger.info("Obteniendo fecha actual")
    return datetime.now().strftime("%Y-%m-%d")


agent = Agent(
    name="Planificador de Finde",
    instructions=(
        "Ayudas a planificar sus fines de semana y elegir las mejores actividades según el clima."
        "Si una actividad sería desagradable con el clima actual, no la sugieras."
    ),
    tools=[get_weather, get_activities, get_current_date],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)


async def main():
    result = await Runner.run(agent, input="hola ¿qué puedo hacer este fin de semana en Quito?")
    print(result.final_output)

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
