# ADR-0019: In-Memory Redis Data Infrastructure (Pulsar Decommissioned)

## Status
🟢 **Accepted & Implemented** (Pulsar standalone decommissioned; In-Memory Redis active)

## Context
Following the cluster-wide domain namespace partitioning into `data`, `apps`, `observability`, and `system` (ADR-0018), the fleet required a unified **high-speed in-memory caching layer**:
1. **In-Memory Caching (Redis)**: Required for session caching, rate-limiting, and AI vector lookups without disk latency or persistent volume overhead.
2. **Event Streaming Backbone (Pulsar - Decommissioned)**: The legacy Pulsar standalone broker has been decommissioned to streamline data infrastructure and reclaim memory on `arm10`.
3. **Hardware Boundaries**:
   * `arm10` (Master Node): 10 GB RAM, suitable for stateful and JVM engines.
   * `amd11` (Worker Node): 1 GB RAM, dedicated to featherweight C/Rust runtimes.
   * `gce10` (GCP Outpost): 1 GB RAM, dedicated US edge static cache and disaster outpost.

## Decision

1. **In-Memory Redis Cache (`data` namespace)**:
   * **Node Placement**: Pinned to `amd11` (`nodeSelector: kubernetes.io/hostname: amd11`) for microsecond-level latency to Tokyo workloads.
   * **Storage**: **Pure In-Memory (0 PVC/Disk Allocations)** with `--save ""` disabling RDB/AOF disk dumps.
   * **Memory Management**: `maxmemory: 384mb` with `maxmemory-policy: allkeys-lru` and resource limits capped at `256Mi RAM`.
   * **Service Discovery**: `redis.data.svc.cluster.local:6379` (or `redis.data:6379`).

2. **Compact Apache Pulsar Engine (`data` namespace)**:
   * **Node Placement**: Pinned strictly to `arm10` (`nodeSelector: kubernetes.io/hostname: arm10`).
   * **Architecture**: Compact standalone engine running embedded ZooKeeper metadata, embedded BookKeeper ledger storage, and Pulsar Broker in **1 single process** (`bin/pulsar standalone --no-functions-worker`).
   * **Zero Proxy Overhead**: Applications connect directly to `pulsar.data:6650` (Binary protocol) and `pulsar.data:8080` (Admin REST API), eliminating proxy latency and saving memory.
   * **JVM Sizing**: `-Xms256m -Xmx384m -XX:MaxDirectMemorySize=128m` with container cgroup limits set to `1024Mi RAM`.
   * **Storage**: `pulsar-data-pv` and `pulsar-data-pvc` (10 GiB) on `/opt/pulsar-data` on `arm10` with `useHostNameAsBookieID=true`.

## Consequences

### Positive
* **Zero Disk Overhead for Redis**: Pure in-memory caching eliminates SSD write wear and disk bottlenecks.
* **Low Memory Footprint**: Compact Pulsar standalone consumes only ~380 MiB RAM (saving ~1 GB compared to a 3-pod distributed cluster).
* **Multi-Namespace DNS**: Microservices in `apps` (e.g. `anythingllm`, `memos`, `umami`) connect seamlessly to `redis.data:6379` and `pulsar.data:6650`.
* **Zero Downtime & Verified Streaming**: Full pub/sub message production and consumption verified with 0 dropped events.
