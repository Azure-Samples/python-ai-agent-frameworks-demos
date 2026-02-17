# pip install agent-framework-devui==1.0.0b260212
import os
from typing import Any

from agent_framework import AgentExecutorResponse, WorkflowBuilder
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from pydantic import BaseModel

# Configurar el cliente para usar Azure OpenAI, GitHub Models, Ollama o OpenAI
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

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


# Definir salida estructurada para resultados de revisión
class ResultadoRevision(BaseModel):
    """Evaluación de revisión con puntajes y retroalimentación."""

    puntaje: int  # Puntaje general de calidad (0-100)
    retroalimentacion: str  # Retroalimentación concisa y accionable
    claridad: int  # Puntaje de claridad (0-100)
    completitud: int  # Puntaje de completitud (0-100)
    precision: int  # Puntaje de precisión (0-100)
    estructura: int  # Puntaje de estructura (0-100)


# Función de condición: enviar al editor si puntaje < 80
def necesita_edicion(message: Any) -> bool:
    """Verificar si el contenido necesita edición basándose en el puntaje de revisión."""
    if not isinstance(message, AgentExecutorResponse):
        return False
    try:
        revision = ResultadoRevision.model_validate_json(message.agent_response.text)
        return revision.puntaje < 80
    except Exception:
        return False


# Función de condición: el contenido está aprobado (puntaje >= 80)
def esta_aprobado(message: Any) -> bool:
    """Verificar si el contenido está aprobado (alta calidad)."""
    if not isinstance(message, AgentExecutorResponse):
        return True
    try:
        revision = ResultadoRevision.model_validate_json(message.agent_response.text)
        return revision.puntaje >= 80
    except Exception:
        return True


# Crear agente Escritor - genera contenido
def create_escritor():
    return client.as_agent(
        name="Escritor",
        instructions=(
            "Sos un excelente escritor de contenido. "
            "Creá contenido claro y atractivo basado en la solicitud del usuario. "
            "Enfocate en la claridad, precisión y estructura adecuada."
        ),
    )


# Crear agente Revisor - evalúa y proporciona retroalimentación estructurada
def create_revisor():
    return client.as_agent(
        name="Revisor",
        instructions=(
            "Sos un experto revisor de contenido. "
            "Evaluá el contenido del escritor basándote en:\n"
            "1. Claridad - ¿Es fácil de entender?\n"
            "2. Completitud - ¿Aborda completamente el tema?\n"
            "3. Precisión - ¿Es correcta la información?\n"
            "4. Estructura - ¿Está bien organizado?\n\n"
            "Devolvé un objeto JSON con:\n"
            "- puntaje: calidad general (0-100)\n"
            "- retroalimentacion: retroalimentación concisa y accionable\n"
            "- claridad, completitud, precision, estructura: puntajes individuales (0-100)"
        ),
        response_format=ResultadoRevision,
    )


# Crear agente Editor - mejora el contenido basándose en la retroalimentación
def create_editor():
    return client.as_agent(
        name="Editor",
        instructions=(
            "Sos un editor habilidoso. "
            "Recibirás contenido junto con retroalimentación de revisión. "
            "Mejorá el contenido abordando todos los problemas mencionados en la retroalimentación. "
            "Mantené la intención original mientras mejorás la claridad, completitud, precisión y estructura."
        ),
    )


# Crear agente Publicador - formatea el contenido para publicación
def create_publicador():
    return client.as_agent(
        name="Publicador",
        instructions=(
            "Sos un agente de publicación. "
            "Recibís contenido aprobado o editado. "
            "Formatealo para publicación con encabezados y estructura adecuados."
        ),
    )


# Crear agente Resumidor - crea el informe final de publicación
def create_resumidor():
    return client.as_agent(
        name="Resumidor",
        instructions=(
            "Sos un agente resumidor. "
            "Creá un informe de publicación final que incluya:\n"
            "1. Un breve resumen del contenido publicado\n"
            "2. El camino del flujo de trabajo seguido (aprobación directa o editado)\n"
            "3. Aspectos destacados y conclusiones clave\n"
            "Mantené la concisión y profesionalismo."
        ),
    )


# Construir flujo de trabajo con ramificación y convergencia:
# Escritor → Revisor → [ramas]:
#   - Si puntaje >= 80: → Publicador → Resumidor (ruta de aprobación directa)
#   - Si puntaje < 80: → Editor → Publicador → Resumidor (ruta de mejora)
# Ambas rutas convergen en Resumidor para el informe final
escritor = create_escritor()
revisor = create_revisor()
editor = create_editor()
publicador = create_publicador()
resumidor = create_resumidor()

flujo_trabajo = (
    WorkflowBuilder(
        name="Flujo de Trabajo de Revisión de Contenido",
        description="Creación de contenido con enrutamiento basado en calidad (Escritor → Revisor → Editor/Publicador)",
        start_executor=escritor,
    )
    .add_edge(escritor, revisor)
    # Rama 1: Alta calidad (>= 80) va directamente al publicador
    .add_edge(revisor, publicador, condition=esta_aprobado)
    # Rama 2: Baja calidad (< 80) va primero al editor, luego al publicador
    .add_edge(revisor, editor, condition=necesita_edicion)
    .add_edge(editor, publicador)
    # Ambas rutas convergen: Publicador → Resumidor
    .add_edge(publicador, resumidor)
    .build()
)


def main():
    from agent_framework.devui import serve

    serve(entities=[flujo_trabajo], port=8093, auto_open=True)


if __name__ == "__main__":
    main()
