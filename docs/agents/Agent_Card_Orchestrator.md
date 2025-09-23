# 🎼 **Agent Card: Orchestrator**

```yaml
Orchestrator: "The Master Coordinator"
├── 🎭 IDENTITY
│   ├── Persona: Diplomatic conductor
│   ├── Primary Role: Multi-agent coordination & synthesis
│   ├── Specialization: Intent parsing, routing, response fusion
│   └── Interaction Style: Clear, summarizing, action-oriented
├── 🛠️ CAPABILITIES
│   ├── Core Functions: Route, coordinate, synthesize, track context
│   ├── Query Patterns: Decomposition, parallel execution, merge
│   ├── Decision Logic: Intent classification, agent selection
│   └── Output Formats: Executive summary, detailed analysis, action plans
├── 📊 DATA & CONTEXT
│   ├── Primary Sources: Other agents' outputs
│   ├── User Context: Full context + conversation history
│   ├── Access Control: Enforces across all agents
│   └── Knowledge Gaps: Only knows what agents tell it
├── 🔧 TOOLS
│   ├── Templates: route_query(), decompose_complex()
│   ├── Free Query: orchestrate_investigation()
│   └── Utilities: track_context(), synthesize_responses()
├── 🎯 BUSINESS QUESTIONS
│   ├── Primary Owner: All complex multi-step questions
│   ├── Supports: All questions (as coordinator)
│   └── Cannot Handle: None (routes everything)
├── 🔄 EVOLUTION PATH
│   ├── v1 Demo: Simple routing, sequential execution
│   ├── v2 Enhanced: Parallel execution, learning routing
│   └── v3 Production: Workflow automation, proactive suggestions
└── 🎬 DEMO SCENARIOS
    ├── Solo: "Why is payment service degraded?"
    ├── Collaborative: Coordinates 3-agent investigation
    └── Advanced: "Prepare change impact report for tonight's maintenance"
```

## 🤖 **Orchestrator - Detailed View**

### Routing Decision Matrix

```yaml
Intent Recognition:
  "show me" / "list" / "find" → Inspector
  "depends" / "connected" / "impact" → Navigator
  "changed" / "modified" / "anomaly" → Inspector (later Sentinel)
  "why is X slow" → Inspector + Navigator
  "prepare report" → All agents

Complex Query Patterns:
  Investigation: Inspector.get_current → Navigator.analyze → Synthesize
  Root Cause: Inspector.get_timeline → Navigator.dependencies → Correlate
  Change Impact: Navigator.topology → Inspector.planned_changes → Oracle.simulate
```

### Tool Specifications

```python
def classify_intent(query: str) -> dict:
    """
    Classify user intent and required agents
    Returns: {
        primary_intent: str,
        required_agents: [str],
        complexity: simple|complex|investigation
    }
    """

def route_to_agent(agent_name: str, query: str, context: dict) -> dict:
    """Route query to specific agent with context"""

def orchestrate_complex_query(query: str, user_context: dict) -> dict:
    """
    Decompose and coordinate multi-agent query
    Returns: {
        steps: [...],
        results: {...},
        synthesis: str,
        confidence: float
    }
    """

def track_conversation_context(query: str, response: dict) -> None:
    """Maintain conversation state for follow-ups"""
```
