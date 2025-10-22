import asyncio
import os

import azure.identity
import openai
from agents import Agent, OpenAIChatCompletionsModel, Runner, function_tool, set_tracing_disabled
from dotenv import load_dotenv

# Disable tracing since we're not using OpenAI.com models
set_tracing_disabled(disabled=True)

# Setup the OpenAI client to use either Azure OpenAI or GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = openai.AsyncOpenAI(base_url="https://models.inference.ai.azure.com", api_key=os.environ["GITHUB_TOKEN"])
    MODEL_NAME = os.getenv("GITHUB_MODEL", "gpt-4o")
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    client = openai.AsyncAzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
elif API_HOST == "ollama":
    client = openai.AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="none")
    MODEL_NAME = "llama3.1:latest"


@function_tool
def get_weather(city: str) -> str:
    return {
        "city": city,
        "temperature": 72,
        "description": "Sunny",
    }


agent = Agent(
    name="Weather agent",
    instructions="You can only provide weather information.",
    tools=[get_weather],
)

spanish_agent = Agent(
    name="Spanish agent",
    instructions="You only speak Spanish.",
    tools=[get_weather],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)

english_agent = Agent(
    name="English agent",
    instructions="You only speak English",
    tools=[get_weather],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)

triage_agent = Agent(
    name="Triage agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",
    handoffs=[spanish_agent, english_agent],
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
)


async def main():
    result = await Runner.run(triage_agent, input="Hola, ¿cómo estás? ¿Puedes darme el clima para San Francisco CA?")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
