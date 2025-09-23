import asyncio
import os

import azure.identity
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.messages import HandoffMessage
from autogen_agentchat.teams import Swarm
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

travel_agent = AssistantAgent(
    "travel_agent",
    model_client=client,
    handoffs=["flights_refunder", "user"],
    system_message="""Eres un agente de viajes.
    El flights_refunder se encarga de reembolsar vuelos.
    Si necesitas información del usuario, primero manda tu mensaje y después pásale la conversación al usuario.
    Usa TERMINATE cuando la planificación del viaje esté completa.""",
)


def refund_flight(flight_id: str) -> str:
    """Reembolsar un vuelo"""
    return f"Vuelo {flight_id} reembolsado"


flights_refunder = AssistantAgent(
    "flights_refunder",
    model_client=client,
    handoffs=["travel_agent", "user"],
    tools=[refund_flight],
    system_message="""Eres un agente especializado en reembolsar vuelos.
    Solo necesitas el número de referencia del vuelo para hacer el reembolso.
    Puedes reembolsar un vuelo usando la herramienta refund_flight.
    Si necesitas información del usuario, primero manda tu mensaje y después pásale la conversación al usuario.
    Cuando termines la transacción, pásale la conversación al agente de viajes para finalizar.""",
)


async def run_team_stream(task: str) -> None:
    termination = HandoffTermination(target="user") | TextMentionTermination("TERMINATE")
    team = Swarm([travel_agent, flights_refunder], termination_condition=termination)

    task_result = await Console(team.run_stream(task=task))
    last_message = task_result.messages[-1]

    while isinstance(last_message, HandoffMessage) and last_message.target == "user":
        user_message = input("Usuario: ")

        task_result = await Console(team.run_stream(task=HandoffMessage(source="user", target=last_message.source, content=user_message)))
        last_message = task_result.messages[-1]


if __name__ == "__main__":
    asyncio.run(run_team_stream("Necesito que me reembolsen mi vuelo."))
