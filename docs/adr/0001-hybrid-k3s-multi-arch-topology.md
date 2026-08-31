# ADR-0001: 3-Node Hybrid Multi-Architecture K3s Kubernetes Fleet

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
We have 3 Always Free compute instances on Oracle Cloud Infrastructure (OCI) in the Tokyo region (`ap-tokyo-1`):
* `amd10`: VM.Standard.E2.1.Micro (AMD64, 1 OCPU, 1 GB RAM, 1 Reserved Public IPv4).
* `amd11`: VM.Standard.E2.1.Micro (AMD64, 1 OCPU, 1 GB RAM, Private IP).
* `arm10`: VM.Standard.A1.Flex (ARM64 Ampere, 2 OCPUs, 10 GB RAM, Private IP).

Running isolated Docker containers on each machine creates high operational friction, duplicate reverse proxies, fractured networking, and zero self-healing orchestration.

---

## 2. Decision
We unified the infrastructure into a single, cohesive **3-Node Hybrid K3s Kubernetes Cluster**:
1. **`arm10` (ARM64 • 10 GB RAM)**: Configured as the **K3s Control Plane (Master)**. Hosts heavy workloads including PostgreSQL 18, AnythingLLM, VictoriaMetrics, VictoriaLogs, Grafana 11, Uptime Kuma, and OpenTelemetry Collector.
2. **`amd11` (AMD64 • 1 GB RAM)**: Configured as the **K3s Worker Node**. Hosts lightweight workloads including Navidrome (FLAC streaming), VietCalendar (Rust API), and FileBrowser.
3. **`amd10` (AMD64 • 1 GB RAM)**: Positioned as the **Edge Ingress Gateway**. Runs Caddy Reverse Proxy, AdGuard Home DoT (853), and serves the Hugo static blog directly from disk.
4. **VCN Private Routing**: Communication between nodes occurs over the private Oracle VCN subnet (`10.0.0.0/16`).
5. **Workload Pinning**: Workloads are pinned using explicit Kubernetes `nodeSelector`:
   * `kubernetes.io/hostname: arm10` for ARM64/heavy services.
   * `kubernetes.io/arch: amd64` for AMD64 services.

---

## 3. Consequences
### Positive:
* Unified control plane and single kubeconfig context (`oci-k3s`).
* Efficient resource utilization: RAM-heavy workloads run on `arm10` while `amd10`/`amd11` stay lean (< 50% RAM usage).
* Flannel overlay network (`10.42.0.0/16`) enables transparent pod-to-pod communication.

### Negative / Trade-offs:
* Container images must be multi-arch (`linux/arm64` and `linux/amd64`) or explicitly targeted via `nodeSelector`.
