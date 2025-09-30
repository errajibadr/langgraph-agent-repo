"""Clarify Graph implementation.

This module contains the main graph factory function for creating
clarification workflows that help disambiguate user queries.
"""

from datetime import datetime
from typing import Literal, Type

from ai_engine.agents.base.utils import get_user_context
from ai_engine.agents.clarify_agent.prompts.clarify_prompts import CLARIFY_AIOPS_PROMPT
from ai_engine.agents.clarify_agent.states import ClarifyContext, ClarifyState, ClarifyWithUser
from ai_engine.models.custom_chat_model import create_chat_model
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command


def get_clarify_graph(
    state_schema: type[ClarifyState] = ClarifyState,
    input_schema: Type[ClarifyState] | None = None,
    output_schema: Type[ClarifyState] | None = None,
    context_schema: Type[ClarifyContext] | None = ClarifyContext,
    *,
    name: str | None = None,
    system_prompt: str | None = None,
    research_brief: bool = False,
    max_rounds: int = 3,
    is_subgraph: bool = False,
    parent_next_node: str = "__end__",
    **kwargs,
) -> CompiledStateGraph[ClarifyState, ClarifyContext, ClarifyState, ClarifyState]:
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

    async def model_node(state: ClarifyState, runtime: Runtime[ClarifyContext]) -> Command:
        """Main clarification node that processes user queries.

        This node uses an LLM to determine if clarification is needed
        and generates appropriate questions or verification messages.
        """
        context = runtime.context or {}
        runtime_prompt = runtime.context.get("clarify_system_prompt", "") if runtime.context else ""
        model = context.get("model")
        print(f"iteration: {state.get('current_round', 0)}")
        # Prepare template parameters with defaults
        params = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_context": get_user_context(context.get("user_id")),
            "clarification_round": state["current_round"],
            "max_rounds": state.get("max_rounds", max_rounds),
            "current_incidents_alerts": context.get("current_incidents_alerts", "No current incidents or alerts"),
            "aiops_vocabulary": context.get("aiops_vocabulary", "Standard AI-OPS terminology"),
        }

        prompt_template = runtime_prompt or system_prompt or CLARIFY_AIOPS_PROMPT.format(**params)
        system_message = SystemMessage(content=prompt_template)

        model = create_chat_model(model=model).with_structured_output(ClarifyWithUser)

        # Get clarification response
        clarify_response: ClarifyWithUser = await model.ainvoke(
            [system_message, *state.get("messages", [])], config={"tags": ["clarify_agent", "structured_output"]}
        )  # type: ignore : typing Known limitations for langchain w/ pydantic v1/v2 mismatches

        command_config = {"goto": "__end__"}
        # Determine next step
        goto: Literal["__end__", "research_brief_node"]
        if not clarify_response.need_clarification and research_brief:
            goto = "research_brief_node"
        else:
            goto = "__end__"

        command_config["goto"] = goto
        if is_subgraph and goto == "__end__":
            command_config["graph"] = Command.PARENT
            command_config["goto"] = parent_next_node if not clarify_response.need_clarification else "__end__"

        return Command(
            goto=command_config["goto"],
            graph=command_config.get("graph", None),
            update={
                "current_round": +1,
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
    graph = StateGraph(
        state_schema=state_schema, input_schema=input_schema, output_schema=output_schema, context_schema=context_schema
    )

    async def research_brief_node(state: ClarifyState):
        return {"messages": [AIMessage(content="Enriching query...")]}

    # Add nodes
    graph.add_node("clarification_node", model_node)
    graph.add_node("research_brief_node", research_brief_node)

    # Add edges
    graph.add_edge(START, "clarification_node")
    graph.add_edge("research_brief_node", END)

    # Compile and return
    compiled_graph = graph.compile(name=name or "ClarifyAgent", **kwargs)
    return compiled_graph
    #
    #
    #
    #
    #
