# Use Cases Discovery

## Topological Questions

### UC1: Dependencies Mapping

**Use Case:**
Static dependency mapping from Discovery topology to answer impact analysis questions during maintenance operations.

**Prerequisites for Quick Win:**
- **Basic Graph Model:** Simple parent-child relationships (Component → Connected_To → Component)
- **Think of some temporal link in modelization** How does Graph modelization handles Slowly changing relationships?
- **Minimal Data:** Just Discovery topology exports with hostnames and connections
- **Simple Query:** Basic graph traversal (NetworkX is sufficient)


```yaml Graph Modelization example
Application X (s00v99949963)
  ├── Runs on VM: s00v99949947
  │   ├── Hosted on ESX: s02ie9913856
  │   ├── Connected to Switch: REST12-CLOUDA-AL16Y
  │   └── Uses Storage: CLUS238_DS000_VSAN_MARNE
  ├── Load Balanced by: PortGroup[s1e01v010.244.64.22:12180]
  └── Has Certificate: CN=s00v99949963 (expires: 2026-04-19)
```

**Quick Wins:**
```yaml
Simple Implementation:
1. Model: Component Graph structure ( A -> B -> C )
2. Query: "What depends on Switch X?" or "What is the composition of my app" 

3. Tools:
- Tool : GraphQueryTool
- Tool : DependencyMappingTool (e.g.)
# MATCH (sw:Switch {name: "Switch_name"})<-[:CONNECTED_TO]-(vm:VM)<-[:RUNS_ON]-(app:Application)
# RETURN DISTINCT app.name AS Impacted_Application, vm.name AS VM, sw.name AS Switch

4. Output: Flat list of impacted components or any open question related to the graph

```

**Limitations/Weaknesses:**
- Only shows static infrastructure dependencies, not runtime behavior
- Cannot detect redundancy or failover paths **future evolution -- needs Illumio data**
- Missing criticality scoring (all dependencies treated equal) **future evolution**
- No temporal aspect (doesn't know when dependencies are active) **How to handle Slowly changing relationships?**

**Ambiguities:**
- Do we know what is prod vs non prod? ( code_ap is same in all environments??)
- What defines an "application boundary"? (Multiple VMs? Containers? Services?)
- How to handle partial dependencies? (App works but degraded without component X)
- Bidirectional impacts? (Does VM failure impact switch metrics?)


**Prerequisites for Future Evolution:**
- **Advanced Graph Modeling:** Typed relationships (DEPENDS_ON, RUNS_ON, CONNECTS_TO)
- **Criticality Scoring:** Environment tags, SLA data, business priority matrix
- **Redundancy Detection:** Network flow data from Illumio
- **Historical Data:** Past incident correlations for maintenance window optimization

**Future Evolution:**
```yaml
Phase 2: Add criticality scoring
- Tag: environment (prod=10, staging=5, dev=1)
- Calculate: cascade_impact_score
- Output: "3 CRITICAL prod apps, 12 low-priority dev apps"

Phase 3: Add redundancy detection (needs Illumio)
- Detect: alternative paths/failover options
- Output: "Payment has failover, safe to maintain"

Phase 4: Smart maintenance windows
- Analyze: historical incident correlation
- Suggest: optimal maintenance timing
```

## K8S Event Analysis

### UC2: Latest Updates Check

**Use Case:**
Analyze recent changes in Kubernetes environments to detect potential issues proactively.

**Prerequisites for Quick Win:**
- **Define Normal:** Simple static thresholds (e.g., average changes per hour)
- **Basic Event Access:** Query K8s events by timeframe and namespace
- **Simple Filters:** No Production namespace identifier (`dws.env.name: "hprd"`)
- **Time Windows:** Define what "recent" means (last 1h, 24h, since last check)

```yaml Event Structure Example
Event Stream:
  ├── Timestamp: 2025-09-21T14:30:00
  ├── Action: iks_audit.verb: "update"
  ├── Resource: iks_audit.objectRef.resource: "configmaps"
  ├── Target: iks_audit.objectRef.name: "payment-config"
  ├── Actor: iks_audit.user.username: "system:serviceaccount:cicd"
  └── Business Context: 
      ├── dws.client.name: "aiops-pp"
      ├── dws.product.ap_code: "a100575"
      └── dws.env.name: "hprd"
```

**Quick Wins:**
```yaml
Simple Implementation:
1. Query: Events in timeframe with aggregation
2. Filter: Production only (dws.env.name = "hprd")

3. Tools:
- Tool: EventQueryTool (Elasticsearch query wrapper)
- Tool: EventAggregatorTool (group by verb, namespace, user)
- Tool: ThresholdAlertTool (simple rule engine)

4. Output: Event summary with anomaly flags
   - "847 changes (normal: ~100): 23 deletes, 156 updates"
   - "Unusual actor: temp-contractor (first time in prod)"
```

**Limitations/Weaknesses:**
- **Easily replaced by dashboard** for simple counting -- But gives visibility to the AGENT to do **in-depth** analysis
- No causal analysis (what triggered these changes?) **future evolution**
- High noise-to-signal ratio without intelligent filtering **future evolution - needs ML**
- Just counting events, not understanding impact

**Ambiguities:**
- What's the baseline for "normal"? (Weekday vs weekend patterns?)
- How to identify "critical" apps? (Based on ap_code? namespace? labels?) **Big One**
- Should we track all verbs or focus on risky ones (delete, patch)?
- How to handle batch deployments that naturally spike changes?

**Prerequisites for Future Evolution:**
- **Statistical Baselines:** 30+ days of historical data with hourly aggregations
- **Event Classification:** Risk matrix for different operation types
- **Pattern Library:** Historical incident patterns for comparison
- **Correlation Engine:** Link changes to impacts (ConfigMap → Pod restarts)

**Future Evolution:**
```yaml
Phase 2: Pattern correlation
- Link: ConfigMap changes → Pod restarts
- Detect: Cascade effects
- Output: "Config change caused 15 pod restarts"

Phase 3: Historical comparison
- Compare: Current pattern vs past incidents
- Alert: "Similar to incident #1234 (memory leak)"

Phase 4: Predictive alerts
- ML model: Predict incident probability
- Alert: "85% chance of incident in next 2h"
```
---

### UC3: Suspect Change Detection

**Use Case:**
Identify abnormal change patterns that could indicate risks or ongoing incidents.

**Prerequisites for Quick Win:**
- **Simple Rules Definition:** 3 hardcoded anomaly rules
- **Basic Thresholds:** Fixed limits (>100 changes/10min)
- **Event Access:** Query capability with filters (verb, namespace, timestamp)
- **Time Awareness:** Business hours definition (9am-6pm weekdays)

```yaml Suspect Pattern Examples
Rule-based Detection:
  ├── Volume Anomaly:
  │   ├── Normal: ~50 changes/hour
  │   └── Suspect: 450 changes/hour (9x spike)
  ├── Timing Anomaly:
  │   ├── Event: "delete" operations at 3:47 AM
  │   └── Flag: Outside business hours + destructive
  ├── Actor Anomaly:
  │   ├── User: "unknown-user"
  │   └── Flag: First time in production namespace
  └── Sequence Anomaly:
      ├── Pattern: delete → delete → delete (rapid)
      └── Flag: Potential cleanup or attack
```

**Quick Wins:**
```yaml
Simple Implementation:
1. Define 3 rules:
   - Rule 1: >100 changes in 10 minutes = suspect
   - Rule 2: Any "delete" in prod by non-admin = suspect  
   - Rule 3: Any changes between 2am-5am weekday = suspect

2. Tools:
- Tool: EventPatternDetector (rule engine)
- Tool: AnomalyScorer (simple scoring 0-10)
- Tool: ActorProfiler (known vs unknown users)

3. Output: Suspect events with risk scores
   - "HIGH RISK (8/10): 450 changes detected (normal: 50)"
   - "MEDIUM RISK (6/10): Deletes at 3am by new user"
```

**Limitations/Weaknesses:**
- High false positive rate without proper tuning
- "Suspect" is subjective and context-dependent
- No learning from feedback (static rules) **future evolution - needs ML**
- Alert fatigue risk if too sensitive

**Ambiguities:**
- How to handle legitimate emergency changes at 3am?
- What if month-end always has 10x changes (seasonal pattern)?
- Should service accounts be treated differently than humans?
- How to distinguish between cleanup and attack patterns?

**Prerequisites for Future Evolution:**
- **Historical Baseline:** 30+ days of event data with patterns
- **Statistical Methods:** Z-score calculation, time-series decomposition
- **ML Infrastructure:** Isolation Forest or similar anomaly detection
- **Feedback Loop:** Label historical anomalies as true/false positives

**Future Evolution:**
```yaml
Phase 2: Statistical anomaly detection
- Implement: Z-score for volume anomalies
- Add: Seasonal decomposition (daily/weekly patterns)
- Output: "450 changes (z-score: 4.2, p-value: 0.0001)"

Phase 3: ML-based detection
- Train: Isolation Forest on normal patterns
- Feature engineering: Time, volume, verb, actor features
- Output: Anomaly score with feature importance

Phase 4: Behavioral analysis
- Profile: Normal behavior per user/service
- Detect: Deviation from profile
- Alert: "ServiceAccount-X never deletes, but deleted 10 pods"
```

---

### UC4: Dynamic Dependencies Detection

**Use Case:**
Infer runtime dependencies between Kubernetes components based on behavioral patterns.

**Prerequisites for Quick Win:**
- **Simple Correlation:** Track events within 1-minute windows
- **Basic Counter:** Count co-occurrences over sliding window
- **Minimal Statistics:** Correlation threshold (>80% = dependency)
- **Event Enrichment:** Namespace, labels, and timing data available

```yaml Behavioral Pattern Example
Correlated Events Timeline:
T+0s:   ConfigMap "db-config" updated
T+2s:   Pod "payment-api-abc123" terminated
T+3s:   Pod "payment-api-xyz789" terminated  
T+5s:   Pod "payment-api-abc123" started
T+6s:   Pod "payment-api-xyz789" started
T+30s:  Pod "order-service-def456" restarted
T+31s:  Pod "inventory-service-ghi789" restarted

Inferred Dependencies:
  payment-api → depends on → db-config (100% correlation)
  order-service → might depend on → payment-api (70% correlation)
```

**Quick Wins:**
```yaml
Simple Implementation:
1. Track: Events in sliding 1-minute windows
2. Correlate: Count co-occurrences

3. Tools:
- Tool: EventCorrelator (time-window analysis)
- Tool: DependencyInferencer (correlation calculator)
- Tool: GraphBuilder (add inferred edges to graph)

4. Output: Dependency confidence scores
   - "payment-api → db-config (95% confidence)"
   - "order-service → payment-api (70% confidence)"
```

**Limitations/Weaknesses:**
- **Correlation ≠ Causation** (coincidence possible)
- Without network data, only behavioral inference **future evolution - needs Illumio**
- High false positives from batch jobs (everything restarts at 2am)
- Cannot detect external dependencies (SaaS APIs, external DBs)

**Ambiguities:**
- How many co-occurrences needed to confirm dependency? (5? 10? 100?)
- How to handle periodic patterns? (daily batch jobs correlation)
- What about delayed dependencies? (A affects B after 5 minutes)
- Should we consider anti-patterns? (A stops when B starts)

**Prerequisites for Future Evolution:**
- **Network Flow Data:** Illumio integration for actual communication
- **Multi-Signal Correlation:** ConfigMap/Secret sharing, resource quotas
- **Statistical Significance:** Proper p-values, confidence intervals
- **Graph Algorithms:** Community detection for dependency clusters

**Future Evolution:**
```yaml
Phase 2: Multi-signal correlation
- Add: ConfigMap/Secret sharing analysis
- Add: Same namespace/labels clustering
- Confidence: Weighted score from multiple signals

Phase 3: Network flow integration (needs Illumio)
- Confirm: Actual TCP/HTTP connections
- Direction: Request flow direction
- Volume: Requests per second, bandwidth

Phase 4: Dependency graph auto-generation
- Build: Real-time dependency map updates
- Detect: Dependency breaks or changes
- Alert: "New dependency detected: service-A → service-B"
```

---

## Multi-Layer Analysis

### UC5: Application X-Ray Vision

**Use Case:**
Provide comprehensive 360° view of an application across all infrastructure layers.

**Prerequisites for Quick Win:**
- **Simple Identifier:** Use single field (ap_code OR label OR namespace)
- **Cross-Reference Capability:** Link K8s resources to VM resources **How to do it?**
- **Graph modelization linking discovery topology to k8s resources** : We need to define both graph modelizations + how to link them up ! .
- **Basic Queries:** Direct lookups in both data sources
- **Output Template:** Predefined layer structure

```yaml Application Composition Example
Application: "x-service" (ap_code: a100575)
  ├── Business Layer:
  │   ├── Client: "aiops-pp"
  │   ├── Product: "x-platform"
  │   └── Environment: "hprd" (production)
  ├── Kubernetes Layer:
  │   ├── Namespace: "x-prod"
  │   ├── Deployments: ["x-api", "x-worker"]
  │   ├── Pods: 5 instances across 3 nodes
  │   └── ConfigMaps: ["x-config", "db-config"]
  ├── VM Layer:
  │   ├── VMs: ["s00v99949947", "s00v99949948"]
  │   ├── ESX Host: "s02ie9913856"
  │   └── Datacenter: "par64"
  └── Network Layer:
      ├── VLAN: 244
      ├── Switch: "REST12-CLOUDA-AL16Y"
      └── Load Balancer: "PortGroup[10.244.64.22:12180]"
```

**Quick Wins:**
```yaml
Simple Implementation:
1. Input: ap_code or application name
2. Query: Both data sources with identifier

3. Tools:
- Tool: ApplicationDiscoveryTool (find all components)
- Tool: LayerAggregatorTool (organize by layer)
- Tool: ApplicationSummarizerTool (generate overview)

4. Output: Structured multi-layer view
   - Business context (client, environment)
   - Infrastructure components (VMs, network)
   - Kubernetes resources (pods, services)
   - Dependencies and connections
```

**Limitations/Weaknesses:**
- **Boundary ambiguity:** Where does one app end? **Need clear definition**
- Missing application logic layer (code, APIs) **not in current data**
- No performance metrics or health status **future evolution - needs metrics**
- Static snapshot only (no historical view) **future evolution**

**Ambiguities:**
- Is ap_code unique across environments or same in dev/staging/prod?
- How to handle shared services? (shared database, message queue)
- What about multi-cluster applications? (cross-region deployments)
- How to represent blue/green deployments or canary releases?

**Prerequisites for Future Evolution:**
- **Complex Boundary Detection:** Graph algorithms for component clustering
- **Visualization Engine:** D3.js or similar for interactive diagrams
- **Performance Metrics:** CPU, memory, latency data integration
- **Historical Tracking:** Changes over time, version history

**Future Evolution:**
```yaml
Phase 2: Smart boundary detection
- Algorithm: Graph community detection
- Identify: Core vs peripheral components
- Output: "Core: 5 services, Extensions: 3 services"

Phase 3: Architecture visualization
- Generate: Interactive diagram
- Layers: Business/Application/Infrastructure
- Features: Zoom, drill-down, filters

Phase 4: Health overlay
- Add: Real-time metrics (CPU, memory, errors)
- Show: Performance bottlenecks
- Alert: "Payment-API at 95% memory"

Phase 5: Change impact simulation
- What-if: "If I update payment-config..."
- Predict: "Will restart 5 pods, affect 2 services"
- Recommend: "Best time: Sunday 3am, lowest traffic"
```

---

## Prerequisites Summary Table

| Use Case | Quick Win Prerequisites | Future Evolution Prerequisites |
|----------|------------------------|-------------------------------|
| **Dependencies Mapping** | • Basic graph (NetworkX)<br>• Simple relationships<br>• Discovery data only | • Criticality scoring system<br>• Illumio network flows<br>• Historical incident data |
| **Latest Updates** | • Event query capability<br>• Static thresholds<br>• Namespace filters | • 30+ days baselines<br>• Pattern correlation engine<br>• ML anomaly detection |
| **Suspect Changes** | • 3 simple rules<br>• Fixed thresholds<br>• Basic event access | • Statistical models<br>• Behavioral profiles<br>• Risk scoring matrix |
| **Dynamic Dependencies** | • 1-minute time windows<br>• Simple counters<br>• Basic correlation | • Network flow data<br>• Multi-signal analysis<br>• Graph algorithms |
| **Application X-Ray** | • Single identifier<br>• Direct queries<br>• Template output | • Boundary detection<br>• Visualization engine<br>• Performance metrics |

## Implementation Readiness Assessment

### ✅ Ready Now (Have Prerequisites)
- **Dependencies Mapping (Quick Win)** - Have Discovery data, just need graph
- **Application X-Ray (Quick Win)** - Have identifiers and data

### ⚠️ Can Start (Partial Prerequisites)  
- **Suspect Changes (Quick Win)** - Need to define the 3 rules
- **Latest Updates (Quick Win)** - Need to set thresholds

### 🔴 Blocked for Future Evolution
- **All use cases** - Need Illumio data for network dependencies
- **All use cases** - Need 30+ days historical data for ML

## Recommended Demo Priority

1. **Dependencies Mapping** - Clear value, achievable
2. **Application X-Ray** - Impressive visualization potential
3. **Suspect Changes** - If time permits

## Critical Success Factors

1. **Graph Quality** > Agent Sophistication
2. **Clear Definitions** (app boundaries, "suspect", criticality)
3. **Start Simple** (rules before ML)
4. **Show Clear Value** vs existing dashboards
5. **Focus on Actionable Insights** not just data retrieval