5_Langsmith_cheatsheet.md

## Basics: 

Add LANGSMITH_TRACING
- LANGSMITH_API_KEY
- LANGSMITH_PROJECT_NAME

- using @traceable decorator to explicitly trace a function
--> we can add metadata in the decorator to trace more details about the run
hint : adding model name/ provider allows langsmith to compute the cost of the run

In langchain functions it's already traced.

## RUN TYPE
UI sugar :
 llm / tool / chain(default)/ retriever / Parser / Prompt

using reducers for llm calls 

```python
def _reduce_chunks(chunks: list):
    all_text = "".join([chunk["choices"][0]["message"]["content"] for chunk in chunks])
    return {"choices": [{"message": {"content": all_text, "role": "assistant"}}]}
```

## Tracing types : 

### traceable decorator
manages innput and output for us 
```python
@traceable 
()

```

### LANGChain runnables - out of the box tracing
update in config={"configurable": {"thread_id": "thread-1"},"metadata":{"foo":"bar"}}

### OPEN AI Wrapper 
extra_langsmith arguments in the wrapper

### with trace 
context manager to trace a block of code
trace.end(outputs={...})



### RunTree -Advanced - 
To manually create and propagate traces 
