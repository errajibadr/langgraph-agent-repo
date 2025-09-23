# 🗺️ **Agent Card: Navigator**

```yaml
Navigator: "The Graph Intelligence Expert"
├── 🎭 IDENTITY
│   ├── Persona: Strategic topology analyst
│   ├── Primary Role: Graph queries & dependency analysis
│   ├── Specialization: Relationships, paths, impact zones
│   └── Interaction Style: Visual, connecting dots, big picture
├── 🛠️ CAPABILITIES
│   ├── Core Functions: Traverse, analyze paths, calculate impact
│   ├── Query Patterns: Graph traversals, shortest paths, clusters
│   ├── Decision Logic: Depth vs breadth, confidence thresholds
│   └── Output Formats: Dependency trees, impact scores, paths
├── 📊 DATA & CONTEXT
│   ├── Primary Sources: Pre-built NetworkX graph
│   ├── User Context: User→Team→App relationships in graph
│   ├── Access Control: Traversal limited to user's app subgraph
│   └── Knowledge Gaps: Missing runtime dependencies
├── 🔧 TOOLS
│   ├── Templates: find_dependencies(), blast_radius(), my_apps()
│   ├── Free Query: custom_traversal(), path_finder()
│   └── Utilities: calculate_impact(), visualize_subgraph()
├── 🎯 BUSINESS QUESTIONS
│   ├── Primary Owner: Q1, Q2, Q6, Q7, Q9, Q10
│   ├── Supports: Q8 (certificate paths)
│   └── Cannot Handle: Q11 (needs Inspector for events)
├── 🔄 EVOLUTION PATH
│   ├── v1 Demo: Basic traversal + simple impact
│   ├── v2 Enhanced: Split to Navigator + Oracle
│   └── v3 Production: Graph ML, real-time updates
└── 🎬 DEMO SCENARIOS
    ├── Solo: "Show my team's application topology"
    ├── Collaborative: Impact analysis with Inspector's changes
    └── Advanced: "Find single points of failure"
```

## 🤖 **Navigator - Detailed View**

### Graph Schema Knowledge

```yaml
Node Types:
  User: {properties: [user_id, name, role]}
  Team: {properties: [team_id, name, scope]}
  Application: {properties: [ap_code, name, env, criticality]}
  Infrastructure: {properties: [hostname, type, datacenter]}
  Network: {properties: [vlan_id, subnet, zone]}

Edge Types:
  BELONGS_TO: User → Team
  MANAGES: Team → Application
  RUNS_ON: Application → Infrastructure
  DEPENDS_ON: Application → Application
  CONNECTS_TO: Infrastructure → Network

Traversal Patterns:
  my_apps: User -BELONGS_TO-> Team -MANAGES-> App
  impact: Component <-DEPENDS_ON*- Apps
  infrastructure: App -RUNS_ON-> Infrastructure
```

### Tool Specifications

```python
def find_dependencies(node_id: str, direction: str = "both", max_depth: int = 3) -> dict:
    """
    Find all dependencies of a node
    Returns: {direct: [...], indirect: [...], depth_map: {...}}
    """

def calculate_blast_radius(failure_point: str) -> dict:
    """
    Calculate impact of component failure
    Returns: {
        affected_apps: [...],
        impact_score: 85,
        critical_paths: [...],
        redundancy: bool
    }
    """

def my_applications(user_id: str) -> list:
    """Get all applications managed by user's team"""

def visualize_topology(app_code: str, format: str = "hierarchical") -> str:
    """Generate visual representation of app topology"""
```
