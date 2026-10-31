# ADR-0045: Online Expansion of `arm10` Boot Volume to 100 GB Within OCI Always Free Tier

* **Status**: 🟢 Accepted
* **Date**: 2026-10-25
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement

The K3s control-plane and stateful database node `arm10` (`VM.Standard.A1.Flex`, 2 OCPUs, 12 GB RAM) was originally provisioned with the default **47 GB** Oracle Linux 10.2 (`aarch64`) boot volume (`ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2a2yyvbher7soj3ndrkylx2y4uj6ugavtca`).

As the microservice fleet expanded to include Apache Pulsar (`apachepulsar/pulsar-all:4.0.12`, 3.17 GB image), AnythingLLM (`1.1 GB` image), VictoriaMetrics (`5.6 GB` TSDB), VictoriaLogs (`478 MB`), PostgreSQL 18 (`310 MB`), OpenViking (`295 MB`), andPercona MongoDB (`315 MB`), the root LVM XFS filesystem (`/dev/mapper/ocivolume-root`) reached **92% utilization** (`41 GB` used out of `45 GB`, leaving only `3.6 GB` free):
- `/var/lib/rancher/k3s`: **21 GB** (`14 GB` containerd overlayfs snapshots + `5.8 GB` content blobs).
- `/opt`: **7.9 GB** (`local-storage` PVs and `hostPath` volumes).
- `/usr` & `/home/opc`: **6.1 GB**.

At 92% utilization, `arm10` was approaching Kubelet's `nodefs.available<10%` eviction threshold, risking `DiskPressure` taints and pod evictions on the control plane. Meanwhile, the OCI tenancy had **59 GB** of unallocated Always Free Block Storage quota (`141 GB` used across 3 × 47 GB boot volumes out of the `200 GB` Always Free limit).

---

## 2. Decision

1. **Online In-Place Boot Volume Resize (`47 GB` → `100 GB`)**:
   - Resize `arm10`'s boot volume (`ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca`) online from **47 GB** to **100 GB** (`10 VPUs/GB`).
   - Total tenancy block/boot storage becomes **194 GB** (`47 GB` `amd10` + `47 GB` `amd11` + `100 GB` `arm10`), remaining strictly within the **200 GB** OCI Always Free Block Storage tier (`$0.00/month`) with a **6 GB** safety buffer.
2. **Zero-Downtime Kernel Block Rescan & LVM/XFS Expansion**:
   - Trigger an online SCSI block device rescan (`echo 1 | sudo tee /sys/class/block/sda/device/rescan`) on `arm10`.
   - Execute `/usr/libexec/oci-growfs -y` on `arm10` to grow `/dev/sda3`, the `ocivolume` LVM physical/logical volume (`/dev/mapper/ocivolume-root`), and the root `xfs` filesystem (`/`) online from `45 GB` to `~98 GB` without rebooting or stopping K3s.
3. **Containerd & K3s Ephemeral Storage Hygiene**:
   - Prune completed (`Succeeded`) K3s job pods and unreferenced containerd images (`k3s crictl rmi --prune`).
4. **Declarative Terraform Codification**:
   - Codify `boot_volume_size_in_gbs = 100` in `oci_core_instance.arm10.source_details` within [`compute.tf`](../../compute.tf) and import `oci_core_instance.arm10` into `terraform.tfstate`.

---

## 3. Consequences

### Positive:
* **Zero Downtime**: Expanded `arm10` root storage by **+53 GB** (more than doubling usable root capacity from `45 GB` to `98 GB` and dropping utilization from `92%` to `<40%`) with zero pod restarts or database downtime.
* **Unified Capacity Pool**: Both `/var/lib/rancher/k3s` (containerd image store) and `/opt` (database PVs and TSDBs) share the expanded `98 GB` XFS volume.
* **$0.00/Month Cost**: Uses `194 GB` of the `200 GB` OCI Always Free Block Storage entitlement.

### Negative / Trade-offs:
* OCI boot volumes cannot be shrunk in-place once expanded; `194 GB / 200 GB` is now permanently allocated across the three OCI instances unless a boot volume is recreated.
