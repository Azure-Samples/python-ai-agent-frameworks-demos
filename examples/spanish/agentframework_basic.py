import asyncio
import os

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from azure.identity.aio import get_bearer_token_provider
from dotenv import load_dotenv
from rich import print

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    client = OpenAIChatClient(
        base_url=os.environ.get("AZURE_OPENAI_ENDPOINT") + "/openai/v1/",
        api_key=get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"),
        model_id=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
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
    client = OpenAIChatClient(api_key=os.environ.get("OPENAI_API_KEY"), model_id=os.environ.get("OPENAI_MODEL", "gpt-4o"))

agent = ChatAgent(chat_client=client, instructions="Eres un agente informativo. Responde a las preguntas con alegría.")


async def main():
    response = await agent.run("¿Qué clima hace hoy en San Francisco?")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
