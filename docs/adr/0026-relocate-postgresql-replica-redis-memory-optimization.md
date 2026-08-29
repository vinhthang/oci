# ADR 0026: Relocate PostgreSQL Replica, Pgpool, and Redis for Memory Optimization

**Date**: 2026-08-30
**Status**: 🟢 Accepted

## Context
The `amd11` Always Free node (`VM.Standard.E2.1.Micro`) is strictly constrained to 1GB of total RAM. Over time, the node became over-provisioned, hosting the PostgreSQL Replica (384Mi limit), Pgpool connection pooler (256Mi limit), and Redis in-memory cache (384MB limit). Combined, these limits totaled 1024MB, leaving exactly zero memory buffer for the Oracle Linux 10 host OS, the K3s Kubelet, and the Flannel CNI overlay. 

This created an unsustainable environment highly susceptible to kernel Out-Of-Memory (OOM) kills under load, which would destabilize the database replica and caching layer.

## Decision
Instead of artificially squashing the memory limits of these crucial services below their safe operational margins, we decided to leverage our available cross-cloud hybrid nodes:

1. **Move Redis to `arm10`**: Redis acts as the high-speed in-memory state for several microservices. Moving it to the 12GB `arm10` Control Plane provides it with ample headroom for future caching needs without starving edge nodes.
2. **Move PostgreSQL Replica to `oracle10`**: The heavy physical node (`oracle10` with 32GB RAM) is well-suited for stateful database loads.
3. **Move Pgpool to `oracle10`**: Pgpool is relocated alongside the replica to offload the 1GB `amd11` node entirely.

## Consequences
- **Positive**: The `amd11` node is completely freed from heavy memory constraints, stabilizing the cluster's worker plane.
- **Positive**: The PostgreSQL Replica and Redis have safe memory boundaries to operate in without triggering OOM crashes.
- **Negative**: The PostgreSQL Replica now relies on the `oracle10` external Tailscale mesh. If the VPN drops, the primary on `arm10` will lose sync with the replica. However, per ADR-0023, the replica is optional and failover is handled gracefully.
