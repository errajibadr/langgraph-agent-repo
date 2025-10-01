"""Clarify Graph implementation.

This module contains the main graph factory function for creating
clarification workflows that help disambiguate user queries.
"""

from datetime import datetime
from logging import getLogger
from typing import Annotated, Callable, Literal, Tuple, Type

from annotated_types import Gt
from core.models.artifacts import Artifact, NotesArtifact
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph, RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command

from ai_engine.agents.base.utils import get_user_context
from ai_engine.agents.base.utils.context_utils import is_subgraph
from ai_engine.agents.clarify_agent.prompts.clarify_prompts import CLARIFY_AIOPS_PROMPT, RESEARCH_BRIEF_PROMPT
from ai_engine.agents.clarify_agent.states import (
    ClarifyContext,
    ClarifyInputState,
    ClarifyState,
    ClarifyWithUser,
    ResearchBrief,
)
from ai_engine.models.custom_chat_model import create_chat_model
from ai_engine.utils.helpers import get_today_date

logger = getLogger(__name__)


def get_clarify_graph(
    state_schema: type[ClarifyState] = ClarifyState,
    input_schema: Type[ClarifyInputState] | None = None,
    output_schema: Type[ClarifyState] | None = None,
    context_schema: Type[ClarifyContext] | None = ClarifyContext,
    *,
    name: str | None = None,
    system_prompt: str | None = None,
    research_brief: bool = True,
    max_iterations: Annotated[int, Gt(0)] = 3,
    circuit_breaker_fn: Callable[[ClarifyState], bool] | None = None,
    parent_next_node: str = "__end__",
    **kwargs,
) -> CompiledStateGraph[ClarifyState, ClarifyContext, ClarifyInputState, ClarifyState]:
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

    def get_context(runtime: Runtime[ClarifyContext]) -> Tuple:
        """Get the context for the clarify graph."""
        context = runtime.context or {}
        return (context.get("user_id", None), context.get("clarify_system_prompt", ""), context.get("model", None))

    def clarification_circuit_breaker(
        state: ClarifyState, config: RunnableConfig
    ) -> Command[Literal["research_brief_node", "clarification_node", "__end__"]]:
        """Circuit breaker node for the clarify graph."""
        logger.warning(f"iteration: {state.get('clarification_iteration', 0)} / {max_iterations}")
        has_reached_max_iterations = state.get("clarification_iteration", 0) >= max_iterations
        should_stop = circuit_breaker_fn(state) if circuit_breaker_fn else False

        if not has_reached_max_iterations and not should_stop:
            return Command(goto="clarification_node")

        if research_brief:
            return Command(
                goto="research_brief_node", update={"clarification_iteration": -state.get("clarification_iteration", 0)}
            )

        ## Fallback to going to end if no research brief is defined
        if not is_subgraph(config):
            return Command(goto="__end__")

        return Command(graph=Command.PARENT, goto="__end__")

    async def clarify_node(state: ClarifyState, runtime: Runtime[ClarifyContext], config: RunnableConfig) -> Command:
        """Main clarification node that processes user queries.

        This node uses an LLM to determine if clarification is needed
        and generates appropriate questions or verification messages.
        """
        # config = get_config()
        user_id, runtime_prompt, model = get_context(runtime)

        params = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_context": get_user_context(user_id),
            "clarification_round": state["clarification_iteration"],
            "max_rounds": max_iterations,
            "current_incidents_alerts": "No current incidents or alerts",
            "aiops_vocabulary": "Standard AI-OPS terminology",
        }

        prompt_template = runtime_prompt or system_prompt or CLARIFY_AIOPS_PROMPT.format(**params)
        system_message = SystemMessage(content=prompt_template)

        model = create_chat_model(model=model).with_structured_output(ClarifyWithUser)

        # Get clarification response
        clarify_response: ClarifyWithUser = await model.ainvoke(
            [system_message, *state.get("messages", [])],
            config={"tags": ["clarify_agent", "structured_output"] + [name] if name else []},
        )  # type: ignore : typing Known limitations for langchain w/ pydantic v1/v2 mismatches

        command_config = {"goto": "__end__"}
        # Determine next step
        goto: Literal["__end__", "research_brief_node"]
        if not clarify_response.need_clarification and research_brief:
            goto = "research_brief_node"
        else:
            goto = "__end__"

        command_config["goto"] = goto
        if is_subgraph(config) and goto == "__end__":
            command_config["graph"] = Command.PARENT
            command_config["goto"] = parent_next_node if not clarify_response.need_clarification else "__end__"

        return Command(
            goto=command_config["goto"],
            graph=command_config.get("graph", None),
            update={
                "clarification_iteration": +1 if clarify_response.artifacts else 0,
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

    def write_research_brief(state: ClarifyState):
        """Write the research brief Node"""
        model = create_chat_model().with_structured_output(ResearchBrief)
        research_brief: ResearchBrief = model.invoke(
            [SystemMessage(content=RESEARCH_BRIEF_PROMPT.format(date=get_today_date()))] + state["messages"],  # type: ignore
            config={"tags": ["clarify_agent", "structured_output"] + [name] if name else []},
        )

        return {
            "research_brief": research_brief,
        }

    # Build the graph
    graph = StateGraph(
        state_schema=state_schema, input_schema=input_schema, output_schema=output_schema, context_schema=context_schema
    )

    # Add nodes
    graph.add_node("clarification_node", clarify_node)
    graph.add_node("research_brief_node", write_research_brief)
    graph.add_node("clarification_circuit_breaker", clarification_circuit_breaker)

    # Add edges
    graph.add_edge(
        START,
        "clarification_circuit_breaker",
    )
    graph.add_edge("research_brief_node", END)

    # Compile and return
    compiled_graph = graph.compile(name=name or "ClarifyAgent", **kwargs)
    return compiled_graph
    #
    #
    #
    #
    #
