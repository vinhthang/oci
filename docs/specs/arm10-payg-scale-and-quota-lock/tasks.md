# Implementation Tasks: Scale `arm10` to 4 OCPUs / 24 GB RAM & Lock Always-Free PAYG Quotas

**Feature ID**: `arm10-payg-scale-and-quota-lock`  
**Status**: Planning  

---

## Task Checklist

- [ ] **Task 1: Scale `arm10` to 4 OCPUs and 24 GB RAM via OCI CLI**
  - Run `rtk oci compute instance update --instance-id ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna --shape-config '{"ocpus": 4, "memoryInGBs": 24}' --force --wait-for-state RUNNING`.
  - Verify `arm10` boots back up cleanly, SSH is reachable, `lscpu` shows `4` CPUs, `free -h` shows `~22–23 GiB` RAM, and all K3s nodes/pods are `Ready`/`Running`.
  - Traceability: `REQ-001`

- [ ] **Task 2: Create Root Tenancy Compartment Quota Lock (`always-free-payg-guardrail`)**
  - Check `oci limits resource-availability get` for `standard-a1-core-count` and `standard-a1-memory-count` after the 4 OCPU / 24 GB resize to determine exact `used` values.
  - Create quota `always-free-payg-guardrail` via `rtk oci limits quota create` locking `standard-a1-core-count`, `standard-a1-memory-count`, and `total-storage-gb` (`200`).
  - Verify `effective-quota-value` and `available = 0` on `standard-a1-core-count` and `standard-a1-memory-count`, and `effective-quota-value = 200` on `total-storage-gb`.
  - Traceability: `REQ-002`

- [ ] **Task 3: Codify 4 OCPUs / 24 GB RAM and Quota Lock in Terraform (`compute.tf`)**
  - Update `oci_core_instance.arm10.shape_config` in `compute.tf` to `ocpus = 4` and `memory_in_gbs = 24`.
  - Add `oci_limits_quota.always_free_guardrail` to `compute.tf`, import the created quota OCID into `terraform.tfstate`, and run `rtk terraform validate`.
  - Traceability: `REQ-003`

- [ ] **Task 4: Author ADR-0046, Update `docs/README.md`, and Record Verification Evidence**
  - Author `docs/adr/0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md` and register in `docs/README.md`.
  - Record verbatim verification outputs in `docs/specs/arm10-payg-scale-and-quota-lock/verification.md`.
  - Traceability: `REQ-004`
