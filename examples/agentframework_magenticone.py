"""
Agent Framework MagenticOne Example - Travel Planning with Multiple Agents
pip install agent-framework-orchestrations==1.0.0b260212
"""
import asyncio
import json
import os
from typing import cast

from agent_framework import Agent, AgentResponseUpdate, Message, WorkflowEvent
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import MagenticBuilder, MagenticProgressLedger
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

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

# Initialize rich console
console = Console()

# Create the agents
local_agent = Agent(
    client=client,
    instructions=(
        "You are a helpful assistant that can suggest authentic and interesting local activities "
        "or places to visit for a user and can utilize any context information provided."
    ),
    name="local_agent",
    description="A local assistant that can suggest local activities or places to visit.",
)

language_agent = Agent(
    client=client,
    instructions=(
        "You are a helpful assistant that can review travel plans, providing feedback on important/critical "
        "tips about how best to address language or communication challenges for the given destination. "
        "If the plan already includes language tips, you can mention that the plan is satisfactory, with rationale."
    ),
    name="language_agent",
    description="A helpful assistant that can provide language tips for a given destination.",
)

travel_summary_agent = Agent(
    client=client,
    instructions=(
        "You are a helpful assistant that can take in all of the suggestions and advice from the other agents "
        "and provide a detailed final travel plan. You must ensure that the final plan is integrated and complete. "
        "YOUR FINAL RESPONSE MUST BE THE COMPLETE PLAN. Provide a comprehensive summary when all perspectives "
        "from other agents have been integrated."
    ),
    name="travel_summary_agent",
    description="A helpful assistant that can summarize the travel plan.",
)

manager_agent = Agent(
    client=client,
    description="Orchestrator that coordinates the research and coding workflow",
    instructions="You coordinate a team to complete complex tasks efficiently.",
    name="manager_agent",
)

magentic_orchestrator = MagenticBuilder(
        participants=[local_agent, language_agent, travel_summary_agent],
        manager_agent=manager_agent,
        max_round_count=20,
        max_stall_count=3,
        max_reset_count=2,
).build()


def handle_event(event: WorkflowEvent, last_message_id: str | None) -> str | None:
    """Handle streaming events and return updated last_message_id."""
    if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
        message_id = event.data.message_id
        if message_id != last_message_id:
            if last_message_id is not None:
                console.print()
            console.print(f"🤖 {event.executor_id}:", end=" ")
            last_message_id = message_id
        console.print(event.data, end="")
        return last_message_id

    elif event.type == "magentic_orchestrator":
        console.print()
        emoji = "✅" if event.data.event_type.name == "PROGRESS_LEDGER_UPDATED" else "🦠"
        if isinstance(event.data.content, MagenticProgressLedger):
            console.print(
                Panel(
                    json.dumps(event.data.content.to_dict(), indent=2),
                    title=f"{emoji} Orchestrator: {event.data.event_type.name}",
                    border_style="bold yellow",
                    padding=(1, 2),
                )
            )
        elif hasattr(event.data.content, "text"):
            console.print(
                Panel(
                    Markdown(event.data.content.text),
                    title=f"{emoji} Orchestrator: {event.data.event_type.name}",
                    border_style="bold green",
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    Markdown(str(event.data.content)),
                    title=f"{emoji} Orchestrator: {event.data.event_type.name}",
                    border_style="bold green",
                    padding=(1, 2),
                )
            )

    return last_message_id


def print_final_result(output_event: WorkflowEvent | None) -> None:
    """Print the final travel plan."""
    if output_event:
        output_messages = cast(list[Message], output_event.data)
        console.print(
            Panel(
                Markdown(output_messages[-1].text),
                title="🌎 Final Travel Plan",
                border_style="bold green",
                padding=(1, 2),
            )
        )


async def main():
    last_message_id: str | None = None
    output_event: WorkflowEvent | None = None

    async for event in magentic_orchestrator.run("Plan a half-day trip to Costa Rica", stream=True):
        last_message_id = handle_event(event, last_message_id)
        if event.type == "output" and not isinstance(event.data, AgentResponseUpdate):
            output_event = event

    print_final_result(output_event)

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
