# ADR-0047: Dedicated 3-Cluster K3s Topology on `pc-1` with `arm10` External Federation Datastores

* **Status**: Accepted
* **Date**: 2026-10-31
* **Category**: Architecture / Multi-Cluster Kubernetes & Hybrid Datastores
* **Related Spec**: [`docs/specs/pc1-qa-router-multicluster-refactor/`](../specs/pc1-qa-router-multicluster-refactor/spec.md)

---

## Context

Previously ([ADR-0034](0034-add-on-premise-hyperv-nodes-via-wireguard.md), [ADR-0038](0038-dedicated-operators-namespace-and-ephemeral-redis-ha-cluster.md), [ADR-0039](0039-percona-mongodb-operator-and-ephemeral-replicaset.md)), the on-premise Windows Hyper-V workstation (`pc-1`, 32 logical cores, 128 GB physical RAM) hosted 4 worker VMs (`k3s-worker-1` through `k3s-worker-4`) joined as remote worker nodes to `arm10`'s single `oci-k3s` control plane.

To support the `gitlab/kube_vedge` multi-cluster federation topology (`cloud-qa-router`, `cloud-qa-f1` / `bec1`, and `cloud-qa-f2` / `bec2`), three independent Kubernetes clusters are required so each site maintains isolated cluster-scoped resources, namespaces, and gateway planes while sharing a common Federation datastore plane (`qa-fed-router-pg.corp.intranet`, `router-rds-lb-qa-fed.corp.intranet`, `router-mongo-lb-qa-fed.corp.intranet`, `pulsar-stream-qa-fed.corp.intranet`, `pulsar-admin-qa-fed.corp.intranet`).

Meanwhile, `arm10` (`10.0.0.216`, 4 OCPUs / 24 GB RAM per [ADR-0046](0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md)) already hosts PostgreSQL 18, Opstree Redis, Percona MongoDB, and Apache Pulsar in the `data` namespace. Running all three `kube_vedge` K3s clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) on `pc-1` while keeping `arm10` strictly as the external shared Federation datastore host isolates the 24/7 OCI control plane from workstation node churn and maximizes `pc-1`'s 128 GB RAM capacity.

---

## Decision

1. **Decommission Legacy Worker VMs (`REQ-001`)**:
   - Destroy `k3s-worker-1` through `k3s-worker-4` on `pc-1` and remove their stale node objects from `arm10` (`oci-k3s`).
   - Schedule `arm10`'s `data` namespace Opstree Redis (`clusterSize: 1`) and Percona MongoDB (`clusterSize: 1`) directly on `arm10` alongside PostgreSQL 18 and Apache Pulsar.

2. **Provision 5 Hyper-V VMs Across 3 Independent K3s Clusters on `pc-1` (`REQ-002`, `REQ-003`)**:
   - Provision 5 Oracle Linux 10 Generation 2 Hyper-V VMs on `pc-1` wired into `amd10`'s WireGuard hub (`10.10.0.0/24` on `wg0`, UDP `51820`):
     - **Cluster 1 (`pc1-qa-router`, namespace `cloud-qa-router`)**: `k3s-qa-router` (`10.10.0.10`, 6 vCPUs, 16 GB RAM).
     - **Cluster 2 (`pc1-bec1`, namespace `cloud-qa-f1`)**: `k3s-bec1-server` (`10.10.0.11`, 6 vCPUs, 20 GB RAM) + `k3s-bec1-worker` (`10.10.0.12`, 6 vCPUs, 20 GB RAM).
     - **Cluster 3 (`pc1-bec2`, namespace `cloud-qa-f2`)**: `k3s-bec2-server` (`10.10.0.21`, 6 vCPUs, 20 GB RAM) + `k3s-bec2-worker` (`10.10.0.22`, 6 vCPUs, 20 GB RAM).
   - Register kubeconfig contexts `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` in `~/.kube/config`.

3. **Hybrid Datastore Split & Cross-Cluster CoreDNS (`REQ-004`, `REQ-005`)**:
   - **`arm10` (`10.0.0.216`) External Shared Federation Datastores**:
     - Expose `arm10`'s `data` namespace datastores over private VCN/WireGuard ports (`5432` for PostgreSQL 18 seeded with all 45 `POSTGRES_MULTIPLE_DATABASES` schemas, `12000`/`6379` for Redis, `27017` for MongoDB, and `6650`/`6651`/`12555` for Apache Pulsar, strictly avoiding host port `8080` per [ADR-0040](0040-migrate-apache-pulsar-to-data-namespace-and-port-governance.md)).
     - Configure `coredns-custom` `*.corp.intranet` host mappings across `pc1-qa-router`, `pc1-bec1`, and `pc1-bec2` resolving `qa-fed-router-pg.corp.intranet`, `router-rds-lb-qa-fed.corp.intranet`, `router-mongo-lb-qa-fed.corp.intranet`, `pulsar-stream-qa-fed.corp.intranet`, and `pulsar-admin-qa-fed.corp.intranet` to `10.0.0.216`, plus Kubernetes Service/Endpoints bridges in `cloud-qa-router` (`charts/qa-router-datastores/`).
   - **`pc1-bec1` & `pc1-bec2` Compact 1-Replica Local BEC Datastores**:
     - Deploy compact 1-replica BEC-local PostgreSQL (`vedge-api-postgres-service:5432` seeded with the 10 BEC schemas), Redis (`redb-cloud-qa-f*-headless:12000`), MongoDB (`mck-mongodb-cloud-qa-f*-mongos-lb:27017`), and Internal + External Pulsar brokers (`pulsar-internal-cloud-qa-f*`, `pulsar-external-cloud-qa-f*`) in `cloud-qa-f1` and `cloud-qa-f2` via `charts/bec-datastores/`.

---

## Consequences

### Positive
* **100% Control-Plane Isolation for OCI (`oci-k3s`)**: `arm10`, `amd11`, and `gce10` remain completely unaffected by `pc-1` power states or multi-cluster QA testing.
* **1:1 Multi-Cluster Federation Parity**: Three dedicated K3s clusters (`pc1-qa-router`, `pc1-bec1`, `pc1-bec2`) mirror the production/QA OKE federation topology (`cloud-qa-router`, `cloud-qa-f1`, `cloud-qa-f2`).
* **Zero Duplicate Router Datastore Overhead on `pc-1`**: Reusing `arm10`'s 24 GB RAM data plane for the shared Federation datastores saves ~6–8 GB RAM on `pc-1` while keeping high-throughput BEC-local datastores on `pc-1` local NVMe storage.

### Negative / Trade-offs
* **Cross-WAN RTT for Shared Federation Datastore Queries**: Traffic between `pc-1` (`10.10.0.10..22`) and `arm10` (`10.0.0.216`) traverses the `amd10` WireGuard tunnel (~30–60 ms RTT).
* **Phased Rollout**: Datastore infrastructure is provisioned and verified in this phase; application microservice charts (`vedge-mv-unify-singleapp` and `envoy-gateway-resources`) are deployed in a subsequent phase.
