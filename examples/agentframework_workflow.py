# pip install agent-framework-devui==1.0.0b251016
import os
from typing import Any

from agent_framework import AgentExecutorResponse, WorkflowBuilder
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from pydantic import BaseModel

# Configure OpenAI client based on environment
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

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


# Define structured output for review results
class ReviewResult(BaseModel):
    """Review evaluation with scores and feedback."""

    score: int  # Overall quality score (0-100)
    feedback: str  # Concise, actionable feedback
    clarity: int  # Clarity score (0-100)
    completeness: int  # Completeness score (0-100)
    accuracy: int  # Accuracy score (0-100)
    structure: int  # Structure score (0-100)


# Condition function: route to editor if score < 80
def needs_editing(message: Any) -> bool:
    """Check if content needs editing based on review score."""
    if not isinstance(message, AgentExecutorResponse):
        return False
    try:
        review = ReviewResult.model_validate_json(message.agent_run_response.text)
        return review.score < 80
    except Exception:
        return False


# Condition function: content is approved (score >= 80)
def is_approved(message: Any) -> bool:
    """Check if content is approved (high quality)."""
    if not isinstance(message, AgentExecutorResponse):
        return True
    try:
        review = ReviewResult.model_validate_json(message.agent_run_response.text)
        return review.score >= 80
    except Exception:
        return True


# Create Writer agent - generates content
def create_writer():
    return client.create_agent(
        name="Writer",
        instructions=(
            "You are an excellent content writer. "
            "Create clear, engaging content based on the user's request. "
            "Focus on clarity, accuracy, and proper structure."
        ),
    )


# Create Reviewer agent - evaluates and provides structured feedback
def create_reviewer():
    return client.create_agent(
        name="Reviewer",
        instructions=(
            "You are an expert content reviewer. "
            "Evaluate the writer's content based on:\n"
            "1. Clarity - Is it easy to understand?\n"
            "2. Completeness - Does it fully address the topic?\n"
            "3. Accuracy - Is the information correct?\n"
            "4. Structure - Is it well-organized?\n\n"
            "Return a JSON object with:\n"
            "- score: overall quality (0-100)\n"
            "- feedback: concise, actionable feedback\n"
            "- clarity, completeness, accuracy, structure: individual scores (0-100)"
        ),
        response_format=ReviewResult,
    )


# Create Editor agent - improves content based on feedback
def create_editor():
    return client.create_agent(
        name="Editor",
        instructions=(
            "You are a skilled editor. "
            "You will receive content along with review feedback. "
            "Improve the content by addressing all the issues mentioned in the feedback. "
            "Maintain the original intent while enhancing clarity, completeness, accuracy, and structure."
        ),
    )


# Create Publisher agent - formats content for publication
def create_publisher():
    return client.create_agent(
        name="Publisher",
        instructions=(
            "You are a publishing agent. "
            "You receive either approved content or edited content. "
            "Format it for publication with proper headings and structure."
        ),
    )


# Create Summarizer agent - creates final publication report
def create_summarizer():
    return client.create_agent(
        name="Summarizer",
        instructions=(
            "You are a summarizer agent. "
            "Create a final publication report that includes:\n"
            "1. A brief summary of the published content\n"
            "2. The workflow path taken (direct approval or edited)\n"
            "3. Key highlights and takeaways\n"
            "Keep it concise and professional."
        ),
    )


# Build workflow with branching and convergence:
# Writer → Reviewer → [branches]:
#   - If score >= 80: → Publisher → Summarizer (direct approval path)
#   - If score < 80: → Editor → Publisher → Summarizer (improvement path)
# Both paths converge at Summarizer for final report
workflow = (
    WorkflowBuilder(
        name="Content Review Workflow",
        description="Multi-agent content creation with quality-based routing (Writer→Reviewer→Editor/Publisher)",
    )
    .register_agent(create_writer, name="Writer")
    .register_agent(create_reviewer, name="Reviewer")
    .register_agent(create_editor, name="Editor")
    .register_agent(create_publisher, name="Publisher")
    .register_agent(create_summarizer, name="Summarizer")
    .set_start_executor("Writer")
    .add_edge("Writer", "Reviewer")
    # Branch 1: High quality (>= 80) goes directly to publisher
    .add_edge("Reviewer", "Publisher", condition=is_approved)
    # Branch 2: Low quality (< 80) goes to editor first, then publisher
    .add_edge("Reviewer", "Editor", condition=needs_editing)
    .add_edge("Editor", "Publisher")
    # Both paths converge: Publisher → Summarizer
    .add_edge("Publisher", "Summarizer")
    .build()
)


def main():
    from agent_framework.devui import serve

    serve(entities=[workflow], port=8093, auto_open=True)


if __name__ == "__main__":
    main()
