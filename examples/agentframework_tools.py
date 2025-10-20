import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field
from rich import print
from rich.logging import RichHandler

# Setup logging with rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("weekend_planner")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    client = AzureOpenAIChatClient(
        credential=DefaultAzureCredential(),
        deployment_name=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_version=os.environ.get("AZURE_OPENAI_VERSION"),
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
    client = OpenAIChatClient(
        api_key=os.environ.get("OPENAI_API_KEY"), model_id=os.environ.get("OPENAI_MODEL", "gpt-4o")
    )


def get_weather(
    city: Annotated[str, Field(description="The city to get the weather for.")],
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


def get_activities(
    city: Annotated[str, Field(description="The city to get activities for.")],
    date: Annotated[str, Field(description="The date to get activities for in format YYYY-MM-DD.")],
) -> list[dict]:
    """Returns a list of activities for a given city and date."""
    logger.info(f"Getting activities for {city} on {date}")
    return [
        {"name": "Hiking", "location": city},
        {"name": "Beach", "location": city},
        {"name": "Museum", "location": city},
    ]


def get_current_date() -> str:
    """Gets the current date from the system and returns as a string in format YYYY-MM-DD."""
    logger.info("Getting current date")
    return datetime.now().strftime("%Y-%m-%d")


agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You help users plan their weekends and choose the best activities for the given weather. "
        "If an activity would be unpleasant in weather, don't suggest it. Include date of the weekend in response."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


async def main():
    response = await agent.run("hii what can I do this weekend in San Francisco?")
    print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
