# ADR 0048: Decommission On-Premise Hyper-V Worker Nodes

## Status
Accepted

## Context
ADR-0034 added four on-premise Hyper-V worker nodes (`k3s-worker-1` to `k3s-worker-4`) to the K3s cluster over the WireGuard mesh, and ADR-0038 / ADR-0039 placed the Redis HA cluster and the MongoDB replica set on those workers via required `nodeAffinity`.

The owner has since deleted all four on-premise workers. They were already absent from the cluster on the evening of 2026-10-31 and confirmed still absent on 2026-11-01: `kubectl get nodes` shows only `amd11`, `arm10` (control-plane), and `gce10`, all Ready, with 35 pods Running and 9 Completed and zero non-running pods. A repo-wide search confirms no live chart configuration references the workers: the only `k3s-worker` mentions in tracked files are the historical ADR texts themselves, and the worker `nodeAffinity` hits are operator CRD schemas, not workload pinning.

## Decision
1. **Decommission**: The on-premise Hyper-V worker nodes are decommissioned. The cluster is now the three cloud nodes `arm10`, `amd11`, and `gce10`.
2. **ADR-0034 deprecated**: The on-premise expansion decision is reversed; ADR-0034 is marked Deprecated (superseded by this ADR).
3. **Placement notes in ADR-0038 / ADR-0039 no longer apply**: The worker-pinning parts of those ADRs are moot. Redis and MongoDB now run on `arm10` (verified live 2026-11-01); the rest of those ADRs (operators namespace, Redis HA, MongoDB operator) still stands, so their status is unchanged.
4. **WireGuard mesh untouched**: The `wg0` mesh (`10.10.0.0/24`) still serves other traffic (e.g. the web-reader ingress) and is not removed or reconfigured by this change.
5. **No chart changes**: Because no live configuration referenced the workers, this decommission needs no Helm value or manifest change.

## Consequences
- **Positive**: The repo no longer implies capacity that does not exist; the ADR index reflects the real 3-node fleet.
- **Negative**: Loss of the on-premise compute capacity from ADR-0034; remaining headroom is the three cloud nodes only.
- **Negative**: Redis and MongoDB now share `arm10` with the control plane and the rest of the fleet; placement is whatever the scheduler decides, not the pinned topology ADR-0038 / ADR-0039 described.
- **Neutral**: If on-premise workers ever return, that is a new decision (new ADR), not a revert of this one.
