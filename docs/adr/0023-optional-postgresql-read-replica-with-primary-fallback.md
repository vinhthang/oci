# ADR-0023: Optional PostgreSQL Read-Replica with Resilient Primary Fallback

## Status
🟢 **Accepted & Implemented**

## Context
PostgreSQL 18 (`data` namespace) is deployed with:
* **Primary Instance (`postgres-primary`)**: Hosted on the 24/7 cloud master node `arm10` (10 GB RAM, persistent NVMe storage). Single source of truth for all transactional databases (`memos`, `umami`, `vector_db`).
* **Read-Replica Instance (`postgres-replica`)**: Hosted on the resource-constrained worker node `amd11` (1 GB RAM) via streaming replication.
* **Problem / Invariant**: `amd11` is memory-sensitive (1 GB RAM limit). If `amd11` experiences memory pressure, restart loops, or network partitions, database operations across the entire cluster must **never degrade or fail**.
* The Read-Replica must be treated strictly as an **optional, nice-to-have read-scaling feature**, not a hard dependency.

## Decision

1. **Strictly Optional Read-Replica Lifecycle**:
   * Introduced `postgres.replica.enabled: true/false` in `charts/vinhthang-fleet/values.yaml`.
   * When disabled or absent, all replica resources (PV, PVC, Deployment, Service) are omitted from the cluster without impacting primary operations.

2. **Automatic Primary Fallback Architecture**:
   * **Direct Critical Workloads**: Core applications requiring write consistency connect directly to `postgres-primary.data.svc.cluster.local:5432`.
   * **Unified Service & Load Balancing (`postgres.data.svc.cluster.local`)**:
     * When `pgpool` is active, PgPool monitors the health of `postgres-replica` (backend 1). If the replica becomes unhealthy or unresponsive, PgPool automatically marks backend 1 as offline and routes **100% of read and write traffic directly to `postgres-primary` (backend 0)**.
     * When `pgpool` is disabled or bypassed, `service/postgres` automatically routes directly to `app: postgres-primary`.

3. **Fault Tolerance & Zero Failure Guarantee**:
   * Any failure, crash, eviction, or decommissioning of `postgres-replica` on `amd11` has **zero impact** on database read/write availability.
   * Master `arm10` maintains continuous 24/7 relational database integrity.

## Consequences

### Positive
* **High Availability**: Memory exhaustion or crash of `amd11` will never bring down cluster databases.
* **Operational Flexibility**: The read-replica can be enabled or disabled on demand via a single Helm flag without schema migration or primary restart.
* **Cost & Resource Efficiency**: Easily free up ~300 MB of RAM on `amd11` whenever needed.
