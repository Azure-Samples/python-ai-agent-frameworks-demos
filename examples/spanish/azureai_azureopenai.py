import logging
import os

import azure.identity
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
load_dotenv(override=True)

client = ChatCompletionsClient(
    endpoint=f'{os.environ["AZURE_OPENAI_ENDPOINT"]}/openai/deployments/{os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]}',
    credential=azure.identity.AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID")),
    credential_scopes=["https://cognitiveservices.azure.com/.default"],
    api_version=os.environ["AZURE_OPENAI_VERSION"],
)

response = client.complete(
    messages=[
        SystemMessage(content="Eres un asistente útil."),
        UserMessage(content="¿Cuál es la capital de Francia?"),
    ],
    model=os.environ["AZURE_OPENAI_CHAT_MODEL"],
)
print(response.choices[0].message.content)
