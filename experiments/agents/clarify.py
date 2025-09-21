from datetime import datetime
from operator import add
from typing import Annotated, Callable, Literal, Protocol, Type, TypedDict, TypeVar

from ai_engine.models.custom_chat_model import create_chat_model
from langchain_core.messages import AIMessage, AIMessageChunk, AnyMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph, RunnableConfig, StateGraph
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph.typing import ContextT, InputT, OutputT, StateT
from pydantic import BaseModel, Field


class HasMessages(Protocol):
    """Protocol qui définit qu'un objet doit avoir un attribut messages."""

    messages: list[AnyMessage | BaseMessage]


# InputT = TypeVar("InputT", bound=HasMessages)
# OutputT = TypeVar("OutputT", bound=HasMessages)
# StateT = TypeVar("StateT", bound=HasMessages)


CLARIFY_AIOPS_PROMPT = """
You are a clarification assistant in an AI-OPS workflow that helps disambiguate operational queries before routing them to specialist agents.

You have access to the following user context:
{user_context}

Current operational context for user's apps: {current_incidents_alerts}

Today's date is {date}.

AI-OPS Domain Vocabulary:
{aiops_vocabulary}

CLARIFICATION RULES:
1. **Time Scope Ambiguity**: Terms like "recent", "latest", "today" need clarification:
   - Recent changes: last hour, since deployment, today?
   - Current status: right now, last check, trend over time?

2. **Environment Scope**: If user has access to multiple environments and doesn't specify:
   - Ask which environment: prod, staging, dev, or all?

3. **Resource Scope**: Terms like "my app", "our system", "everything":
   - If user manages multiple apps, ask which specific app
   - Clarify if they mean their team's apps or broader scope

4. **Action Ambiguity**: Vague actions like "check", "show", "analyze":
   - Check what aspect: health, performance, changes, dependencies?
   - Show which view: summary, details, timeline?

5. **Infrastructure Terms**: If user mentions infrastructure components without context:
   - Which specific component, environment, or scope?

IMPORTANT: 
- If you have already asked a clarifying question in previous rounds, avoid repeating similar questions
- Use the user's context to suggest smart defaults when helpful

Respond in valid JSON format with these exact keys:
"need_clarification": boolean,
"question": "<question to ask the user>",
"verification": "<verification message that we will proceed with analysis>"

If you need to ask a clarifying question:
{{
"need_clarification": true,
"question": "<your clarifying question with context-aware suggestions>",
"verification": ""
}}

If you do not need clarification:
{{
"need_clarification": false,
"question": "",
"verification": "<acknowledgement of what you understood and will analyze>"
}}

For the verification message when no clarification is needed:
- Acknowledge the specific scope you understood (time, environment, resources)
- Confirm what type of analysis will be performed
- Keep it concise and operational

CRITICAL: This is clarification round {clarification_round} of maximum {max_rounds} rounds. If you are at the maximum round ({max_rounds}), you MUST set "need_clarification": false and proceed with the best reasonable interpretation of the user's request, even if some ambiguity remains.
"""


# def model_node(state: StateT, runtime: Runtime[ContextT]) -> OutputT:
#     return OutputT(messages=create_chat_model().invoke(state.messages, config=runtime.config))


class ClarifyWithUser(BaseModel):
    """State for the clarify with user node."""

    need_clarification: bool = Field(
        default=False, description="Whether you need more clarification from the user to start the research"
    )
    question: str = Field(description="The question to ask the user to clarify the scope of the research")
    verification: str = Field(
        description="Verify message that we will start research after the user has provided the necessary information.",
    )


class ClarifyState(TypedDict):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]
    current_round: Annotated[int, add]
    max_rounds: int


class UserContext(BaseModel):
    user_name: str = Field(description="The name of the user")
    user_id: str = Field(description="The ID of the user")
    user_teams: list[str] = Field(description="The teams the user is a member of")
    user_apps: list[str] = Field(description="The apps the user has access to")
    user_environments: list[str] = Field(description="The environments the user has access to")
    current_incidents_alerts: str = Field(description="The current incidents and alerts for the user's apps")

    def __str__(self) -> str:
        return (
            f"- User: {self.user_name} (ID: {self.user_id})\n"
            f"- Teams: {', '.join(self.user_teams)}\n"
            f"- Managed Apps: {', '.join(self.user_apps)}\n"
            f"- Accessible Environments: {', '.join(self.user_environments)}\n"
            f"- Current Incidents/Alerts: {self.current_incidents_alerts}"
        )


def get_user_context(user_id: str) -> UserContext:
    return UserContext(
        user_id=user_id,
        user_name="John Doe",
        user_teams=["team1", "team2"],
        user_apps=["app1", "app2"],
        user_environments=["env1", "env2"],
        current_incidents_alerts="No incidents or alerts",
    )


def get_clarify_graph(
    state_schema: type[StateT],
    output_schema: type[OutputT] | None = None,
    *,
    name: str | None = None,
    system_prompt: str | None = None,
    enrich_query_enabled: bool = False,
    **kwargs,
) -> CompiledStateGraph[StateT]:
    def model_node(state: state_schema, runtime: Runtime[state_schema]) -> Command[Literal["__end__", "enrich_query"]]:
        context = runtime.context or {}
        print(f"Context: {context}")
        runtime_prompt = runtime.context["clarify_system_prompt"] if runtime.context else ""
        print(f"Runtime object: {runtime}")
        print(f"Runtime prompt: {runtime_prompt}")

        # Prepare all required keys with None as default, then update with actual values
        params = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "user_context": get_user_context(context.get("user_id", "")),
            "clarification_round": state.get("current_round", 0),
            "max_rounds": state.get("max_rounds", 3),
            "current_incidents_alerts": context.get("current_incidents_alerts", None),
            "aiops_vocabulary": context.get("aiops_vocabulary", None),
        }

        _s_p = system_prompt or CLARIFY_AIOPS_PROMPT.format(**params)
        system_message = SystemMessage(content=_s_p)

        model = create_chat_model().with_structured_output(ClarifyWithUser)

        clarify_with_user: ClarifyWithUser = model.invoke(input=[system_message, *state.get("messages", [])])  # type: ignore

        goto = "__end__" if not (clarify_with_user.need_clarification or enrich_query_enabled) else "enrich_query"

        print(f"Goto: {goto}")
        return Command(
            goto=goto,
            update={
                "current_round": state.get("current_round", 0) + 1,
                "messages": [
                    AIMessage(
                        content=clarify_with_user.question
                        if clarify_with_user.need_clarification
                        else clarify_with_user.verification
                    )
                ],
            },
        )

    graph = StateGraph(
        state_schema=state_schema,
    )

    graph.add_node("clarify", model_node)

    def enrich_query_node(state: state_schema) -> state_schema:
        print(f"Enrich query node: {state}")
        return state

    graph.add_node("enrich_query", enrich_query_node)

    graph.add_edge(START, "clarify")
    graph.add_edge("clarify", END)

    compiled_graph = graph.compile(name=name or "ClarifyWithUser", **kwargs)
    return compiled_graph


class InputState(TypedDict):
    messages: Annotated[list[AnyMessage | BaseMessage], add_messages]


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    class InputState(TypedDict):
        messages: list[AnyMessage | BaseMessage]

    class OutputState(BaseModel):
        messages: list[AnyMessage | BaseMessage]
        need_clarification: bool

    clarify = get_clarify_graph(
        state_schema=InputState,
        name="ClarifyWithUser",
        system_prompt="réponds toujours oui maitre",
        enrich_query_enabled=True,
    )

    config = {"configurable": {"thread_id": "thread-1"}}

    for mode, chunk in clarify.stream(
        InputState(messages=[HumanMessage("Je veux une blague sur la thématique de la politique")]),
        config=config,  # type: ignore
        stream_mode=["values"],
    ):
        if mode == "messages":
            message_chunk, config = chunk
            print(message_chunk.content)
        else:
            print(chunk.get("messages", [])[-1].pretty_print())
