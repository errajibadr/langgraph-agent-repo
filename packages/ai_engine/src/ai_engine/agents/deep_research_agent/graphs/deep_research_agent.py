# ===== FINAL REPORT GENERATION =====

from ai_engine.agents.deep_research_agent.graphs.scoping_graph import clarify_with_user, write_research_brief
from ai_engine.agents.deep_research_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.agents.deep_research_agent.prompts.deep_research_prompt import final_report_generation_prompt
from ai_engine.agents.deep_research_agent.research_agent_states import ResearchAgentInputState, ResearchAgentState
from ai_engine.models.custom_chat_model import CustomChatModel
from ai_engine.utils.helpers import get_today_date
from langchain_core.messages import HumanMessage
from langgraph.graph.state import END, START, StateGraph

writer_model = CustomChatModel(model="gpt-4.1-mini")


async def final_report_generation(state: ResearchAgentState):
    """
    Final report generation node.

    Synthesizes all research findings into a comprehensive final report
    """

    notes = state.notes

    findings = "\n".join(notes)

    final_report_prompt = final_report_generation_prompt.format(
        research_brief=state.research_brief, findings=findings, date=get_today_date()
    )

    final_report = await writer_model.ainvoke([HumanMessage(content=final_report_prompt)])

    return {
        "final_report": final_report.content,
        "messages": ["Here is the final report:\n\n" + str(final_report.content)],
    }


# ===== GRAPH CONSTRUCTION =====
# Build the overall workflow
def get_deep_research_agent_graph():
    deep_researcher_builder = StateGraph(ResearchAgentState, input_schema=ResearchAgentInputState)

    supervisor_agent = get_supervisor_graph()
    # Add workflow nodes
    deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
    deep_researcher_builder.add_node("write_research_brief", write_research_brief)
    deep_researcher_builder.add_node("supervisor_subgraph", supervisor_agent)
    deep_researcher_builder.add_node("final_report_generation", final_report_generation)

    # Add workflow edges
    deep_researcher_builder.add_edge(START, "clarify_with_user")
    deep_researcher_builder.add_edge("write_research_brief", "supervisor_subgraph")
    deep_researcher_builder.add_edge("supervisor_subgraph", "final_report_generation")
    deep_researcher_builder.add_edge("final_report_generation", END)

    # Compile the full workflow
    agent = deep_researcher_builder.compile()
    return agent


async def main():
    agent = get_deep_research_agent_graph()
    result = await agent.ainvoke(
        ResearchAgentInputState(
            messages=[HumanMessage("How many member countries (member states) are there in the EU?")]
        )
    )
    print(type(result))
    print(result.keys())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
