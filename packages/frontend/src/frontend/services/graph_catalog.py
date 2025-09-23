"""Graph Catalog Service.

This module provides a catalog of available LangGraph agents that can be used
in the Streamlit frontend. Each graph has metadata and factory functions.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from ai_engine.agents.aiops_deepsearch_agent.graphs.deepsearch_graph import get_deepsearch_graph
from ai_engine.agents.aiops_supervisor_agent.graphs.supervisor_graph import get_supervisor_graph
from ai_engine.agents.clarify_agent import get_clarify_graph
from langgraph.checkpoint.memory import InMemorySaver


@dataclass
class GraphInfo:
    """Information about a graph in the catalog."""

    id: str
    name: str
    description: str
    category: str
    factory_function: Callable[..., Any]
    default_config: Dict[str, Any]
    icon: str = "🤖"


class GraphCatalog:
    """Catalog of available graphs for the frontend."""

    def __init__(self):
        self._graphs = self._initialize_catalog()

    def _initialize_catalog(self) -> Dict[str, GraphInfo]:
        """Initialize the catalog with available graphs."""
        return {
            "aiops_deepsearch_agent": GraphInfo(
                id="aiops_deepsearch_agent",
                name="AI-OPS Deep Search Agent",
                description="AI-OPS deep search agent that disambiguates user queries before planning and routing to specialist agents",
                category="Deep Search",
                factory_function=get_deepsearch_graph,
                default_config={
                    "name": "DeepSearchAgent",
                    "checkpointer": InMemorySaver(),
                },
                icon="👔",
            ),
            "clarify_agent": GraphInfo(
                id="clarify_agent",
                name="Clarify Agent",
                description="AI-OPS clarification agent that helps disambiguate operational queries before routing to specialist agents",
                category="Clarification",
                factory_function=get_clarify_graph,
                default_config={
                    "name": "ClarifyAgent",
                    "enrich_query_enabled": False,
                    "checkpointer": InMemorySaver(),
                },
                icon="❓",
            ),
            "supervisor_agent": GraphInfo(
                id="supervisor_agent",
                name="Supervisor Agent",
                description="AI-OPS supervisor agent that orchestrates investigation and monitoring tasks",
                category="Supervision",
                factory_function=get_supervisor_graph,
                default_config={
                    "name": "SupervisorAgent",
                    "checkpointer": InMemorySaver(),
                },
                icon="👔",
            ),
            # Future graphs can be added here:
            # "research_agent": GraphInfo(...),
            # "react_agent": GraphInfo(...),
        }

    def get_all_graphs(self) -> List[GraphInfo]:
        """Get all available graphs."""
        return list(self._graphs.values())

    def get_graph_by_id(self, graph_id: str) -> GraphInfo | None:
        """Get a graph by its ID."""
        return self._graphs.get(graph_id)

    def get_graphs_by_category(self, category: str) -> List[GraphInfo]:
        """Get graphs filtered by category."""
        return [graph for graph in self._graphs.values() if graph.category == category]

    def create_graph_instance(self, graph_id: str, **kwargs) -> Any:
        """Create an instance of a graph by ID."""
        graph_info = self.get_graph_by_id(graph_id)
        if not graph_info:
            raise ValueError(f"Graph '{graph_id}' not found in catalog")

        # Merge default config with provided kwargs
        config = {**graph_info.default_config, **kwargs}

        # Create the graph instance
        return graph_info.factory_function(**config)


# Global catalog instance
catalog = GraphCatalog()
