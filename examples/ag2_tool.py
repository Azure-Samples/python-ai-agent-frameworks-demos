import asyncio
import logging
import os
import random
from typing import Annotated

from autogen import AssistantAgent, LLMConfig, UserProxyAgent
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

# Setup logging
handler = RichHandler(show_path=False, rich_tracebacks=True, show_level=False)
logging.basicConfig(level=logging.WARNING, handlers=[handler], force=True, format="%(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure LLM based on environment
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

async_credential = None
if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default")
    llm_config = LLMConfig(
        api_type="openai",
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/deployments/{os.environ['AZURE_OPENAI_CHAT_DEPLOYMENT']}",
        api_key=token_provider,
    )
elif API_HOST == "github":
    llm_config = LLMConfig(
        api_type="openai",
        model=os.getenv("GITHUB_MODEL", "openai/gpt-4o"),
        base_url="https://models.github.ai/inference",
        api_key=os.environ["GITHUB_TOKEN"],
    )
elif API_HOST == "ollama":
    llm_config = LLMConfig(
        api_type="openai",
        model=os.environ.get("OLLAMA_MODEL", "llama3.1:latest"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
    )
else:
    llm_config = LLMConfig(
        api_type="openai",
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        api_key=os.environ["OPENAI_API_KEY"],
    )


def get_weather(
    city: Annotated[str, "City name, spelled out fully"],
) -> dict:
    """Returns weather data for a given city, a dictionary with temperature and description."""
    logger.info(f"Getting weather for {city}")
    if random.random() < 0.05:
        return {
            "temperature": 72,
            "description": "Sunny",
        }
    else:
        return {
            "temperature": 60,
            "description": "Rainy",
        }


async def main():
    with llm_config:
        assistant = AssistantAgent(
            name="WeatherAgent",
            system_message="You're an informational agent. Answer questions cheerfully. Use tools when needed. "
            "When you have answered the question, end your response with TERMINATE.",
        )
        user_proxy = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or ""),
        )

    # Register tool on both agents (AG2 pattern: LLM agent decides to call, executor runs it)
    assistant.register_for_llm(description="Get weather data for a city")(get_weather)
    user_proxy.register_for_execution()(get_weather)

    result = user_proxy.initiate_chat(
        assistant,
        message="how's weather today in sf?",
    )
    print(result.chat_history[-1]["content"].replace("TERMINATE", "").strip())

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
