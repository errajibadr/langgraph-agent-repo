import operator
from typing import Annotated, Literal, Optional, TypedDict

from ai_engine.models.custom_chat_model import CustomChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, BaseMessage, add_messages
from langgraph.types import Send
from pydantic import BaseModel, Field, field_validator, validator


class GlobalStateSchema(TypedDict):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    topic: str
    subjects: list[str]
    jokes: Annotated[list[str], operator.add]
    best_joke: int
    joke: str


class InputState(BaseModel):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]


class OutputState(BaseModel):
    joke: str
    topic: str


class Topic(BaseModel):
    topic: str = Field(description="The topic of the message")


class Subjects(BaseModel):
    subjects: list[str] = Field(description="The subjects based on the topic")


def identify_topic(state: GlobalStateSchema) -> GlobalStateSchema:
    model = CustomChatModel()
    response = model.with_structured_output(Topic).invoke(
        [
            SystemMessage(
                content="You are a helpful assistant that identifies the topic of the user message on which we will generate a joke"
            )
        ]
        + state["messages"]
    )
    return {"topic": response.topic}


def generate_subjects(state: GlobalStateSchema) -> GlobalStateSchema:
    model = CustomChatModel()
    response = model.with_structured_output(Subjects).invoke(
        [
            SystemMessage(
                content=f"You are a helpful assistant that generates 5 subjects based on the topic {state['topic']} to generate jokes on"
            )
        ]
    )
    return {"subjects": response.subjects}


class JokeState(BaseModel):
    subject: str


def continue_to_jokes(state: GlobalStateSchema):
    return [Send("generate_joke", JokeState(subject=subject)) for subject in state["subjects"]]


def generate_joke(state: JokeState) -> GlobalStateSchema:
    model = CustomChatModel()
    response = model.invoke(
        [SystemMessage(content=f"You are a helpful assistant that generates a joke on the subject {state.subject}")]
    )
    return {"jokes": [response.content]}


class BestJoke(BaseModel):
    best_joke_index: int
    reason: str


def find_best_joke(state: GlobalStateSchema):
    model = CustomChatModel().with_structured_output(BestJoke)
    response = model.invoke(
        [
            SystemMessage(
                content=f"You are a helpful assistant that finds the best joke from the following jokes: \n{'\n'.join([f'{i}: {joke}' for i, joke in zip(range(len(state['jokes'])), state['jokes'])])}"
            )
        ]
    )
    return {"best_joke": response.best_joke_index}


def generate_response(state: GlobalStateSchema):
    return {
        "messages": [AIMessage(content=f"Here is the best joke i can think of: {state['jokes'][state['best_joke']]}")]
    }


joke_graph = StateGraph(GlobalStateSchema, input_schema=InputState, output_schema=OutputState)
joke_graph.add_node("identify_topic", identify_topic)
joke_graph.add_node("generate_subjects", generate_subjects)
joke_graph.add_node("continue_to_jokes", continue_to_jokes)
joke_graph.add_node("generate_joke", generate_joke)
joke_graph.add_node("find_best_joke", find_best_joke)
joke_graph.add_node("generate_response", generate_response)

joke_graph.add_edge(START, "identify_topic")
joke_graph.add_edge("identify_topic", "generate_subjects")
joke_graph.add_conditional_edges("generate_subjects", continue_to_jokes, ["generate_joke"])
joke_graph.add_edge("generate_joke", "find_best_joke")
joke_graph.add_edge("find_best_joke", "generate_response")
joke_graph.add_edge("generate_response", END)


compiled_joke_graph = joke_graph.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    for chunk in compiled_joke_graph.stream(
        InputState(
            messages=[HumanMessage("i want to have fun about something related to dogs and loyalty?", name="hammy")]
        ),
        config={"configurable": {"thread_id": "thread-2"}},
        stream_mode=["updates"],
    ):
        print(chunk)
