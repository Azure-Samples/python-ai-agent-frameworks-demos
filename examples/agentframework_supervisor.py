import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from pydantic import Field
from rich import print
from rich.logging import RichHandler

# Setup logging
handler = RichHandler(show_path=False, rich_tracebacks=True, show_level=False)
logging.basicConfig(level=logging.WARNING, handlers=[handler], force=True, format="%(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure OpenAI client based on environment
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

async_credential = None
if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatClient(
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/v1/",
        api_key=token_provider,
        model_id=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
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
    client = OpenAIChatClient(api_key=os.environ["OPENAI_API_KEY"], model_id=os.environ.get("OPENAI_MODEL", "gpt-4o"))

# ----------------------------------------------------------------------------------
# Sub-agent 1 tools: weekend planning
# ----------------------------------------------------------------------------------


def get_weather(
    city: Annotated[str, Field(description="The city to get the weather for.")],
    date: Annotated[str, Field(description="The date to get weather for in format YYYY-MM-DD.")],
) -> dict:
    """Returns weather data for a given city and date."""
    logger.info(f"Getting weather for {city} on {date}")
    if random.random() < 0.05:
        return {"temperature": 72, "description": "Sunny"}
    else:
        return {"temperature": 60, "description": "Rainy"}


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
    """Gets the current date from the system (YYYY-MM-DD)."""
    logger.info("Getting current date")
    return datetime.now().strftime("%Y-%m-%d")


weekend_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You help users plan their weekends and choose the best activities for the given weather. "
        "If an activity would be unpleasant in the weather, don't suggest it. "
        "Include the date of the weekend in your response."
    ),
    tools=[get_weather, get_activities, get_current_date],
)


async def plan_weekend(query: str) -> str:
    """Plan a weekend based on user query and return the final response."""
    logger.info("Tool: plan_weekend invoked")
    response = await weekend_agent.run(query)
    return response.text


# ----------------------------------------------------------------------------------
# Sub-agent 2 tools: meal planning
# ----------------------------------------------------------------------------------


def find_recipes(
    query: Annotated[str, Field(description="User query or desired meal/ingredient")],
) -> list[dict]:
    """Returns recipes (JSON) based on a query."""
    logger.info(f"Finding recipes for '{query}'")
    if "pasta" in query.lower():
        recipes = [
            {
                "title": "Pasta Primavera",
                "ingredients": ["pasta", "vegetables", "olive oil"],
                "steps": ["Cook pasta.", "Sauté vegetables."],
            }
        ]
    elif "tofu" in query.lower():
        recipes = [
            {
                "title": "Tofu Stir Fry",
                "ingredients": ["tofu", "soy sauce", "vegetables"],
                "steps": ["Cube tofu.", "Stir fry veggies."],
            }
        ]
    else:
        recipes = [
            {
                "title": "Grilled Cheese Sandwich",
                "ingredients": ["bread", "cheese", "butter"],
                "steps": ["Butter bread.", "Place cheese between slices.", "Grill until golden brown."],
            }
        ]
    return recipes


def check_fridge() -> list[str]:
    """Returns a JSON list of ingredients currently in the fridge."""
    logger.info("Checking fridge for current ingredients")
    if random.random() < 0.5:
        items = ["pasta", "tomato sauce", "bell peppers", "olive oil"]
    else:
        items = ["tofu", "soy sauce", "broccoli", "carrots"]
    return items


meal_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You help users plan meals and choose the best recipes. "
        "Include the ingredients and cooking instructions in your response. "
        "Indicate what the user needs to buy from the store when their fridge is missing ingredients."
    ),
    tools=[find_recipes, check_fridge],
)


async def plan_meal(query: str) -> str:
    """Plan a meal based on user query and return the final response."""
    logger.info("Tool: plan_meal invoked")
    response = await meal_agent.run(query)
    return response.text


# ----------------------------------------------------------------------------------
# Supervisor agent orchestrating sub-agents
# ----------------------------------------------------------------------------------

supervisor_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You are a supervisor managing two specialist agents: a weekend planning agent and a meal planning agent. "
        "Break down the user's request, decide which specialist (or both) to call via the available tools, "
        "and then synthesize a final helpful answer. When invoking a tool, provide clear, concise queries."
    ),
    tools=[plan_weekend, plan_meal],
)


async def main():
    user_query = "my kids want pasta for dinner"
    response = await supervisor_agent.run(user_query)
    print(response.text)

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
