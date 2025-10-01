import asyncio
import os

import azure.identity
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

# Setup the client to use either Azure OpenAI or GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")


if API_HOST == "github":
    client = OpenAIChatCompletionClient(model=os.getenv("GITHUB_MODEL", "gpt-4o"), api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatCompletionClient(model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], api_key=token_provider, base_url=os.environ["AZURE_OPENAI_ENDPOINT"])

local_agent = AssistantAgent(
    "local_agent",
    model_client=client,
    description="Un asistente local que puede sugerir actividades o lugares interesantes para visitar.",
    system_message="Eres un asistente buena onda que puede sugerir actividades auténticas y lugares interesantes para visitar, aprovechando cualquier información adicional que te den.",
)

language_agent = AssistantAgent(
    "language_agent",
    model_client=client,
    description="Un asistente buena onda que puede dar consejos sobre el idioma del destino.",
    system_message="Eres un asistente buena onda que revisa planes de viaje y da consejos importantes sobre cómo manejar mejor el idioma o los problemas de comunicación en el destino elegido. Si el plan ya incluye buenos tips de idioma, puedes decir que está todo bien y explicar por qué.",
)

travel_summary_agent = AssistantAgent(
    "travel_summary_agent",
    model_client=client,
    description="Un asistente buena onda que puede resumir el plan de viaje.",
    system_message="Eres un asistente buena onda que toma todas las sugerencias y consejos de los otros asistentes y arma un plan de viaje final detallado. Asegúrate de que el plan final esté completo y bien integrado. TU RESPUESTA FINAL DEBE SER EL PLAN COMPLETO. Cuando el plan esté listo y todas las perspectivas integradas, responde con TERMINATE.",
)


async def run_agents():
    termination = TextMentionTermination("TERMINATE")
    group_chat = MagenticOneGroupChat(
        [local_agent, language_agent, travel_summary_agent],
        termination_condition=termination,
        model_client=client,
    )
    await Console(group_chat.run_stream(task="Planea un viaje de 3 días a Egipto"))


if __name__ == "__main__":
    asyncio.run(run_agents())
