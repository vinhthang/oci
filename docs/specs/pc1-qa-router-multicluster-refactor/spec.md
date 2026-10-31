# Specification: `pc-1` Multi-Cluster K3s Refactor & Hybrid Federation Datastores (`qa-router`, `bec1`, `bec2`)

- **Feature ID**: `pc1-qa-router-multicluster-refactor`
- **Status**: `Planning`
- **Date**: 2026-10-31
- **Repositories**: `/Users/thanghoang/github/oci`, `/Users/thanghoang/gitlab/kube_vedge`
- **Governing ADRs**: `ADR-0001`, `ADR-0019`, `ADR-0034`, `ADR-0038`, `ADR-0039`, `ADR-0042`, `ADR-0044`, `ADR-0046`, `ADR-0047`

---

## 1. Overview & Architectural Scope

Refactor the hybrid Kubernetes infrastructure across `pc-1` (Windows Hyper-V workstation) and `arm10` (`10.0.0.216`, OCI ARM Master in `oci-k3s`) to establish the 3-cluster Kubernetes foundation and full datastore layer for `gitlab/kube_vedge` (`cloud-qa-router`, `cloud-qa-f1` / `bec1`, and `cloud-qa-f2` / `bec2`):

1. **All 3 `kube_vedge` K3s Clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) Run Exclusively on `pc-1`** across 5 Hyper-V virtual machines.
2. **`arm10` (`10.0.0.216`) Serves Exclusively as the External Shared Federation Datastore Host** over WireGuard (`10.10.0.0/24`) and VCN (`10.0.0.0/24`), providing shared PostgreSQL 18 (seeded with all 45 federation databases), Opstree Redis, Percona MongoDB, and Apache Pulsar Notification/Stream broker for `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2`.
3. **`pc1-bec1` and `pc1-bec2` Run Compact 1-Replica Local BEC Datastores** inside their respective clusters (`cloud-qa-f1` and `cloud-qa-f2`) for BEC-isolated state (BEC-local PostgreSQL, Redis, MongoDB, and Internal/External Pulsar).
4. **Phase Scope Boundary**: This phase provisions the 3 K3s clusters, WireGuard networking, cross-cluster CoreDNS (`*.corp.intranet`), `arm10` shared datastores, and `pc1-bec1`/`pc1-bec2` local BEC datastores. Deployment of `kube_vedge` application microservices (`vedge-mv-unify-singleapp` and `envoy-gateway-resources`) is deferred to a subsequent phase.

---

## 2. Normative Requirements

### `REQ-001`: Decommission Legacy `pc-1` Worker VMs & Detach from `arm10`
- **Description**: Destroy all existing Hyper-V virtual machines (`k3s-worker-1`, `k3s-worker-2`, `k3s-worker-3`, `k3s-worker-4`) and their virtual hard disks on `pc-1`, and delete the corresponding stale node objects (`k3s-worker-1..4`) from `arm10`'s `oci-k3s` Kubernetes cluster. Also update `arm10` (`oci-k3s`) `data` namespace Redis and MongoDB node affinities so they run on `arm10` instead of waiting for deleted `k3s-worker-*` nodes.
- **Acceptance Criteria**:
  1. `Get-VM` on `pc-1` confirms zero legacy `k3s-worker-*` VMs remain.
  2. `kubectl --context oci-k3s get nodes` on `arm10` contains no `k3s-worker-*` nodes and all remaining `oci-k3s` nodes are `Ready`.

### `REQ-002`: Provision 5 Hyper-V VMs on `pc-1` with WireGuard Mesh Connectivity
- **Description**: Inspect `pc-1` host CPU, RAM, and NVMe storage capacity and provision 5 new Linux Hyper-V Generation 2 VMs auto-sized to ~80% of `pc-1` available resources, connected to the `10.10.0.0/24` WireGuard mesh via `amd10` (`10.10.0.1`) with direct routing to `arm10` (`10.0.0.216`):
  - `k3s-qa-router` (`10.10.0.10`): Control-plane + worker node for `pc1-qa-router` (`cloud-qa-router`).
  - `k3s-bec1-server` (`10.10.0.11`): Control-plane + worker node for `pc1-bec1` (`cloud-qa-f1`).
  - `k3s-bec1-worker` (`10.10.0.12`): Dedicated worker node for `pc1-bec1` (`cloud-qa-f1`).
  - `k3s-bec2-server` (`10.10.0.21`): Control-plane + worker node for `pc1-bec2` (`cloud-qa-f2`).
  - `k3s-bec2-worker` (`10.10.0.22`): Dedicated worker node for `pc1-bec2` (`cloud-qa-f2`).
- **Acceptance Criteria**:
  1. All 5 Hyper-V VMs are `Running` on `pc-1` with static WireGuard IPs (`10.10.0.10`, `10.10.0.11`, `10.10.0.12`, `10.10.0.21`, `10.10.0.22`).
  2. Every VM can ping and reach `arm10` (`10.0.0.216`) and all peer `pc-1` VMs (`10.10.0.10..22`) with 0% packet loss.

### `REQ-003`: Bootstrap 3 Independent K3s Clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`)
- **Description**: Bootstrap three isolated K3s clusters on the 5 `pc-1` VMs (`pc1-qa-router` on `k3s-qa-router`; `pc1-bec1` across `k3s-bec1-server` + `k3s-bec1-worker`; `pc1-bec2` across `k3s-bec2-server` + `k3s-bec2-worker`) with non-overlapping pod/service CIDRs and `--kubelet-arg=max-pods=250`, create target namespaces (`cloud-qa-router`, `cloud-qa-f1`, `cloud-qa-f2`), and merge all three cluster contexts (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) into `/Users/thanghoang/.kube/config`.
- **Acceptance Criteria**:
  1. `kubectl --context pc1-qa-router get nodes` shows `k3s-qa-router` in `Ready` state.
  2. `kubectl --context pc1-bec1 get nodes` shows `k3s-bec1-server` and `k3s-bec1-worker` in `Ready` state.
  3. `kubectl --context pc1-bec2 get nodes` shows `k3s-bec2-server` and `k3s-bec2-worker` in `Ready` state.
  4. Namespaces `cloud-qa-router`, `cloud-qa-f1`, and `cloud-qa-f2` are `Active` on their respective clusters.

### `REQ-004`: Configure `arm10` External Shared Federation Datastores & Cross-Cluster DNS
- **Description**: Configure `arm10`'s (`10.0.0.216`) shared datastores in `charts/vinhthang-fleet/` (PostgreSQL 18, Opstree Redis, Percona MongoDB, and Apache Pulsar Notification/Stream broker in namespace `data`) to run on `arm10` and expose private VCN/WireGuard listeners reachable from `10.10.0.0/24` (strictly avoiding host port `8080`), seed all 45 required `POSTGRES_MULTIPLE_DATABASES` schemas on `arm10` PostgreSQL, and configure CoreDNS `hosts` entries + Kubernetes Service/Endpoints bridges across `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2`:
  - In `pc1-qa-router` (`cloud-qa-router`): Service/Endpoints bridges for `vedge-api-postgres-service:5432`, `redb-cloud-qa-router-headless:12000`, `mck-mongodb-cloud-qa-router-mongos-lb:27017`, and `pulsar-noti-cloud-qa-router-broker` (`6650`/`6651`/`8443`) pointing to `arm10` (`10.0.0.216`).
  - Across `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` CoreDNS: `*.corp.intranet` host entries (`qa-fed-router-pg.corp.intranet`, `router-rds-lb-qa-fed.corp.intranet`, `router-mongo-lb-qa-fed.corp.intranet`, `pulsar-stream-qa-fed.corp.intranet`, `pulsar-admin-qa-fed.corp.intranet`) resolving to `arm10` (`10.0.0.216`).
- **Acceptance Criteria**:
  1. All 4 (PostgreSQL 18, Redis, MongoDB, Pulsar) shared datastores on `arm10` (`oci-k3s` namespace `data`) are `Running`/`Ready` and all 45 `kube_vedge` databases exist on `arm10` PostgreSQL.
  2. Pods inside `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` can resolve and establish TCP/protocol connections to `arm10` PostgreSQL (`5432`), Redis (`12000`), MongoDB (`27017`), and Pulsar (`6650`/`6651`/`12555`) via both `cloud-qa-router` Service names and `*.corp.intranet` hostnames.
  3. Zero generic port `8080` host bindings are introduced on `arm10` (`RULE[adr-governance]`).

### `REQ-005`: Deploy Compact 1-Replica Local BEC Datastores in `pc1-bec1` and `pc1-bec2`
- **Description**: Deploy compact 1-replica local BEC datastores and deterministic datastore credentials (`postgres-secret`, `redis-secret`, `mongodb-secret`, Pulsar TLS secrets) inside `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`):
  - BEC-local PostgreSQL (`vedge-api-postgres-service:5432`) seeded with the 10 BEC-local databases (`vedge_api_device`, `vedge_api_firmware`, `vedge_api_Telemetry`, `vedge_api_speedtest`, `vedge_api_migration`, `vedge_api_topology`, `vedge_api_scheduler`, `vedge_api_reports`, `vedge_api_wifi_Scheduler`, `vedge_api_virtual_device`).
  - BEC-local Redis (`redb-cloud-qa-f1-headless:12000` / `redb-cloud-qa-f2-headless:12000`).
  - BEC-local MongoDB (`mck-mongodb-cloud-qa-f1-mongos-lb:27017` / `mck-mongodb-cloud-qa-f2-mongos-lb:27017`).
  - BEC-local Internal & External Pulsar brokers (`pulsar-internal-cloud-qa-f1-broker` / `pulsar-external-cloud-qa-f1-broker` and `-f2-`).
- **Acceptance Criteria**:
  1. All local datastore pods (PostgreSQL, Redis, MongoDB, Internal Pulsar, External Pulsar) in `cloud-qa-f1` (`pc1-bec1`) and `cloud-qa-f2` (`pc1-bec2`) reach `1/1 Running` (`Ready`).
  2. In-cluster verification probes in `cloud-qa-f1` and `cloud-qa-f2` confirm working SQL queries on all 10 BEC Postgres databases, Redis `PING -> PONG` on port `12000`, MongoDB `ping` on port `27017`, and Pulsar broker/admin readiness on `pulsar-internal` and `pulsar-external`.

### `REQ-006`: Author & Register `ADR-0047` in `/Users/thanghoang/github/oci`
- **Description**: Document the architectural refactor in `/Users/thanghoang/github/oci/docs/adr/0047-pc1-multi-cluster-qa-router-federation-topology.md` (Nygard format) and register it in `/Users/thanghoang/github/oci/docs/README.md`, updating `charts/vinhthang-fleet/` declaratively for `arm10` shared datastore configurations.
- **Acceptance Criteria**:
  1. `docs/adr/0047-pc1-multi-cluster-qa-router-federation-topology.md` exists and follows the repository ADR standard.
  2. `docs/README.md` includes a valid link and summary row for `ADR-0047`.
