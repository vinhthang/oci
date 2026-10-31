# Execution Tasks: `pc-1` Multi-Cluster K3s Refactor & Hybrid Federation Datastores

- **Feature ID**: `pc1-qa-router-multicluster-refactor`
- **Status**: `In-Progress`
- **Date**: 2026-10-31
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`, `REQ-006`

---

## Task Checklist

- [x] **Task 1: Decommission Legacy `pc-1` Worker VMs & Detach Nodes from `arm10`** (`REQ-001`)
  - [x] Delete stale worker nodes `k3s-worker-1`, `k3s-worker-2`, `k3s-worker-3`, `k3s-worker-4` from `arm10` (`oci-k3s` context) (`REQ-001`).
  - [x] Stop and destroy legacy Hyper-V VMs `k3s-worker-1..4` and remove their virtual hard disks on `pc-1` (`REQ-001`).
  - [x] Verify `Get-VM` on `pc-1` and `kubectl --context oci-k3s get nodes` on `arm10` are clean (`REQ-001`).

- [x] **Task 2: Provision 5 New Hyper-V VMs on `pc-1` & Configure WireGuard Mesh (`10.10.0.0/24`)** (`REQ-002`)
  - [x] Inspect `pc-1` CPU/RAM/disk capacity and calculate ~80% RAM allocation across `k3s-qa-router` (`10.10.0.10`), `k3s-bec1-server` (`10.10.0.11`), `k3s-bec1-worker` (`10.10.0.12`), `k3s-bec2-server` (`10.10.0.21`), and `k3s-bec2-worker` (`10.10.0.22`) (`REQ-002`).
  - [x] Provision the 5 Hyper-V VMs on `pc-1`, configure static WireGuard peers on `amd10` (`10.10.0.1`), and verify full mesh routing to `arm10` (`10.0.0.216`) (`REQ-002`).

- [x] **Task 3: Bootstrap 3 Independent K3s Clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) & Merge Kubeconfigs** (`REQ-003`)
  - [x] Bootstrap `pc1-qa-router` K3s server on `k3s-qa-router` (`10.10.0.10`) and create namespace `cloud-qa-router` (`REQ-003`).
  - [x] Bootstrap `pc1-bec1` K3s server on `k3s-bec1-server` (`10.10.0.11`), join `k3s-bec1-worker` (`10.10.0.12`), and create namespace `cloud-qa-f1` (`REQ-003`).
  - [x] Bootstrap `pc1-bec2` K3s server on `k3s-bec2-server` (`10.10.0.21`), join `k3s-bec2-worker` (`10.10.0.22`), and create namespace `cloud-qa-f2` (`REQ-003`).
  - [x] Merge kubeconfig contexts `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` into `/Users/thanghoang/.kube/config` and verify `kubectl get nodes` across all 3 contexts (`REQ-003`).

- [ ] **Task 4: Configure `arm10` External Shared Federation Datastores & Cross-Cluster CoreDNS** (`REQ-004`)
  - [x] Update `charts/vinhthang-fleet/` on `arm10` (`10.0.0.216`) so PostgreSQL 18, Opstree Redis, Percona MongoDB, and Apache Pulsar Notification broker run on `arm10` and expose VCN/WireGuard listeners (`5432`, `12000`, `27017`, `6650`/`6651`/`12555`) without generic port `8080` collisions (`REQ-004`).
  - [x] Seed the 45 `POSTGRES_MULTIPLE_DATABASES` schemas and credentials on `arm10` PostgreSQL (`REQ-004`).
  - [ ] Configure `coredns-custom` `*.corp.intranet` host entries across `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` and Service/Endpoints bridges in `cloud-qa-router` pointing to `arm10` (`10.0.0.216`), and verify connectivity from all 3 clusters (`REQ-004`).

- [ ] **Task 5: Deploy Compact 1-Replica Local BEC Datastores in `pc1-bec1` & `pc1-bec2`** (`REQ-005`)
  - [ ] Seed datastore Secrets and deploy BEC-local PostgreSQL (`vedge-api-postgres-service` with 10 BEC schemas), Redis (`redb-cloud-qa-f*-headless:12000`), MongoDB (`mck-mongodb-cloud-qa-f*-mongos-lb:27017`), and Internal/External Pulsar (`pulsar-internal-cloud-qa-f*`, `pulsar-external-cloud-qa-f*`) in `cloud-qa-f1` (`pc1-bec1`) and `cloud-qa-f2` (`pc1-bec2`) (`REQ-005`).
  - [ ] Verify all BEC-local datastore pods reach `1/1 Ready` and pass SQL, Redis, MongoDB, and Pulsar protocol checks (`REQ-005`).

- [ ] **Task 6: Author `ADR-0047` & Record End-to-End Verification Evidence** (`REQ-006`)
  - [x] Create `/Users/thanghoang/github/oci/docs/adr/0047-pc1-multi-cluster-qa-router-federation-topology.md` and register in `/Users/thanghoang/github/oci/docs/README.md` (`REQ-006`).
  - [ ] Record verbatim verification outputs in `verification.md` mapped to `REQ-001` through `REQ-006` (`REQ-006`).
