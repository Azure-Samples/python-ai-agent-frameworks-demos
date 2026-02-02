"""
Agent Framework MagenticOne Example - Travel Planning with Multiple Agents
"""
import asyncio
import os
from typing import cast

from agent_framework import (
    AgentRunUpdateEvent,
    ChatAgent,
    ChatMessage,
    MagenticBuilder,
    MagenticOrchestratorEvent,
    MagenticProgressLedger,
    WorkflowOutputEvent,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

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

# Create a manager agent for orchestration
manager_agent = ChatAgent(
    chat_client=client,
    instructions="You coordinate a team to complete travel planning tasks efficiently.",
    name="magentic_manager",
    description="Orchestrator that coordinates the travel planning workflow",
)

# Build the Magentic workflow
magentic_orchestrator = (
    MagenticBuilder()
    .participants([local_agent, language_agent, travel_summary_agent])
    .with_manager(
        agent=manager_agent,
        max_round_count=20,
        max_stall_count=3,
        max_reset_count=2,
    )
    .build()
)


async def main():
    # Keep track of the last message to format output nicely in streaming mode
    last_message_id: str | None = None
    output_event: WorkflowOutputEvent | None = None

    async for event in magentic_orchestrator.run_stream("Plan a half-day trip to Costa Rica"):
        if isinstance(event, AgentRunUpdateEvent):
            message_id = event.data.message_id
            if message_id != last_message_id:
                if last_message_id is not None:
                    console.print()  # Add spacing after previous message
                console.print(Rule(f"🤖 {event.executor_id}", style="bold blue"))
                last_message_id = message_id
            console.print(event.data, end="")

        elif isinstance(event, MagenticOrchestratorEvent):
            console.print()  # Ensure panel starts on a new line
            if isinstance(event.data, ChatMessage):
                # Show the plan creation in a panel
                console.print(
                    Panel(
                        Markdown(event.data.text),
                        title=f"📋 Orchestrator: {event.event_type.name}",
                        border_style="bold green",
                        padding=(1, 2),
                    )
                )
            elif isinstance(event.data, MagenticProgressLedger):
                # Show a compact progress summary in a panel
                ledger = event.data
                satisfied = "✅" if ledger.is_request_satisfied.answer else "⏳ Steps pending"
                progress = "✅" if ledger.is_progress_being_made.answer else "❌ Progress stalled"
                loop = "⚠️ Loop detected" if ledger.is_in_loop.answer else ""
                next_agent = ledger.next_speaker.answer
                instruction = ledger.instruction_or_question.answer

                status_text = f"Plan satisfied? {satisfied} | Making progress? {progress} {loop}\n\n➡️  Next step: [bold]{next_agent}[/bold]\n{instruction}"
                console.print(
                    Panel(
                        status_text,
                        title=f"📊 Orchestrator: {event.event_type.name}",
                        border_style="bold yellow",
                        padding=(1, 2),
                    )
                )
                            

        elif isinstance(event, WorkflowOutputEvent):
            output_event = event

    if output_event:
        console.print()  # Add spacing
        # The output of the Magentic workflow is a list of ChatMessages with only one final message
        output_messages = cast(list[ChatMessage], output_event.data)
        if output_messages:
            console.print(
                Panel(
                    Markdown(output_messages[-1].text),
                    title="🌎 Final Travel Plan",
                    border_style="bold green",
                    padding=(1, 2),
                )
            )

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
