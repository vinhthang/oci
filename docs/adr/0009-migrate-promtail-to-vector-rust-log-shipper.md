# ADR-0009: Migration from Promtail (EOL) to Vector (Rust) Log Harvester

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-25
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Grafana officially marked **Promtail as End-of-Life (EOL) in March 2026** and discontinued commercial support. Promtail's Go runtime consumes ~30 MB RAM per node and relies on regex-heavy path harvesting. We needed an actively maintained, ultra-lightweight replacement to tail Kubernetes container logs and ship them to VictoriaLogs.

---

## 2. Decision
We migrated our cluster log harvesting pipeline from **Promtail** to **Vector** (`timberio/vector:0.45.0-alpine`):
1. **Engine**: Pure Rust runtime with zero garbage-collection pauses.
2. **Kubernetes Integration**: Uses Vector's native `kubernetes_logs` source with automatic pod/container/namespace metadata enrichment.
3. **VictoriaLogs Sink**: Native `loki` sink forwarding logs to VictoriaLogs (`http://victorialogs:9428/insert/loki/api/v1/push`).
4. **DaemonSet Deployment**: Deployed across both `arm10` and `amd11` in [`charts/vinhthang-fleet/templates/vector.yaml`](../../charts/vinhthang-fleet/templates/vector.yaml).

---

## 3. Consequences
### Positive:
* **50% Memory Reduction**: Vector consumes only **`~12 – 15 MiB RAM`** per node (down from Promtail's ~30 MiB), giving `amd11` maximum headroom.
* **Actively Maintained**: Modern, high-performance CNCF-supported log router.
* **Automatic Metadata**: Zero complex path regexes needed; pod names, namespaces, and stream labels are natively attached.

### Negative / Trade-offs:
* Replaces Promtail's pipeline stages with Vector Remap Language (VRL).
