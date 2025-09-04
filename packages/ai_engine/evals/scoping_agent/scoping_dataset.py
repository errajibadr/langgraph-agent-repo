from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import AnyMessage, BaseMessage
from langsmith import Client

conversation_with_clarification = [
    [HumanMessage("who are the currently the top 3 players of al mountakhab?")],
]

cwc_criterias = ["reask the user for clarification", "definition of top players", "definition of mountakhab"]


conversation_research_brief = [
    HumanMessage(
        "who are the currently the top 3 players of al mountakhab?",
    ),
    AIMessage(
        "When you say “al mountakhab” which team do you mean? A few quick clarifying points so I can answer accurately:\n\n- Which country’s national team? (e.g., Tunisia, Morocco, Egypt, etc.)\n- Which sport? I’ll assume football (soccer) unless you tell me otherwise.\n- How should I measure “top 3 players”? Options: current form/coach’s first-choice XI, market value (Transfermarkt), recent goals/assists or impact, or fan/popular opinion. Pick one or say “your choice” and I’ll use the most common metric.\n\nYou can reply briefly (for example: “Morocco, football, by current form”)."
    ),
    HumanMessage("Morocco, men's football, by current form and last season stats"),
]


research_brief_criterias = ["morocco men's football team ", "by current form", "2024-2025 season stats"]


load_dotenv()

client = Client()

dataset_name = "deep_research_scoping_dataset"

if not client.has_dataset(dataset_name=dataset_name):
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="A dataset for the scoping agent",
    )

    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {"messages": conversation_with_clarification},
                "outputs": {"criteria": cwc_criterias},
            },
            {
                "inputs": {"messages": conversation_research_brief},
                "outputs": {"criteria": research_brief_criterias},
            },
        ],
    )
