# Architecture Decisions: `pc-1` Multi-Cluster K3s Refactor & Hybrid Federation Datastores

- **Feature ID**: `pc1-qa-router-multicluster-refactor`
- **Status**: `Planning`
- **Date**: 2026-10-31
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`

---

## ADR-0047: Dedicated 3-Cluster K3s Topology on `pc-1` with `arm10` External Federation Datastores (Datastore Foundation Phase)

- **Status**: Proposed
- **Date**: 2026-10-31
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`

### Context
Previously (`ADR-0034`, `ADR-0038`, `ADR-0039`), `pc-1` hosted 4 Hyper-V worker VMs (`k3s-worker-1` through `k3s-worker-4`) joined as remote worker nodes to `arm10`'s single `oci-k3s` control plane over the `amd10` WireGuard hub (`10.10.0.0/24`), with Redis and MongoDB pinned via `nodeAffinity` to those `k3s-worker-*` nodes. However, the `gitlab/kube_vedge` QA Federation architecture (`cloud-qa-router`, `cloud-qa-f1` / `bec1`, and `cloud-qa-f2` / `bec2`) requires three distinct Kubernetes clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) on `pc-1`, while using `arm10` (`10.0.0.216`, 4 OCPUs / 24 GB RAM) strictly as the external shared datastore host (`qa-fed-router-pg.corp.intranet`, `router-rds-lb-qa-fed.corp.intranet`, `router-mongo-lb-qa-fed.corp.intranet`, `pulsar-stream-qa-fed.corp.intranet`).

Furthermore, to ensure clean phase separation and verify datastore stability before onboarding ~150+ microservices, the user explicitly directed that this phase deploy only the 3 K3s clusters and the complete datastore layer (both `arm10` external shared datastores and `pc1-bec1`/`pc1-bec2` local BEC datastores), deferring `kube_vedge` microservice deployment to a subsequent phase.

### Decision
1. **Decommission Legacy Worker VMs & Repin `arm10` Shared Datastores (`REQ-001`, `REQ-004`)**:
   - Destroy `k3s-worker-1..4` on `pc-1` and delete their node registrations from `arm10`'s `oci-k3s` cluster.
   - Update `charts/vinhthang-fleet/` on `arm10` (`oci-k3s`) so Opstree Redis and Percona MongoDB in namespace `data` schedule onto `arm10` (1 replica each) alongside PostgreSQL 18 and Apache Pulsar, rather than pinning to removed `k3s-worker-*` nodes.
2. **Provision 5 Hyper-V VMs Across 3 Independent K3s Clusters on `pc-1` (`REQ-002`, `REQ-003`)**:
   - **Cluster 1 (`pc1-qa-router`, namespace `cloud-qa-router`)**: 1 Hyper-V VM (`k3s-qa-router`, WireGuard IP `10.10.0.10`).
   - **Cluster 2 (`pc1-bec1`, namespace `cloud-qa-f1`)**: 2 Hyper-V VMs (`k3s-bec1-server` at `10.10.0.11`, `k3s-bec1-worker` at `10.10.0.12`).
   - **Cluster 3 (`pc1-bec2`, namespace `cloud-qa-f2`)**: 2 Hyper-V VMs (`k3s-bec2-server` at `10.10.0.21`, `k3s-bec2-worker` at `10.10.0.22`).
   - Allocate ~80% of `pc-1` host RAM and CPU across the 5 VMs and register kubeconfig contexts `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` in `~/.kube/config`.
3. **Hybrid Datastore Split & Cross-Cluster DNS (`REQ-004`, `REQ-005`)**:
   - **`arm10` (`10.0.0.216`)**: Hosts the shared Federation datastores (PostgreSQL 18 seeded with all 45 `POSTGRES_MULTIPLE_DATABASES`, Opstree Redis on `12000`/`6379`, Percona MongoDB on `27017`, and Apache Pulsar Notification/Stream broker on `6650`/`6651`/`12555`), wired into `pc1-qa-router` via Kubernetes Service/Endpoints bridges and into all 3 `pc-1` clusters via CoreDNS `*.corp.intranet` host entries.
   - **`pc1-bec1` & `pc1-bec2`**: Each BEC cluster runs compact 1-replica local datastores (PostgreSQL with 10 BEC schemas, Redis on `12000`, MongoDB on `27017`, and Internal + External Pulsar brokers) inside `cloud-qa-f1` and `cloud-qa-f2`.
4. **Governance & ADR Registration (`REQ-006`)**:
   - Document `ADR-0047` in `docs/adr/0047-pc1-multi-cluster-qa-router-federation-topology.md` and register in `docs/README.md`.

### Trade-offs & Risks
- **Cross-WAN Latency for Shared Federation Datastores (`pc-1` <-> `arm10`)**:
  - `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` connect to `arm10` (`10.0.0.216`) over the `amd10` WireGuard tunnel (`10.10.0.0/24`) for shared federation database/cache/broker traffic (~30–60 ms WAN RTT), saving ~6–8 GB of RAM on `pc-1` by reusing `arm10`'s 24 GB RAM capacity.
  - *Mitigation*: High-throughput BEC-local Pulsar (`pulsar-internal`, `pulsar-external`) and BEC-local PostgreSQL/Redis/MongoDB run locally inside `pc1-bec1` and `pc1-bec2` on `pc-1` NVMe storage.
- **Repinning `arm10` Redis & MongoDB from `k3s-worker-*` to `arm10`**:
  - Under `ADR-0038` and `ADR-0039`, Redis and MongoDB in `oci-k3s` were pinned to `k3s-worker-1..4`. With `arm10` upgraded to 4 OCPUs / 24 GB RAM (`ADR-0046`) and `k3s-worker-1..4` decommissioned, repinning compact 1-replica Redis and MongoDB onto `arm10` keeps shared datastores 24/7 online on `arm10` well within its 24 GB RAM envelope.

### Rejected Alternatives
1. **Deploy Microservices and Datastores Simultaneously in a Single Monolithic Phase**:
   - *Rejected*: Explicitly superseded by user instruction (`"the deployment of my services could be in other phase, just deploy the data stores"`). Separating datastore provisioning and verification guarantees clean connectivity baselines before microservice rollout.
2. **Run `cloud-qa-router` on `arm10` (`oci-k3s`)**:
   - *Rejected*: Explicitly superseded by user instruction (`"the arm10 is my external services, I want all these qa-router and becs on my pc-1 only"`).
3. **Collapse `qa-router`, `bec1`, and `bec2` into a Single K3s Cluster**:
   - *Rejected*: Three independent K3s clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) preserve 1:1 multi-cluster isolation for `cloud-qa-router`, `cloud-qa-f1`, and `cloud-qa-f2`.
