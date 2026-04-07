import os

import openai
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

# Configuración del cliente OpenAI para usar Azure OpenAI
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
        "description": "Consulta el clima para una ciudad o código postal dado.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "El nombre de la ciudad",
                },
                "zip_code": {
                    "type": "string",
                    "description": "El código postal",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "lookup_movies",
        "description": "Consulta películas en cartelera en una ciudad o código postal dado.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "El nombre de la ciudad",
                },
                "zip_code": {
                    "type": "string",
                    "description": "El código postal",
                },
            },
            "additionalProperties": False,
        },
    },
]

response = client.responses.create(
    model=MODEL_NAME,
    input=[
        {"role": "system", "content": "Eres un chatbot de turismo."},
        {
            "role": "user",
            "content": (
                "¿está lloviendo lo suficiente en Cuenca, Ecuador"
                " como para ir a ver películas y cuáles están en cartelera?"
            ),
        },
    ],
    tools=tools,
    tool_choice="auto",
    store=False,
)

print(f"Respuesta de {MODEL_NAME} en {API_HOST}: \n")
for item in response.output:
    if item.type == "function_call":
        print(item.name)
        print(item.arguments)
