# ADR-0029: Remove External Node `oracle10` from K3s Cluster

## Status
🟢 Accepted

## Context
Previously, we integrated a 32 GB RAM external physical node, `oracle10`, to handle heavy Java microservices and Apache Pulsar (ADR-0020, ADR-0024, ADR-0028). 
However, maintaining an external node joined over a Tailscale WAN introduced network routing complexities (ADR-0025) and potential single points of failure for stateful components like the PostgreSQL read replica (ADR-0026) and the event bus (Pulsar).
To streamline the cluster architecture and minimize external dependencies, a decision was made to cleanly sever and remove `oracle10` from the k3s cluster.

## Decision
1. **Remove `oracle10` from Terraform**: All infrastructure declarations binding `oracle10` to the Tailscale mesh and cluster (including SSH provisioning steps) have been deleted from `hybrid_nodes.tf` and `outputs.tf`.
2. **Relocate Apache Pulsar**: Apache Pulsar (zookeeper, bookkeeper, broker, autorecovery) has been migrated back to the internal control-plane node `arm10`. The local storage path for Pulsar has been moved from `/home/thang/pulsar` to `/opt/pulsar`.
3. **Relocate PostgreSQL Replica & Pgpool**: The read replica and pgpool instances have been relocated to `arm10` within the private subnet.
4. **Update Blogs and Documentation**: References to `oracle10` as a functional node within the active system have been deprecated across the deployment configurations and ADR index.

## Consequences
- **Positive**: Simplified network topology entirely contained within cloud native perimeters (OCI + GCP). Eliminates the risk of external node disconnects taking down internal event buses.
- **Negative**: The cluster's total RAM capacity decreases by 32 GB, requiring stricter resource management for workloads scheduled on `arm10` and `amd11`. Java microservices must now be scaled accordingly to fit the existing compute pool.
