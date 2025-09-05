from ai_engine.agents.deep_research_agent.graphs.researcher_graph import get_researcher_graph
from langsmith.run_trees import RunTree


def evaluate_research_agent(outputs: RunTree, reference_output):
    """Evaluate the research agent"""
    last_message = outputs.outputs["researcher_messages"][-1] if outputs.outputs is not None else None
    if last_message is None:
        return {
            "key": "correct_stop_decision",
            "score": False,
        }
    tool_calls = last_message.tool_calls

    return {
        "key": "correct_stop_decision",
        "score": (tool_calls is None or len(tool_calls) == 0) == reference_output.outputs["should_stop"],
    }


def target_function(input: dict):
    """Target function for the research agent"""
    import uuid

    agent = get_researcher_graph()
    config = {"configurable": {"thread_id": uuid.uuid4()}}
    output = agent.nodes["llm_call"].invoke(input, config=config)
    return output


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    from langsmith import Client

    client = Client()
    client.evaluate(
        target_function,
        experiment_prefix="DeepSearch_research_stop_decision",
        data="deep_research_researcher_dataset",
        evaluators=[evaluate_research_agent],
    )
