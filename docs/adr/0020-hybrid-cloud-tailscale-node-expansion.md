# ADR-0020: Hybrid-Cloud External Node Integration for 20+ Java Microservices via Tailscale

## Status
🔴 **Deprecated (Superseded by ADR-0029)**

## Context
Following the cluster-wide domain namespace partitioning (ADR-0018) and high-speed data backbone setup (ADR-0019), the fleet required a massive compute expansion to host **20+ Java/Spring Boot microservices**.
* **Cloud Constraint**: OCI free-tier ARM/AMD nodes (`arm10`, `amd11`) and GCP outpost (`gce10`) provide ~12 GB total RAM.
* **External Powerhouse (`oracle10`)**: A physical/remote machine offering **32 GB RAM, 8 vCPUs, and 476.9 GB NVMe SSD (258 GB free)**.
* **Remote Isolation & Safety Constraint**: The host is accessed remotely over Tailscale; any disruption to `oracle10`'s Tailscale connection would sever remote management.

## Decision

1. **Zero-Touch Tailscale WireGuard Mesh Interconnect**:
   * `arm10` (Master Node) was provisioned with the official Tailscale daemon (`tailscaled`) running with `--accept-dns=false` to protect K8s CoreDNS.
   * `oracle10`'s existing Tailscale connection was treated with a strict **Zero-Touch Invariant** (read-only IP inspection `tailscale ip -4` $\to$ `100.86.104.67`).
   * Bidirectional point-to-point WireGuard mesh (`100.110.28.71` $\leftrightarrow$ `100.86.104.67`) established with **0% packet loss**.

2. **K3s Control Plane & Agent Configuration**:
   * **Control Plane (`arm10`)**: Configured with `--flannel-iface tailscale0`, `--advertise-address 100.110.28.71`, `--egress-selector-mode disabled`, and TLS SANs for `100.110.28.71`.
   * **Worker Node (`oracle10`)**: Joined via `k3s agent` targeting `https://100.110.28.71:6443` with `--flannel-iface tailscale0`, `--node-ip 100.86.104.67`, and node labels `workload=java-services` and `compute=high-ram`.

3. **Terraform-First Codification & Local Pre-Flight Testing**:
   * Codified in [`hybrid_nodes.tf`](../../hybrid_nodes.tf) and [`outputs.tf`](../../outputs.tf).
   * Verified on Mac using OpenTofu `v1.12.6` and HashiCorp Terraform `v1.16.0` (`tofu validate` and `tofu fmt`).

4. **Dedicated Workload Allocation for 20+ Java Services**:
   * `oracle10` is labeled with `workload=java-services` and `compute=high-ram` to allocate up to 22.0 GB RAM for 20+ JVM microservice containers.

## Consequences

### Positive
* **Massive Fleet Capacity**: Increased total cluster RAM from **12 GB $\to$ 44 GB** (with **25.0 GiB available immediately** on `oracle10`).
* **Zero Remote Disruption**: Zero dropped SSH packets during Tailscale joining and agent initialization.
* **Full Service Discovery**: Pods on `oracle10` resolve and connect directly to `pulsar.data:6650`, `pulsar.data:8080`, and `postgres-primary.data:5432` across the encrypted mesh.
* **Automated Log Streaming**: Vector log harvester DaemonSet deployed automatically to `oracle10` (`10.42.3.x`), streaming all node and container logs to VictoriaLogs.
