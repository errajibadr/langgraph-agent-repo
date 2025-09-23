# 🔍 **Agent Card: Inspector**

```yaml
Inspector: "The Data Retrieval Specialist"
├── 🎭 IDENTITY
│   ├── Persona: Meticulous data archaeologist
│   ├── Primary Role: Direct Elasticsearch queries across all indices
│   ├── Specialization: Multi-index search & aggregation
│   └── Interaction Style: Precise, factual, no interpretation
├── 🛠️ CAPABILITIES
│   ├── Core Functions: Search, filter, aggregate, correlate
│   ├── Query Patterns: Template-based (70%) + Free query (30%)
│   ├── Decision Logic: Template first, free query for complex needs
│   └── Output Formats: Raw JSON, formatted tables, counts
├── 📊 DATA & CONTEXT
│   ├── Primary Sources: K8s events, Discovery topology, VM events
│   ├── User Context: team, managed_apps, environment_access
│   ├── Access Control: Auto-filter by user's app/env permissions
│   └── Knowledge Gaps: No network flows, no metrics
├── 🔧 TOOLS
│   ├── Templates: 8 pre-defined queries
│   ├── Free Query: query_k8s_events(), query_discovery(), query_vm()
│   └── Utilities: validate_query(), format_results()
├── 🎯 BUSINESS QUESTIONS
│   ├── Primary Owner: Q3, Q4, Q5, Q11
│   ├── Supports: Q1, Q2 (data retrieval)
│   └── Cannot Handle: Q12 (needs Illumio)
├── 🔄 EVOLUTION PATH
│   ├── v1 Demo: Basic queries, 8 templates
│   ├── v2 Enhanced: Cross-index correlation, 20+ templates
│   └── v3 Production: ML query optimization, caching
└── 🎬 DEMO SCENARIOS
    ├── Solo: "What changed in payment service last 2 hours?"
    ├── Collaborative: Feeds data to Navigator for impact analysis
    └── Advanced: "Show distribution of changes by hour this week"
```

## 🤖 **Inspector - Detailed View**

### Specialization Variants

```yaml
K8sEventInspector: "Kubernetes Audit Specialist"
├── Deep Knowledge: iks_audit.* schema
├── Special Patterns: Event correlation, actor profiling
├── Aggregations: Changes per namespace, verb distribution
└── Prompt Context: Includes K8s resource types, common operators

DiscoveryInspector: "Infrastructure Topology Specialist"  
├── Deep Knowledge: BMC Discovery schema, relationships
├── Special Patterns: Multi-layer traversal, component search
├── Aggregations: By datacenter, by type, by environment
└── Prompt Context: Includes infrastructure layers, naming conventions

VMEventInspector: "Legacy Infrastructure Specialist"
├── Deep Knowledge: VM configuration schema
├── Special Patterns: Configuration drift, patch history
├── Aggregations: By hypervisor, by OS, by cluster
└── Prompt Context: Includes VM states, change types
```

### Tool Specifications

```python
# Template Tool
def query_from_template(template_name: str, **params) -> dict:
    """
    Execute pre-defined query template
    Templates: get_app_infrastructure, recent_changes, find_by_hostname,
               get_app_by_team, changes_by_actor, resource_by_type,
               namespace_activity, certificate_status
    """

# Free Query Tools  
def query_k8s_events(es_query: str) -> dict:
    """
    Free-form query on K8s audit index
    Validates query structure, adds user context filters
    """

def query_discovery_topology(es_query: str) -> dict:
    """
    Free-form query on Discovery index
    Auto-includes environment filters based on user access
    """

# Utility Tools
def validate_query(query: str) -> str:
    """Validate and sanitize ES query for security"""

def format_results(results: dict, format: str = "table") -> str:
    """Format raw ES results as table|json|summary"""
```
