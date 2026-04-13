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

# Demos de Frameworks de Agentes de IA en Python

[![Abrir en GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos)
[![Abrir en Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/python-ai-agent-frameworks-demos)

Este repositorio ofrece ejemplos de muchos frameworks populares de agentes de IA en Python.

* [Cómo empezar](#cómo-empezar)
  * [GitHub Codespaces](#github-codespaces)
  * [VS Code Dev Containers](#vs-code-dev-containers)
  * [Entorno local](#entorno-local)
* [Configurar proveedores de modelos](#configurar-proveedores-de-modelos)
  * [Usar modelos de Azure OpenAI](#usar-modelos-de-azure-openai)
  * [Usar modelos de OpenAI.com](#usar-modelos-de-openaicom)
  * [Usar modelos de Ollama](#usar-modelos-de-ollama)
* [Ejecutar los ejemplos en Python](#ejecutar-los-ejemplos-en-python)
* [Recursos](#recursos)

## Cómo empezar

Tienes varias opciones para comenzar con este repositorio.
La forma más rápida es usar GitHub Codespaces, ya que te configurará todo automáticamente, pero también puedes [configurarlo localmente](#entorno-local).

### GitHub Codespaces

Puedes ejecutar este repositorio virtualmente usando GitHub Codespaces. Haz clic en uno de los botones para abrir una instancia web de VS Code en tu navegador:

**Predeterminado (Azure OpenAI):**

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos)

**Ollama (modelos locales, requiere 64GB+ de memoria):**

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Azure-Samples/python-ai-agent-frameworks-demos?devcontainer_path=.devcontainer/ollama/devcontainer.json)

El Codespace de Ollama pre-instala Ollama y descarga el modelo `gemma4:e2b`, y copia `.env.sample.ollama` como tu archivo `.env`. Ten en cuenta que el requisito de 64GB de memoria consumirá tu cuota de Codespace más rápido.

Una vez abierto el Codespace, abre una terminal y continúa con los pasos para ejecutar los ejemplos.

### VS Code Dev Containers

Una opción relacionada es VS Code Dev Containers, que abrirá el proyecto en tu VS Code local usando la [extensión Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Inicia Docker Desktop (instálalo si no lo tienes ya)
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
    cd python-ai-agent-frameworks-demos
    ```

3. Configura un entorno virtual:

    ```shell
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

4. Instala los requisitos:

    ```shell
    pip install -r requirements.txt
    ```

## Configurar proveedores de modelos

Estos ejemplos se pueden ejecutar con una cuenta de Azure OpenAI, OpenAI.com o servidor local de Ollama, dependiendo de las variables de entorno que configures. Todos los scripts hacen referencia a las variables de entorno de un archivo `.env`, y se proporciona un archivo de ejemplo `.env.sample`. Las instrucciones específicas de cada proveedor se encuentran a continuación.

## Usar modelos de Azure OpenAI

Para ejecutar los ejemplos usando modelos de Azure OpenAI, necesitas provisionar los recursos de Azure AI, lo que generará costos.

Este proyecto incluye infraestructura como código (IaC) para provisionar despliegues de Azure OpenAI de "gpt-5.4" y "text-embedding-3-large". La IaC está definida en el directorio `infra` y usa Azure Developer CLI para provisionar los recursos.

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

## Usar modelos de OpenAI.com

1. Crea un archivo `.env` copiando el archivo `.env.sample` y actualizándolo con tu clave API de OpenAI y el nombre del modelo deseado.

    ```bash
    cp .env.sample .env
    ```

2. Actualiza el archivo `.env` con tu clave API de OpenAI y el nombre del modelo deseado:

    ```bash
    API_HOST=openai
    OPENAI_API_KEY=tu_clave_api_de_openai
    OPENAI_MODEL=gpt-4o-mini
    ```

## Usar modelos de Ollama

1. Instala [Ollama](https://ollama.com/) y sigue las instrucciones para configurarlo en tu máquina local.
2. Descarga un modelo, por ejemplo:

    ```shell
    ollama pull qwen3:30b
    ```

    Ten en cuenta que la mayoría de los modelos no soportan llamadas de herramientas en la medida requerida por los frameworks de agentes, así que elige un modelo en consecuencia.

3. Crea un archivo `.env` copiando el archivo `.env.sample` y actualizándolo con tu endpoint de Ollama y nombre de modelo.

    ```bash
    cp .env.sample .env
    ```

4. Actualiza el archivo `.env` con tu endpoint de Ollama y nombre de modelo (cualquier modelo que hayas descargado):

    ```bash
    API_HOST=ollama
    OLLAMA_ENDPOINT=http://localhost:11434/v1
    OLLAMA_MODEL=gemma4:e2b
    ```

## Ejecutar los ejemplos en Python

Puedes ejecutar los ejemplos en este repositorio ejecutando los scripts en el directorio `examples/spanish`. Cada script demuestra un patrón o framework diferente de agente de IA.

### Microsoft Agent Framework

| Ejemplo | Descripción |
| ------- | ----------- |
| [agentframework_basic.py](agentframework_basic.py) | Usa Agent Framework para crear un agente informativo básico. |
| [agentframework_tool.py](agentframework_tool.py) | Usa Agent Framework para crear un agente con una única herramienta de clima. |
| [agentframework_tools.py](agentframework_tools.py) | Usa Agent Framework para crear un agente planificador de fin de semana con múltiples herramientas. |
| [agentframework_supervisor.py](agentframework_supervisor.py) | Usa Agent Framework con un supervisor que orquesta subagentes de actividades y recetas. |
| [agentframework_magenticone.py](agentframework_magenticone.py) | Usa Agent Framework para crear un agente MagenticOne. |
| [agentframework_hitl.py](agentframework_hitl.py) | Usa Agent Framework con human-in-the-loop (HITL) para confirmar o editar respuestas. |
| [agentframework_workflow.py](agentframework_workflow.py) | Usa Agent Framework para crear un agente basado en flujo de trabajo. |

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
| [pydanticai_supervisor.py](pydanticai_supervisor.py) | Usa PydanticAI con un supervisor orquestando múltiples agentes. |
| [pydanticai_graph.py](pydanticai_graph.py) | Usa PydanticAI con pydantic-graph para construir un pequeño grafo de evaluación pregunta/respuesta. |
| [pydanticai_tools.py](pydanticai_tools.py) | Usa PydanticAI con múltiples herramientas de Python para planificar actividades de fin de semana. |
| [pydanticai_mcp_http.py](pydanticai_mcp_http.py) | Usa PydanticAI con un conjunto de herramientas de servidor MCP HTTP para planificación de viajes (búsqueda de hoteles). |
| [pydanticai_mcp_github.py](pydanticai_mcp_github.py) | Usa PydanticAI con un conjunto de herramientas de servidor MCP de GitHub para triar issues del repositorio. |

### Otros frameworks

| Ejemplo | Descripción |
| ------- | ----------- |
| [llamaindex.py](llamaindex.py) | Usa LlamaIndex para construir un agente ReAct para RAG en múltiples índices. |
| [mcp_server_basic.py](mcp_server_basic.py) | Servidor MCP básico para exponer herramientas locales. |

## Recursos

* [Documentación de Agent Framework](https://learn.microsoft.com/agent-framework/)
* [Documentación de Langchain v1](https://docs.langchain.com/oss/python/langchain/overview)
* [Documentación de LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
* [Documentación de LlamaIndex](https://docs.llamaindex.ai/en/latest/)
* [Documentación de OpenAI Agents](https://openai.github.io/openai-agents-python/)
* [Documentación de OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling?api-mode=chat)
* [Documentación de Pydantic AI](https://ai.pydantic.dev/multi-agent-applications/)
