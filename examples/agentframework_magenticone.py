"""
Agent Framework MagenticOne Example - Travel Planning with Multiple Agents
"""
import asyncio
import os

from agent_framework import (
    ChatAgent,
    MagenticAgentDeltaEvent,
    MagenticBuilder,
    MagenticCallbackEvent,
    MagenticCallbackMode,
    MagenticOrchestratorMessageEvent,
    WorkflowOutputEvent,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Setup the client to use either Azure OpenAI or GitHub Models
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

# Create the agents
local_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You are a helpful assistant that can suggest authentic and interesting local activities "
        "or places to visit for a user and can utilize any context information provided."
    ),
    name="local_agent",
    description="A local assistant that can suggest local activities or places to visit.",
)

language_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You are a helpful assistant that can review travel plans, providing feedback on important/critical "
        "tips about how best to address language or communication challenges for the given destination. "
        "If the plan already includes language tips, you can mention that the plan is satisfactory, with rationale."
    ),
    name="language_agent",
    description="A helpful assistant that can provide language tips for a given destination.",
)

travel_summary_agent = ChatAgent(
    chat_client=client,
    instructions=(
        "You are a helpful assistant that can take in all of the suggestions and advice from the other agents "
        "and provide a detailed final travel plan. You must ensure that the final plan is integrated and complete. "
        "YOUR FINAL RESPONSE MUST BE THE COMPLETE PLAN. Provide a comprehensive summary when all perspectives "
        "from other agents have been integrated."
    ),
    name="travel_summary_agent",
    description="A helpful assistant that can summarize the travel plan.",
)


# Event callback for streaming output
async def on_event(event: MagenticCallbackEvent) -> None:
    if isinstance(event, MagenticOrchestratorMessageEvent):
        print(f"[ORCHESTRATOR]: {event.message.text}")
    elif isinstance(event, MagenticAgentDeltaEvent):
        print(event.text, end="")


magentic_orchestrator = (
    MagenticBuilder()
    .participants(
        local_agent=local_agent,
        language_agent=language_agent,
        travel_summary_agent=travel_summary_agent,
    )
    .on_event(on_event, mode=MagenticCallbackMode.STREAMING)
    .with_standard_manager(
        chat_client=client,
        max_round_count=20,
        max_stall_count=3,
        max_reset_count=2,
    )
    .build()
)


async def main():
    async for event in magentic_orchestrator.run_stream("Plan a 3 day trip to Egypt"):
        if isinstance(event, WorkflowOutputEvent):
            final_result = event.data
            print(final_result.text)


if __name__ == "__main__":
    asyncio.run(main())
