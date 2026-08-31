# ADR-0028: Taint and Isolate External Node `oracle10` to Prevent Cluster Entropy

## Status
🔴 Deprecated (Superseded by ADR-0029)

## Context
`oracle10` is an external host with 32 GB RAM joined to the cluster via an encrypted Tailscale WireGuard mesh (ADR-0020). While it provides significant memory capacity, operating an external node over a public WAN overlay introduces several failure modes:
1. **CNI / Overlay Routing Asymmetry**: Cross-node Flannel packet forwarding and K3s cluster service routing (`10.43.0.1:443`) occasionally experience latency spikes, socket timeouts, or MTU fragmentation.
2. **Greedy Default Scheduling**: Because `oracle10` possesses 32 GB RAM, the standard Kubernetes scheduler routinely prioritized `oracle10` for new workloads (including critical databases like `pgpool` and monitoring agents like `kube-state-metrics` and `vmagent`).
3. **Cascading Service Failures**: When core components landed on `oracle10`, they suffered connection timeouts to the API server and `arm10` databases, causing widespread outages for downstream applications (such as Umami and Memos failing to connect to `postgres.data`).

## Decision
We apply a strict `NoSchedule` taint to `oracle10`:
```bash
kubectl taint nodes oracle10 dedicated=external-compute:NoSchedule --overwrite
```

1. **Default Exclusion**: General fleet workloads, core persistence tiers (PostgreSQL primary, Redis), observability agents (`vmagent`, `kube-state-metrics`), and ingress proxies are strictly prevented from scheduling on `oracle10`.
2. **Explicit Tolerations Only**: Only heavy, decoupled workloads (e.g. the 20+ Java microservices suite or batch compute jobs) that explicitly define matching `tolerations` and `nodeSelector` will execute on `oracle10`.
3. **Core Services Fixed to `arm10`**: All databases, AI vector engines (`weaviate`), and core control plane services remain pinned to the robust local OCI private network on `arm10`.

## Consequences
- **Positive**: Eliminates cross-node network failure cascades; standard deployments will always land on the local OCI network (`arm10` / `amd11`).
- **Positive**: Preserves the 32 GB RAM on `oracle10` as a dedicated compute pool for future batch workloads without endangering core platform stability.
- **Negative**: Workloads intended for `oracle10` must explicitly declare tolerations in their Helm templates.
