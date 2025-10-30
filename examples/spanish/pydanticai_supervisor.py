import asyncio
import os
import random
from typing import Literal

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

"""Ejemplo de múltiples agentes: triaje y traspaso a agentes del clima según el idioma.

Esto replica la lógica en `openai_agents_handoffs.py` pero implementado con
Pydantic AI usando traspaso programático: un agente de triaje determina si la
solicitud está en español o en inglés, luego invocamos al agente del clima
correspondiente que puede llamar a una herramienta del clima.
"""

# Configuración del cliente OpenAI para usar Azure OpenAI, GitHub Models u Ollama
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
    model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))
else:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = OpenAIChatModel(os.environ.get("OPENAI_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))


class Weather(BaseModel):
    city: str
    temperature: int
    wind_speed: int
    rain_chance: int


class TriageResult(BaseModel):
    language: Literal["spanish", "english"]
    reason: str


async def get_weather(ctx: RunContext[None], city: str) -> Weather:
    """Devuelve datos meteorológicos para la ciudad indicada."""
    temp = random.randint(50, 90)
    wind_speed = random.randint(5, 20)
    rain_chance = random.randint(0, 100)
    return Weather(city=city, temperature=temp, wind_speed=wind_speed, rain_chance=rain_chance)


spanish_weather_agent = Agent(
    model,
    tools=[get_weather],
    system_prompt=(
        "Eres un agente del clima. Solo respondes en español con información del tiempo para la ciudad pedida. "
        "Usa la herramienta 'get_weather' para obtener datos. Devuelve una respuesta breve y clara."
    ),
)

english_weather_agent = Agent(
    model,
    tools=[get_weather],
    system_prompt=(
        "You are a weather agent. You only respond in English with weather info for the requested city. "
        "Use the 'get_weather' tool to fetch data. Keep responses concise."
    ),
)


# Agente de triaje decide qué agente de idioma debe manejar la solicitud
triage_agent = Agent(
    model,
    output_type=TriageResult,
    system_prompt=(
        "Eres un agente de triaje. Determina si la solicitud del usuario está principalmente en español o inglés. "
        "Devuelve language (ya sea 'spanish' o 'english') y reason (una breve explicación de tu elección). "
        "Solo elige 'spanish' si la solicitud está completamente en español; de lo contrario, elige 'english'."
    ),
)


async def main():
    user_input = "Hola, ¿cómo estás? ¿Puedes darme el clima para San Francisco CA?"
    triage = await triage_agent.run(user_input)
    triage_output = triage.output
    print("Resultado del triaje:", triage_output)
    if triage_output.language == "spanish":
        weather_result = await spanish_weather_agent.run(user_input)
    else:
        weather_result = await english_weather_agent.run(user_input)
    print(weather_result.output)

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
