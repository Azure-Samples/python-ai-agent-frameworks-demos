import asyncio
import os
from typing import Literal

import azure.identity
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from rich.prompt import Prompt

# Configuración del cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    client = AsyncAzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )
    model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))


class Flight(BaseModel):
    flight_number: str


class Failed(BaseModel):
    """No se pudo encontrar una opción satisfactoria."""


flight_search_agent = Agent(
    model,
    output_type=Flight | Failed,
    system_prompt=(
        'Usa la herramienta "flight_search" para encontrar un vuelo desde el origen hasta el destino indicado.'
    ),
)


@flight_search_agent.tool
async def flight_search(ctx: RunContext[None], origin: str, destination: str) -> Flight | None:
    # en realidad, esto llamaría a una API de búsqueda de vuelos o
    # usaría un navegador para buscar en un sitio web de búsqueda de vuelos
    return Flight(flight_number="AK456")


async def find_flight() -> Flight | None:
    message_history: list[ModelMessage] | None = None
    for _ in range(3):
        prompt = Prompt.ask(
            "¿Desde dónde y hacia dónde te gustaría volar?",
        )
        result = await flight_search_agent.run(prompt, message_history=message_history)
        if isinstance(result.output, Flight):
            return result.output
        else:
            message_history = result.all_messages()


class Seat(BaseModel):
    row: int = Field(ge=1, le=30)
    seat: Literal["A", "B", "C", "D", "E", "F"]


# Este agente es responsable de extraer la selección de asiento del usuario
seat_preference_agent = Agent(
    model,
    output_type=Seat | Failed,
    system_prompt=(
        "Extrae la preferencia de asiento del usuario. "
        "Los asientos A y F son asientos de ventana. "
        "La fila 1 es la fila delantera y tiene más espacio para las piernas. "
        "Las filas 14 y 20 también tienen más espacio para las piernas."
    ),
)


async def find_seat() -> Seat:
    message_history: list[ModelMessage] | None = None
    while True:
        answer = Prompt.ask("¿Qué asiento te gustaría?")

        result = await seat_preference_agent.run(answer, message_history=message_history)
        if isinstance(result.output, Seat):
            return result.output
        else:
            print("No pude entender tu preferencia de asiento. Por favor, intenta de nuevo.")
            message_history = result.all_messages()


async def main():
    opt_flight_details = await find_flight()
    if opt_flight_details is not None:
        print(f"Vuelo encontrado: {opt_flight_details.flight_number}")
        seat_preference = await find_seat()
        print(f"Preferencia de asiento: {seat_preference}")


if __name__ == "__main__":
    asyncio.run(main())
