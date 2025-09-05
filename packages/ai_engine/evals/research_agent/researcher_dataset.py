from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

should_continue_research = [
    HumanMessage(
        "who are  currently the top 3 players of morrocan al mountakhab? by current form and last season stats"
    ),
    AIMessage(
        content="I will search for the top 3 players of morrocan al mountakhab focusing on current form and last season stats in 2024-2025",
        tool_calls=[
            {
                "name": "tavily_search",
                "args": {
                    "query": "who are the currently the top 3 players of morrocan al mountakhab? by current form and last season stats in 2024-2025"
                },
                "id": "search_continue_research_001",
                "type": "tool_call",
            }
        ],
    ),
    ToolMessage(
        content="""Search results: Ziyech is known as the wizard and one of the best left foot players in the world but in a decline in recent years. Achraf Hakimi is a talented player who is a key player for the moroccan national team that is aiming for the ballon d'or. Yassine Bono is very regular and reliable goalkeeper ranking amongst the best goalkeepers in the world. Amine Harit was a young talented player but never really fullfilled promises. Recent rising stars are Iliess benSghir and Ibrahim Diaz""",
        tool_call_id="search_continue_research_001",
    ),
    AIMessage(
        content="I have found the top 3 players of morrocan al mountakhab focusing on current form and last season stats in 2024-2025",
        tool_calls=[
            {
                "name": "think_tool",
                "args": {
                    "reflection": "Analysis of search result shows : 2 players that seem to be really good and definitly amongst best players. But i still need to find the third one."
                },
                "id": "search_continue_think_001",
                "type": "tool_call",
            }
        ],
    ),
    ToolMessage(
        content="Reflection Recorded : Analysis of search result shows : 2 players thatseem to be really good and definitly amongst best players. But i still need to find the third one.",
        tool_call_id="search_continue_think_001",
    ),
]

should_stop_research = [
    HumanMessage(
        "who are currently the top 3 players of moroccan al mountakhab? by current form and last season stats"
    ),
    AIMessage(
        content="I will search for the top 3 players of moroccan al mountakhab focusing on current form and last season stats in 2024-2025",
        tool_calls=[
            {
                "name": "tavily_search",
                "args": {
                    "query": "top 3 moroccan national team players 2024-2025 current form last season stats Achraf Hakimi Yassine Bono Hakim Ziyech"
                },
                "id": "search_stop_research",
                "type": "tool_call",
            }
        ],
    ),
    ToolMessage(
        content="""Search results: Based on current form and 2024-2025 season statistics, the top 3 Moroccan national team players are: 
        1. Achraf Hakimi (PSG) - 28 appearances, 5 goals, 7 assists, excellent defensive stats and attacking contribution from right-back position. Key player in Morocco's recent World Cup success.
        2. Yassine Bono (Al-Hilal) - 31 clean sheets in 45 matches, 85% save rate, consistent performances for both club and country. Considered one of the world's best goalkeepers currently.
        3. Sofyan Amrabat (Manchester United/Fiorentina) - 42 matches, 89% pass accuracy, exceptional defensive midfielder with 4.2 tackles per game, crucial in Morocco's midfield stability and World Cup run.
        Additional context: Hakim Ziyech has had limited playing time this season, while rising stars like Azzedine Ounahi and Youssef En-Nesyri are also performing well but haven't quite reached the consistency of the top 3.""",
        tool_call_id="search_stop_research",
    ),
    AIMessage(
        content="Based on my search, I have identified the top 3 Moroccan national team players with comprehensive statistics and analysis.",
        tool_calls=[
            {
                "name": "think_tool",
                "args": {
                    "reflection": "Perfect! I have found detailed information about the top 3 Moroccan players with specific statistics: Achraf Hakimi (28 apps, 5 goals, 7 assists), Yassine Bono (31 clean sheets, 85% save rate), and Sofyan Amrabat (42 matches, 89% pass accuracy, 4.2 tackles/game). The search provided current form data, last season stats, and clear justification for each player's ranking. This comprehensive answer fully addresses the user's question with no gaps."
                },
                "id": "search_stop_think_001",
                "type": "tool_call",
            }
        ],
    ),
    ToolMessage(
        content="Reflection Recorded: Perfect! I have found detailed information about the top 3 Moroccan players with specific statistics: Achraf Hakimi (28 apps, 5 goals, 7 assists), Yassine Bono (31 clean sheets, 85% save rate), and Sofyan Amrabat (42 matches, 89% pass accuracy, 4.2 tackles/game). The search provided current form data, last season stats, and clear justification for each player's ranking. This comprehensive answer fully addresses the user's question with no gaps.",
        tool_call_id="search_stop_think_001",
    ),
]


if __name__ == "__main__":
    from dotenv import load_dotenv
    from langsmith import Client

    load_dotenv()

    client = Client()

    dataset_name = "deep_research_researcher_dataset"
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description="A dataset for the researcher agent",
        )
        client.create_examples(
            dataset_id=dataset.id,
            examples=[
                {
                    "inputs": {"researcher_messages": should_continue_research},
                    "outputs": {"should_stop": False},
                },
                {
                    "inputs": {"researcher_messages": should_stop_research},
                    "outputs": {"should_stop": True},
                },
            ],
        )
    else:
        print(f"Dataset {dataset_name} already exists")
