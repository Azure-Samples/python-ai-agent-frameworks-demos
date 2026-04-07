# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
from dataclasses import dataclass, field

from agent_framework import (
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentRunResponse,
    ChatAgent,
    ChatMessage,
    Executor,
    RequestInfoEvent,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowOutputEvent,
    handler,
    response_handler,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from typing_extensions import Never

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

"""
Sample: Human-in-the-loop workflow

Pipeline layout:
writer_agent -> Coordinator -> writer_agent
-> Coordinator -> final_editor_agent -> Coordinator -> output

The writer agent drafts content based on a user-provided topic. A custom executor
packages the draft and emits a RequestInfoEvent so a human can comment, then replays the human
guidance back into the conversation before the final editor agent produces the polished output.

Demonstrates:
- Capturing the writer's output for human review.
- Human-in-the-loop feedback that can approve or request revisions.
"""


@dataclass
class DraftFeedbackRequest:
    """Payload sent for human review."""

    prompt: str = ""
    draft_text: str = ""
    conversation: list[ChatMessage] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class Coordinator(Executor):
    """Bridge between the writer agent, human feedback, and final editor."""

    def __init__(self, id: str, writer_id: str, final_editor_id: str) -> None:
        super().__init__(id)
        self.writer_id = writer_id
        self.final_editor_id = final_editor_id

    @handler
    async def on_writer_response(
        self,
        draft: AgentExecutorResponse,
        ctx: WorkflowContext[Never, AgentRunResponse],
    ) -> None:
        """Handle responses from the other two agents in the workflow."""
        if draft.executor_id == self.final_editor_id:
            # Final editor response; yield output directly.
            await ctx.yield_output(draft.agent_run_response)
            return

        # Writer agent response; request human feedback.
        # Preserve the full conversation so the final editor
        # can see tool traces and the initial prompt.
        conversation: list[ChatMessage]
        if draft.full_conversation is not None:
            conversation = list(draft.full_conversation)
        else:
            conversation = list(draft.agent_run_response.messages)
        draft_text = draft.agent_run_response.text.strip()
        if not draft_text:
            draft_text = "No draft text was produced."

        prompt = (
            "Review the draft from the writer and provide a short directional note "
            "(tone tweaks, must-have detail, target audience, etc.). "
            "Keep it under 30 words."
        )
        await ctx.request_info(
            request_data=DraftFeedbackRequest(prompt=prompt, draft_text=draft_text, conversation=conversation),
            response_type=str,
        )

    @response_handler
    async def on_human_feedback(
        self,
        original_request: DraftFeedbackRequest,
        feedback: str,
        ctx: WorkflowContext[AgentExecutorRequest],
    ) -> None:
        note = feedback.strip()
        if note.lower() == "approve":
            # Human approved the draft as-is; forward it unchanged.
            await ctx.send_message(
                AgentExecutorRequest(
                    messages=original_request.conversation
                    + [ChatMessage(Role.USER, text="The draft is approved as-is.")],
                    should_respond=True,
                ),
                target_id=self.final_editor_id,
            )
            return

        # Human provided feedback; prompt the writer to revise.
        conversation: list[ChatMessage] = list(original_request.conversation)
        instruction = (
            "A human reviewer shared the following guidance:\n"
            f"{note or 'No specific guidance provided.'}\n\n"
            "Rewrite the draft from the previous assistant message into a polished final version. "
            "Keep the response under 120 words and reflect any requested tone adjustments."
        )
        conversation.append(ChatMessage(Role.USER, text=instruction))
        await ctx.send_message(
            AgentExecutorRequest(messages=conversation, should_respond=True), target_id=self.writer_id
        )


def create_writer_agent() -> ChatAgent:
    """Creates a writer agent."""
    return client.create_agent(
        name="writer_agent",
        instructions=(
            "You are an excellent content writer. "
            "Create clear, engaging content based on the user's request. "
            "Focus on clarity, accuracy, and proper structure. "
            "Keep your drafts concise (3-5 sentences)."
        ),
    )


def create_final_editor_agent() -> ChatAgent:
    """Creates a final editor agent."""
    return client.create_agent(
        name="final_editor_agent",
        instructions=(
            "You are an editor who polishes marketing copy after human approval. "
            "Correct any legal or factual issues. Return the final version even if no changes are made. "
        ),
    )


def build_workflow():
    """Build and return the workflow."""
    return (
        WorkflowBuilder()
        .register_agent(create_writer_agent, name="writer_agent")
        .register_agent(create_final_editor_agent, name="final_editor_agent")
        .register_executor(
            lambda: Coordinator(
                id="coordinator",
                writer_id="writer_agent",
                final_editor_id="final_editor_agent",
            ),
            name="coordinator",
        )
        .set_start_executor("writer_agent")
        .add_edge("writer_agent", "coordinator")
        .add_edge("coordinator", "writer_agent")
        .add_edge("final_editor_agent", "coordinator")
        .add_edge("coordinator", "final_editor_agent")
        .build()
    )


async def main() -> None:
    """Run the workflow and bridge human feedback between two agents."""

    # Build the workflow.
    workflow = build_workflow()

    # Prompt user for what to write about
    print("What would you like the writer to create content about?")
    topic = input("Topic: ").strip()

    print(
        "\nInteractive mode. When prompted, provide a short feedback note for the editor.",
        flush=True,
    )

    pending_responses: dict[str, str] | None = None
    completed = False
    initial_run = True

    while not completed:
        if initial_run:
            stream = workflow.run_stream(f"Write a short piece about: {topic}")
            initial_run = False
        elif pending_responses is not None:
            stream = workflow.send_responses_streaming(pending_responses)
            pending_responses = None
        else:
            break

        requests: list[tuple[str, DraftFeedbackRequest]] = []

        async for event in stream:
            if isinstance(event, RequestInfoEvent) and isinstance(event.data, DraftFeedbackRequest):
                # Stash the request so we can prompt the human after the stream completes.
                requests.append((event.request_id, event.data))
            elif isinstance(event, WorkflowOutputEvent):
                response = event.data
                print("\n===== Final output =====")
                final_text = getattr(response, "text", str(response))
                print(final_text.strip())
                completed = True

        if requests and not completed:
            responses: dict[str, str] = {}
            for request_id, request in requests:
                print("\n----- Writer draft -----")
                print(request.draft_text.strip())
                print("\nProvide guidance for the editor (or 'approve' to accept the draft).")
                answer = input("Human feedback: ").strip()  # noqa: ASYNC250
                if answer.lower() == "exit":
                    print("Exiting...")
                    return
                responses[request_id] = answer
            pending_responses = responses

    print("Workflow complete.")

    # Close the async credential if it was created
    if async_credential is not None:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
