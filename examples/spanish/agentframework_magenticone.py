"""
Ejemplo de MagenticOne con Agent Framework - Planificación de Viaje con Múltiples Agentes
"""
import asyncio
import os

from agent_framework import (
    ChatAgent,
    MagenticAgentMessageEvent,
    MagenticBuilder,
    MagenticCallbackEvent,
    MagenticCallbackMode,
    MagenticOrchestratorMessageEvent,
    WorkflowOutputEvent,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# Configurar el cliente para usar Azure OpenAI, GitHub Models, Ollama o OpenAI
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

async_credential = None
if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    client = OpenAIChatClient(
        base_url=os.environ.get("AZURE_OPENAI_ENDPOINT") + "/openai/v1/", api_key=get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default"), model_id=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT")
    )
elif API_HOST == "github":
    client = OpenAIChatClient(base_url="https://models.github.ai/inference", api_key=os.environ["GITHUB_TOKEN"], model_id=os.getenv("GITHUB_MODEL", "openai/gpt-4o"))
elif API_HOST == "ollama":
    client = OpenAIChatClient(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none", model_id=os.environ.get("OLLAMA_MODEL", "llama3.1:latest"))
else:
    client = OpenAIChatClient(api_key=os.environ.get("OPENAI_API_KEY"), model_id=os.environ.get("OPENAI_MODEL", "gpt-4o"))

# Initializar la consola rich
console = Console()

# Crear los agentes
agente_local = ChatAgent(
    chat_client=client,
    instructions=("Sos un asistente útil que puede sugerir actividades locales auténticas e interesantes " "o lugares para visitar para un usuario y puede utilizar cualquier información de contexto proporcionada."),
    name="agente_local",
    description="Un asistente local que puede sugerir actividades locales o lugares para visitar.",
)

agente_idioma = ChatAgent(
    chat_client=client,
    instructions=(
        "Sos un asistente útil que puede revisar planes de viaje, brindando comentarios sobre consejos importantes/críticos "
        "sobre cómo abordar mejor los desafíos de idioma o comunicación para el destino dado. "
        "Si el plan ya incluye consejos de idioma, podés mencionar que el plan es satisfactorio, con justificación."
    ),
    name="agente_idioma",
    description="Un asistente útil que puede proporcionar consejos de idioma para un destino dado.",
)

agente_resumen_viaje = ChatAgent(
    chat_client=client,
    instructions=(
        "Sos un asistente útil que puede tomar todas las sugerencias y consejos de los otros agentes "
        "y proporcionar un plan de viaje final detallado. Debes asegurarte de que el plan final esté integrado y completo. "
        "TU RESPUESTA FINAL DEBE SER EL PLAN COMPLETO. Proporciona un resumen exhaustivo cuando todas las perspectivas "
        "de otros agentes se hayan integrado."
    ),
    name="agente_resumen_viaje",
    description="Un asistente útil que puede resumir el plan de viaje.",
)


# Event callback for streaming output with rich formatting
async def on_event(event: MagenticCallbackEvent) -> None:
    if isinstance(event, MagenticOrchestratorMessageEvent):
        emoji = "✅" if event.kind == "task_ledger" else "🦠"
        console.print(
            Panel(
                Markdown(event.message.text),
                title=f"{emoji} orquestador: {event.kind}",
                border_style="bold green",
                padding=(1, 2),
            )
        )
    elif isinstance(event, MagenticAgentMessageEvent):
        console.print(
            Panel(
                Markdown(event.message.text),
                title=f"🤖 {event.agent_id}",
                border_style="bold blue",
                padding=(1, 2),
            )
        )


orquestador_magentico = (
    MagenticBuilder()
    .participants(
        agente_local=agente_local,
        agente_idioma=agente_idioma,
        agente_resumen_viaje=agente_resumen_viaje,
    )
    .on_event(on_event, mode=MagenticCallbackMode.NON_STREAMING)
    .with_standard_manager(
        chat_client=client,
        max_round_count=20,
        max_stall_count=3,
        max_reset_count=2,
    )
    .build()
)


async def main():
    async for event in orquestador_magentico.run_stream("Planificá un viaje de medio día a Costa Rica"):
        if isinstance(event, WorkflowOutputEvent):
            resultado_final = event.data
            console.print(
                Panel(
                    Markdown(resultado_final.text),
                    title="🌎 final travel plan",
                    border_style="bold green",
                    padding=(1, 2),
                )
            )
    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
