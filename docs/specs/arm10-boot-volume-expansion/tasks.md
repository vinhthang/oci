# Implementation Tasks: Online `arm10` Boot Volume Expansion to 100 GB

**Feature ID**: `arm10-boot-volume-expansion`  
**Status**: Complete  

---

## Task Checklist

- [x] **Task 1: Resize `arm10` Boot Volume Online via OCI CLI (`47 GB` -> `100 GB`)**
  - Run `rtk oci bv boot-volume update --boot-volume-id ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca --size-in-gbs 100 --wait-for-state AVAILABLE`.
  - Verify OCI Always Free block storage usage is `194 GB / 200 GB` (`6 GB` remaining available).
  - Traceability: `REQ-001`

- [x] **Task 2: Rescan `/dev/sda` and Grow LVM + XFS Root Filesystem Online on `arm10`**
  - Trigger SCSI block device rescan on `arm10`: `echo 1 | sudo tee /sys/class/block/sda/device/rescan`.
  - Execute `sudo /usr/libexec/oci-growfs -y` on `arm10`.
  - Verify `lsblk`, `sudo lvs`, and `df -Th /` show `/dev/mapper/ocivolume-root` expanded to `~98 GB`.
  - Traceability: `REQ-002`

- [x] **Task 3: Prune Completed K3s Job Pods & Unused Containerd Images on `arm10`**
  - Delete `Succeeded` job pods (`k3s kubectl delete pod -A --field-selector=status.phase==Succeeded`).
  - Prune unreferenced containerd images (`k3s crictl rmi --prune`).
  - Verify K3s node `arm10` reports updated `ephemeral-storage` capacity and `DiskPressure=False`.
  - Traceability: `REQ-004`

- [x] **Task 4: Codify `boot_volume_size_in_gbs = 100` in Terraform & Sync State**
  - Update `oci_core_instance.arm10.source_details` in `compute.tf` with `boot_volume_size_in_gbs = 100`.
  - Import `oci_core_instance.arm10` (`amd10` and `amd11` if needed) into `terraform.tfstate`.
  - Traceability: `REQ-003`

- [x] **Task 5: Author ADR-0045, Register in `docs/README.md`, and Record Verification Evidence**
  - Create `docs/adr/0045-expand-arm10-boot-volume-storage.md` and register in `docs/README.md`.
  - Record verbatim verification outputs in `docs/specs/arm10-boot-volume-expansion/verification.md`.
  - Traceability: `REQ-005`
