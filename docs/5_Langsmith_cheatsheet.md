5_Langsmith_cheatsheet.md

## Tracing Basics: 

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


## Evaluations ( Datasets, evaluators, experiments and summary evaluators )

### Datasets 
(Manually or in UI) We can create dataset w/ input schema and output schema to normalize the data.
```python
client.create_dataset(
    dataset_name="my_dataset",
    description="A dataset for my model",
    input_schema=InputSchema,
    output_schema=OutputSchema,
)
```

### Evaluators

in UI directly 

in code directly:  Evaluator functions takes output and reference output.
target func to evaluate. dataset name or id and evaluators list. 


```python
dataset = client.list_examples(dataset_name="my_dataset", splits=["train", "test"])


client.evaluate(
    target_func,
    data="my_dataset",
    evaluators=[evaluator1, evaluator2],
    experiment_prefix="my_experiment",
    num_repetitions=x,
    max_concurrency=x,
    metadata={"foo":"bar"},
)
```

### Experiments

#### Pairwise experiments
In the case it's difficult to see based on a metric if the model is improving or not.
we can compare runs to have more precise evaluation.

```python
def pairwise_evaluator(inputs: dict, outputs: List[dict]) -> dict:
    compare outputs[0] vs outputs[1]
    ...
    return {
        "key": "pairwise_score",
        "score": [0,1], # means output of experiment 2 is better
    }

client.evaluate(
    (experiment_id_1, experiment_id_2),
    evaluators=[pairwise_evaluator],
)
```

#### Summary evaluators

Can only be run on the entire dataset and have no real significance for asingle run of example.

```python
def f1_score_evaluator(outputs: List[dict], reference_outputs: List[dict]) -> dict:
    for i in zip(outputs, reference_outputs):
        f1 score logic ...


client.evaluate(
    target_func,
    data="my_dataset",
    evaluators=[f1_score_evaluator],
)
```


### Prompt Management

#### Playground:
can iterate on prompts and run live experiments on them given a dataset.

#### PromptHub: 
We can edit our prompts and version them and call them from the code so that we don't need to update the code everytime we change the prompt.
creates a hard dependency on the prompt hub and langchain ecosystem;

#### Prompt Canvas: 
helps us generate prompts using LLMs directly in the UI.

### Human Feedback

#### Fedbacks 


generate run_id and inject it in metadata to allow us to associate the feedback with the run.
```python
from langsmith import client

feedback = {
    "is_correct": True,
    "conciseness": 4,
}

client.create_feedback(
    run_id=run_id,
    feedback=feedback,
)
```

if we want to create feedback from the frontend directly, we should use presigned url to upload the feedback.
```python
presigned_url = client.create_presigned_feedback_token(pre_signed_url_id, "user_presigned_feedback")

# In client side : 
requests.get(f"{presigned_url.url}/is_correct=True")
```


#### Annotation Queues
Adding to queue for human to review and potentially add to dataset

### Prod observalibility 

#### Online Evaluation 

Online evaluators take only input and output. ( unlike offline evaluators that take reference output )

Best practice is to align llm as a judge evaluator with human feedbacks.
1. We add to annotation queus some runs
2. we test them in the evaluator playground to match the human feedbacks
3. Have the evaluator aligned with our feedbacks

Common use cases : 
Did hallucinate : E.g. in rag app : given context, did llm patch up a response ? 


#### Automations 

--> Add to queue/ datasets/ webhook/ Extend data retention 

e.g. 

 for status == FAILED, Notify or ping someone
 Sample 1% of all traces to add to annotation queue then dataset and build up dataset w/ prod data over time
 Sample ALL negative feedbacks to add to anotation queue 
 Sample ALL user positive feedbacks to add to dataset ( or annotation queue to double check)
 for RAG APP : Evaluate if retrieved docs are relevant to the question --> if not, add to anotation queue


#### Monitoring