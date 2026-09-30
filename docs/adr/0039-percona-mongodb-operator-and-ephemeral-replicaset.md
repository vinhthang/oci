# ADR 0039: Percona MongoDB Operator & Ephemeral ReplicaSet Fleet on On-Premise Hyper-V Nodes

## Context
- **On-Premise Infrastructure Expansion**: Following ADR-0034, four on-premise Hyper-V worker nodes (`k3s-worker-1` to `k3s-worker-4`) were integrated into the K3s cluster over an encrypted WireGuard mesh. These nodes are hosted on high-performance local developer hardware but are inherently intermittent (powered off outside work hours).
- **NoSQL Document Storage Requirement**: Upcoming AI, agentic workflows, and batch pipelines executing on on-premise PC nodes require document/NoSQL persistence and scratch state without generating cross-WAN traffic or consuming precious cloud memory.
- **Multi-Operator Namespace Isolation**: ADR-0038 established the dedicated `operators` namespace to isolate Kubernetes automation controllers from application workloads, enforcing strict RBAC hygiene and operational separation.

## Decision
1. **Deploy Percona Server for MongoDB Operator in `operators` Namespace**:
   - Deploy `percona/percona-server-mongodb-operator:1.23.0` into the `operators` namespace.
   - Strictly pin the operator pod to the 24/7 cloud master node (`arm10`) using `nodeSelector` (`kubernetes.io/hostname: arm10`).
   - Configure bounded resource constraints (requests: 50m CPU / 64Mi RAM, limits: 200m CPU / 256Mi RAM).
   - Configure health probes on port 8082 (`/healthz` and `/readyz`) and metrics on port 8083, strictly avoiding generic port 8080 per ADR-0005/ADR-0038 port governance.
2. **Deploy 3-Member Ephemeral MongoDB ReplicaSet on Hyper-V Nodes**:
   - Install Percona Server for MongoDB Operator Custom Resource Definitions (`charts/vinhthang-fleet/crds/psmdb-operator-crds.yaml`).
   - Declaratively define a `PerconaServerMongoDB` CR (`mongodb`) in the `data` namespace using image `percona/percona-server-mongodb:8.0.26-11` and standard port 27017.
   - Configure replica set `rs0` with `size: 3` and `emptyDir: {}` ephemeral storage, treating MongoDB as an in-memory/ephemeral high-throughput document store with zero persistent volume requirements.
   - Configure `unsafeFlags: { tls: true }` to disable internal TLS encryption for the local cluster network, avoiding cert-manager overhead for ephemeral development data.
   - Enforce hard `nodeAffinity` strictly pinning replica set pods to on-premise Hyper-V nodes (`k3s-worker-1`, `k3s-worker-2`, `k3s-worker-3`, `k3s-worker-4`).
   - Enforce hard `podAntiAffinity` across `kubernetes.io/hostname` so that no two MongoDB replicas run on the same virtual machine.
3. **Automate User Credentials and Helm Fleet Integration**:
   - Manage MongoDB authentication secrets (`mongodb-secrets`) declaratively in Helm within the `data` namespace.
   - Integrate both operator and replica set definitions into the Master Umbrella Helm Chart (`charts/vinhthang-fleet/`).

## Consequences
- **Sub-Millisecond NoSQL Latency**: On-premise agentic and batch workloads interact with MongoDB replicas within the local Hyper-V virtual switch / network (`172.18.x.x`), achieving sub-millisecond document read/write latency.
- **Zero Cloud Memory Impact**: MongoDB database pods run strictly on Hyper-V nodes, leaving `arm10`, `amd11`, and `gce10` memory intact for core relational databases (PostgreSQL), vector engines (Weaviate), and edge caching.
- **Zero Cross-WAN Traffic**: All document queries, writes, and replica sync traffic remain strictly local to the on-premise LAN, avoiding WireGuard tunnel congestion and egress bandwidth costs.
- **Graceful Ephemeral Lifecycle**: Because data is ephemeral (`emptyDir: {}`), shutting down or restarting the host workstation causes zero impact to core 24/7 cloud services, and the replica set automatically re-converges when nodes return online.
