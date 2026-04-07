import os

import openai
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Setup the OpenAI client to use Azure OpenAI
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "azure")

if API_HOST == "azure":
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = openai.OpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1",
        api_key=token_provider,
    )
    MODEL_NAME = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
elif API_HOST == "ollama":
    client = openai.OpenAI(
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
    )
    MODEL_NAME = os.environ["OLLAMA_MODEL"]

tools = [
    {
        "type": "function",
        "name": "lookup_weather",
        "description": "Lookup the weather for a given city name or zip code.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "The city name",
                },
                "zip_code": {
                    "type": "string",
                    "description": "The zip code",
                },
            },
            "additionalProperties": False,
        },
    }
]

response = client.responses.create(
    model=MODEL_NAME,
    input=[
        {"role": "system", "content": "You're a weather chatbot"},
        {"role": "user", "content": "whats the weather in NYC?"},
    ],
    tools=tools,
    store=False,
)

print(f"Response from {MODEL_NAME} on {API_HOST}: \n")
for item in response.output:
    if item.type == "function_call":
        print(item.name)
        print(item.arguments)
