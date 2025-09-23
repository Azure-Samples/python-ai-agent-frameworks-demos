import asyncio
import logging
import os
import random
from datetime import datetime

import azure.identity
import openai
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from dotenv import load_dotenv
from rich.logging import RichHandler

# Configuración de logging con rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("weekend_planner")

# Desactivamos el rastreo ya que no estamos conectados a un proveedor compatible
set_tracing_disabled(disabled=True)

# Configuramos el cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")
if API_HOST == "github":
    client = openai.AsyncOpenAI(base_url="https://models.inference.ai.azure.com", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "gpt-4o")
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = openai.AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]


@function_tool
def get_weather(city: str) -> str:
    logger.info(f"Obteniendo el clima para {city}")
    if random.random() < 0.05:
        return {
            "city": city,
            "temperature": 72,
            "description": "Soleado",
        }
    else:
        return {
            "city": city,
            "temperature": 60,
            "description": "Lluvioso",
        }


@function_tool
def get_activities(city: str, date: str) -> list:
    logger.info(f"Obteniendo actividades para {city} el {date}")
    return [
        {"name": "Senderismo", "location": city},
        {"name": "Playa", "location": city},
        {"name": "Museo", "location": city},
    ]


@function_tool
def get_current_date() -> str:
    logger.info("Obteniendo fecha actual")
    return datetime.now().strftime("%Y-%m-%d")


agent = Agent(
    name="Planificador de Finde",
    instructions="Ayudas a los usuarios a planificar sus fines de semana y elegir las mejores actividades según el clima. Si una actividad sería desagradable con el clima actual, no la sugieras. Incluye la fecha del fin de semana en tu respuesta.",
    tools=[get_weather, get_activities, get_current_date],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)


async def main():
    result = await Runner.run(agent, input="hola ¿qué puedo hacer este fin de semana en Quito?")
    print(result.final_output)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())