import asyncio
import os

from autogen import AssistantAgent, LLMConfig, UserProxyAgent
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rich import print

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


async def main():
    with llm_config:
        assistant = AssistantAgent(
            name="assistant",
            system_message="You're an informational agent. Answer questions cheerfully.",
        )
        user_proxy = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
        )

    result = user_proxy.initiate_chat(
        assistant,
        message="Whats weather today in San Francisco?",
    )
    print(result.chat_history[-1]["content"])

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
