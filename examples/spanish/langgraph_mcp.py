"""Ejemplo de grafo de estado personalizado LangGraph + MCP HTTP.

Prerrequisito:
Inicia el servidor MCP local definido en `mcp_server_basic.py` en el puerto 8000:
    python examples/mcp_server_basic.py
"""

import os

import azure.identity
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

# Configuración del cliente para usar Azure OpenAI o GitHub Models
load_dotenv(override=True)
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
    )
else:
    model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=os.environ["GITHUB_TOKEN"],
    )


async def setup_agent():
    client = MultiServerMCPClient(
        {
            "weather": {
                # Asegúrate de iniciar tu servidor del clima en el puerto 8000
                "url": "http://localhost:8000/mcp/",
                "transport": "streamable_http",
            }
        }
    )
    tools = await client.get_tools()

    def call_model(state: MessagesState):
        response = model.bind_tools(tools).invoke(state["messages"])
        return {"messages": response}

    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")
    graph = builder.compile()
    hotel_response = await graph.ainvoke({"messages": "Encuentra un hotel en SF para 2 noches comenzando el 2024-01-01. Necesito WiFi gratis y piscina."})
    print(hotel_response["messages"][-1].content)
    image_bytes = graph.get_graph().draw_mermaid_png()
    with open("examples/images/langgraph_mcp_http_graph.png", "wb") as f:
        f.write(image_bytes)


if __name__ == "__main__":
    import asyncio
    import logging

    logging.basicConfig(level=logging.WARNING)
    asyncio.run(setup_agent())
