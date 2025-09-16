from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class K8sObjectRef(BaseModel):
    api_group: Optional[str] = Field(default=None, alias="apiGroup")
    api_version: Optional[str] = Field(default=None, alias="apiVersion")
    name: Optional[str] = None
    namespace: Optional[str] = None
    resource: Optional[str] = None
    resource_version: Optional[str] = Field(default=None, alias="resourceVersion")
    uid: Optional[str] = None


class DwsClient(BaseModel):
    ap_code: Optional[str] = Field(default=None, alias="ap_code")
    name: Optional[str] = None
    cluster: Optional[str] = None


class DwsEnv(BaseModel):
    name: Optional[str] = None


class DwsMeta(BaseModel):
    client: Optional[DwsClient] = None
    env: Optional[DwsEnv] = None
    platform: Optional[str] = None


class KubernetesContext(BaseModel):
    pod_name: Optional[str] = Field(default=None, alias="pod.name")
    node_name: Optional[str] = Field(default=None, alias="node.name")
    container_name: Optional[str] = Field(default=None, alias="container.name")


class K8sAuditEvent(BaseModel):
    timestamp: datetime = Field(alias="@timestamp")

    # High-level event
    event_action: Optional[str] = Field(default=None, alias="event.action")
    event_dataset: Optional[str] = Field(default=None, alias="event.dataset")

    # Audit core
    audit_id: Optional[str] = Field(default=None, alias="iks_audit.auditID")
    level: Optional[str] = Field(default=None, alias="iks_audit.level")
    request_uri: Optional[str] = Field(default=None, alias="iks_audit.requestURI")

    object_ref: Optional[K8sObjectRef] = None

    # DWS enrichment
    dws: Optional[DwsMeta] = None

    # Kubernetes runtime context (flattened selection)
    k8s_pod_name: Optional[str] = Field(default=None, alias="kubernetes.pod.name")
    k8s_node_name: Optional[str] = Field(default=None, alias="kubernetes.node.name")
    container_name: Optional[str] = Field(default=None, alias="kubernetes.container.name")

    # Raw parts (optional for debugging)
    results: Optional[Any] = Field(default=None, alias="iks_audit.results")

    class Config:
        populate_by_name = True
        extra = "ignore"
