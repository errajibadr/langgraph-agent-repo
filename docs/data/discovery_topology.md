# DISCOVERY TOPOLOGY - Data Models

**Assymption :** We have a code_ap field in the data for each resource.

## Data Architecture

The discovery topology encompasses four main infrastructure components: virtualization platforms, software instances, network and storage infrastructure, and containerized environments.

## 1. Export ESX vCenter

### Data Structure
| Field | Description |
|-------|-------------|
| Hostname | Server hostname |
| Host_IPAddress | Host IP address |
| Host_OS | Host operating system |
| HardwareVendor | Hardware vendor |
| ESX_Hostname | ESX hostname |
| ESX_IPAddress | ESX IP address |
| ESX_InterfaceName | ESX interface name |
| Switch_InterfaceName | Switch interface name |
| Switch_SystemName | Switch system name |
| Hostname | Hostname |
| Type | System type |
| ap_code | Application code |

### Example
```
Hostname: s00v99949947
Host_IPAddress: 10.244.78.113
Host_OS: VMware, Inc.
HardwareVendor: s02ie9913856
ESX_Hostname: 10.26.230.173
ESX_IPAddress: vmk2
ESX_InterfaceName: Ethernet18
Switch_InterfaceName: REST12-CLOUDA-AL16Y.fr.net.intra
Switch_SystemName: 10_255_236_120
Hostname: VMware vCenter Server
Type: [Type non spécifié dans l'exemple]
```

## 2. Export Software Instance

### Data Structure
| Field | Description |
|-------|-------------|
| Hostname | Hostname |
| Host_OS | Host operating system |
| Host_IPAddress | Host IP address |
| HardwareVendor | Hardware vendor |
| Host_IPAddress | Host IP address |
| SoftwareInstance_Name | Software instance name |
| SoftwareInstance_FullVersion | Software full version |
| SoftwareInstance_DBInstance_Name | Database instance name |
| Managed_SoftwareInstance_Type | Managed software instance type |
| ap_code | Application code |

### Example
```
Hostname: s00v99949947
Host_OS: Red Hat Enterprise Linux Server release 7.9 (Maipo)
Host_IPAddress: 10.244.78.113
HardwareVendor: VMware, Inc.
SoftwareInstance_Name: s00v99949963
SoftwareInstance_FullVersion: 2025-04-19 19:30:11+00:00
SoftwareInstance_DBInstance_Name: 2026-04-19 19:30:11+00:00
Managed_SoftwareInstance_Type: vCenter Server Manager
Certificate_CommonName: CN=s00v99949963,OU=s00v99949963,NodeC1Cell,OU=s00v99949963,O=IBM,C=US
```

## 3. Export NetworkDevices & LB & Storage

### Data Structure
| Field | Description |
|-------|-------------|
| Hostname | Hostname |
| Host_IPAddress | Host IP address |
| Host_OS | Host operating system |
| Host_HardwareVendor | Host hardware vendor |
| Host_InterfaceName | Host interface name |
| Switch_Name | Switch name |
| Switch_InterfaceName | Switch interface name |
| LoadBalancerMember_Name | Load balancer member name |
| LoadBalancerMember_Type | Load balancer member type |
| StorageSystemGroup_Name | Storage system group name |
| StorageSystemGroup_Type | Storage system group type |
| StorageSystemGroup_ManagedCluster_Name | Storage system managed cluster name |
| StorageSystemGroup_ManagedCluster_Type | Storage system managed cluster type |
| ap_code | Application code |

### Example
```
Hostname: s00v99949963
Host_IPAddress: 10.244.64.22
Host_OS: Red Hat Enterprise Linux Server release 7.9 (Maipo)
Host_HardwareVendor: VMware, Inc.
LoadBalancer_NetworkDevice_Name: StorageSystemGroup_Name
StorageSystemGroup_Type: REST12-CLOUDA-AL26Y.fr.net.intra
Switch_Name: CLUS238_DS000_VSAN_MARNE
Switch_InterfaceName: CLUS238_SY480_MARNE_CLOUD_VDCA_WAS
LoadBalancerMember_Name: vCenter Cluster
LoadBalancerMember_Type: PortGroup[s1e01v010.244.64.22:12180]
```

## 4. Export Kubernetes_s100575 → kubernetes Resources List

### Data Structure
| Field | Description |
|-------|-------------|
| ClusterKube_Name | Kubernetes cluster name |
| ClusterKube_region | Kubernetes cluster region |
| ClusterKube_datacenter | Kubernetes cluster datacenter |
| ClusterMembers_Name | Cluster members name |
| ClusterMembers_Name | Cluster members name |
| Namespace_Type | Namespace type |
| Namespace_Name | Namespace name |
| LoadBalancerMember_IPAddress | Load balancer member IP address |
| LoadBalancerPool_Name | Load balancer pool name |
| LoadBalancerPool_IPAddr | Load balancer pool IP address |
| SoftwarePod_Name | Software pod name |
| SoftwareContainer_Name | Software container name |
| ContainerImage_Name | Container image name |
| Deployment_Name | Deployment name |
| ap_code | Application code |

### Example
```
ClusterKube_Name: ClusterKube_region ClusterKube_datacenter
ClusterMembers_Name: ClusterMembers_Name Namespace_Type Namespace_Name
LoadBalancerMember_IPAddress: 10.26.199.172
LoadBalancerPool_Name: kube-dns-proxy on 10.26.199.172
LoadBalancerPool_IPAddr: [privacyLevel.icr.io/ap43591-hprdprpanz/kube-ics-s100567-hprd-89f36c5ad] 
SoftwarePod_Name: par64
SoftwareContainer_Name: eu-fr-2
ContainerImage_Name: opentelemetry-65895477-67act
Deployment_Name: [kube-dns-proxy, opentelemetry-operator]
```

---