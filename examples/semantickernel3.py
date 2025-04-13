# https://learn.microsoft.com/semantic-kernel/frameworks/agent/examples/example-agent-collaboration?pivots=programming-language-python

import asyncio
import os

import azure.identity
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AsyncOpenAI
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelFunctionFromPrompt

"""
The following sample demonstrates how to create a simple,
agent group chat that utilizes a Reviewer Chat Completion
Agent along with a Writer Chat Completion Agent to
complete a user's task.
"""

# Define agent names
REVIEWER_NAME = "Reviewer"
WRITER_NAME = "Writer"

load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

def create_kernel() -> Kernel:
    """Creates a Kernel instance with an Azure OpenAI ChatCompletion service."""
    kernel = Kernel()

    if API_HOST == "azure":
        token_provider = azure.identity.get_bearer_token_provider(
            azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        chat_client = AsyncAzureOpenAI(
            api_version=os.environ["AZURE_OPENAI_VERSION"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_ad_token_provider=token_provider,
        )
        chat_completion_service = OpenAIChatCompletion(
            ai_model_id=os.environ["AZURE_OPENAI_CHAT_MODEL"],
            async_client=chat_client)
    else:
        chat_client = AsyncOpenAI(
            api_key=os.environ["GITHUB_TOKEN"],
            base_url="https://models.inference.ai.azure.com")
        chat_completion_service = OpenAIChatCompletion(
            ai_model_id="gpt-4o",
            async_client=chat_client)
    kernel.add_service(chat_completion_service)
    return kernel


async def main():
    # Create a single kernel instance for all agents.
    kernel = create_kernel()

    # Create ChatCompletionAgents using the same kernel.
    agent_reviewer = ChatCompletionAgent(
        kernel=kernel,
        name=REVIEWER_NAME,
        instructions="""
Your responsibility is to review and identify how to improve user provided content.
If the user has provided input or direction for content already provided, specify how to address this input.
Never directly perform the correction or provide an example.
Once the content has been updated in a subsequent response, review it again until it is satisfactory.

RULES:
- Only identify suggestions that are specific and actionable.
- Verify previous suggestions have been addressed.
- Never repeat previous suggestions.
""",
    )

    agent_writer = ChatCompletionAgent(
        kernel=kernel,
        name=WRITER_NAME,
        instructions="""
Your sole responsibility is to rewrite content according to review suggestions.
- Always apply all review directions.
- Always revise the content in its entirety without explanation.
- Never address the user.
""",
    )

    # Define a selection function to determine which agent should take the next turn.
    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""
Examine the provided RESPONSE and choose the next participant.
State only the name of the chosen participant without explanation.
Never choose the participant named in the RESPONSE.

Choose only from these participants:
- {REVIEWER_NAME}
- {WRITER_NAME}

Rules:
- If RESPONSE is user input, it is {REVIEWER_NAME}'s turn.
- If RESPONSE is by {REVIEWER_NAME}, it is {WRITER_NAME}'s turn.
- If RESPONSE is by {WRITER_NAME}, it is {REVIEWER_NAME}'s turn.

RESPONSE:
{{{{$lastmessage}}}}
""",
    )

    # Define a termination function where the reviewer signals completion with "yes".
    termination_keyword = "yes"

    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
Examine the RESPONSE and determine whether the content has been deemed satisfactory.
If the content is satisfactory, respond with a single word without explanation: {termination_keyword}.
If specific suggestions are being provided, it is not satisfactory.
If no correction is suggested, it is satisfactory.

RESPONSE:
{{{{$lastmessage}}}}
""",
    )

    history_reducer = ChatHistoryTruncationReducer(target_count=5)

    # Create the AgentGroupChat with selection and termination strategies.
    chat = AgentGroupChat(
        agents=[agent_reviewer, agent_writer],
        selection_strategy=KernelFunctionSelectionStrategy(
            initial_agent=agent_reviewer,
            function=selection_function,
            kernel=kernel,
            result_parser=lambda result: str(result.value[0]).strip() if result.value[0] is not None else WRITER_NAME,
            history_variable_name="lastmessage",
            history_reducer=history_reducer,
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[agent_reviewer],
            function=termination_function,
            kernel=kernel,
            result_parser=lambda result: termination_keyword in str(result.value[0]).lower(),
            history_variable_name="lastmessage",
            maximum_iterations=10,
            history_reducer=history_reducer,
        ),
    )

    print(
        "Ready! Type your input, or 'exit' to quit, 'reset' to restart the conversation. "
        "You may pass in a file path using @<path_to_file>."
    )

    is_complete = False
    while not is_complete:
        print()
        user_input = input("User > ").strip()
        if not user_input:
            continue

        if user_input.lower() == "exit":
            is_complete = True
            break

        if user_input.lower() == "reset":
            await chat.reset()
            print("[Conversation has been reset]")
            continue

        # Try to grab files from the script's current directory
        if user_input.startswith("@") and len(user_input) > 1:
            file_name = user_input[1:]
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, file_name)
            try:
                if not os.path.exists(file_path):
                    print(f"Unable to access file: {file_path}")
                    continue
                with open(file_path, encoding="utf-8") as file:
                    user_input = file.read()
            except Exception:
                print(f"Unable to access file: {file_path}")
                continue

        # Add the current user_input to the chat
        await chat.add_chat_message(message=user_input)

        try:
            async for response in chat.invoke():
                if response is None or not response.name:
                    continue
                print()
                print(f"# {response.name.upper()}:\n{response.content}")
        except Exception as e:
            print(f"Error during chat invocation: {e}")

        # Reset the chat's complete flag for the new conversation round.
        chat.is_complete = False


if __name__ == "__main__":
    asyncio.run(main())
