import os

import azure.identity
from dotenv import load_dotenv
from smolagents import AzureOpenAIServerModel, CodeAgent, DuckDuckGoSearchTool, OpenAIServerModel

# Setup the OpenAI client to use either Azure OpenAI or GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "github":
    model = OpenAIServerModel(
        model_id=os.getenv("GITHUB_MODEL", "gpt-4o"),
        api_base="https://models.inference.ai.azure.com",
        api_key=os.environ["GITHUB_TOKEN"],
    )
elif API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    model = AzureOpenAIServerModel(
        model_id=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        api_version=os.environ["AZURE_OPENAI_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        client_kwargs={"azure_ad_token_provider": token_provider},
    )
elif API_HOST == "ollama":
    model = OpenAIServerModel(model_id="llama3.1:latest", api_base="http://localhost:11434/v1", api_key="none")

agent = CodeAgent(tools=[DuckDuckGoSearchTool()], model=model)

agent.run("How many seconds would it take for a leopard at full speed to run through Pont des Arts?")
