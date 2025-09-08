# Langgraph Exploration of capabilities

## Leaderboard for tool use
https://www.vellum.ai/llm-leaderboard?utm_source=google&utm_medium=organic

https://huggingface.co/spaces/gorilla-llm/berkeley-function-calling-leaderboard
#not updated



## Workflow Patterns

### Router

### Planner + Executor

### Evaluator + Optimizer (Reflection principle)

### Handoff
[langgraph handoff](https://mirror-feeling-d80.notion.site/Understanding-Multi-agent-Handoffs-1c0808527b17809ca43bf9ef4d11a471)


## Agentic Workflow types : 

### Orchestrator
[ytb.video](https://www.youtube.com/watch?v=4oC1ZKa9-Hs)
Sub agents are used to perform the tasks. 
They have access to all the memory of the orchestrator. 


### Orchestrator with tool use

Sub agents are used to perform the tasks. 
They only have access to what they are given in tool calls. 

### Hierarchical Agentic system







### Swarm 
[ytb.video](https://www.youtube.com/watch?v=JeyDrn1dSUQ)
Agents coordinate between each other to perform the tasks. 
they "hand off" the tasks to each other. 
idea behind is they each have 'tools' to hand-off the tasks to another one.





questions : 
memory saver / checkpointer in langgraph : how does it work?
swarm : how does swarm works?
How does handoffs work



### Streaming with langgraph
    
Streaming Modes Reference
Mode	Description
values	Emits complete state after every node execution
updates	Emits only changes for bandwidth-efficient incremental updates
messages	Streams LLM output token-by-token from any node or subgraph
custom	Streams arbitrary user-defined data via StreamWriter
debug	Streams extensive debug info: node names, full execution state

for custom streaming : 
from langgraph.config import get_stream_writer







