# Langgraph Cheatsheet

## State & Memory
###  State class : 
Can be either :  
- TypedDict
- Dataclass
- Pydantic BaseModel - to enforce type safety

### State Reducers :

```
class Basic GraphState(TypedDict):
    cumulative: int = 1

def node_1(state: BasicGraphState, event: int) -> BasicGraphState:
    return {"cumulative": 3}

...
graph.invoke()
```

will return state with cumulative = 3 ( basic implem ovverides existing value)


```
def add_ints(left: int, right: int) -> int:
    return left + right

class GraphState(TypedDict):
    cumulative: Annotated[int, add_ints] = 1

def node_1(state: GraphState, event: int) -> GraphState:
    return {"cumulative": 3}
```

will return state with cumulative = 4 because of the reducer add_ints


### Multiple State Schemas : 

You might not want to expose the overall Graph state to the user.

that case you can define an input schema and an output schema.

```
class OverallState(BaseModel):
    messages: list[AnyMessage | BaseMessage]
    mood: str = Literal["happy", "sad", "neutral"]

class InputState(BaseModel):
    messages: list[AnyMessage | BaseMessage]

class OutputState(BaseModel):
    mood: str = Literal["happy", "sad", "neutral"]
```

### Edit state : 

Breakpoint + update the state before resuming the graph.
compiled_graph.update_state(
            config=config,
            values=HumanMessage...,
            as_node="node_name",
        )

or 
graph.get_state(config)
Then current_state['values']['messages'][-1]


### MemorySaver : 

InMemorySaver is a simple in-memory state saver that can be used to save the state of the graph for the graph runtime.

to keep the state between invocations, we need to use a `persistant` checkpointer. (slite, postgres, redis?)

```
from langgraph.checkpoint.memory import InMemorySaver

saver = InMemorySaver()
```

```
from sqlite3
conn = sqlite3.connect("langgraph.db")

from langgraph.checkpoint.sqlite import SqliteSaver
saver = SqliteSaver(conn)
```

## Graphs
### Interrupt : 

#### Static Interrupt : 
```
compiled_graph = graph.compile(checkpointer=saver, interrupt_before=["node_name"])
```

or
```

#### Dynamically Interrupt : 
```
node():
 response = interrupt(message_prompt)


# in runtime 
graph.stream(Command(resume=user_input), config=config)
```



### Command : 

How to inject tool call id

def create_handoff_tool(*, agent_name: str, description: str | None = None):
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer to {agent_name}"

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState], 
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": name,
            "tool_call_id": tool_call_id,
        }
        return Command(  
            goto=agent_name,  
            update={"messages": state["messages"] + [tool_message]},  
            graph=Command.PARENT,  
        )
    return handoff_tool

@tool
def update_user_name(
    new_name: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Update user-name in short-term memory."""
    return Command(update={
        "user_name": new_name,
        "messages": [
            ToolMessage(f"Updated user name to {new_name}", tool_call_id=tool_call_id)
        ]
    })

### Parallelism : 

When updating the state simultaneously in multiple nodes, use a state reducer to merge the states.

### Subgraphs : 

Parent graph and subgraph must have the same key schema to "communicate" data between them.

```python
class ParentState(BaseModel):
    raw_logs: list[str]
    reports: list[str]
    summary: str

class SummarySubgraphState(BaseModel):
    raw_logs: list[str]
    summary: str
    key_abc: Any

class ReportsSubgraphState(BaseModel):
    raw_logs: list[str]
    reports: list[str]
    key_xyz: Any

graph = StateGraph(ParentState)
summary_subgraph = StateGraph(SummarySubgraphState)
reports_subgraph = StateGraph(ReportsSubgraphState)
graph.add_node("summary_subgraph", summary_subgraph.compile())
graph.add_node("reports_subgraph", reports_subgraph.compile())

graph.add_edge(Start, "node_1")
graph.add_edge("node_1", "summary_subgraph")
graph.add_edge("node_1", "reports_subgraph")
graph.add_edge("summary_subgraph", "node_2")
graph.add_edge("reports_subgraph", "node_2")
graph.add_edge("node_2", END)
```

### Memory : 

Short terme memory is State memory that is kept for a given `Thread`(generally it's a conversation).

--> we use checkpointer to save the state.

Long term memory is State memory that is kept for a given `object`(generally User for instance).

--> we use a store to save the long terme memory

### StateGraph : 

```python
graph = StateGraph(StateSchema)
```

## Langgraph Platform : 

Langgraph SDK --> create agents which are the graph.py:graph_agents

langgraph platform --> Deploy agents to langgraph Server
comes w/ streamling/Human in the loop/ Short term/Long term memory management.
+ cron features / Background agents / Double texting + "Assistant" feature

Server architecture is as follows :
task worker + http worker (to communicate with client)
Redis pub/sub for workers to communicate with each other
Postgres for state management & persistence

Langgraph Client --> communicate with server/ Run "remote graphs" 

Langgraph CLI --> helps buildng some "DOCKER" image for the server.

Server can be either fully managed / BYOC / self-hosted

--> I want to deep dive into thep "Assistant" feature + Cli Docker image creationx@
Langgraph

### Build Docker image : 

```
langgraph build -t langgraph-server:latest
```

you need to have the configuration file in the root of the project.
```langgraph.json
{
  "python_version": "3.12",
  "dependencies": [".", "../core"],
  "graphs": {
    "chat": "ai_engine.agents.agent_1:graph",
    "scratch": "ai_engine.agents.scratch_agent:graph",
    "joker": "ai_engine.agents.scratch_agent_map_reduce:compiled_joke_graph"
  },
  "image_distro": "wolfi"
}
```

it still needs Redis & Postgres to be running.
so a docker compose file is needed to run the server.
```docker-compose.yaml
volumes:
    langgraph-data:
        driver: local
services:
    langgraph-redis:
        image: redis:6
    langgraph-postgres:
        image: postgres:16
    langgraph-api:
        image: "{built_image_name}:latest"
        ports:
            - "8123:8000"
        depends_on:
            - langgraph-redis
            - langgraph-postgres
```
and define POSTGRES_URI & REDIS_URI in the environment variables.
and Atleast LANGSMITH_API_KEY or LANGGRAPH_CLOUD_LICENSE_KEY

### Run Client : 

```python
from langgraph_sdk.client import get_client

url_for_cli_deployment = "http://localhost:8123"
client = get_client(url=url_for_cli_deployment)
```

There is also the "RemoteGraph" concept which
allows you to import a graph from langgraph library.
```Remote Graph : 
graph = RemoteGraph("graph_name", url)
```

We can execute the graph by "running" it remotely.
Fire and forget - async API 
blocking / Polling - sync/Async API


### Double texting : 

4 strategies allowed in Langgraph server when calling run.stream 

Reject Interrupt Enqueue Rollback 

Reject --> interrupt is rejected and the run is continued.
Interrupt --> The run is interrupted (tools & messages history kept) and a new run is created.
Enqueue --> interrupt is enqueued and thread emits second run with euqueued message.
Rollback --> current run is rolled back and a new run is created.

### Assistants : 
Assistant is a graph but with custom configraution to customize it's behavior.

Usually done with context and 
accessed in nodes

```python
def node(state: State, runtime: Runtime[ContextSchema]):
    runtime.context == {"model":"custom", "system_prompt":"this is a custom system prompt"}
    ...
    return state
```

## Runtime

### init :

```python
class ContextSchema(BaseModel):
    model: str
    system_prompt: str

graph = StateGraph(StateSchema, context_init=ContextSchema)
```

### USing runtime context

```python
from langgraph.runtime import Runtime

def node_a(state: State, runtime: Runtime[ContextSchema]):
    llm = get_llm(runtime.context.llm_provider)
    ...

from langgraph.runtime import get_runtime

def tool(i: int) -> int:
    rt= get_runtime(ContextSchema)
    ${rt.context.context_var}...
```

###  Dynamic model choice w/ runtime 
```python
def select_model(state: AgentState, runtime: Runtime[CustomContext]) -> BaseChatModel:
    if runtime.context.provider == "anthropic":
        model = anthropic_model
    elif runtime.context.provider == "openai":
        model = openai_model
    else:
        raise ValueError(f"Unsupported provider: {runtime.context.provider}")

    # With dynamic model selection, you must bind tools explicitly
    return model.bind_tools([weather])
```