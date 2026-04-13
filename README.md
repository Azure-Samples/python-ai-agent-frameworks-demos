<!--
---
name: Python AI Agent Frameworks Demos
description: Collection of Python examples for popular AI agent frameworks using Azure OpenAI.
languages:
- python
products:
- azure-openai
- azure
page_type: sample
urlFragment: python-ai-agent-frameworks-demos
---
-->
# Python AI Agent Frameworks Demos

[![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos)
[![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)

This repository provides examples of many popular Python AI agent frameworks.

* [Getting started](#getting-started)
  * [GitHub Codespaces](#github-codespaces)
  * [VS Code Dev Containers](#vs-code-dev-containers)
  * [Local environment](#local-environment)
* [Configuring model providers](#configuring-model-providers)
  * [Using Azure OpenAI models](#using-azure-openai-models)
  * [Using OpenAI.com models](#using-openaicom-models)
  * [Using Ollama models](#using-ollama-models)
* [Running the Python examples](#running-the-python-examples)
* [Resources](#resources)

## Getting started

You have a few options for getting started with this repository.
The quickest way to get started is GitHub Codespaces, since it will setup everything for you, but you can also [set it up locally](#local-environment).

### GitHub Codespaces

You can run this repository virtually by using GitHub Codespaces. Click one of the buttons below to open a web-based VS Code instance in your browser:

**Default (Azure OpenAI):**

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos)

**Ollama (local models, requires 64GB+ memory):**

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos?devcontainer_path=.devcontainer/ollama/devcontainer.json)

The Ollama Codespace pre-installs Ollama and pulls the `gemma4:e2b` model, and copies `.env.sample.ollama` as your `.env` file. Note that the 64GB memory requirement will consume your Codespace quota faster.

Once the Codespace is open, open a terminal window and continue with the steps to run the examples.

### VS Code Dev Containers

A related option is VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project:

    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)

3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the steps to run the examples

### Local environment

1. Make sure the following tools are installed:

    * [Python 3.10+](https://www.python.org/downloads/)
    * Git

2. Clone the repository:

    ```shell
    git clone https://github.com/Azure-Samples/python-ai-agent-frameworks-demos
    cd python-ai-agent-frameworks-demos
    ```

3. Set up a virtual environment:

    ```shell
3. Create a virtual environment and install dependencies:

    ```shell
    uv sync
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

## Configuring model providers

These examples can be run with Azure OpenAI account, OpenAI.com, or local Ollama server, depending on the environment variables you set. All the scripts reference the environment variables from a `.env` file, and an example `.env.sample` file is provided. Host-specific instructions are below.

## Using Azure OpenAI models

To run the examples using models from Azure OpenAI, you need to provision the Azure AI resources, which will incur costs.

This project includes infrastructure as code (IaC) to provision Azure OpenAI deployments of "gpt-5.4" and "text-embedding-3-large". The IaC is defined in the `infra` directory and uses the Azure Developer CLI to provision the resources.

1. Make sure the [Azure Developer CLI (azd)](https://aka.ms/install-azd) is installed.

2. Login to Azure:

    ```shell
    azd auth login
    ```

    For GitHub Codespaces users, if the previous command fails, try:

   ```shell
    azd auth login --use-device-code
    ```

3. Provision the OpenAI account:

    ```shell
    azd provision
    ```

    It will prompt you to provide an `azd` environment name (like "agents-demos"), select a subscription from your Azure account, and select a location. Then it will provision the resources in your account.

4. Once the resources are provisioned, you should now see a local `.env` file with all the environment variables needed to run the scripts.
5. To delete the resources, run:

    ```shell
    azd down
    ```

## Using OpenAI.com models

1. Create a `.env` file by copying the `.env.sample` file and updating it with your OpenAI API key and desired model name.

    ```bash
    cp .env.sample .env
    ```

2. Update the `.env` file with your OpenAI API key and desired model name:

    ```bash
    API_HOST=openai
    OPENAI_API_KEY=your_openai_api_key
    OPENAI_MODEL=gpt-4o-mini
    ```

## Using Ollama models

1. Install [Ollama](https://ollama.com/) and follow the instructions to set it up on your local machine.
2. Pull a model, for example:

    ```shell
    ollama pull qwen3:30b
    ```

    Note that most models do not support tool calling to the extent required by agents frameworks, so choose a model accordingly.

3. Create a `.env` file by copying the `.env.sample` file and updating it with your Ollama endpoint and model name.

    ```bash
    cp .env.sample .env
    ```

4. Update the `.env` file with your Ollama endpoint and model name (any model you've pulled):

    ```bash
    API_HOST=ollama
    OLLAMA_ENDPOINT=http://localhost:11434/v1
    OLLAMA_MODEL=gemma4:e2b
    ```

## Running the Python examples

You can run the examples in this repository by executing the scripts in the `examples` directory. Each script demonstrates a different AI agent pattern or framework.

### Microsoft Agent Framework

| Example | Description |
| ------- | ----------- |
| [agentframework_basic.py](examples/agentframework_basic.py) | Uses Agent Framework to build a basic informational agent. |
| [agentframework_tool.py](examples/agentframework_tool.py) | Uses Agent Framework to build an agent with a single weather tool. |
| [agentframework_tools.py](examples/agentframework_tools.py) | Uses Agent Framework to build a weekend planning agent with multiple tools. |
| [agentframework_supervisor.py](examples/agentframework_supervisor.py) | Uses Agent Framework with a supervisor orchestrating activity and recipe sub-agents. |
| [agentframework_magenticone.py](examples/agentframework_magenticone.py) | Uses Agent Framework to build a MagenticOne agent. |
| [agentframework_workflow.py](examples/agentframework_workflow.py) | Uses Agent Framework to build a workflow-based agent. |

### Langchain v1 and LangGraph

| Example | Description |
| ------- | ----------- |
| [langchainv1_basic.py](examples/langchainv1_basic.py) | Uses LangChain v1 to build a basic informational agent. |
| [langchainv1_tool.py](examples/langchainv1_tool.py) | Uses LangChain v1 to build an agent with a single weather tool. |
| [langchainv1_tools.py](examples/langchainv1_tools.py) | Uses LangChain v1 to build a weekend planning agent with multiple tools. |
| [langchainv1_supervisor.py](examples/langchainv1_supervisor.py) | Uses LangChain v1 with a supervisor orchestrating activity and recipe sub-agents. |
| [langchainv1_quickstart.py](examples/langchainv1_quickstart.py) | Uses LangChain v1 to build an assistant with tool calling, structured output, and memory. Based off official Quickstart docs. |
| [langchainv1_mcp_github.py](examples/langchainv1_mcp_github.py) | Uses Langchain v1 agent with GitHub MCP server to triage repository issues. |
| [langchainv1_mcp_http.py](examples/langchainv1_mcp_http.py) | Uses Langchain v1 agent with tools from local MCP HTTP server. |
| [langgraph_agent.py](examples/langgraph_agent.py) | Builds LangGraph graph for an agent to play songs. |
| [langgraph_mcp.py](examples/langgraph_mcp.py) | Builds Langgraph graph that uses tools from MCP HTTP server. |

### OpenAI and OpenAI-Agents

| Example | Description |
| ------- | ----------- |
| [openai_functioncalling.py](examples/openai_functioncalling.py) | Uses OpenAI Function Calling to call functions based on LLM output. |
| [openai_agents_basic.py](examples/openai_agents_basic.py) | Uses the OpenAI Agents framework to build a single agent. |
| [openai_agents_handoffs.py](examples/openai_agents_handoffs.py) | Uses the OpenAI Agents framework to handoff between several agents with tools. |
| [openai_agents_tools.py](examples/openai_agents_tools.py) | Uses the OpenAI Agents framework to build a weekend planner with tools. |
| [openai_agents_mcp_http.py](examples/openai_agents_mcp_http.py) | Uses the OpenAI Agents framework with an MCP HTTP server (travel planning tools). |

### PydanticAI

| Example | Description |
| ------- | ----------- |
| [pydanticai_basic.py](examples/pydanticai_basic.py) | Uses PydanticAI to build a basic single agent (Spanish tutor). |
| [pydanticai_multiagent.py](examples/pydanticai_multiagent.py) | Uses PydanticAI to build a two-agent sequential workflow (flight + seat selection). |
| [pydanticai_supervisor.py](examples/pydanticai_supervisor.py) | Uses PydanticAI with a supervisor orchestrating multiple agents. |
| [pydanticai_graph.py](examples/pydanticai_graph.py) | Uses PydanticAI with pydantic-graph to build a small question/answer evaluation graph. |
| [pydanticai_tools.py](examples/pydanticai_tools.py) | Uses PydanticAI with multiple Python tools for weekend activity planning. |
| [pydanticai_mcp_http.py](examples/pydanticai_mcp_http.py) | Uses PydanticAI with an MCP HTTP server toolset for travel planning (hotel search). |
| [pydanticai_mcp_github.py](examples/pydanticai_mcp_github.py) | Uses PydanticAI with an MCP GitHub server toolset to triage repository issues. |

### Other frameworks

| Example | Description |
| ------- | ----------- |
| [llamaindex.py](examples/llamaindex.py) | Uses LlamaIndex to build a ReAct agent for RAG on multiple indexes. |

## Resources

* [Agent Framework Documentation](https://learn.microsoft.com/agent-framework/)
* [Langchain v1 Documentation](https://docs.langchain.com/oss/python/langchain/overview)
* [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/overview)
* [LlamaIndex Documentation](https://docs.llamaindex.ai/en/latest/)
* [OpenAI Agents Documentation](https://openai.github.io/openai-agents-python/)
* [OpenAI Function Calling Documentation](https://platform.openai.com/docs/guides/function-calling?api-mode=chat)
* [Pydantic AI Documentation](https://ai.pydantic.dev/multi-agent-applications/)
