# Implementation Tasks: Scale `arm10` to 4 OCPUs / 24 GB RAM & Lock Always-Free PAYG Quotas

**Feature ID**: `arm10-payg-scale-and-quota-lock`  
**Status**: Complete  

---

## Task Checklist

- [x] **Task 1: Create Root Tenancy Compartment Quota Lock First (`always-free-payg-guardrail`)**
  - Create quota `always-free-payg-guardrail` via `rtk oci limits quota create` locking `standard-a1-core-count` (`4`), `standard-a1-memory-count` (`24`), and `total-storage-gb` (`200`) before resizing `arm10`.
  - Verify `effective-quota-value` is active via `rtk oci limits resource-availability get`.
  - Traceability: `REQ-002`

- [x] **Task 2: Scale `arm10` to 4 OCPUs and 24 GB RAM Inside Locked Quota Envelope**
  - Run `rtk oci compute instance update --instance-id ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna --shape-config '{"ocpus": 4, "memoryInGBs": 24}' --force --wait-for-state RUNNING`.
  - Verify `arm10` boots back up cleanly, SSH is reachable, `lscpu` shows `4` CPUs, `free -h` shows `~22–23 GiB` RAM, and all K3s nodes/pods are `Ready`/`Running`.
  - Re-check `oci limits resource-availability get` after resize; if `used` is `3` / `18` (due to the initial 1 OCPU / 6 GB Free Tier baseline), tighten `always-free-payg-guardrail` to `3` and `18` so `available = 0`.
  - Traceability: `REQ-001`, `REQ-002`

- [x] **Task 3: Codify Quota Lock and 4 OCPUs / 24 GB RAM in Terraform (`compute.tf`)**
  - Add `oci_limits_quota.always_free_guardrail` to `compute.tf` and update `oci_core_instance.arm10.shape_config` to `ocpus = 4` and `memory_in_gbs = 24`.
  - Import the created quota OCID into `terraform.tfstate` and run `rtk terraform validate`.
  - Traceability: `REQ-003`

- [x] **Task 4: Author ADR-0046, Update `docs/README.md`, and Record Verification Evidence**
  - Author `docs/adr/0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md` and register in `docs/README.md`.
  - Record verbatim verification outputs in `docs/specs/arm10-payg-scale-and-quota-lock/verification.md`.
  - Traceability: `REQ-004`
