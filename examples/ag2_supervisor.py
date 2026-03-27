import asyncio
import logging
import os
import random
from datetime import datetime
from typing import Annotated

from autogen import AssistantAgent, GroupChat, GroupChatManager, LLMConfig, UserProxyAgent
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

# ----------------------------------------------------------------------------------
# Weekend planning tools
# ----------------------------------------------------------------------------------


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


# ----------------------------------------------------------------------------------
# Meal planning tools
# ----------------------------------------------------------------------------------


def find_recipes(
    query: Annotated[str, "User query or desired meal/ingredient"],
) -> list[dict]:
    """Returns recipes (JSON) based on a query."""
    logger.info(f"Finding recipes for '{query}'")
    if "pasta" in query.lower():
        return [
            {
                "title": "Pasta Primavera",
                "ingredients": ["pasta", "vegetables", "olive oil"],
                "steps": ["Cook pasta.", "Sauté vegetables."],
            }
        ]
    elif "tofu" in query.lower():
        return [
            {
                "title": "Tofu Stir Fry",
                "ingredients": ["tofu", "soy sauce", "vegetables"],
                "steps": ["Cube tofu.", "Stir fry veggies."],
            }
        ]
    else:
        return [
            {
                "title": "Grilled Cheese Sandwich",
                "ingredients": ["bread", "cheese", "butter"],
                "steps": ["Butter bread.", "Place cheese between slices.", "Grill until golden brown."],
            }
        ]


def check_fridge() -> list[str]:
    """Returns a JSON list of ingredients currently in the fridge."""
    logger.info("Checking fridge for current ingredients")
    if random.random() < 0.5:
        return ["pasta", "tomato sauce", "bell peppers", "olive oil"]
    else:
        return ["tofu", "soy sauce", "broccoli", "carrots"]


async def main():
    with llm_config:
        # Specialist agents
        weekend_planner = AssistantAgent(
            name="WeekendPlanner",
            system_message=(
                "You help users plan their weekends and choose the best activities for the given weather. "
                "If an activity would be unpleasant in the weather, don't suggest it. "
                "Include the date of the weekend in your response. "
                "When you have fully answered, end your response with TERMINATE."
            ),
        )
        meal_planner = AssistantAgent(
            name="MealPlanner",
            system_message=(
                "You help users plan meals and choose the best recipes. "
                "Include the ingredients and cooking instructions in your response. "
                "Indicate what the user needs to buy from the store when their fridge is missing ingredients. "
                "When you have fully answered, end your response with TERMINATE."
            ),
        )
        user_proxy = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            is_termination_msg=lambda msg: "TERMINATE" in (msg.get("content") or ""),
        )

    # Register weekend planning tools
    for tool_fn in [get_weather, get_activities, get_current_date]:
        weekend_planner.register_for_llm()(tool_fn)
        user_proxy.register_for_execution()(tool_fn)

    # Register meal planning tools
    for tool_fn in [find_recipes, check_fridge]:
        meal_planner.register_for_llm()(tool_fn)
        user_proxy.register_for_execution()(tool_fn)

    # GroupChat — AG2's multi-agent orchestration with automatic speaker selection
    groupchat = GroupChat(
        agents=[user_proxy, weekend_planner, meal_planner],
        messages=[],
        max_round=12,
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    result = user_proxy.initiate_chat(
        manager,
        message="my kids want pasta for dinner, and plan a fun weekend in Seattle",
    )
    print(result.chat_history[-1]["content"].replace("TERMINATE", "").strip())

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    asyncio.run(main())
