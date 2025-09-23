import asyncio
import os

import azure.identity
import openai
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from agents.extensions.visualization import draw_graph
from dotenv import load_dotenv

# Desactivamos el rastreo ya que no estamos usando modelos de OpenAI.com
set_tracing_disabled(disabled=True)

# Configuramos el cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = openai.AsyncOpenAI(base_url="https://models.inference.ai.azure.com", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "gpt-4o")
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = openai.AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]


@function_tool
def get_weather(city: str) -> str:
    return {
        "city": city,
        "temperature": 72,
        "description": "Sunny",
    }


agent = Agent(
    name="Agente del clima",
    instructions="Solo puedes proporcionar información del clima.",
    tools=[get_weather],
)

spanish_agent = Agent(
    name="Agente en español",
    instructions="Solo hablas español.",
    tools=[get_weather],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)

english_agent = Agent(
    name="Agente en inglés",
    instructions="Solo hablas inglés",
    tools=[get_weather],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)

triage_agent = Agent(
    name="Agente de clasificación",
    instructions="Transfiere al agente apropiado según el idioma de la solicitud.",
    handoffs=[spanish_agent, english_agent],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)


async def main():
    result = await Runner.run(triage_agent, input="Hola, ¿cómo estás? ¿Puedes darme el clima para Cuenca, Ecuador?")
    gz_source = draw_graph(triage_agent, filename="openai_agents_handoffs.png")
    # guardamos el grafo en un archivo en formato graphviz
    gz_source.save("openai_agents_handoffs.dot")

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())