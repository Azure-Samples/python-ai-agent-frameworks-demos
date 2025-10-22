<!--
---
name: Python AI Agent Frameworks Demos
description: Collection of Python examples for popular AI agent frameworks using GitHub Models or Azure OpenAI.
languages:
- python
products:
- azure-openai
- azure
page_type: sample
urlFragment: python-ai-agent-frameworks-demos
---
-->

# Demos de Frameworks de Agentes de IA en Python

[![Abrir en GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos)
[![Abrir en Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)

Este repositorio ofrece ejemplos de muchos frameworks populares de agentes de IA en Python usando LLMs de [GitHub Models](https://github.com/marketplace/models). Estos modelos son gratuitos para cualquiera con una cuenta de GitHub, hasta un [límite diario](https://docs.github.com/github-models/prototyping-with-ai-models#rate-limits).

* [Cómo empezar](#cómo-empezar)
  * [GitHub Codespaces](#github-codespaces)
  * [VS Code Dev Containers](#vs-code-dev-containers)
  * [Entorno local](#entorno-local)
* [Ejecutar los ejemplos en Python](#ejecutar-los-ejemplos-en-python)
* [Guía](#guía)
  * [Costos](#costos)
  * [Pautas de seguridad](#pautas-de-seguridad)
* [Recursos](#recursos)

## Cómo empezar

Tenés varias opciones para comenzar con este repositorio.
La forma más rápida es usar GitHub Codespaces, ya que te configurará todo automáticamente, pero también podés [configurarlo localmente](#entorno-local).

### GitHub Codespaces

Podés ejecutar este repositorio virtualmente usando GitHub Codespaces. El botón abrirá una instancia de VS Code basada en web en tu navegador:

1. Abre el repositorio (esto puede tardar varios minutos):

    [![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos)

2. Abre una ventana de terminal
3. Continúa con los pasos para ejecutar los ejemplos

### VS Code Dev Containers

Una opción relacionada es VS Code Dev Containers, que abrirá el proyecto en tu VS Code local usando la [extensión Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Inicia Docker Desktop (instálalo si no lo tenés ya)
2. Abre el proyecto:

    [![Abrir en Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)

3. En la ventana de VS Code que se abre, una vez que aparezcan los archivos del proyecto (esto puede tardar varios minutos), abre una ventana de terminal.
4. Continúa con los pasos para ejecutar los ejemplos

### Entorno local

1. Asegúrate de tener instaladas las siguientes herramientas:

    * [Python 3.10+](https://www.python.org/downloads/)
    * Git

2. Clona el repositorio:

    ```shell
    git clone https://github.com/Azure-Samples/python-ai-agent-frameworks-demos
    cd python-ai-agents-demos
    ```

3. Configura un entorno virtual:

    ```shell
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

4. Instala los requisitos:

    ```shell
    pip install -r requirements.txt
    ```

## Ejecutar los ejemplos en Python

Podés ejecutar los ejemplos en este repositorio ejecutando los scripts en el directorio `examples/spanish`. Cada script demuestra un patrón o framework diferente de agente de IA.

### Microsoft Agent Framework

| Ejemplo | Descripción |
| ------- | ----------- |
| [agentframework_basic.py](agentframework_basic.py) | Usa Agent Framework para crear un agente informativo básico. |
| [agentframework_tool.py](agentframework_tool.py) | Usa Agent Framework para crear un agente con una única herramienta de clima. |
| [agentframework_tools.py](agentframework_tools.py) | Usa Agent Framework para crear un agente planificador de fin de semana con múltiples herramientas. |
| [agentframework_supervisor.py](agentframework_supervisor.py) | Usa Agent Framework con un supervisor que orquesta subagentes de actividades y recetas. |

### LangChain v1 y LangGraph

| Ejemplo | Descripción |
| ------- | ----------- |
| [langchainv1_basic.py](langchainv1_basic.py) | Usa LangChain v1 para crear un agente informativo básico. |
| [langchainv1_tool.py](langchainv1_tool.py) | Usa LangChain v1 para crear un agente con una única herramienta de clima. |
| [langchainv1_tools.py](langchainv1_tools.py) | Usa LangChain v1 para crear un agente planificador de fin de semana con múltiples herramientas. |
| [langchainv1_supervisor.py](langchainv1_supervisor.py) | Usa LangChain v1 con un supervisor orquestando subagentes de actividades y recetas. |
| [langchainv1_quickstart.py](langchainv1_quickstart.py) | Usa LangChain v1 para crear un asistente con llamadas de herramientas, salida estructurada y memoria. Basado en los documentos oficiales de Inicio Rápido. |
| [langchainv1_mcp_github.py](langchainv1_mcp_github.py) | Usa agente Langchain v1 con servidor MCP de GitHub para triar issues del repositorio. |
| [langchainv1_mcp_http.py](langchainv1_mcp_http.py) | Usa agente Langchain v1 con herramientas de un servidor MCP HTTP local. |
| [langgraph_agent.py](langgraph_agent.py) | Construye un grafo LangGraph para un agente que reproduce canciones. |
| [langgraph_mcp.py](langgraph_mcp.py) | Construye un grafo Langgraph que usa herramientas de un servidor MCP HTTP. |

### OpenAI y OpenAI Agents

| Ejemplo | Descripción |
| ------- | ----------- |
| [openai_githubmodels.py](openai_githubmodels.py) | Configuración básica para usar modelos de GitHub con la API de OpenAI. |
| [openai_functioncalling.py](openai_functioncalling.py) | Usa OpenAI Function Calling para llamar funciones basadas en la salida del LLM. |
| [openai_agents_basic.py](openai_agents_basic.py) | Usa el framework de Agentes de OpenAI para crear un agente único. |
| [openai_agents_handoffs.py](openai_agents_handoffs.py) | Usa el framework de Agentes de OpenAI para transferir entre varios agentes con herramientas. |
| [openai_agents_tools.py](openai_agents_tools.py) | Usa el framework de Agentes de OpenAI para crear un planificador de fin de semana con herramientas. |
| [openai_agents_mcp_http.py](openai_agents_mcp_http.py) | Usa el framework de Agentes de OpenAI con un servidor MCP HTTP (herramientas de planificación de viajes). |

### PydanticAI

| Ejemplo | Descripción |
| ------- | ----------- |
| [pydanticai_basic.py](pydanticai_basic.py) | Usa PydanticAI para construir un agente único básico (tutor de inglés). |
| [pydanticai_multiagent.py](pydanticai_multiagent.py) | Usa PydanticAI para construir un flujo secuencial de dos agentes (vuelo + selección de asiento). |
| [pydanticai_graph.py](pydanticai_graph.py) | Usa PydanticAI con pydantic-graph para construir un pequeño grafo de evaluación pregunta/respuesta. |
| [pydanticai_tools.py](pydanticai_tools.py) | Usa PydanticAI con múltiples herramientas de Python para planificar actividades de fin de semana. |
| [pydanticai_mcp_http.py](pydanticai_mcp_http.py) | Usa PydanticAI con un conjunto de herramientas de servidor MCP HTTP para planificación de viajes (búsqueda de hoteles). |
| [pydanticai_mcp_github.py](pydanticai_mcp_github.py) | Usa PydanticAI con un conjunto de herramientas de servidor MCP de GitHub para triar issues del repositorio. |
| [pydanticai_supervisor.py](pydanticai_supervisor.py) | Usa PydanticAI con patrón de triaje/supervisor que traspasa entre agentes del clima en español e inglés. |

### AutoGen

| Ejemplo | Descripción |
| ------- | ----------- |
| [autogen_basic.py](autogen_basic.py) | Usa AutoGen para crear un agente tutor de inglés básico. |
| [autogen_tools.py](autogen_tools.py) | Usa AutoGen para crear un agente planificador de fin de semana con herramientas. |
| [autogen_swarm.py](autogen_swarm.py) | Usa AutoGen con patrón Swarm para transferir entre múltiples agentes. |
| [autogen_magenticone.py](autogen_magenticone.py) | Usa AutoGen con patrón MagenticOne para resolver problemas complejos con múltiples agentes. |

### Semantic Kernel

| Ejemplo | Descripción |
| ------- | ----------- |
| [semantickernel_basic.py](semantickernel_basic.py) | Usa Semantic Kernel para crear un agente básico con chat de dos turnos. |
| [semantickernel_groupchat.py](semantickernel_groupchat.py) | Usa Semantic Kernel para crear un chat grupal con múltiples agentes que colaboran. |
| [semantickernel_mcp_http.py](semantickernel_mcp_http.py) | Usa Semantic Kernel con herramientas de servidor MCP HTTP para planificación de viajes. |

### Azure AI

| Ejemplo | Descripción |
| ------- | ----------- |
| [azureai_githubmodels.py](azureai_githubmodels.py) | Usa Azure AI Inference SDK con modelos de GitHub. |
| [azureai_azureopenai.py](azureai_azureopenai.py) | Usa Azure AI Inference SDK con Azure OpenAI. |

### Otros frameworks

| Ejemplo | Descripción |
| ------- | ----------- |
| [llamaindex.py](llamaindex.py) | Usa LlamaIndex para construir un agente ReAct para RAG en múltiples índices. |
| [smolagents_codeagent.py](smolagents_codeagent.py) | Usa SmolAgents para construir un agente de respuesta a preguntas que puede buscar en la web y ejecutar código. |
| [mcp_server_basic.py](mcp_server_basic.py) | Servidor MCP HTTP básico con herramientas de búsqueda de hoteles (prerequisito para varios ejemplos MCP). |

## Configurar GitHub Models

Si abres este repositorio en GitHub Codespaces, podés ejecutar los scripts gratis usando GitHub Models sin pasos adicionales, ya que tu `GITHUB_TOKEN` ya está configurado en el entorno de Codespaces.

Si querés ejecutar los scripts localmente, necesitás configurar la variable de entorno `GITHUB_TOKEN` con un token de acceso personal (PAT) de GitHub. Podés crear un PAT siguiendo estos pasos:

1. Ve a la configuración de tu cuenta de GitHub.
2. Haz clic en "Developer settings" en la barra lateral izquierda.
3. Haz clic en "Personal access tokens" en la barra lateral izquierda.
4. Haz clic en "Tokens (classic)" o "Fine-grained tokens" según tu preferencia.
5. Haz clic en "Generate new token".
6. Dale un nombre a tu token y selecciona los alcances que querés otorgar. Para este proyecto, no necesitás alcances específicos.
7. Haz clic en "Generate token".
8. Copia el token generado.
9. Configura la variable de entorno `GITHUB_TOKEN` en tu terminal o IDE:

    ```shell
    export GITHUB_TOKEN=tu_token_de_acceso_personal
    ```

10. Opcionalmente, podés usar un modelo diferente a "gpt-4o" configurando la variable de entorno `GITHUB_MODEL`. Usa un modelo que soporte llamadas de funciones, como: `gpt-4o`, `gpt-4o-mini`, `o3-mini`, `AI21-Jamba-1.5-Large`, `AI21-Jamba-1.5-Mini`, `Codestral-2501`, `Cohere-command-r`, `Ministral-3B`, `Mistral-Large-2411`, `Mistral-Nemo`, `Mistral-small`

## Provisionar recursos de Azure AI

Podés ejecutar todos los ejemplos en este repositorio usando GitHub Models. Si querés ejecutar los ejemplos usando modelos de Azure OpenAI, necesitás provisionar los recursos de Azure AI, lo que generará costos.

Este proyecto incluye infraestructura como código (IaC) para provisionar despliegues de Azure OpenAI de "gpt-4o" y "text-embedding-3-large". La IaC está definida en el directorio `infra` y usa Azure Developer CLI para provisionar los recursos.

1. Asegúrate de tener instalado [Azure Developer CLI (azd)](https://aka.ms/install-azd).

2. Inicia sesión en Azure:

    ```shell
    azd auth login
    ```

    Para usuarios de GitHub Codespaces, si el comando anterior falla, prueba:

   ```shell
    azd auth login --use-device-code
    ```

3. Provisiona la cuenta de OpenAI:

    ```shell
    azd provision
    ```

    Te pedirá que proporciones un nombre de entorno `azd` (como "agents-demos"), selecciones una suscripción de tu cuenta de Azure y selecciones una ubicación. Luego aprovisionará los recursos en tu cuenta.

4. Una vez que los recursos estén aprovisionados, deberías ver un archivo local `.env` con todas las variables de entorno necesarias para ejecutar los scripts.
5. Para eliminar los recursos, ejecuta:

    ```shell
    azd down
    ```

## Recursos

* [Documentación de LangGraph](https://langchain-ai.github.io/langgraph/tutorials/introduction/)
* [Documentación de LlamaIndex](https://docs.llamaindex.ai/en/latest/)
* [Documentación de OpenAI Agents](https://openai.github.io/openai-agents-python/)
* [Documentación de OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling?api-mode=chat)
* [Documentación de PydanticAI](https://ai.pydantic.dev/multi-agent-applications/)
* [Documentación de Semantic Kernel](https://learn.microsoft.com/semantic-kernel/overview/)
* [Documentación de SmolAgents](https://huggingface.co/docs/smolagents/index)
