import asyncio
import logging
import os
import random
from datetime import datetime
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
    city: Annotated[str, "The city to get the weather for."],
    date: Annotated[str, "The date to get weather for in format YYYY-MM-DD."],
) -> dict:
    """Returns weather data for a given city and date."""
    logger.info(f"Getting weather for {city} on {date}")
    if random.random() < 0.05:
        return {"temperature": 72, "description": "Sunny"}
    else:
        return {"temperature": 60, "description": "Rainy"}


def get_activities(
    city: Annotated[str, "The city to get activities for."],
    date: Annotated[str, "The date to get activities for in format YYYY-MM-DD."],
) -> list[dict]:
    """Returns a list of activities for a given city and date."""
    logger.info(f"Getting activities for {city} on {date}")
    return [
        {"name": "Hiking", "location": city},
        {"name": "Beach", "location": city},
        {"name": "Museum", "location": city},
    ]


def get_current_date() -> str:
    """Gets the current date from the system (YYYY-MM-DD)."""
    logger.info("Getting current date")
    return datetime.now().strftime("%Y-%m-%d")


async def main():
    with llm_config:
        assistant = AssistantAgent(
            name="WeekendPlanner",
            system_message=(
                "You help users plan their weekends and choose the best activities for the given weather. "
                "If an activity would be unpleasant in the weather, don't suggest it. "
                "Include the date of the weekend in your response. "
                "When you have provided the full plan, end your response with TERMINATE."
            ),
        )
        user_proxy = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or ""),
        )

    # Register all tools on both agents
    for tool_fn in [get_weather, get_activities, get_current_date]:
        assistant.register_for_llm()(tool_fn)
        user_proxy.register_for_execution()(tool_fn)

    result = user_proxy.initiate_chat(
        assistant,
        message="what can I do for funzies this weekend in Seattle?",
    )
    print(result.chat_history[-1]["content"].replace("TERMINATE", "").strip())

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
