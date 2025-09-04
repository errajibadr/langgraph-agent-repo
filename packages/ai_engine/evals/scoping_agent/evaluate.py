from ai_engine.agents.deep_research_agent.graphs.scoping_graph import get_scoping_graph
from ai_engine.agents.deep_research_agent.research_agent_states import ResearchAgentInputState
from ai_engine.models.custom_chat_model import CustomChatModel
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from packages.ai_engine.evals.scoping_agent.laaj_prompts import (
    AI_RESPONSE_CRITERION_PROMPT,
    BRIEF_CRITERIA_PROMPT,
    BRIEF_HALLUCINATION_PROMPT,
)

#### CRITERIA EVALUATION


class Criteria(BaseModel):
    """Individual success criteria evaluation results"""

    criteria_text: str = Field(description="The criteria text")
    reasoning: str = Field(description="The reasoning for the criteria")
    is_captured: bool = Field(
        description="Whether the criteria is adequately captured in the research brief or not by the scoping agent"
    )


def evaluate_criteria(outputs: dict, reference_outputs: dict) -> dict:
    """this function evaluates each criteria one by one for each output

    Args:
        outputs (dict): dictionary of outputs from the scoping agent
        reference_outputs (dict): dictionary of reference outputs

    Returns:
        bool: boolean value indicating if the criteria is adequately captured in the research brief or not by the scoping agent
    """

    research_brief = outputs.get("research_brief", "")
    messages = outputs.get("messages", [])
    criterias = reference_outputs.get("criteria", [])

    if not research_brief:
        prompt = AI_RESPONSE_CRITERION_PROMPT
        data = messages
    else:
        prompt = BRIEF_CRITERIA_PROMPT
        data = research_brief

    model = CustomChatModel().with_structured_output(Criteria)

    responses: list[Criteria] = [
        model.invoke(
            [HumanMessage(content=prompt.format(criterion=criterion, data=research_brief))]  # type: ignore
        )
        for criterion in criterias
    ]

    # Ensure we take good criteria text ( avoid hallucination)
    individual_evals = [
        Criteria(criteria_text=criterion, reasoning=response.reasoning, is_captured=response.is_captured)
        for criterion, response in zip(criterias, responses)
    ]

    # Calculate overall score as percentage of captured criteria
    captured_count = sum(1 for eval_result in individual_evals if eval_result.is_captured)
    total_count = len(individual_evals)

    return {
        "key": "success_criteria_score",
        "score": captured_count / total_count if total_count > 0 else 0.0,
        "individual_evaluations": [
            {
                "criteria": eval_result.criteria_text,
                "captured": eval_result.is_captured,
                "reasoning": eval_result.reasoning,
            }
            for eval_result in individual_evals
        ],
    }


#### BRIEF HALLUCINATION EVALUATION
class NoAssumptions(BaseModel):
    """
    Evaluation model for checking if research brief makes unwarranted assumptions.

    This model evaluates whether the research brief contains any assumptions,
    inferences, or additions that were not explicitly stated by the user in their
    original conversation. It provides detailed reasoning for the evaluation decision.
    """

    no_assumptions: bool = Field(
        description="Whether the research brief avoids making unwarranted assumptions. True if the brief only includes information explicitly provided by the user, False if it makes assumptions beyond what was stated."
    )
    reasoning: str = Field(
        description="Detailed explanation of the evaluation decision, including specific examples of any assumptions found or confirmation that no assumptions were made beyond the user's explicit statements."
    )


def evaluate_no_assumptions(outputs: dict, reference_outputs: dict):
    """
    Evaluate whether the research brief avoids making unwarranted assumptions.

    This evaluator checks that the research brief only includes information
    and requirements that were explicitly provided by the user, without
    making assumptions about unstated preferences or requirements.

    Args:
        outputs: Dictionary containing the research brief to evaluate
        reference_outputs: Dictionary containing the success criteria for reference

    Returns:
        Dict with evaluation results including boolean score and detailed reasoning
    """
    research_brief = outputs.get("research_brief", "")
    success_criteria = reference_outputs.get("criteria", [])

    if not research_brief:
        pass

    model = CustomChatModel(model="gpt-4.1", temperature=0)
    structured_output_model = model.with_structured_output(NoAssumptions)

    response: NoAssumptions = structured_output_model.invoke(  # type: ignore
        [
            HumanMessage(
                content=BRIEF_HALLUCINATION_PROMPT.format(
                    research_brief=research_brief, success_criteria=str(success_criteria)
                )
            )
        ]
    )

    return {"key": "no_assumptions_score", "score": response.no_assumptions, "reasoning": response.reasoning}


if __name__ == "__main__":
    import uuid

    from dotenv import load_dotenv

    load_dotenv()

    def target_func(inputs: dict):
        config = {"configurable": {"thread_id": uuid.uuid4()}}
        scoping = get_scoping_graph()
        return scoping.invoke(input=ResearchAgentInputState(**inputs), config=config)  # type: ignore

    from langsmith import Client

    langsmith_client = Client()

    langsmith_client.evaluate(
        target_func,
        data="deep_research_scoping_dataset",
        evaluators=[evaluate_criteria, evaluate_no_assumptions],
        experiment_prefix="Deep Research Scoping",
    )

    langsmith_client.evaluate(
        target_func,
        data="deep_research_scoping_dataset",
        evaluators=[evaluate_criteria, evaluate_no_assumptions],
        experiment_prefix="Deep Research Scoping",
    )
