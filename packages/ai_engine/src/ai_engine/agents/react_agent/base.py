"""Generic React Agent base class with full type safety."""

from typing import Any, Dict, Generic, List, Literal, Optional, Type, Union, overload

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.chat_agent_executor import AgentState, AgentStatePydantic

from ai_engine.models.custom_chat_model import CustomChatModel

from .types import DEFAULT_SYSTEM_PROMPT_TEMPLATE, InputT, OutputT, StateT, StructuredResponseSchema, ToolType


class PydanticReactAgent(Generic[StateT, InputT, OutputT]):
    """
    Generic React Agent class with full type safety.

    This class provides a type-safe way to create React agents with different
    state schemas while preserving type information at both compile-time and runtime.

    Type Parameters:
        StateT: The main state schema type (AgentState, AgentStatePydantic, or custom BaseModel)
        InputT: The input state schema type (defaults to StateT if not provided)
        OutputT: The output state schema type (defaults to StateT if not provided)

    Example:
        ```python
        # Create a weather agent with specific state types
        weather_agent: PydanticReactAgent[
            WeatherAgentStatePydantic,
            InputWeatherAgentStatePydantic,
            OutputWeatherAgentStatePydantic
        ] = PydanticReactAgent(
            name="weather_agent",
            model=model,
            tools=[get_weather, escalate_to_user],
            state_schema=WeatherAgentStatePydantic,
            input_schema=InputWeatherAgentStatePydantic,
            output_schema=OutputWeatherAgentStatePydantic,
            response_format=Summary,
        )
        ```
    """

    def __init__(
        self,
        name: str,
        model: CustomChatModel,
        tools: List[ToolType],
        *,
        state_schema: Type[StateT],
        input_schema: Optional[Type[InputT]] = None,
        output_schema: Optional[Type[OutputT]] = None,
        response_format: Optional[StructuredResponseSchema] = None,
        system_prompt_template: str = DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    ):
        """
        Initialize the React Agent with type-safe schema definitions.

        Args:
            name: Agent name for identification
            model: The language model to use
            tools: List of tools available to the agent
            state_schema: Main state schema class (required)
            input_schema: Input state schema class (optional, defaults to state_schema)
            output_schema: Output state schema class (optional, defaults to state_schema)
            response_format: Structured response format schema (optional)
            system_prompt_template: System prompt template string
        """
        self.name = name
        self.model = model
        self.tools = tools

        # Bind tools to model if provided
        if self.tools:
            self.model = self.model.bind_tools(self.tools, parallel_tool_calls=True)

        # Store schema types with runtime type information
        self.state_schema: Type[StateT] = state_schema
        self.input_schema: Type[Union[InputT, StateT]] = input_schema or state_schema
        self.output_schema: Type[Union[OutputT, StateT]] = output_schema or state_schema

        self.response_format = response_format
        self.system_prompt_template = system_prompt_template

        # Validate schema compatibility at runtime
        self._validate_schemas()

    def _validate_schemas(self) -> None:
        """Validate that all schemas are compatible and properly defined."""
        # Basic validation - can be extended based on requirements
        if not hasattr(self.state_schema, "__annotations__"):
            raise ValueError(f"state_schema {self.state_schema} must have type annotations")

        # Ensure required fields exist in state schema
        annotations = getattr(self.state_schema, "__annotations__", {})
        if "messages" not in annotations:
            raise ValueError("state_schema must have a 'messages' field")
        if "remaining_steps" not in annotations:
            raise ValueError("state_schema must have a 'remaining_steps' field")

    def call_model(self, state: StateT) -> StateT:
        """
        Call the language model with the current state.

        Args:
            state: Current agent state

        Returns:
            Updated state with model response
        """
        return self.state_schema(
            messages=[
                self.model.invoke(
                    input=[self.system_prompt_template, *state.messages],  # type: ignore
                )
            ],
            remaining_steps=state.remaining_steps - 1,  # type: ignore
        )

    def format_response(self, state: StateT) -> Union[OutputT, StateT]:
        """
        Format the final response using structured output.

        Args:
            state: Current agent state

        Returns:
            Formatted response in the output schema format
        """
        if not self.response_format:
            # If no response format specified, return state as-is
            return state

        model = self.model.with_structured_output(self.response_format)
        summary = model.invoke(
            input=state.messages,  # type: ignore
            model="openai/gpt-oss-120b",
            config={"run_name": "Structured Output"},
        )

        # Create output using the output schema
        return self.output_schema(summary=summary, messages=[AIMessage(content=str(summary))])

    def post_llm_node_condition(self, state: StateT) -> Literal["tool_node", "format_response", "__end__"]:
        """
        Determine the next node based on the LLM response.

        Args:
            state: Current agent state

        Returns:
            Next node name to execute
        """
        print(f"remaining steps: {state.remaining_steps}")  # type: ignore

        # Check if we have tool calls to execute
        messages = getattr(state, "messages", [])
        if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
            print(f"calling tool id: {messages[-1].tool_calls[0].get('id')}")
            return "tool_node"

        # Check if we need to format the response
        if self.response_format:
            return "format_response"

        return "__end__"

    def _get_state_dict(self) -> Dict[str, Any]:
        """
        Get state schema dictionary for StateGraph construction.

        Returns:
            Dictionary with schema information for LangGraph
        """
        state_dict = {
            "state_schema": self.state_schema,
        }

        # Only add input/output schemas if they differ from state schema
        if self.input_schema != self.state_schema:
            state_dict["input_schema"] = self.input_schema

        if self.output_schema != self.state_schema:
            state_dict["output_schema"] = self.output_schema

        return state_dict

    def get_graph(self) -> CompiledStateGraph:
        """
        Build and compile the agent graph.

        Returns:
            Compiled LangGraph StateGraph ready for execution
        """
        # Create the graph with proper schema information
        graph = StateGraph(**self._get_state_dict())

        # Add core nodes
        graph.add_node("call_model", self.call_model)
        graph.add_node("tool_node", ToolNode(tools=self.tools, tags=[f"{self.name}_tool_node"]))

        # Add format_response node only if response_format is specified
        if self.response_format:
            graph.add_node("format_response", self.format_response)

        # Set up edges
        graph.add_edge(START, "call_model")

        # Set up conditional edges based on available nodes
        conditional_edges = {"tool_node": "tool_node", "__end__": END}

        if self.response_format:
            conditional_edges["format_response"] = "format_response"

        graph.add_conditional_edges(
            "call_model",
            self.post_llm_node_condition,
            conditional_edges,
        )

        # Connect tool node back to model
        graph.add_edge("tool_node", "call_model")

        # Connect format_response to end if it exists
        if self.response_format:
            graph.add_edge("format_response", END)

        return graph.compile(name=self.name, checkpointer=MemorySaver())


# Type-safe factory functions for common use cases
def create_simple_agent(
    name: str,
    model: CustomChatModel,
    tools: List[ToolType],
    *,
    state_schema: Type[StateT] = AgentStatePydantic,  # type: ignore
    system_prompt_template: str = DEFAULT_SYSTEM_PROMPT_TEMPLATE,
) -> PydanticReactAgent[StateT, StateT, StateT]:
    """
    Create a simple React agent with the same schema for input/output/state.

    Args:
        name: Agent name
        model: Language model
        tools: Available tools
        state_schema: State schema to use for all state types
        system_prompt_template: System prompt template

    Returns:
        Configured React agent
    """
    return PydanticReactAgent(
        name=name,
        model=model,
        tools=tools,
        state_schema=state_schema,
        system_prompt_template=system_prompt_template,
    )
