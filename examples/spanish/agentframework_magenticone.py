"""
Ejemplo de MagenticOne con Agent Framework - Planificación de Viaje con Múltiples Agentes
"""
import asyncio
import os

from agent_framework import (
    ChatAgent,
    MagenticAgentDeltaEvent,
    MagenticBuilder,
    MagenticCallbackEvent,
    MagenticCallbackMode,
    MagenticOrchestratorMessageEvent,
    WorkflowOutputEvent,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Configurar el cliente para usar Azure OpenAI o GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    client = AzureOpenAIChatClient(
        credential=DefaultAzureCredential(),
        deployment_name=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_version=os.environ.get("AZURE_OPENAI_VERSION"),
    )
elif API_HOST == "github":
    client = OpenAIChatClient(
        base_url="https://models.github.ai/inference",
        api_key=os.environ["GITHUB_TOKEN"],
        model_id=os.getenv("GITHUB_MODEL", "openai/gpt-4o"),
    )
elif API_HOST == "ollama":
    client = OpenAIChatClient(
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
        model_id=os.environ.get("OLLAMA_MODEL", "llama3.1:latest"),
    )
else:
    client = OpenAIChatClient(
        api_key=os.environ.get("OPENAI_API_KEY"), model_id=os.environ.get("OPENAI_MODEL", "gpt-4o")
    )

# Crear los agentes
agente_local = ChatAgent(
    chat_client=client,
    instructions=(
        "Sos un asistente útil que puede sugerir actividades locales auténticas e interesantes "
        "o lugares para visitar para un usuario y puede utilizar cualquier información de contexto proporcionada."
    ),
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


# Callback de eventos para salida en streaming
async def on_event(event: MagenticCallbackEvent) -> None:
    if isinstance(event, MagenticOrchestratorMessageEvent):
        print(f"[ORQUESTADOR]: {event.message.text}")
    elif isinstance(event, MagenticAgentDeltaEvent):
        print(event.text, end="")


orquestador_magentico = (
    MagenticBuilder()
    .participants(
        agente_local=agente_local,
        agente_idioma=agente_idioma,
        agente_resumen_viaje=agente_resumen_viaje,
    )
    .on_event(on_event, mode=MagenticCallbackMode.STREAMING)
    .with_standard_manager(
        chat_client=client,
        max_round_count=20,
        max_stall_count=3,
        max_reset_count=2,
    )
    .build()
)


async def main():
    async for event in orquestador_magentico.run_stream("Planificá un viaje de 3 días a Egipto"):
        if isinstance(event, WorkflowOutputEvent):
            resultado_final = event.data
            print(resultado_final.text)


if __name__ == "__main__":
    asyncio.run(main())
