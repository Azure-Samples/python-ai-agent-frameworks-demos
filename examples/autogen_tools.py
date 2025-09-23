import asyncio
import logging
import os
import random
from datetime import datetime

import azure.identity
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from rich.logging import RichHandler

# Setup logging with rich
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("weekend_planner")


# Setup the client to use either Azure OpenAI or GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")


if API_HOST == "github":
    client = OpenAIChatCompletionClient(model=os.getenv("GITHUB_MODEL", "gpt-4o"), api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com", parallel_tool_calls=False)
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatCompletionClient(model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], api_key=token_provider, base_url=os.environ["AZURE_OPENAI_ENDPOINT"], parallel_tool_calls=False)


def get_weather(city: str) -> str:
    logger.info(f"Getting weather for {city}")
    if random.random() < 0.05:
        return {
            "city": city,
            "temperature": 72,
            "description": "Sunny",
        }
    else:
        return {
            "city": city,
            "temperature": 60,
            "description": "Rainy",
        }


def get_activities(city: str, date: str) -> list:
    logger.info(f"Getting activities for {city} on {date}")
    return [
        {"name": "Hiking", "location": city},
        {"name": "Beach", "location": city},
        {"name": "Museum", "location": city},
    ]


def get_current_date() -> str:
    logger.info("Getting current date")
    return datetime.now().strftime("%Y-%m-%d")


agent = AssistantAgent(
    "weekend_planner",
    model_client=client,
    tools=[get_weather, get_activities, get_current_date],
    system_message="You help users plan their weekends and choose the best activities for the given weather. If an activity would be unpleasant in the weather, don't suggest it. Include the date of the weekend in your response.",
)


async def main() -> None:
    team = RoundRobinGroupChat([agent], termination_condition=TextMessageTermination(agent.name))

    async for task_result in team.run_stream(task="what can I do for funzies this weekend in Seattle?"):
        logger.debug("%s: %s", type(task_result).__name__, task_result)
    print(task_result.messages[-1].content)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
