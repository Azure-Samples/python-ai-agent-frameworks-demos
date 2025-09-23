"""
El siguiente ejemplo muestra cómo crear un simple
chat grupal de agentes que utiliza un Agente de Revisión
junto con un Agente Escritor para
completar una tarea del usuario.

Del tutorial completo aquí:
https://learn.microsoft.com/semantic-kernel/frameworks/agent/examples/example-agent-collaboration?pivots=programming-language-python
"""

import asyncio
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncOpenAI
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelFunctionFromPrompt

# Define nombres de agentes
REVIEWER_NAME = "Revisor"
WRITER_NAME = "Escritor"

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")


def create_kernel() -> Kernel:
    """Crea una instancia de Kernel con un servicio de Azure OpenAI ChatCompletion."""
    kernel = Kernel()

    if API_HOST == "azure":
        token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
        chat_client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=token_provider,
    )
        chat_completion_service = OpenAIChatCompletion(ai_model_id=os.environ["AZURE_OPENAI_CHAT_MODEL"], async_client=chat_client)
    else:
        chat_client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
        chat_completion_service = OpenAIChatCompletion(ai_model_id=os.getenv("GITHUB_MODEL", "gpt-4o"), async_client=chat_client)
    kernel.add_service(chat_completion_service)
    return kernel


async def main():
    # Crear una única instancia de kernel para todos los agentes
    kernel = create_kernel()

    # Crear ChatCompletionAgents usando el mismo kernel
    agent_reviewer = ChatCompletionAgent(
        kernel=kernel,
        name=REVIEWER_NAME,
        instructions="""
Tu responsabilidad es revisar e identificar cómo mejorar el contenido proporcionado por el usuario.
Si el usuario ha proporcionado indicaciones sobre contenido ya entregado, especifica cómo abordar estas indicaciones.
Nunca realices la corrección directamente ni proporciones ejemplos.
Una vez que el contenido haya sido actualizado en una respuesta posterior, revísalo nuevamente hasta que sea satisfactorio.

REGLAS:
- Solo identifica sugerencias específicas y accionables.
- Verifica que las sugerencias previas hayan sido implementadas.
- Nunca repitas sugerencias anteriores.
""",
    )

    agent_writer = ChatCompletionAgent(
        kernel=kernel,
        name=WRITER_NAME,
        instructions="""
Tu única responsabilidad es reescribir contenido según las sugerencias de revisión.
- Siempre aplica todas las indicaciones de la revisión.
- Siempre revisa el contenido en su totalidad sin explicaciones.
- Nunca te dirijas al usuario.
""",
    )

    # Definir una función de selección para determinar qué agente debe tomar el siguiente turno
    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""
Examina la RESPUESTA proporcionada y elige al próximo participante.
Indica solo el nombre del participante elegido sin explicación.
Nunca elijas al participante nombrado en la RESPUESTA.

Elige solo entre estos participantes:
- {REVIEWER_NAME}
- {WRITER_NAME}

Reglas:
- Si la RESPUESTA es input del usuario, es turno de {REVIEWER_NAME}.
- Si la RESPUESTA es de {REVIEWER_NAME}, es turno de {WRITER_NAME}.
- Si la RESPUESTA es de {WRITER_NAME}, es turno de {REVIEWER_NAME}.

RESPUESTA:
{{{{$lastmessage}}}}
""",
    )

    # Definir una función de terminación donde el revisor señala la finalización con "sí"
    termination_keyword = "sí"

    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
Examina la RESPUESTA y determina si el contenido ha sido considerado satisfactorio.
Si el contenido es satisfactorio, responde con una sola palabra sin explicación: {termination_keyword}.
Si se están proporcionando sugerencias específicas, no es satisfactorio.
Si no se sugiere ninguna corrección, es satisfactorio.

RESPUESTA:
{{{{$lastmessage}}}}
""",
    )

    history_reducer = ChatHistoryTruncationReducer(target_count=5)

    # Crear el AgentGroupChat con estrategias de selección y terminación
    chat = AgentGroupChat(
        agents=[agent_reviewer, agent_writer],
        selection_strategy=KernelFunctionSelectionStrategy(
            initial_agent=agent_reviewer,
            function=selection_function,
            kernel=kernel,
            result_parser=lambda result: str(result.value[0]).strip() if result.value[0] is not None else WRITER_NAME,
            history_variable_name="lastmessage",
            history_reducer=history_reducer,
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[agent_reviewer],
            function=termination_function,
            kernel=kernel,
            result_parser=lambda result: termination_keyword in str(result.value[0]).lower(),
            history_variable_name="lastmessage",
            maximum_iterations=10,
            history_reducer=history_reducer,
        ),
    )

    print("¡Listo! Escribe tu mensaje, o 'exit' para salir, 'reset' para reiniciar la conversación. " "Puedes pasar un archivo usando @<ruta_del_archivo>.")

    is_complete = False
    while not is_complete:
        print()
        user_input = input("Usuario > ").strip()
        if not user_input:
            continue

        if user_input.lower() == "exit":
            is_complete = True
            break

        await chat.add_chat_message(message=user_input)
        try:
            async for response in chat.invoke():
                if response is None or not response.name:
                    continue
                print()
                print(f"# {response.name.upper()}:\n{response.content}")
        except Exception as e:
            print(f"Error durante la invocación del chat: {e}")

        # Reinicia la bandera de completado del chat para la nueva ronda de conversación
        chat.is_complete = False


if __name__ == "__main__":
    asyncio.run(main())