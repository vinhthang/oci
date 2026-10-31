# Functional Specification: Online `arm10` Boot Volume Expansion to 100 GB (OCI Always Free Tier)

**Feature ID**: `arm10-boot-volume-expansion`  
**Status**: Planning (Pending Human Approval)  
**Target Host**: `arm10` (`10.0.0.216`, `VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM, `ap-tokyo-1`)  
**Scope**: OCI Block Storage / Oracle Linux 10 LVM+XFS / Terraform IaC / K3s Control Plane  

---

## 1. Problem Statement & Context

The K3s control-plane and core workload node `arm10` currently operates on its default **47 GB** OCI Boot Volume (`ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca`). Its root LVM filesystem (`/dev/mapper/ocivolume-root`, `xfs`) has reached **92% utilization** (`41 GB` used out of `45 GB`, with only `3.6 GB` available):
- `/var/lib/rancher/k3s`: **21 GB** (`14 GB` containerd overlayfs snapshots + `5.8 GB` content blobs).
- `/opt`: **7.9 GB** (`5.6 GB` VictoriaMetrics TSDB, `769 MB` backups, `478 MB` VictoriaLogs, `310 MB` PostgreSQL 18, `234 MB` Grafana, `151 MB` AnythingLLM, `96 MB` Pulsar, `57 MB` OpenViking, `18 MB` Weaviate).
- `/usr` & `/home/opc`: **6.1 GB**.

At 92% utilization, `arm10` is approaching Kubelet's `nodefs.available<10%` eviction threshold, risking `DiskPressure` taints and control-plane pod evictions. Meanwhile, the OCI tenancy has **59 GB** of unused Always Free Block Storage quota (`141 GB` used across 3 × 47 GB boot volumes out of the `200 GB` Always Free limit).

---

## 2. Normative Requirements

### `REQ-001`: Online OCI Boot Volume Expansion within Always Free Quota
- The `arm10` boot volume (`ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca`) MUST be resized online from `47 GB` to `100 GB` (`vpus-per-gb = 10`).
- Total tenancy block/boot storage consumption MUST equal `194 GB` (`47 + 47 + 100 GB`), remaining strictly within the `200 GB` OCI Always Free Block Storage limit (`$0.00/month`) with a `6 GB` safety buffer.

### `REQ-002`: Zero-Downtime Kernel Block Rescan & Online LVM/XFS Expansion
- The paravirtualized block device `/dev/sda` on `arm10` MUST be rescanned online (`echo 1 | sudo tee /sys/class/block/sda/device/rescan`) so the Linux kernel detects the `100 GB` device capacity without rebooting.
- `/usr/libexec/oci-growfs -y` MUST be executed on `arm10` to expand partition `/dev/sda3`, LVM physical volume `/dev/sda3`, LVM logical volume `/dev/mapper/ocivolume-root`, and the root `xfs` filesystem (`/`) online.
- Post-expansion, `df -h /` on `arm10` MUST report total root filesystem size `>= 95G` and usage `<= 45%`.

### `REQ-003`: Declarative Terraform Codification & State Alignment
- `compute.tf` MUST declare `boot_volume_size_in_gbs = 100` inside `oci_core_instance.arm10.source_details`.
- `oci_core_instance.arm10` (`ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna`) MUST be imported into `terraform.tfstate` (if not already present) so declarative Terraform configuration aligns with live OCI state.

### `REQ-004`: K3s Ephemeral Storage & Containerd Space Hygiene
- Completed (`Succeeded`) job pods and unused containerd images on `arm10` MUST be pruned safely via `k3s kubectl delete pod -A --field-selector=status.phase==Succeeded` and `k3s crictl rmi --prune`.
- K3s node `arm10` MUST report updated `ephemeral-storage` capacity (`~98 GiB`), `Ready=True`, and `DiskPressure=False`.

### `REQ-005`: Architecture Governance (ADR-0045)
- An Architecture Decision Record `ADR-0045: Online Expansion of arm10 Boot Volume to 100 GB Within OCI Always Free Tier` MUST be authored in `docs/adr/0045-expand-arm10-boot-volume-storage.md` following the Nygard format.
- `ADR-0045` MUST be registered in `docs/README.md`.
