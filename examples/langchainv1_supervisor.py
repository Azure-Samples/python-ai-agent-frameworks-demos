import logging
import os
import random
from datetime import datetime

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from rich import print
from rich.logging import RichHandler

logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("lang_triage")

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    base_model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1",
        api_key=token_provider,
    )
elif API_HOST == "github":
    base_model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ.get("GITHUB_TOKEN"),
    )
elif API_HOST == "ollama":
    base_model = ChatOpenAI(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
    )
else:
    base_model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


# ----------------------------------------------------------------------------------
# SUB-AGENT 1: Activity planning agent
# ----------------------------------------------------------------------------------
@tool
def get_weather(city: str, date: str) -> dict:
    """Returns weather data for a given city and date."""
    logger.info(f"Getting weather for {city} on {date}")
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


@tool
def get_activities(city: str, date: str) -> list:
    """Returns a list of activities for a given city and date."""
    logger.info(f"Getting activities for {city} on {date}")
    return [
        {"name": "Hiking", "location": city},
        {"name": "Beach", "location": city},
        {"name": "Museum", "location": city},
    ]


@tool
def get_current_date() -> str:
    """Gets the current date from the system and returns as a string in format YYYY-MM-DD."""
    logger.info("Getting current date")
    return datetime.now().strftime("%Y-%m-%d")


weekend_agent = create_agent(
    model=base_model,
    system_prompt=("You help users plan their weekends and choose the best activities for the given weather." "If an activity would be unpleasant in the weather, don't suggest it." "Include the date of the weekend in your response."),
    tools=[get_weather, get_activities, get_current_date],
)


@tool
def plan_weekend(query: str) -> str:
    """Plan a weekend based on user query and return the final response."""
    logger.info("Tool: plan_weekend invoked")
    response = weekend_agent.invoke({"messages": [HumanMessage(content=query)]})
    final = response["messages"][-1].content
    return final


# ----------------------------------------------------------------------------------
# SUB-AGENT 2: Recipe planning agent
# ----------------------------------------------------------------------------------


@tool
def find_recipes(query: str) -> list[dict]:
    """Returns recipes based on a query."""
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


@tool
def check_fridge() -> list[str]:
    """Returns a list of ingredients currently in the fridge."""
    logger.info("Checking fridge for current ingredients")
    if random.random() < 0.5:
        return ["pasta", "tomato sauce", "bell peppers", "olive oil"]
    else:
        return ["tofu", "soy sauce", "broccoli", "carrots"]


meal_agent = create_agent(
    model=base_model,
    system_prompt=("You help users plan meals and choose the best recipes." "Include the ingredients and cooking instructions in your response." "Indicate what user needs to buy from store when their fridge is missing ingredients."),
    tools=[find_recipes, check_fridge],
)


@tool
def plan_meal(query: str) -> str:
    """Plan a meal based on user query and return the final response."""
    logger.info("Tool: plan_meal invoked")
    response = meal_agent.invoke({"messages": [HumanMessage(content=query)]})
    final = response["messages"][-1].content
    return final


# ----------------------------------------------------------------------------------
# SUPERVISOR AGENT: Manages the sub-agents
# ----------------------------------------------------------------------------------
supervisor_agent = create_agent(
    model=base_model,
    system_prompt=("You are a supervisor, managing an activity planning agent and recipe planning agent." "Assign work to them as needed in order to answer user's question."),
    tools=[plan_weekend, plan_meal],
)


def main():
    response = supervisor_agent.invoke({"messages": [{"role": "user", "content": "my kids want pasta for dinner"}]})
    latest_message = response["messages"][-1]
    print(latest_message.content)


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
