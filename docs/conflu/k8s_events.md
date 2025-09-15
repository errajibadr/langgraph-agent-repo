# 📊 Semantic Layer - Kubernetes Audit Events Index

## 🎯 Overview

**Source:** Kubernetes audit events enriched with business metadata  
**Granularity:** 1 record = 1 Kubernetes API action  
**Update:** Real-time  
**Volume:** ~70,000 events in 15 minutes (24,000 without GETs)  
**Index:** `datalab-logs-audit-k8s`  
**Access:** https://...:9200

---

## 🏗️ Data Architecture

The index presents a **multi-dimensional** structure with several enriched information layers:

```
📦 Document = 1 K8s event + enriched metadata
├──  iks_audit.*     → Raw Kubernetes API event
├──  dws.*           → Business/organizational metadata  
├──  kubernetes.*   → Enriched Kubernetes context
└──  other objects   → More metadata...
```

---

## 🏢 DWS Object (Data Warehouse System)

### Complete Structure
```json
"dws": {
  "client": {
    "ap_code": "a100567",
    "name": "aiops-pp"
  },
  "env": {
    "name": "hprd"        // dev, staging, prod...
  },
  "platform": {
    "ap_code": "ap24182",
    "name": "iks"
  },
  "product": {
    "ap_code": "a100575", 
    "name": "a100575"
  }
}
```

### 💡 Usage
**Business classification of events** - allows contextualizing each Kubernetes event within its organizational and business environment.

### 🔍 Open Questions
- **Differentiation**: What is the exact difference between `client`, `product`, and `platform`?
- **AP Code**: Which AP code is authoritative during searches? Priority hierarchy?
- **Scope**: Can a client have multiple products? Can a platform serve multiple products?

---

## ☸️ Kubernetes Object (enriched metadata)

### Complete Structure
```json
"kubernetes": {
  "container": {
    "name": "payment-api"
  },
  "namespace": "production",
  "node": {
    "name": "worker-01",
    "hostname": "k8s-worker-01.company.com", 
    "uid": "abc-123-def"
  },
  "pod": {
    "ip": "10.244.1.15",
    "name": "payment-api-7d4b8c9f-xq2m8",
    "uid": "xyz-789-abc"
  }
}
```

### 💡 Usage
**Detailed infrastructure context** - enrichment of raw K8s events with complete operational metadata.

---

## 🔍 IKS_AUDIT Object (raw Kubernetes API event)

### Expected Structure
```json
"iks_audit": {
  "objectRef": {
    "resource": "pods",
    "name": "payment-api-7d4b8c9f-xq2m8",
    "namespace": "production"
  },
  "user": {
    "username": "system:serviceaccount:default:deployment-controller",
    "groups": ["system:serviceaccounts", "system:authenticated"]
  },
  "sourceIPs": ["10.0.0.1"],
  "userAgent": "kube-controller-manager/v1.28.0",
  "verb": "update",
  "requestURI": "/api/v1/namespaces/production/pods/payment-api-7d4b8c9f-xq2m8/status"
}
```

---

## 📋 Identified Analytics Dimensions

### 🏢 Business Dimensions

| Dimension | Path | Values | Description |
|-----------|------|--------|-------------|
| **Client** | `dws.client.name` | Organization names | Client organization/company |
| **Client Code** | `dws.client.ap_code` | Alphanumeric codes | Unique client identifier |
| **Product** | `dws.product.name` | Application names | Business application/service |
| **Product Code** | `dws.product.ap_code` | Alphanumeric codes | Unique product identifier |
| **Environment** | `dws.env.name` | `[..., hprd]` | Runtime environment |
| **Platform** | `dws.platform.name` | Platform names | Technical stack/platform |
| **Platform Code** | `dws.platform.ap_code` | Alphanumeric codes | Unique platform identifier |

### 🔧 Technical Dimensions

| Dimension | Path | Description |
|-----------|------|-------------|
| **Cluster** | `kubernetes.cluster` | Kubernetes cluster |
| **Node** | `kubernetes.node.name` | Execution node |
| **Namespace** | `kubernetes.namespace` | Kubernetes namespace |
| **Pod** | `kubernetes.pod.name` | Pod instance |
| **Container** | `kubernetes.container.name` | Application container |
| **K8s Resource** | `iks_audit.objectRef.resource` | Resource type (pods, services, etc.) |
| **Resource Name** | `iks_audit.objectRef.name` | Specific resource name |

### 👤 Actor Dimensions

| Dimension | Path | Description |
|-----------|------|-------------|
| **User** | `iks_audit.user.username` | User or service account |
| **Groups** | `iks_audit.user.groups` | Membership groups |
| **Source IP** | `iks_audit.sourceIPs` | Origin IP address |
| **User Agent** | `iks_audit.userAgent` | Client/tool used |

---

## 🎯 Identified Analytics Use Cases

### 📊 Supported Business Questions

1. **Q11: Modifications by cluster**
   ```
   "Give me all modifications made to this element 
   (the kube cluster X) made in the last n hours"
   ```
   **Dimensions used:** `kubernetes.cluster`, `iks_audit.verb`, `@timestamp`

2. **Analysis by environment**
   ```
   "What are all production events in the last 24h?"
   ```
   **Dimensions used:** `dws.env.name`, `@timestamp`

3. **Product tracking**
   ```
   "All events related to Payment Service product"
   ```
   **Dimensions used:** `dws.product.name` or `dws.product.ap_code`

### 🔍 Advanced Analysis Patterns

- **Temporal correlation**: Event sequences on same resource
- **Impact analysis**: Event propagation between related resources
- **Anomaly detection**: Detection of unusual patterns by business dimension
- **Capacity planning**: Volumetric analysis by client/product/environment

---

## Attention Points & Recommendations

### Questions to Clarify

1. **AP codes hierarchy**: What is the priority order between `client.ap_code`, `product.ap_code`, `platform.ap_code`?

2. **Identifier uniqueness**: Are AP codes globally unique or unique within their context?

3. **Cardinality**: 
   - Can a client have multiple products?
   - Can a platform serve multiple products?
   - Can a product be on multiple platforms?

4. **Temporal evolution**: Are AP codes stable over time?

### 💡 Implementation Recommendations

1. **AP codes mapping**: Create a correspondence dictionary for searches
2. **Index strategy**: Optimize indexes on most used dimensions
3. **Caching strategy**: Cache business metadata (`dws.*`) that changes infrequently
4. **Monitoring**: Monitor volume by client/product for capacity planning

---

## Impact on Agentic Architecture

### Enriched Kubernetes Agent

The enriched K8s index enables creating a **Business-Aware Kubernetes Agent** capable of:

- **Automatic contextualization**: Understanding the business context of each event
- **Intelligent filtering**: Searches by business AND technical dimensions
- **Advanced correlation**: Links between technical events and business impact
- **Structured reporting**: Summaries by client/product/environment

### Integration with Other Agents

- **VM Agent**: K8s ↔ VM correlation via AP codes
- **Network Agent**: Network impact of contextualized K8s changes
- **Supervisor Agent**: Multi-dimensional query orchestration

---

*Discovery completed on: September 15, 2025*  
*Index analyzed: `datalab-logs-audit-k8s`*  
*Next steps: AP codes clarification and connector implementation*

