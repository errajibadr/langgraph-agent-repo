"""Clarify Graph implementation.

This module contains the main graph factory function for creating
clarification workflows that help disambiguate user queries.
"""

from datetime import datetime
from typing import Literal, TypeVar

from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph.typing import InputT, OutputT

from ai_engine.agents.base.utils import get_user_context
from ai_engine.agents.clarify_agent.prompts.clarify_prompts import CLARIFY_AIOPS_PROMPT
from ai_engine.agents.clarify_agent.states import ClarifyState, ClarifyWithUser
from ai_engine.models.custom_chat_model import create_chat_model

# Type variable for state schema
StateT = TypeVar("StateT")


def get_clarify_graph(
    state_schema: type[StateT] = ClarifyState,
    input_schema: type[InputT] | None = None,
    output_schema: type[OutputT] | None = None,
    *,
    name: str | None = None,
    system_prompt: str | None = None,
    enrich_query_enabled: bool = False,
    **kwargs,
) -> CompiledStateGraph:
    """Create a clarify graph for disambiguating user queries.

    This factory function creates a LangGraph workflow that helps clarify
    ambiguous user queries before routing them to specialist agents.

    Args:
        state_schema: The state schema type to use for the graph
        name: Optional name for the compiled graph
        system_prompt: Optional custom system prompt (defaults to CLARIFY_AIOPS_PROMPT)
        enrich_query_enabled: Whether to enable query enrichment node
        **kwargs: Additional arguments passed to graph.compile()

    Returns:
        Compiled state graph for clarification workflow
    """

    input_schema = input_schema or state_schema
    output_schema = output_schema or state_schema

    def model_node(state: state_schema, runtime: Runtime[state_schema]) -> Command[Literal["__end__", "enrich_query"]]:
        """Main clarification node that processes user queries.

        This node uses an LLM to determine if clarification is needed
        and generates appropriate questions or verification messages.
        """
        context = runtime.context or {}
        runtime_prompt = runtime.context.get("clarify_system_prompt", "") if runtime.context else ""

        # Prepare template parameters with defaults
        params = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_context": get_user_context(context.get("user_id", "")),
            "clarification_round": state.get("current_round", 0),
            "max_rounds": state.get("max_rounds", 3),
            "current_incidents_alerts": context.get("current_incidents_alerts", "No current incidents or alerts"),
            "aiops_vocabulary": context.get("aiops_vocabulary", "Standard AI-OPS terminology"),
        }

        # Use custom prompt or default
        prompt_template = runtime_prompt or system_prompt or CLARIFY_AIOPS_PROMPT.format(**params)
        system_message = SystemMessage(content=prompt_template)

        # Create model with structured output
        model = create_chat_model().with_structured_output(ClarifyWithUser)

        # Get clarification response
        clarify_response: ClarifyWithUser = model.invoke(input=[system_message, *state.get("messages", [])])  # type: ignore : typing Known limitations for langchain w/ pydantic v1/v2 mismatches

        # Determine next step
        goto = "__end__" if not (clarify_response.need_clarification or enrich_query_enabled) else "enrich_query"

        return Command(
            goto=goto,
            update={
                "current_round": state.get("current_round", 0) + 1,
                "messages": [
                    AIMessage(
                        content=clarify_response.question
                        if clarify_response.need_clarification
                        else clarify_response.verification
                    )
                ],
                "artifacts": clarify_response.artifacts,
            },
        )

    # Build the graph
    graph = StateGraph(state_schema=state_schema, input_schema=input_schema, output_schema=output_schema)

    # Add nodes
    graph.add_node("clarify", model_node)
    graph.add_node("enrich_query", lambda state: {})

    # Add edges
    graph.add_edge(START, "clarify")
    graph.add_edge("enrich_query", END)

    # Compile and return
    compiled_graph = graph.compile(name=name or "ClarifyAgent", **kwargs)
    return compiled_graph
