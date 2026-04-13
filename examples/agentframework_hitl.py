# Copyright (c) Microsoft. All rights reserved.

# NOTE: This example intentionally does not use tools in the HITL workflow.
# Tools + HITL causes duplicate item ID errors with the Responses API.
# See https://github.com/microsoft/agent-framework/issues/3295
# For a tools example, see agentframework_tools.py.

import asyncio
import os
from collections.abc import AsyncIterable
from dataclasses import dataclass, field

from agent_framework import (
    Agent,
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentResponse,
    AgentResponseUpdate,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    handler,
    response_handler,
)
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from typing_extensions import Never

# Configure OpenAI client based on environment
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "azure")
async_credential = None

if API_HOST == "azure":
    async_credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(async_credential, "https://cognitiveservices.azure.com/.default")
    client = OpenAIChatClient(
        base_url=f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/v1/",
        api_key=token_provider,
        model=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
    )
elif API_HOST == "ollama":
    client = OpenAIChatClient(
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
        model=os.environ.get("OLLAMA_MODEL", "gemma4:e4b"),
    )
else:
    client = OpenAIChatClient(api_key=os.environ["OPENAI_API_KEY"], model=os.environ.get("OPENAI_MODEL", "gpt-4o"))

"""
Sample: Agents with human feedback

Pipeline layout:
writer_agent -> Coordinator -> writer_agent
-> Coordinator -> final_editor_agent -> Coordinator -> output

The writer agent drafts marketing copy. A custom executor packages the draft
and emits a request_info event so a human can comment, then relays the human
guidance back into the conversation before the final editor agent produces
the polished output.

Demonstrates:
- Capturing the writer's output for human review.
- Streaming AgentResponseUpdate updates alongside human-in-the-loop pauses.

Prerequisites:
- Azure OpenAI configured with the required environment variables.
- Authentication via azure-identity. Run `az login` before running.
"""


@dataclass
class DraftFeedbackRequest:
    """Payload sent for human review."""

    prompt: str = ""
    draft_text: str = ""
    conversation: list[Message] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]


class Coordinator(Executor):
    """Bridge between the writer agent, human feedback, and the final editor."""

    def __init__(self, id: str, writer_name: str, final_editor_name: str) -> None:
        super().__init__(id)
        self.writer_name = writer_name
        self.final_editor_name = final_editor_name

    @handler
    async def on_writer_response(
        self,
        draft: AgentExecutorResponse,
        ctx: WorkflowContext[Never, AgentResponse],
    ) -> None:
        """Handle responses from the writer and final editor agents."""
        if draft.executor_id == self.final_editor_name:
            # Final editor response; yield output directly.
            await ctx.yield_output(draft.agent_response)
            return

        # Writer agent response; request human feedback.
        # Preserve the full conversation so the final editor
        # can see tool traces and the initial prompt.
        conversation = list(draft.full_conversation)
        draft_text = draft.agent_response.text.strip()
        if not draft_text:
            draft_text = "No draft was produced."

        prompt = (
            "Review the writer's draft and share a short directional note "
            "(tone tweaks, must-have details, target audience, etc.). "
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
        """Process human feedback and forward to the appropriate agent."""
        note = feedback.strip()
        if note.lower() == "approve":
            # Human approved the draft as-is; forward it unchanged.
            await ctx.send_message(
                AgentExecutorRequest(
                    messages=original_request.conversation
                    + [Message("user", contents=["The draft is approved as-is."])],
                    should_respond=True,
                ),
                target_id=self.final_editor_name,
            )
            return

        # Human provided feedback; prompt the writer to revise.
        conversation: list[Message] = list(original_request.conversation)
        instruction = (
            "A human reviewer shared the following guidance:\n"
            f"{note or 'No specific guidance provided.'}\n\n"
            "Rewrite the draft from the previous assistant message into a polished final version. "
            "Keep the response under 120 words and reflect any requested tone adjustments."
        )
        conversation.append(Message("user", contents=[instruction]))
        await ctx.send_message(
            AgentExecutorRequest(messages=conversation, should_respond=True), target_id=self.writer_name
        )


async def process_event_stream(stream: AsyncIterable[WorkflowEvent]) -> dict[str, str] | None:
    """Process events from the workflow stream to capture human feedback requests."""
    last_author: str | None = None

    requests: list[tuple[str, DraftFeedbackRequest]] = []
    async for event in stream:
        if event.type == "request_info" and isinstance(event.data, DraftFeedbackRequest):
            requests.append((event.request_id, event.data))
        elif event.type == "output":
            if isinstance(event.data, AgentResponseUpdate):
                update = event.data
                author = update.author_name
                if author != last_author:
                    if last_author is not None:
                        print()
                    print(f"{author}: {update.text}", end="", flush=True)
                    last_author = author
                else:
                    print(update.text, end="", flush=True)
            elif isinstance(event.data, AgentResponse):
                print(f"\n\n✅ Final output:\n{event.data.text.strip()}")

    if requests:
        responses: dict[str, str] = {}
        for request_id, request in requests:
            print("\n\n----- Writer draft -----")
            print(request.draft_text.strip())
            print("\nProvide guidance for the editor (or 'approve' to accept the draft).")
            answer = input("Human feedback: ").strip()  # noqa: ASYNC250
            if answer.lower() == "exit":
                print("Exiting...")
                return None
            responses[request_id] = answer
        return responses
    return None


async def main() -> None:
    """Run the workflow and bridge human feedback between two agents."""
    writer_agent = Agent(
        client=client,
        name="writer_agent",
        instructions="You are a marketing writer. Write clear, engaging copy.",
    )

    final_editor_agent = Agent(
        client=client,
        name="final_editor_agent",
        instructions=(
            "You are an editor who polishes marketing copy after human approval. "
            "Correct any legal or factual issues. Return the final version even if no changes are needed."
        ),
    )

    coordinator = Coordinator(
        id="coordinator",
        writer_name=writer_agent.name,  # type: ignore
        final_editor_name=final_editor_agent.name,  # type: ignore
    )

    workflow = (
        WorkflowBuilder(start_executor=writer_agent)
        .add_edge(writer_agent, coordinator)
        .add_edge(coordinator, writer_agent)
        .add_edge(final_editor_agent, coordinator)
        .add_edge(coordinator, final_editor_agent)
        .build()
    )

    print(
        "Interactive mode. When prompted, provide a short feedback note for the editor.",
        flush=True,
    )

    stream = workflow.run(
        "Create a short launch blurb for the LumenX desk lamp. Emphasize adjustability and warm lighting.",
        stream=True,
    )

    pending_responses = await process_event_stream(stream)
    while pending_responses is not None:
        stream = workflow.run(stream=True, responses=pending_responses)
        pending_responses = await process_event_stream(stream)

    print("\nWorkflow complete.")

    if async_credential:
        await async_credential.close()


if __name__ == "__main__":
    asyncio.run(main())
