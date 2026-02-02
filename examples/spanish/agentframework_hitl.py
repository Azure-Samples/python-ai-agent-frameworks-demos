# Copyright (c) Microsoft. All rights reserved.

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Annotated

from agent_framework import (
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentResponse,
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    Content,
    Executor,
    RequestInfoEvent,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowOutputEvent,
    handler,
    response_handler,
    tool,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from pydantic import Field
from typing_extensions import Never

# Configurar el cliente para usar Azure OpenAI, GitHub Models, Ollama o OpenAI
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")
async_credential = None

if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatClient(
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/v1/",
        api_key=token_provider,
        model_id=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
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
    client = OpenAIChatClient(api_key=os.environ["OPENAI_API_KEY"], model_id=os.environ.get("OPENAI_MODEL", "gpt-4o"))

"""
Ejemplo: Agentes con herramientas y retroalimentación humana

Diseño del flujo:
agente_escritor (usa herramientas de Azure OpenAI) -> Coordinador -> agente_escritor
-> Coordinador -> agente_editor_final -> Coordinador -> salida

El agente escritor llama a herramientas para obtener datos del producto antes de redactar el texto.
Un ejecutor personalizado empaqueta el borrador y emite un RequestInfoEvent para que un humano
pueda comentar, luego reproduce la guía humana en la conversación antes de que el agente editor
final produzca la salida pulida.

Demuestra:
- Adjuntar herramientas de funciones Python a un agente dentro de un flujo de trabajo.
- Capturar la salida del escritor para revisión humana.
- Transmitir actualizaciones de AgentRunUpdateEvent junto con pausas de humano en el ciclo.

Requisitos previos:
- Azure OpenAI configurado para AzureOpenAIChatClient con las variables de entorno requeridas.
- Autenticación via azure-identity. Ejecutá `az login` antes de ejecutar.
"""


# NOTA: approval_mode="never_require" es por brevedad del ejemplo.
@tool(approval_mode="never_require")
def obtener_resumen_producto(
    nombre_producto: Annotated[str, Field(description="Nombre del producto a buscar.")],
) -> str:
    """Devuelve un resumen de marketing para un producto."""
    resumenes = {
        "lámpara de escritorio lumenx": (
            "Producto: Lámpara de Escritorio LumenX\n"
            "- Brazo ajustable de tres puntos con rotación de 270°.\n"
            "- Espectro LED personalizado de cálido a neutro (2700K-4000K).\n"
            "- Base de carga USB-C integrada en la base.\n"
            "- Diseñada para oficinas en casa y sesiones de estudio nocturnas."
        )
    }
    return resumenes.get(nombre_producto.lower(), f"No hay resumen almacenado para '{nombre_producto}'.")


# NOTA: approval_mode="never_require" es por brevedad del ejemplo.
@tool(approval_mode="never_require")
def obtener_perfil_voz_marca(
    nombre_voz: Annotated[str, Field(description="Voz de marca o campaña a emular.")],
) -> str:
    """Devuelve las directrices para la voz de marca solicitada."""
    voces = {
        "lanzamiento lumenx": (
            "Directrices de voz:\n"
            "- Amigable y moderno con oraciones concisas.\n"
            "- Resaltar beneficios prácticos antes que estéticos.\n"
            "- Terminar con una invitación a imaginar el producto en uso diario."
        )
    }
    return voces.get(nombre_voz.lower(), f"No hay perfil de voz almacenado para '{nombre_voz}'.")


@dataclass
class SolicitudRetroalimentacionBorrador:
    """Carga útil enviada para revisión humana."""

    indicacion: str = ""
    texto_borrador: str = ""
    conversacion: list[ChatMessage] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class Coordinador(Executor):
    """Puente entre el agente escritor, la retroalimentación humana y el editor final."""

    def __init__(self, id: str, id_escritor: str, id_editor_final: str) -> None:
        super().__init__(id)
        self.id_escritor = id_escritor
        self.id_editor_final = id_editor_final

    @handler
    async def al_responder_escritor(
        self,
        borrador: AgentExecutorResponse,
        ctx: WorkflowContext[Never, AgentResponse],
    ) -> None:
        """Maneja las respuestas de los otros dos agentes en el flujo de trabajo."""
        if borrador.executor_id == self.id_editor_final:
            # Respuesta del editor final; emitir salida directamente.
            await ctx.yield_output(borrador.agent_response)
            return

        # Respuesta del agente escritor; solicitar retroalimentación humana.
        # Preservar la conversación completa para que el editor final
        # pueda ver los rastros de herramientas y el prompt inicial.
        conversacion: list[ChatMessage]
        if borrador.full_conversation is not None:
            conversacion = list(borrador.full_conversation)
        else:
            conversacion = list(borrador.agent_response.messages)
        texto_borrador = borrador.agent_response.text.strip()
        if not texto_borrador:
            texto_borrador = "No se produjo texto de borrador."

        indicacion = (
            "Revisá el borrador del escritor y proporcioná una nota direccional breve "
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
        nota = retroalimentacion.strip()
        if nota.lower() == "aprobar":
            # El humano aprobó el borrador tal como está; reenviarlo sin cambios.
            await ctx.send_message(
                AgentExecutorRequest(
                    messages=solicitud_original.conversacion
                    + [ChatMessage(Role.USER, text="El borrador está aprobado tal como está.")],
                    should_respond=True,
                ),
                target_id=self.id_editor_final,
            )
            return

        # El humano proporcionó retroalimentación; indicar al escritor que revise.
        conversacion: list[ChatMessage] = list(solicitud_original.conversacion)
        instruccion = (
            "Un revisor humano compartió la siguiente guía:\n"
            f"{nota or 'No se proporcionó guía específica.'}\n\n"
            "Reescribí el borrador del mensaje anterior del asistente en una versión final pulida. "
            "Mantené la respuesta en menos de 120 palabras y reflejá los ajustes de tono solicitados."
        )
        conversacion.append(ChatMessage(Role.USER, text=instruccion))
        await ctx.send_message(
            AgentExecutorRequest(messages=conversacion, should_respond=True), target_id=self.id_escritor
        )


def crear_agente_escritor() -> ChatAgent:
    """Crea un agente escritor con herramientas."""
    return ChatAgent(
        chat_client=client,
        name="agente_escritor",
        instructions=(
            "Sos un escritor de marketing. Llamá a las herramientas disponibles antes de redactar para ser preciso. "
            "Siempre llamá a ambas herramientas una vez antes de redactar. Resumí las salidas de las herramientas "
            "como viñetas, luego producí un borrador de 3 oraciones."
        ),
        tools=[obtener_resumen_producto, obtener_perfil_voz_marca],
        tool_choice="required",
    )


def crear_agente_editor_final() -> ChatAgent:
    """Crea un agente editor final."""
    return ChatAgent(
        chat_client=client,
        name="agente_editor_final",
        instructions=(
            "Sos un editor que pule el texto de marketing después de la aprobación humana. "
            "Corregí cualquier problema legal o fáctico. Devolvé la versión final aunque no se necesiten cambios."
        ),
    )


def mostrar_actualizacion_ejecucion_agente(evento: AgentRunUpdateEvent, ultimo_ejecutor: str | None) -> None:
    """Muestra un AgentRunUpdateEvent en un formato legible."""
    llamadas_herramientas_impresas: set[str] = set()
    resultados_herramientas_impresos: set[str] = set()
    id_ejecutor = evento.executor_id
    actualizacion = evento.data
    # Extraer e imprimir cualquier nueva llamada a herramienta o resultado de la actualización.
    # Content.type indica el tipo de contenido: 'function_call', 'function_result', 'text', etc.
    llamadas_funcion = [c for c in actualizacion.contents if isinstance(c, Content) and c.type == "function_call"]
    resultados_funcion = [c for c in actualizacion.contents if isinstance(c, Content) and c.type == "function_result"]
    if id_ejecutor != ultimo_ejecutor:
        if ultimo_ejecutor is not None:
            print()
        print(f"{id_ejecutor}:", end=" ", flush=True)
        ultimo_ejecutor = id_ejecutor
    # Imprimir cualquier nueva llamada a herramienta antes de la actualización de texto.
    for llamada in llamadas_funcion:
        if llamada.call_id in llamadas_herramientas_impresas:
            continue
        llamadas_herramientas_impresas.add(llamada.call_id)
        args = llamada.arguments
        vista_previa_args = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else (args or "").strip()
        print(
            f"\n{id_ejecutor} [llamada-herramienta] {llamada.name}({vista_previa_args})",
            flush=True,
        )
        print(f"{id_ejecutor}:", end=" ", flush=True)
    # Imprimir cualquier nuevo resultado de herramienta antes de la actualización de texto.
    for resultado in resultados_funcion:
        if resultado.call_id in resultados_herramientas_impresos:
            continue
        resultados_herramientas_impresos.add(resultado.call_id)
        texto_resultado = resultado.result
        if not isinstance(texto_resultado, str):
            texto_resultado = json.dumps(texto_resultado, ensure_ascii=False)
        print(
            f"\n{id_ejecutor} [resultado-herramienta] {resultado.call_id}: {texto_resultado}",
            flush=True,
        )
        print(f"{id_ejecutor}:", end=" ", flush=True)
    # Finalmente, imprimir la actualización de texto.
    print(actualizacion, end="", flush=True)


async def main() -> None:
    """Ejecuta el flujo de trabajo y conecta la retroalimentación humana entre dos agentes."""

    # Construir el flujo de trabajo.
    flujo_trabajo = (
        WorkflowBuilder()
        .register_agent(crear_agente_escritor, name="agente_escritor")
        .register_agent(crear_agente_editor_final, name="agente_editor_final")
        .register_executor(
            lambda: Coordinador(
                id="coordinador",
                id_escritor="agente_escritor",
                id_editor_final="agente_editor_final",
            ),
            name="coordinador",
        )
        .set_start_executor("agente_escritor")
        .add_edge("agente_escritor", "coordinador")
        .add_edge("coordinador", "agente_escritor")
        .add_edge("agente_editor_final", "coordinador")
        .add_edge("coordinador", "agente_editor_final")
        .build()
    )

    # Interruptor para activar la visualización de actualizaciones de ejecución del agente.
    # Por defecto está desactivado para reducir el desorden durante la entrada humana.
    mostrar_actualizaciones = False

    print(
        "Modo interactivo. Cuando se te solicite, proporcioná una nota de retroalimentación breve para el editor.",
        flush=True,
    )

    respuestas_pendientes: dict[str, str] | None = None
    completado = False
    ejecucion_inicial = True

    while not completado:
        ultimo_ejecutor: str | None = None
        if ejecucion_inicial:
            stream = flujo_trabajo.run_stream(
                "Creá un breve texto de lanzamiento para la lámpara de escritorio LumenX. "
                "Enfatizá la ajustabilidad y la iluminación cálida."
            )
            ejecucion_inicial = False
        elif respuestas_pendientes is not None:
            stream = flujo_trabajo.send_responses_streaming(respuestas_pendientes)
            respuestas_pendientes = None
        else:
            break

        solicitudes: list[tuple[str, SolicitudRetroalimentacionBorrador]] = []

        async for evento in stream:
            if isinstance(evento, AgentRunUpdateEvent) and mostrar_actualizaciones:
                mostrar_actualizacion_ejecucion_agente(evento, ultimo_ejecutor)
            if isinstance(evento, RequestInfoEvent) and isinstance(evento.data, SolicitudRetroalimentacionBorrador):
                # Guardar la solicitud para solicitar al humano después de que se complete el stream.
                solicitudes.append((evento.request_id, evento.data))
                ultimo_ejecutor = None
            elif isinstance(evento, WorkflowOutputEvent):
                ultimo_ejecutor = None
                respuesta = evento.data
                print("\n===== Salida final =====")
                texto_final = getattr(respuesta, "text", str(respuesta))
                print(texto_final.strip())
                completado = True

        if solicitudes and not completado:
            respuestas: dict[str, str] = {}
            for id_solicitud, solicitud in solicitudes:
                print("\n----- Borrador del escritor -----")
                print(solicitud.texto_borrador.strip())
                print("\nProporcioná guía para el editor (o 'aprobar' para aceptar el borrador).")
                respuesta_usuario = input("Retroalimentación humana: ").strip()  # noqa: ASYNC250
                if respuesta_usuario.lower() == "salir":
                    print("Saliendo...")
                    return
                respuestas[id_solicitud] = respuesta_usuario
            respuestas_pendientes = respuestas

    print("Flujo de trabajo completado.")

    # Cerrar la credencial asíncrona si fue creada
    if async_credential is not None:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
