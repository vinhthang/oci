# ADR-0014: Cross-Cloud Topology & GCP Always Free Oracle Linux 10 Node (`gce10`)

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-27
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
The **Vinh Thang Cloud Fleet (`vinhthang.dev`)** previously operated exclusively within Oracle Cloud Infrastructure (OCI) in the Tokyo region across three nodes (`amd10`, `amd11`, and `arm10`). 

While this provided strong core compute via the Ampere A1 ARM instance (`arm10`) and free dedicated IPv4 edge gateways (`amd10`), the infrastructure had two limitations:
1. **Single-Cloud & Single-Region Dependency**: All workloads and edge endpoints were concentrated in OCI Tokyo (APAC), creating single-provider failure domain risks and higher latency for traffic from North America/Europe.
2. **Underutilized Always-Free Capacity**: Google Cloud Platform (GCP) offers an **Always Free Tier** providing 1 non-preemptible `e2-micro` instance, 30 GB standard persistent disk, and 1 GB monthly egress at **$0/month**.

---

## 2. Decision

We expanded the fleet into a **Multi-Cloud Hybrid K3s Kubernetes Mesh Architecture** by provisioning a Google Cloud Always Free Compute Engine instance (**`gce10`**) running **Oracle Linux 10** and joining it as a worker node into the central K3s cluster:

```mermaid
flowchart TD
    subgraph OCI APAC Region [Oracle Cloud Infrastructure - Tokyo]
        AMD10["amd10 (OCI AMD 1GB)<br>• Caddy Ingress Gateway<br>• Public IPv4: 152.70.101.162<br>• OAuth2 Forward-Auth & WireGuard Hub"]
        AMD11["amd11 (OCI AMD 1GB • K3s Worker)<br>• Pod CIDR: 10.42.1.0/24<br>• Navidrome, VietCalendar, FileBrowser"]
        ARM10["arm10 (OCI Ampere ARM 10GB • K3s Master)<br>• Pod CIDR: 10.42.0.0/24<br>• PostgreSQL 18 + pgvector, VictoriaMetrics"]
    end

    subgraph GCP US-Central Region [Google Cloud Platform - Iowa]
        GCE10["gce10 (GCP e2-micro 1GB • K3s Worker)<br>• Pod CIDR: 10.42.2.0/24 (Flannel over WireGuard)<br>• Public IPv4: 136.111.37.17<br>• Vector Log Shipper & US Edge Bridge"]
    end

    AMD10 <-->|VCN Private Subnet| ARM10
    AMD10 <-->|VCN Private Subnet| AMD11
    GCE10 <-->|WireGuard Mesh wg0 (10.10.0.4 <-> 10.10.0.1)| AMD10
    GCE10 <-->|Cross-Cloud Flannel vxlan / Pod Routing| ARM10
```

### 1. GCP Free Tier Specifications
* **Project**: `vietcalendar`
* **Zone**: `us-central1-a` (Eligible Always-Free US region)
* **Machine Type**: `e2-micro` (2 vCPUs burstable, 1 GB RAM)
* **OS Image**: `oracle-linux-10` from `oracle-linux-cloud` (Oracle Linux Server 10.1, Kernel 6.12.0 UEK)
* **Boot Disk**: Exactly **30 GB** Standard Persistent Disk (`pd-standard`)
* **Cost**: Strictly **$0.00 / month**

### 2. RAM Hardening & Optimization Playbook
To ensure `k3s-agent`, `containerd`, and scheduled pods run smoothly on 1 GB RAM:
1. **Disabled `kdump` & `crashkernel`**: Removed `crashkernel=...` from GRUB command line via `grubby`.
2. **Decommissioned Redundant Daemons**:
   * Masked Google Guest Agent Suite (`google-guest-agent-manager`, `core_plugin`, `google-guest-compat-manager`) after permanently writing SSH keys to `~/.ssh/authorized_keys` (freed **~81 MiB**).
   * Masked `firewalld`, `tuned`, `google-osconfig-agent`, `rsyslog`, `rngd`, `dtprobed`, `auditd`, and `rpcbind` (freed **~60 MiB**).
3. **Configured 2.0 GB Swapfile**:
   * Allocated `/swapfile` (2 GB) on the 30 GB root volume with `vm.swappiness=10`.
4. **Active K3s Memory Footprint**:
   * With `k3s-agent`, `containerd`, and `vector` running, available RAM is **455 MiB** with 2.0 GB Swap buffer.

### 3. K3s Multi-Cloud Cluster Integration
* **WireGuard Overlay**: `gce10` (`10.10.0.4`) connects to `amd10` (`10.10.0.1`) and forwards cross-cloud traffic to `arm10` (`10.0.0.216`).
* **Flannel Configuration**: Flannel interface bound to `wg0` with Pod CIDR `10.42.2.0/24`.
* **Telemetry & Logs**: Vector daemonset automatically scheduled onto `gce10` and streams node/pod logs back to VictoriaLogs on `arm10`.

---

## 3. Consequences

### Positive:
* **Unified Single-Pane Control**: Single `kubectl` context manages container workloads across both OCI Tokyo and GCP Iowa.
* **Automated Log Shipping**: Vector harvesting on `gce10` feeds into central Grafana and VictoriaLogs on `arm10`.
* **Zero Infrastructure Cost**: 100% Always Free across both cloud providers ($0/month).
* **Fault Isolation**: Workloads can target `topology.kubernetes.io/region: us-central1` or `node.kubernetes.io/cloud: gcp`.

### Negative / Trade-offs:
* **Cross-Cloud Latency**: Cross-cloud pod-to-pod networking incurs a ~146 ms round-trip propagation delay between Tokyo and Iowa.
