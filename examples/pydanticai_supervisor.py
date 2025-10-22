import asyncio
import os
import random
from typing import Literal

from azure.identity import DefaultAzureCredential
from azure.identity.aio import get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

"""Multi-agent example: triage hand-off to language-specific weather agents.

This mirrors the logic in `openai_agents_handoffs.py` but implemented with
Pydantic AI programmatic hand-off: a triage agent determines whether the
request is in Spanish or English, then we invoke the corresponding weather
agent that can call a weather tool.
"""

# Setup the OpenAI client to use either Azure OpenAI, GitHub Models, or Ollama
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    base_model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "azure":
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1",
        api_key=token_provider,
    )
    base_model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    base_model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))
else:
    raise ValueError(f"Unsupported API_HOST: {API_HOST}")


class Weather(BaseModel):
    city: str
    temperature: int
    wind_speed: int
    rain_chance: int


class TriageResult(BaseModel):
    language: Literal["spanish", "english"]
    reason: str


async def get_weather(ctx: RunContext[None], city: str) -> Weather:
    """Returns weather data for the given city."""
    temp = random.randint(50, 90)
    wind_speed = random.randint(5, 20)
    rain_chance = random.randint(0, 100)
    return Weather(city=city, temperature=temp, wind_speed=wind_speed, rain_chance=rain_chance)


spanish_weather_agent = Agent(
    base_model,
    tools=[get_weather],
    system_prompt=("Eres un agente del clima. Solo respondes en español con información del tiempo para la ciudad pedida. " "Usa la herramienta 'get_weather' para obtener datos. Devuelve una respuesta breve y clara."),
)

english_weather_agent = Agent(
    base_model,
    tools=[get_weather],
    system_prompt=("You are a weather agent. You only respond in English with weather info for the requested city. " "Use the 'get_weather' tool to fetch data. Keep responses concise."),
)


# Triage agent decides which language agent should handle the request
triage_agent = Agent(
    base_model,
    output_type=TriageResult,
    system_prompt=(
        "You are a triage agent. Determine whether the user's request is primarily in Spanish or English. "
        "Return language (either 'spanish' or 'english') and reason (a brief explanation of your choice) "
        "Only choose 'spanish' if the request is entirely in Spanish; otherwise choose 'english'."
    ),
)


async def main():
    user_input = "Hola, ¿cómo estás? ¿Puedes darme el clima para San Francisco CA?"
    triage = await triage_agent.run(user_input)
    triage_output = triage.output
    print("Triage output:", triage_output)
    if triage_output.language == "spanish":
        weather_result = await spanish_weather_agent.run(user_input)
    else:
        weather_result = await english_weather_agent.run(user_input)
    print(weather_result.output)


if __name__ == "__main__":
    asyncio.run(main())
