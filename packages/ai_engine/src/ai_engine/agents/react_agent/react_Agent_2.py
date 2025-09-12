from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, Type, TypeVar, Union

from ai_engine.agents.scratchpad.scratch_agent import get_weather
from ai_engine.models.custom_chat_model import CustomChatModel
from ai_engine.tools.reflection_tool import think_tool
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage, trim_messages
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.managed import RemainingSteps
from langgraph.prebuilt import InjectedState, ToolNode, create_react_agent
from langgraph.prebuilt.chat_agent_executor import (
    AgentState,
    AgentStatePydantic,
    StateSchema,
    StateSchemaType,
    StructuredResponse,
    StructuredResponseSchema,
)
from langgraph.types import Command, Interrupt, interrupt
from pydantic import BaseModel, Field
from typing_extensions import Annotated, TypedDict

# Type variables for generic state schemas
StateT = TypeVar("StateT", bound=Union[AgentState, AgentStatePydantic, TypedDict, BaseModel])
InputT = TypeVar("InputT", bound=Union[TypedDict, BaseModel])
OutputT = TypeVar("OutputT", bound=Union[TypedDict, BaseModel])

# Default system prompt template
DEFAULT_SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI assistant.
You have access to tools to help answer questions.
If you don't have the answer for an ambiguous question, you can ask the user for clarification.


When using tools:
- Use the appropriate tool based on the user's question
- Always provide clear explanations of your findings
- If you need more information, ask follow-up questions

User: {user}
Current time: {current_time}
"""


class WeatherAgentStatePydantic(BaseModel):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    weather_messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)
    query: str | None = None
    remaining_steps: RemainingSteps = 5


class InputWeatherAgentStatePydantic(BaseModel):
    """The input state of the agent."""

    query: str
    messages: Annotated[Sequence[BaseMessage], add_messages]


class Summary(BaseModel):
    summary: str = Field(description="The summary of the weather, if unknown, should be specified")
    temperature: float | None = Field(
        default=None, description="The temperature of the weather; if unknown, should be None"
    )


class OutputWeatherAgentStatePydantic(BaseModel):
    """The output state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: Summary


class PydanticReactAgent:
    """React Agent class with modern type hints following LangGraph patterns."""

    def __init__(
        self,
        name: str,
        model: CustomChatModel,
        tools: List[BaseTool | Callable],
        *,
        # State schemas with proper type hints
        state_schema: Optional[StateSchemaType] = None,
        input_schema: Optional[Type[InputT]] = None,
        output_schema: Optional[Type[OutputT]] = None,
        # Response format with modern typing
        response_format: Optional[Union[StructuredResponseSchema, tuple[str, StructuredResponseSchema]]] = None,
        system_prompt_template: str = DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    ):
        self.name = name
        self.model = model
        self.tools = tools

        # Handle tools binding
        if self.tools:
            self.model = self.model.bind_tools(self.tools, parallel_tool_calls=True)

        # Store schema types with proper typing
        self.state_schema: StateSchemaType = state_schema or AgentStatePydantic
        self.input_schema: Optional[Type[InputT]] = input_schema
        self.output_schema: Optional[Type[OutputT]] = output_schema
        self.response_format = response_format
        self.system_prompt_template = system_prompt_template

    def call_model(self, state: StateT) -> StateT:
        """Call the model with current state."""
        return self.state_schema(
            messages=[
                self.model.invoke(
                    input=[self.system_prompt_template, *state.messages],
                )
            ],
            remaining_steps=state.remaining_steps - 1,
        )

    def format_response(self, state: StateT) -> OutputT:
        """Format the response using structured output."""
        if not self.response_format:
            raise ValueError("response_format must be provided for format_response")

        model = self.model.with_structured_output(self.response_format)
        summary = model.invoke(
            input=state.messages, model="openai/gpt-oss-120b", config={"run_name": "Structured Output"}
        )

        # Handle different output schema types
        if self.output_schema:
            return self.output_schema(summary=summary, messages=[AIMessage(content=str(summary))])
        else:
            # Fallback to default output structure
            return type("OutputState", (), {"summary": summary, "messages": [AIMessage(content=str(summary))]})()

    def post_llm_node_condition(
        self, state: Union[AgentState, AgentStatePydantic]
    ) -> Literal["tool_node", "format_response", "__end__"]:
        """Determine next node based on LLM response."""
        print("remaining steps", state.remaining_steps)
        if isinstance(state.messages[-1], AIMessage) and state.messages[-1].tool_calls:
            print("calling tool id", state.messages[-1].tool_calls[0].get("id"))
            return "tool_node"
        if self.response_format:
            return "format_response"
        return "__end__"

    def _get_state_dict(self) -> Dict[str, Any]:
        """Get state schema dictionary for StateGraph."""
        state_dict = {
            "state_schema": self.state_schema,
        }
        if self.input_schema:
            state_dict["input_schema"] = self.input_schema
        if self.output_schema:
            state_dict["output_schema"] = self.output_schema

        return state_dict

    def get_graph(self) -> CompiledStateGraph:
        """Build and compile the agent graph."""
        graph = StateGraph(**self._get_state_dict())

        graph.add_node("call_model", self.call_model)
        graph.add_node("tool_node", ToolNode(tools=self.tools, tags=[f"{self.name}_tool_node"]))

        if self.response_format:
            graph.add_node("format_response", self.format_response)

        graph.add_edge(START, "call_model")

        # Set up conditional edges
        conditional_edges = {"format_response": "format_response", "tool_node": "tool_node", "__end__": END}
        if not self.response_format:
            conditional_edges.pop("format_response")

        graph.add_conditional_edges(
            "call_model",
            self.post_llm_node_condition,
            conditional_edges,
        )

        graph.add_edge("tool_node", "call_model")

        if self.response_format:
            graph.add_edge("format_response", END)

        return graph.compile(name=self.name, checkpointer=MemorySaver())


# Example usage with modern patterns
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    def get_weather(city: str) -> str:
        """Get the weather in a city, should be a legit city like Paris, London, etc."""
        import random

        weather_conditions = ["sunny", "cloudy", "rainy", "stormy", "snowy"]

        return f"The weather in {city} is {random.choice(weather_conditions)}."

    def get_location():
        """Find user localization"""
        raise Exception("No localization found")

    def escalate_to_user(clarification_question: str) -> str:
        """If you need anything from the user, escalate to him."""
        message = f"{clarification_question}"
        feedback = interrupt(value=message)
        return feedback

    model = CustomChatModel(provider="groq")

    # Example with structured response format
    response_format = Summary

    # Create agent with modern schema typing
    weather_agent = PydanticReactAgent(
        name="weather_agent",
        model=model,
        tools=[get_weather, escalate_to_user, get_location],
        state_schema=WeatherAgentStatePydantic,
        input_schema=InputWeatherAgentStatePydantic,
        output_schema=OutputWeatherAgentStatePydantic,
        response_format=response_format,
        system_prompt_template=DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    )

    weather_graph = weather_agent.get_graph()

    def call_weather_agent(state: Annotated[WeatherAgentStatePydantic, InjectedState]):
        """Call the weather agent"""
        response = weather_graph.invoke(
            InputWeatherAgentStatePydantic(
                messages=[state.messages[0]],
                query="Please find the weather from user messages",
            )
        )
        print(response.keys())
        return response.get("summary")

    # Supervisor agent with modern typing
    supervisor_agent = PydanticReactAgent(
        name="supervisor_agent",
        model=model,
        tools=[think_tool, call_weather_agent],
        state_schema=AgentStatePydantic,
        input_schema=AgentStatePydantic,
        system_prompt_template=DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    )

    graph = supervisor_agent.get_graph()

    first_message = AgentStatePydantic(messages=[HumanMessage("What's the weather in Paris?")])
    last_message = None
    for agent_name, mode, chunk in graph.stream(
        first_message,
        config={
            "configurable": {
                "thread_id": "thread-1",
                "project_name": "MyCustomProjectName",
                "metadata": {"user": "John", "project_name": "MyCustomProjectName_e"},
                "langsmith_extra": {"project_name": "My Project"},
            }
        },
        stream_mode=["values", "updates"],
        subgraphs=True,
    ):
        if mode == "values" and "messages" in chunk:
            messages = chunk.get("messages", [])
            message = messages[-1]
            if message != last_message:
                print(f"---------------------------------------{agent_name}---------------------------------------")
                last_message = message
                chunk_without_messages = {k: v for k, v in chunk.items() if k != "messages"}
                print(chunk_without_messages)
                print(message.pretty_print())
                print("--------------------------------")

        elif mode == "updates" and "__interrupt__" in chunk:
            print(chunk.get("__interrupt__")[0].value)
            feedback = input("Do you have anything to add?") or "continue"
            for chunk in graph.stream(
                Command(resume=feedback),
                config={"configurable": {"thread_id": "thread-1"}},
                stream_mode="values",
            ):
                print(chunk.get("messages", [])[-1].pretty_print())
