# Architecture Decisions: Online `arm10` Boot Volume Expansion to 100 GB

**Feature ID**: `arm10-boot-volume-expansion`  
**Status**: Planning  

---

## ADR-0045: Online In-Place Boot Volume Expansion Over Secondary Block Volume Attachment

- **Context**: `arm10`'s 47 GB boot volume is 92% full (`41 GB` / `45 GB` on `/dev/mapper/ocivolume-root`). The two largest storage consumers are `/var/lib/rancher/k3s` (`21 GB` containerd snapshots and blobs) and `/opt` (`7.9 GB` across VictoriaMetrics, PostgreSQL, VictoriaLogs, backups, Weaviate, OpenViking, and Pulsar). The OCI tenancy has `59 GB` of remaining Always Free Block Storage quota (`141 GB` / `200 GB` used).
  We evaluated two options:
  1. **Option A (In-Place Boot Volume Resize)**: Expand `arm10`'s existing boot volume from `47 GB` to `100 GB` online and grow `/dev/mapper/ocivolume-root` (`xfs`) live using `/usr/libexec/oci-growfs -y`.
  2. **Option B (Secondary Block Volume)**: Provision a separate 50–59 GB OCI Block Volume and mount it at `/opt`.
- **Decision**: Choose **Option A** — resize the existing `arm10` boot volume in-place from `47 GB` to `100 GB` (`+53 GB`, total tenancy usage `194 GB / 200 GB`).
- **Consequences**:
  - **Positive**:
    - Zero downtime: Neither K3s nor stateful databases need to be stopped to migrate `/opt` or `/var/lib/rancher/k3s`.
    - Unified capacity pool: Both `/var/lib/rancher/k3s` (containerd image store + kubelet ephemeral storage) and `/opt` (`local-storage` PVs and `hostPath` volumes) share the full `~98 GB` XFS root volume instead of splitting free space across two fixed mountpoints.
    - Preserves a `6 GB` safety buffer below the `200 GB` OCI Always Free Block Storage cap (`$0.00/month`).
  - **Negative**:
    - OCI boot volume sizes can only be increased in-place, never shrunk without recreating the boot volume.
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`, `REQ-005`
