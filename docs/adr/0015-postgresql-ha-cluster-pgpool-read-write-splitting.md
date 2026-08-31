# ADR-0015: PostgreSQL 18 High-Availability Cluster with Physical Streaming Replication and Pgpool-II Read/Write Splitting

## Status
🟢 **Accepted** (2026-08-27)

## Context
As the `vinhthang.dev` fleet grew across multiple services (Umami analytics, Memos microblogging, AnythingLLM knowledge base, and VietCalendar), database operations were concentrated on a single PostgreSQL instance on `arm10`. While `arm10` possesses ample CPU and RAM (12 GB), running a single database node creates a single point of failure (SPOF) for persistence and concentrates all analytical read load on the master instance.

We required an architecture that satisfies three core requirements:
1. **High Availability & Fault Isolation**: Persistent state replicated in real-time to a standby node.
2. **Transparent Read/Write Splitting**: Application services connect to a single unified endpoint (`postgres:5432`) without modifying application code or database connection strings. Write transactions route to the primary master, while read queries route to the standby replica.
3. **Hardware & Resource Efficiency**: Comply with strict hardware boundaries (`arm10` Ampere ARM64 with 12 GB RAM, `amd11` AMD64 with 1 GB RAM).

## Decision

We implemented a 2-Node PostgreSQL 18 Streaming Replication Cluster managed by Pgpool-II within our Master Helm Chart (`charts/vinhthang-fleet`):

```
                                  +-----------------------------+
                                  |   Application Workloads     |
                                  |  (Umami, Memos, AnythingLLM)|
                                  +--------------+--------------+
                                                 |
                                     Port 5432 (Unified DSN)
                                                 v
                                  +-----------------------------+
                                  |    Pgpool-II Query Router   |
                                  |       (Node: amd11)         |
                                  +------+---------------+------+
                                         |               |
                         Write Queries   |               | Read Queries
                         (INSERT/UPDATE) |               | (SELECT)
                                         v               v
                +-----------------------------+   +-----------------------------+
                |   PostgreSQL 18 Primary     |   |    PostgreSQL 18 Standby    |
                |   (Master Node: arm10)      |   |    (Replica Node: amd11)    |
                |   wal_level: replica        |   |    hot_standby: on          |
                |   Storage: /opt/postgres    |   |    Storage: /opt/postgres-r |
                +--------------+--------------+   +-----------------------------+
                               |                                 ^
                               +======= WAL Streaming ===========+
                                  (Async Replication, < 0.5ms)
```

### Key Architectural Specifications:
1. **Primary Master (`postgres-primary`)**:
   - Pinned to `arm10` (`nodeSelector: kubernetes.io/hostname: arm10`).
   - Configured with `wal_level=replica`, `max_wal_senders=10`, `max_replication_slots=10`, and `hot_standby=on`.
   - Automated initialization scripts dynamically create databases (`memos`, `umami`, `vector_db`) and provision the `replicator` role.
2. **Standby Replica (`postgres-replica`)**:
   - Pinned to `amd11` (`nodeSelector: kubernetes.io/hostname: amd11`).
   - Uses an `initContainer` (`init-replica`) to automatically execute `pg_basebackup -h postgres-primary -U replicator -Fp -Xs -R` if `/var/lib/postgresql/data/pgdata` is empty.
   - Runs in Hot Standby mode (`pg_is_in_recovery() = true`), actively streaming WAL logs.
3. **Query Router & Load Balancer (`pgpool`)**:
   - Pinned to `amd11` (`nodeSelector: kubernetes.io/hostname: amd11`) running official `docker.io/pgpool/pgpool:latest` (native AMD64).
   - Configured with `PGPOOL_PARAMS_MASTER_SLAVE_MODE=on`, `PGPOOL_PARAMS_MASTER_SLAVE_SUB_MODE=stream`, and `PGPOOL_PARAMS_LOAD_BALANCE_MODE=on`.
   - Weights: Primary `backend_weight0=0` (writes only), Standby `backend_weight1=1` (100% of read queries).
   - Service `postgres:5432` maps directly to `pgpool:5432`.

## Consequences

### Positive
- **Zero Application Changes**: All client services continue connecting to `postgres:5432` with credentials from `postgres-secret`.
- **Automatic Read Offloading**: Analytical `SELECT` queries from Umami and full-text searches from Memos are served entirely by `postgres-replica` on `amd11`.
- **Sub-millisecond Replication**: Both primary and standby reside within the OCI Tokyo local network, achieving sub-millisecond replication lag.
- **Declarative GitOps Management**: The entire cluster topology is governed via `charts/vinhthang-fleet/templates/postgres.yaml` and parameterized in `values.yaml`.

### Trade-offs & Mitigations
- **Memory Footprint on `amd11`**: `postgres-replica` and `pgpool` consume ~200 MiB RAM combined on `amd11`.
  - *Mitigation*: Resource limits are strictly bounded (`memory: 384Mi` for replica, `memory: 256Mi` for pgpool) backed by a 3.4 GB swap space buffer on `amd11`.
