# https://github.com/JRAlexander/IntroToAgents1-Oxford/blob/main/intro-langgraph/time-travel.ipynb

import os

import azure.identity
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


@tool
def play_song_on_spotify(song: str):
    """Reproducir una canción en Spotify"""
    # Acá llamarías a la API de Spotify...
    return f"¡Listo! Ya puse {song} en Spotify."


@tool
def play_song_on_apple(song: str):
    """Reproducir una canción en Apple Music"""
    # Acá llamarías a la API de Apple Music...
    return f"¡Listo! Ya puse {song} en Apple Music."


tools = [play_song_on_apple, play_song_on_spotify]
tool_node = ToolNode(tools)

# Configurar el cliente para usar Azure OpenAI o modelos de GitHub
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

model = model.bind_tools(tools, parallel_tool_calls=False)

# Definir nodos y conexiones condicionales


# Definir la función que decide si continuar o no
def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    # Si no hay una llamada a función, terminamos
    if not last_message.tool_calls:
        return "end"
    # Si hay llamada a función, seguimos
    else:
        return "continue"


# Definir la función que llama al modelo
def call_model(state):
    messages = state["messages"]
    response = model.invoke(messages)
    # Devolvemos una lista porque esto se agregará a la lista existente
    return {"messages": [response]}


# Definir un nuevo grafo
workflow = StateGraph(MessagesState)

# Definir los dos nodos entre los que vamos a alternar
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)

# Establecer el punto de entrada como `agent`
# Esto significa que este nodo es el primero que se llama
workflow.add_edge(START, "agent")

# Ahora agregamos una conexión condicional
workflow.add_conditional_edges(
    # Primero, definimos el nodo inicial. Usamos `agent`.
    # Esto significa que estas conexiones se toman después de llamar al nodo `agent`.
    "agent",
    # Luego, pasamos la función que determina qué nodo se llama después.
    should_continue,
    # Finalmente, pasamos un mapeo.
    # Las claves son strings, y los valores son otros nodos.
    # END es un nodo especial que indica que el grafo debe terminar.
    # Lo que pasa es que llamamos a `should_continue`, y luego el resultado
    # se compara con las claves de este mapeo.
    # Según cuál coincida, se llamará a ese nodo.
    {
        # Si es `continue`, llamamos al nodo de acción.
        "continue": "action",
        # Si no, terminamos.
        "end": END,
    },
)

# Ahora agregamos una conexión normal desde `action` hacia `agent`.
# Esto significa que después de llamar a `action`, se llama al nodo `agent`.
workflow.add_edge("action", "agent")

# Configurar memoria
memory = MemorySaver()

# Finalmente, ¡lo compilamos!
# Esto lo convierte en un Runnable de LangChain,
# lo que significa que podés usarlo como cualquier otro runnable.

# Agregamos `interrupt_before=["action"]`
# Esto agrega un punto de interrupción antes de llamar al nodo `action`
app = workflow.compile(checkpointer=memory)

config = {"configurable": {"thread_id": "1"}}
input_message = HumanMessage(content="¿Podés poner la canción más popular de Taylor Swift?")
for event in app.stream({"messages": [input_message]}, config, stream_mode="values"):
    event["messages"][-1].pretty_print()
