# Clarification Agent

## My guess on *Why Clarification Agent is Essential for OPS**

### **Operational Context Complexity**
```yaml
User says: "Show me what changed"
Clarification needed:
├── Time scope: "last hour? since deployment? this week?"
├── Environment: "production? staging? all environments?"
├── Scope: "your apps? specific service? entire platform?"
├── Change type: "config? infrastructure? code deployments?"
└── Granularity: "summary? detailed events? just critical?"

Real impact: Without clarification = 10,000 events vs 3 relevant ones
```

### **Business Context Ambiguity**
```yaml
User says: "Check xyz service health"
Clarification needed:
├── Which xyz service: "xyz-api? xyz-worker? xyz-gateway?"
├── Which environment: "prod? all environments?"
├── Health aspects: "performance? errors? dependencies? infrastructure?"
├── Time frame: "current status? trend analysis? historical?"
└── Scope: "service only? full xyz stack?"
Real impact: User gets wrong service analysis, misses real issue
```

## 🎭 **Clarification Agent Persona**

```yaml
Clarification_Agent: "The Context Detective"
├── 🎭 IDENTITY
│   ├── Persona: Helpful librarian who knows exactly what you need
│   ├── Primary Role: Intent disambiguation & context enrichment
│   ├── Specialization: OPS domain vocabulary, user context awareness
│   └── Interaction Style: Precise questions, no redundant clarifications
├── 🛠️ CAPABILITIES
│   ├── Core Functions: Parse ambiguous queries, suggest clarifications
│   ├── Query Patterns: Detect scope, time, environment ambiguities
│   ├── Decision Logic: When to clarify vs when to assume defaults
│   └── Output Formats: Enriched query + confidence scores
├── 📊 DATA & CONTEXT
│   ├── Primary Sources: User profile, app ownership, permission matrix
│   ├── User Context: Team apps, typical environments, recent queries
│   ├── Access Control: Auto-suggest only accessible resources
│   └── Knowledge Gaps: New terminology, edge case scenarios
└── 🔧 TOOLS
    ├── Free Query: Custom disambiguation logic
    └── Utilities: get_user_context, get_app_context 
```

## 🎯 **OPS-Specific Clarification Patterns**

### **Pattern 1: Scope Ambiguity**
```yaml
Input: "What's broken in xyz?"
Clarification Logic:
├── Check user apps: xyz-api, xyz-worker, xyz-gateway
├── Detect: Multiple xyz services
├── Ask: "Which xyz service: xyz-api (yours), xyz-gateway, or all?"
└── Enrich: Add user's primary apps as suggestions
```

### **Pattern 2: Time Scope Ambiguity**
```yaml
Input: "Show recent changes in xyz?"
Clarification Logic:
├── Context: Current time, business hours, deployment windows
├── Suggest: "Last hour (23 changes), since last deployment (156), today (834)"
├── Auto-default: If user always asks for "last hour", suggest that
└── Enrich: Add deployment markers as reference points
```

### **Pattern 3: Environmental Scope**
```yaml
Input: "Check API performance"
Clarification Logic:
├── Check permissions: user has prod + staging access
├── Detect: Performance could mean latency, errors, throughput
├── Ask: "Performance metrics for prod (where issue reported) or all environments?"
└── Enrich: Add recent alert context
```

## 🔄 **Integration with Supervisor Pattern**

### **Flow Architecture**
```yaml
User Query → Clarification Agent → Enriched Query → Supervisor → Specialist Agents

Clarification Decision Tree:
├── Confidence à la discretion du LLM. No need for scores that would be really arbitrary
└── Multiple Valid Interpretations: Present options with context
```

### **State Schema Example**
```python
class ClarificationState(TypedDict):
    original_query: str
    user_context: UserContext
    ambiguities_detected: list[AmbiguityType]
    clarification_questions: list[Question]
    enriched_query: EnrichedQuery | None
    confidence_score: float
    clarification_round: int
```

### **Output Schema Example**
```python
class ClarifiedIntent(TypedDict):
    final_query: str
    scope: QueryScope  # time, environment, resources
    intent_type: IntentType  # investigate, monitor, analyze, report
    target_agents: list[str]  # which specialist agents to route to
    context_enrichments: dict[str, Any]
    confidence: float
```

## 🎬 **Demo Integration Scenarios**

### **Scenario 1: Incident Investigation**
```yaml
User: "Something's wrong with the xyz system"
Clarification: "I see alerts in xyz-api (prod). Check current errors, recent changes, or dependency health?"
Supervisor: Routes to Inspector (errors) + Navigator (dependencies)
```

### **Scenario 2: Maintenance Planning**
```yaml
User: "What will break if I restart the xyz database?"
Clarification: "Which database: xyz-db (prod), user-db (staging), or specify by hostname?"
Supervisor: Routes to Navigator (dependencies) + Inspector (current load)
```

### **Scenario 3: Performance Analysis**
```yaml
User: "Why is everything slow today?"
Clarification: "Define 'everything': your team's apps (xyz, abc), all prod apps, or specific services?"
Supervisor: Routes to Inspector (metrics) + Navigator (topology) for focused analysis
```

## 🚀 **Implementation Recommendations**

### **Phase 1: Core Clarification**
```python
# Essential clarification patterns
CLARIFICATION_PATTERNS = {
    "time_scope": ["recent", "today", "last", "since"],
    "environment": ["prod", "staging", "production", "dev"],
    "scope": ["all", "everything", "my", "our", "team"],
    "action_type": ["show", "check", "find", "analyze", "monitor"]
}
```

## 🎯 **Business Value for Demo**

### **Before Clarification Agent**
- User asks vague question → Agent guesses wrong → Wasted time
- 10,000 irrelevant results → User frustrated → Abandons tool

### **After Clarification Agent**
- User asks vague question → Smart clarification → Precise results
- 3 relevant insights → User delighted → Adopts tool

### **Demo Script Example**
```yaml
Demo: "Show me what changed"
├── Clarification: "Last hour (12 changes), since deployment (45), or today (234)?"
├── User: "Since deployment"
├── Inspector: "45 changes since payment-api v2.1 deployment at 2:30pm"
└── Navigator: "3 critical: config update → 5 pod restarts → temporary latency spike"

Result: Instead of overwhelming data dump, user gets actionable timeline
```
