# Copyright (c) Microsoft. All rights reserved.

# NOTA: Este ejemplo intencionalmente no usa herramientas en el workflow HITL.
# Herramientas + HITL causa errores de ID de item duplicado con la Responses API.
# Ver https://github.com/microsoft/agent-framework/issues/3295
# Para un ejemplo con herramientas, ver agentframework_tools.py.

import asyncio
import os
from collections.abc import AsyncIterable
from dataclasses import dataclass, field

from agent_framework import (
    Agent,
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentResponse,
    AgentResponseUpdate,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    handler,
    response_handler,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from typing_extensions import Never

# Configura el cliente para usar Azure OpenAI, Ollama u OpenAI
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

"""
Ejemplo: agentes con retroalimentación humana

Diseño del pipeline:
agente_escritor -> Coordinador -> agente_escritor
-> Coordinador -> agente_editor_final -> Coordinador -> salida

El agente escritor escribe textos de marketing. Un ejecutor personalizado empaqueta
la versión preliminar y emite un evento request_info para que un humano pueda comentar;
luego incorpora esa guía en la conversación antes de que el editor final produzca
la salida pulida.

Demuestra:
- Capturar la salida del escritor para revisión humana.
- Transmitir actualizaciones de AgentResponseUpdate junto con pausas con intervención humana.

Requisitos previos:
- Azure OpenAI configurado con las variables de entorno requeridas.
- Autenticación vía azure-identity. Ejecutá `az login` antes de ejecutar.
"""


@dataclass
class SolicitudRetroalimentacionBorrador:
    """Carga útil enviada para revisión humana."""

    indicacion: str = ""
    texto_borrador: str = ""
    conversacion: list[Message] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class Coordinador(Executor):
    """Puente entre el agente escritor, la retroalimentación humana y el editor final."""

    def __init__(self, id: str, nombre_escritor: str, nombre_editor_final: str) -> None:
        super().__init__(id)
        self.nombre_escritor = nombre_escritor
        self.nombre_editor_final = nombre_editor_final

    @handler
    async def al_responder_escritor(
        self,
        borrador: AgentExecutorResponse,
        ctx: WorkflowContext[Never, AgentResponse],
    ) -> None:
        """Maneja las respuestas del escritor y el editor final."""
        if borrador.executor_id == self.nombre_editor_final:
            # Respuesta del editor final; emitir salida directamente.
            await ctx.yield_output(borrador.agent_response)
            return

        # Respuesta del agente escritor; solicitar retroalimentación humana.
        # Preservar la conversación completa para que el editor final
        # pueda ver los rastros de herramientas y el prompt inicial.
        conversacion = list(borrador.full_conversation)
        texto_borrador = borrador.agent_response.text.strip()
        if not texto_borrador:
            texto_borrador = "No se produjo ninguna versión preliminar."

        indicacion = (
            "Revisá la versión preliminar del escritor y compartí una nota direccional breve "
            "(ajustes de tono, detalles imprescindibles, público objetivo, etc.). "
            "Mantené la nota en menos de 30 palabras."
        )
        await ctx.request_info(
            request_data=SolicitudRetroalimentacionBorrador(
                indicacion=indicacion, texto_borrador=texto_borrador, conversacion=conversacion
            ),
            response_type=str,
        )

    @response_handler
    async def al_recibir_retroalimentacion_humana(
        self,
        solicitud_original: SolicitudRetroalimentacionBorrador,
        retroalimentacion: str,
        ctx: WorkflowContext[AgentExecutorRequest],
    ) -> None:
        """Procesa la retroalimentación humana y la reenvía al agente apropiado."""
        nota = retroalimentacion.strip()
        if nota.lower() == "aprobar":
            # El humano aprobó el borrador tal como está; reenviarlo sin cambios.
            await ctx.send_message(
                AgentExecutorRequest(
                    messages=solicitud_original.conversacion
                    + [Message("user", contents=["La versión preliminar está aprobada tal como está."])],
                    should_respond=True,
                ),
                target_id=self.nombre_editor_final,
            )
            return

        # El humano proporcionó retroalimentación; indicar al escritor que revise.
        conversacion: list[Message] = list(solicitud_original.conversacion)
        instruccion = (
            "Un revisor humano compartió la siguiente guía:\n"
            f"{nota or 'No se proporcionó guía específica.'}\n\n"
            "Reescribí la versión preliminar del mensaje anterior del asistente en una versión final pulida. "
            "Mantené la respuesta en menos de 120 palabras y reflejá los ajustes de tono solicitados."
        )
        conversacion.append(Message("user", contents=[instruccion]))
        await ctx.send_message(
            AgentExecutorRequest(messages=conversacion, should_respond=True), target_id=self.nombre_escritor
        )


async def procesar_stream_eventos(stream: AsyncIterable[WorkflowEvent]) -> dict[str, str] | None:
    """Procesa eventos del stream del workflow para capturar solicitudes de retroalimentación humana."""
    ultimo_autor: str | None = None

    solicitudes: list[tuple[str, SolicitudRetroalimentacionBorrador]] = []
    async for evento in stream:
        if evento.type == "request_info" and isinstance(evento.data, SolicitudRetroalimentacionBorrador):
            solicitudes.append((evento.request_id, evento.data))
        elif evento.type == "output":
            if isinstance(evento.data, AgentResponseUpdate):
                actualizacion = evento.data
                autor = actualizacion.author_name
                if autor != ultimo_autor:
                    if ultimo_autor is not None:
                        print()
                    print(f"{autor}: {actualizacion.text}", end="", flush=True)
                    ultimo_autor = autor
                else:
                    print(actualizacion.text, end="", flush=True)
            elif isinstance(evento.data, AgentResponse):
                print(f"\n\n✅ Salida final:\n{evento.data.text.strip()}")

    if solicitudes:
        respuestas: dict[str, str] = {}
        for id_solicitud, solicitud in solicitudes:
            print("\n\n----- Versión preliminar del escritor -----")
            print(solicitud.texto_borrador.strip())
            print("\nProporcioná guía para el editor (o 'aprobar' para aceptar la versión preliminar).")
            respuesta_usuario = input("Retroalimentación humana: ").strip()  # noqa: ASYNC250
            if respuesta_usuario.lower() == "salir":
                print("Saliendo...")
                return None
            respuestas[id_solicitud] = respuesta_usuario
        return respuestas
    return None


async def main() -> None:
    """Ejecuta el workflow y conecta la retroalimentación humana entre dos agentes."""
    agente_escritor = Agent(
        client=client,
        name="agente_escritor",
        instructions="Sos un escritor de marketing. Escribí textos claros y atractivos.",
    )

    agente_editor_final = Agent(
        client=client,
        name="agente_editor_final",
        instructions=(
            "Sos un editor que pule el texto de marketing después de la aprobación humana. "
            "Corregí cualquier problema legal o fáctico. Devolvé la versión final aunque no se necesiten cambios."
        ),
    )

    coordinador = Coordinador(
        id="coordinador",
        nombre_escritor=agente_escritor.name,  # type: ignore
        nombre_editor_final=agente_editor_final.name,  # type: ignore
    )

    flujo_trabajo = (
        WorkflowBuilder(start_executor=agente_escritor)
        .add_edge(agente_escritor, coordinador)
        .add_edge(coordinador, agente_escritor)
        .add_edge(agente_editor_final, coordinador)
        .add_edge(coordinador, agente_editor_final)
        .build()
    )

    print(
        "Modo interactivo. Cuando se te solicite, proporcioná una nota de retroalimentación breve para el editor.",
        flush=True,
    )

    stream = flujo_trabajo.run(
        "Creá un breve texto de lanzamiento para la lámpara de escritorio LumenX. "
        "Enfatizá la ajustabilidad y la iluminación cálida.",
        stream=True,
    )

    respuestas_pendientes = await procesar_stream_eventos(stream)
    while respuestas_pendientes is not None:
        stream = flujo_trabajo.run(stream=True, responses=respuestas_pendientes)
        respuestas_pendientes = await procesar_stream_eventos(stream)

    print("\nWorkflow completado.")

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
