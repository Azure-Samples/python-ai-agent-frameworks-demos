"""
Ejemplo de MagenticOne con Agent Framework - Planificación de Viaje con Múltiples Agentes
"""
import asyncio
import json
import os
from typing import cast

from agent_framework import Agent, AgentResponseUpdate, Message, WorkflowEvent
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import MagenticBuilder, MagenticProgressLedger
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Configura el cliente de OpenAI según el entorno
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "azure")

async_credential = None
if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatClient(
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/v1/",
        api_key=token_provider,
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
    )
elif API_HOST == "ollama":
    client = OpenAIChatClient(
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
        model=os.environ.get("OLLAMA_MODEL", "gemma4:e4b"),
    )
else:
    client = OpenAIChatClient(api_key=os.environ["OPENAI_API_KEY"], model=os.environ.get("OPENAI_MODEL", "gpt-4o"))


# Inicializar la consola rich
console = Console()

# Crear los agentes
agente_local = Agent(
    client=client,
    instructions=(
        "Eres un asistente útil que puede sugerir actividades locales auténticas e interesantes "
        "o lugares para visitar para un usuario y puede usar cualquier información de contexto proporcionada."
    ),
    name="agente_local",
    description="Un asistente local que puede sugerir actividades locales o lugares para visitar.",
)

agente_idioma = Agent(
    client=client,
    instructions=(
        "Eres un asistente útil que puede revisar planes de viaje, brindando comentarios sobre consejos importantes "
        "sobre cómo abordar mejor los desafíos de idioma o comunicación para el destino dado. "
        "Si el plan ya incluye consejos de idioma, puedes mencionar que el plan es satisfactorio, con justificación."
    ),
    name="agente_idioma",
    description="Un asistente útil que puede proporcionar consejos de idioma para un destino dado.",
)

agente_resumen_viaje = Agent(
    client=client,
    instructions=(
        "Eres un asistente útil que puede tomar todas las sugerencias y consejos de los otros agentes "
        "y proporcionar un plan de viaje final detallado. Debes asegurarte de que el plan esté integrado y completo. "
        "TU RESPUESTA FINAL DEBE SER EL PLAN COMPLETO. Proporciona un resumen completo cuando todas las perspectivas "
        "de otros agentes se hayan integrado."
    ),
    name="agente_resumen_viaje",
    description="Un asistente útil que puede resumir el plan de viaje.",
)

agente_manager = Agent(
    client=client,
    description="Orquestador que coordina el flujo de trabajo de investigación y codificación",
    instructions="Coordinás un equipo para completar tareas complejas de manera eficiente.",
    name="agente_manager",
)

orquestador_magentico = MagenticBuilder(
    participants=[agente_local, agente_idioma, agente_resumen_viaje],
    manager_agent=agente_manager,
    max_round_count=20,
    max_stall_count=3,
    max_reset_count=2,
).build()


def handle_event(event: WorkflowEvent, last_message_id: str | None) -> str | None:
    """Handle streaming events and return updated last_message_id."""
    if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
        message_id = event.data.message_id
        if message_id != last_message_id:
            if last_message_id is not None:
                console.print()
            console.print(f"🤖 {event.executor_id}:", end=" ")
            last_message_id = message_id
        console.print(event.data, end="")
        return last_message_id

    elif event.type == "magentic_orchestrator":
        console.print()
        emoji = "✅" if event.data.event_type.name == "PROGRESS_LEDGER_UPDATED" else "🦠"
        if isinstance(event.data.content, MagenticProgressLedger):
            console.print(
                Panel(
                    json.dumps(event.data.content.to_dict(), indent=2),
                    title=f"{emoji} Orquestador: {event.data.event_type.name}",
                    border_style="bold yellow",
                    padding=(1, 2),
                )
            )
        elif hasattr(event.data.content, "text"):
            console.print(
                Panel(
                    Markdown(event.data.content.text),
                    title=f"{emoji} Orquestador: {event.data.event_type.name}",
                    border_style="bold green",
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    Markdown(str(event.data.content)),
                    title=f"{emoji} Orquestador: {event.data.event_type.name}",
                    border_style="bold green",
                    padding=(1, 2),
                )
            )

    return last_message_id


def print_final_result(output_event: WorkflowEvent | None) -> None:
    """Print the final travel plan."""
    if output_event:
        output_messages = cast(list[Message], output_event.data)
        console.print(
            Panel(
                Markdown(output_messages[-1].text),
                title="🌎 Plan de Viaje Final",
                border_style="bold green",
                padding=(1, 2),
            )
        )


async def main():
    last_message_id: str | None = None
    output_event: WorkflowEvent | None = None

    async for event in orquestador_magentico.run("Planificá un viaje de medio día a Costa Rica", stream=True):
        last_message_id = handle_event(event, last_message_id)
        if event.type == "output" and not isinstance(event.data, AgentResponseUpdate):
            output_event = event

    print_final_result(output_event)

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
