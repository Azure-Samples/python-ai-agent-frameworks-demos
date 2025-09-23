import asyncio
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Configuración del cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=token_provider,
    )
    model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))

agent: Agent[None, str] = Agent(
    model,
    system_prompt="Eres un tutor de inglés. Ayuda al usuario a aprender inglés. SOLO responde en inglés.",
    output_type=str,
)


async def main():
    result = await agent.run("Hola. ¿Cómo estás?")
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
