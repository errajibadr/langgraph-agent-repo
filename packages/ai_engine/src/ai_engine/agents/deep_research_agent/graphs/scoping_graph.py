from typing import Literal

from ai_engine.agents.deep_research_agent.prompts.scoping_prompts import (
    clarify_with_user_instructions,
    transform_messages_into_research_topic_prompt,
)
from ai_engine.agents.deep_research_agent.research_agent_states import (
    ClarifyWithUser,
    ResearchAgentInputState,
    ResearchAgentOutputState,
    ResearchAgentState,
    ResearchBrief,
)
from ai_engine.models.custom_chat_model import CustomChatModel
from ai_engine.utils.dates import get_today_date
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


def clarify_with_user(state: ResearchAgentState) -> Command[Literal["write_research_brief", "__end__"]]:
    """Clarify with the user Node"""
    model = CustomChatModel().with_structured_output(ClarifyWithUser)
    response: ClarifyWithUser = model.invoke(
        [SystemMessage(content=clarify_with_user_instructions.format(date=get_today_date()))] + state.messages,  # type: ignore
    )

    if response.need_clarification:
        return Command(goto="__end__", update={"messages": [AIMessage(content=response.question)]})
    else:
        return Command(goto="write_research_brief", update={"messages": [AIMessage(content=response.verification)]})


def write_research_brief(state: ResearchAgentState):
    """Write the research brief Node"""
    model = CustomChatModel().with_structured_output(ResearchBrief)
    response: ResearchBrief = model.invoke(
        [SystemMessage(content=transform_messages_into_research_topic_prompt.format(date=get_today_date()))]
        + state.messages,  # type: ignore
    )

    return {"research_brief": response.research_brief}


def get_scoping_graph():
    graph = StateGraph(ResearchAgentState, input_schema=ResearchAgentInputState, output_schema=ResearchAgentOutputState)

    graph.add_node("clarify_with_user", clarify_with_user)
    graph.add_node("write_research_brief", write_research_brief)

    graph.add_edge(START, "clarify_with_user")
    graph.add_edge("write_research_brief", END)

    compiled_graph = graph.compile()
    return compiled_graph


if __name__ == "__main__":
    compiled_graph = get_scoping_graph()
    config = {"configurable": {"thread_id": "thread-1"}}
    print(
        compiled_graph.invoke(
            ResearchAgentInputState(messages=[HumanMessage("What is the weather in Tokyo?")]),
            config=config,  # type: ignore
        )
    )
