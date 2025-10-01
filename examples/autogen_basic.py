import asyncio
import os

import azure.identity
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

# Setup the client to use either Azure OpenAI or GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")
if API_HOST == "github":
    client = OpenAIChatCompletionClient(model=os.getenv("GITHUB_MODEL", "gpt-4o"), api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatCompletionClient(model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], api_key=token_provider, base_url=os.environ["AZURE_OPENAI_ENDPOINT"])


agent = AssistantAgent(
    "spanish_tutor",
    model_client=client,
    system_message="You are a Spanish tutor. Help the user learn Spanish. ONLY respond in Spanish.",
)


async def main() -> None:
    response = await agent.on_messages(
        [TextMessage(content="hii how are you?", source="user")],
        cancellation_token=CancellationToken(),
    )
    print(response.chat_message.content)


if __name__ == "__main__":
    asyncio.run(main())
