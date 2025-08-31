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