from __future__ import annotations as _annotations

import asyncio
import os
from dataclasses import dataclass, field

import azure.identity
from dotenv import load_dotenv
from groq import BaseModel
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic_ai import Agent, format_as_xml
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_graph import (
    BaseNode,
    End,
    Graph,
    GraphRunContext,
)

# Configuración del cliente OpenAI para usar Azure OpenAI o Modelos de GitHub
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    client = AsyncOpenAI(api_key=os.environ["GITHUB_TOKEN"], base_url="https://models.inference.ai.azure.com")
    model = OpenAIChatModel(os.getenv("GITHUB_MODEL", "gpt-4o"), provider=OpenAIProvider(openai_client=client))
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    client = AsyncAzureOpenAI(
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_ad_token_provider=token_provider,
    )
    model = OpenAIChatModel(os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], provider=OpenAIProvider(openai_client=client))
elif API_HOST == "ollama":
    client = AsyncOpenAI(base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"), api_key="none")
    model = OpenAIChatModel(os.environ["OLLAMA_MODEL"], provider=OpenAIProvider(openai_client=client))


"""
Definiciones de agentes
"""

ask_agent = Agent(model, output_type=str, instrument=True)


class EvaluationResult(BaseModel, use_attribute_docstrings=True):
    correct: bool
    """Si la respuesta es correcta."""
    comment: str
    """Comentario sobre la respuesta, regaña al usuario si la respuesta está mal."""


evaluate_agent = Agent(
    model,
    output_type=EvaluationResult,
    system_prompt="Dada una pregunta y respuesta, evalúa si la respuesta es correcta.",
)

"""
Estado del grafo y nodos
"""


@dataclass
class QuestionState:
    question: str | None = None
    ask_agent_messages: list[ModelMessage] = field(default_factory=list)
    evaluate_agent_messages: list[ModelMessage] = field(default_factory=list)


@dataclass
class Ask(BaseNode[QuestionState]):
    async def run(self, ctx: GraphRunContext[QuestionState]) -> Answer:
        result = await ask_agent.run(
            "Formula una pregunta simple con solo una respuesta correcta.",
            message_history=ctx.state.ask_agent_messages,
        )
        ctx.state.ask_agent_messages += result.all_messages()
        ctx.state.question = result.output
        return Answer(result.output)


@dataclass
class Answer(BaseNode[QuestionState]):
    question: str

    async def run(self, ctx: GraphRunContext[QuestionState]) -> Evaluate:
        answer = input(f"{self.question}: ")
        return Evaluate(answer)


@dataclass
class Evaluate(BaseNode[QuestionState, None, str]):
    answer: str

    async def run(
        self,
        ctx: GraphRunContext[QuestionState],
    ) -> End[str] | Reprimand:
        assert ctx.state.question is not None
        result = await evaluate_agent.run(
            format_as_xml({"question": ctx.state.question, "answer": self.answer}),
            message_history=ctx.state.evaluate_agent_messages,
        )
        ctx.state.evaluate_agent_messages += result.all_messages()
        if result.output.correct:
            return End(result.output.comment)
        else:
            return Reprimand(result.output.comment)


@dataclass
class Reprimand(BaseNode[QuestionState]):
    comment: str

    async def run(self, ctx: GraphRunContext[QuestionState]) -> Ask:
        print(f"Comentario: {self.comment}")
        ctx.state.question = None
        return Ask()


question_graph = Graph(nodes=(Ask, Answer, Evaluate, Reprimand), state_type=QuestionState)


async def main():
    state = QuestionState()
    node = Ask()
    end = await question_graph.run(node, state=state)
    print("FIN:", end.output)


if __name__ == "__main__":
    asyncio.run(main())
