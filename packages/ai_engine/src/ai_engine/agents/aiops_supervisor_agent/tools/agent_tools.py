import asyncio
import random
from typing import Annotated

from ai_engine.agents.aiops_supervisor_agent.states import SupervisorState
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


@tool
async def call_inspector_agent(app: str, query: str) -> str:
    """Tool that can access the current agent state."""
    # Access state.messages, state.remaining_steps, etc.
    issues = ["Application issue, Kubernetes Node isn't running, Load is all going to one node"]
    # , "Application issue", "Network issue", "Security issue", "Performance issue"]
    await asyncio.sleep(random.randint(1, 10))
    return f"For application {app}, we detected the following issue: {issues[random.randint(0, len(issues) - 1)]}"


@tool
async def call_navigator_agent(app: str, query: str) -> str:
    """Tool that can access the current agent state."""
    impact = ["High", "Medium", "Low"]
    await asyncio.sleep(random.randint(1, 10))
    return f"For application {app}, we detected the following impact: {impact[random.randint(0, len(impact) - 1)]}"
