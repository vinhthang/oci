# ADR 0038: Dedicated Operators Namespace & Ephemeral Redis HA Cluster on On-Premise Hyper-V Nodes

## Context
- **On-Premise Infrastructure Expansion**: Following ADR-0034, four on-premise Hyper-V worker nodes (`k3s-worker-1` to `k3s-worker-4`) were added to the K3s cluster over an encrypted WireGuard mesh. These nodes are hosted on high-performance local developer hardware but are inherently intermittent (powered off outside work hours).
- **Ghost Standalone Redis on Cloud Control Plane**: A standalone Redis instance has been running on the `arm10` cloud control plane node in the `data` namespace, consuming a 512Mi memory limit despite having 0 persistent keys and 0 client commands from cloud services.
- **Upcoming Ephemeral Workloads**: Upcoming AI and batch workloads executing on on-premise PC nodes require high-throughput, low-latency caching without generating continuous cross-WAN traffic over WireGuard to OCI.
- **Multi-Operator Namespace Isolation**: ADR-0018 partitioned the cluster into four functional domains (`data`, `apps`, `observability`, `system`). As Kubernetes operator patterns are adopted across the fleet, running operators within workload namespaces compromises least-privilege RBAC hygiene and lifecycle separation. An explicit amendment to ADR-0018 is required to establish a dedicated `operators` namespace for cluster automation controllers.

## Decision
1. **Establish Dedicated `operators` Namespace**:
   - Amend ADR-0018 domain partitioning to introduce the `operators` namespace dedicated exclusively to Kubernetes controllers and CRD operators.
   - Deploy the Opstree Redis Operator (`quay.io/opstree/redis-operator:v0.26.0`) into the `operators` namespace, pinned to the 24/7 cloud master node (`arm10`) with strict resource bounds (requests: 50m CPU / 64Mi RAM, limits: 200m CPU / 256Mi RAM) and health probes on port 8081 (avoiding generic port 8080).
2. **Deploy Ephemeral Master-Replica Redis HA Cluster**:
   - Install Opstree Redis Custom Resource Definitions (`redisreplications.redis.redis.opstreelabs.in`, `redissentinels.redis.redis.opstreelabs.in`, `redisclusters.redis.redis.opstreelabs.in`, `redis.redis.redis.opstreelabs.in`) into the cluster.
   - Declaratively define a `RedisReplication` resource (`redis`) in the `data` namespace with `clusterSize: 2` and 3 Sentinel monitors.
   - Strictly pin Redis pods to on-premise Hyper-V worker nodes (`k3s-worker-1`, `k3s-worker-2`, `k3s-worker-3`, `k3s-worker-4`) using required `nodeAffinity`.
   - Enforce hard `podAntiAffinity` across `kubernetes.io/hostname` to guarantee replicas and Sentinels are never co-located on the same physical VM.
   - Utilize `emptyDir` ephemeral in-memory storage, explicitly treating Redis as an ephemeral scratch and caching layer with zero persistent volume requirements.
3. **Decommission Standalone Redis on `arm10`**:
   - Set `redis.enabled: false` in the Master Umbrella Helm Chart (`charts/vinhthang-fleet/values.yaml`).
   - Terminate the legacy standalone Redis deployment on `arm10` and delete redundant static manifests (`k8s/redis.yaml`).

## Consequences
- **Sub-Millisecond Local Cache Latency**: On-premise workloads communicate with Redis directly within the local Hyper-V virtual switch / subnet (`172.18.x.x`), achieving sub-millisecond latencies.
- **Zero Cross-WAN Overhead**: Cache reads and writes remain strictly local to the on-premise network, eliminating unnecessary WireGuard tunneling overhead and egress bandwidth to OCI.
- **Zero Cloud Impact on Workstation Shutdown**: Because all Redis data is ephemeral (`emptyDir`) and isolated to on-premise nodes, powering off or rebooting the developer PC causes zero degradation to core cloud services on `arm10`, `amd11`, or `gce10`.
- **Cloud Control Plane Resource Reclamation**: Reclaimed 512Mi memory limit and CPU allocation on `arm10`, preserving cloud memory for relational databases, vector search, and core cluster telemetry.
- **Clean Operator Governance**: Establishes a standard architectural pattern for Kubernetes operators via the `operators` namespace, with RBAC scoped through declarative Helm templates.
