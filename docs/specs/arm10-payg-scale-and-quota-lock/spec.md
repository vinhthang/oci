# Functional Specification: Scale `arm10` to 4 OCPUs / 24 GB RAM & Lock Always-Free PAYG Quotas

**Feature ID**: `arm10-payg-scale-and-quota-lock`  
**Status**: Planning (Pending Human Approval)  
**Target Host**: `arm10` (`10.0.0.216`, `VM.Standard.A1.Flex`, `ap-tokyo-1`)  
**Scope**: OCI Compute Shape Scaling / OCI Compartment Quotas / Terraform IaC / K3s Control Plane  

---

## 1. Problem Statement & Context

Following the upgrade of the Oracle Cloud Infrastructure tenancy (`thanghv`, `ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq`) to **Pay-As-You-Go (`PAYG`)**, regional service limits in `ap-tokyo-1` (`tTNg:AP-TOKYO-1-AD-1`) expanded to **250 OCPUs** (`standard-a1-core-count`), **1,666 GB RAM** (`standard-a1-memory-count`), and **61,440 GB** (`total-storage-gb`).

Under OCI PAYG billing rules, the first **3,000 OCPU-hours** and **18,000 GB-hours** per month of `VM.Standard.A1.Flex` compute (equivalent to **4 OCPUs and 24 GB RAM** running 24/7) and the first **200 GB** of Block/Boot Volume storage are **100% free (`$0.00/month`)**. However, because PAYG removes the hard Free Tier provisioning ceiling, any resource inadvertently created or scaled beyond `4 OCPUs / 24 GB RAM` or `200 GB` block storage would incur paid charges.

Currently, `arm10` runs with `2 OCPUs` and `12 GB RAM` (`8.3 GiB` / `10 GiB` memory utilized under K3s). Scaling `arm10` to `4 OCPUs` and `24 GB RAM` doubles control-plane CPU and memory capacity at `$0.00/month`, while locking tenancy quotas via an OCI Compartment Quota policy mechanically prevents accidental paid over-provisioning.

---

## 2. Normative Requirements

### `REQ-001`: Scale `arm10` Compute Shape to 4 OCPUs and 24 GB RAM
- The `arm10` compute instance (`ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna`) MUST be updated to `ocpus = 4.0` and `memoryInGBs = 24.0` (`VM.Standard.A1.Flex`).
- After the shape-change reboot completes, `arm10` MUST report `RUNNING` in OCI, `4` vCPUs in `lscpu`, `~22–23 GiB` total RAM in `free -h`, and `Ready=True` in K3s (`kubectl get nodes`).

### `REQ-002`: Enforce Hard Always-Free Compartment Quota Lock (`$0/month` Guardrail)
- An OCI Compartment Quota policy named `always-free-payg-guardrail` MUST be created in the root tenancy (`ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq`).
- The quota policy MUST lock:
  - `compute-core` quota `standard-a1-core-count` so total `VM.Standard.A1.Flex` OCPUs cannot exceed the 4-OCPU free allowance (`effective-quota-value` matching the exact 4-OCPU ceiling).
  - `compute-memory` quota `standard-a1-memory-count` so total `VM.Standard.A1.Flex` memory cannot exceed the 24-GB free allowance (`effective-quota-value` matching the exact 24-GB ceiling).
  - `block-storage` quota `total-storage-gb` to `200` GB across the tenancy.
- `oci limits resource-availability get` MUST confirm `available = 0` additional paid `standard-a1-core-count` and `standard-a1-memory-count` beyond `arm10`'s 4 OCPUs / 24 GB RAM, and `effective-quota-value = 200` on `total-storage-gb`.

### `REQ-003`: Declarative Terraform Codification & State Alignment
- `compute.tf` MUST be updated so `oci_core_instance.arm10.shape_config` declares `ocpus = 4` and `memory_in_gbs = 24`.
- `compute.tf` MUST declare the `oci_limits_quota.always_free_guardrail` resource and import it into `terraform.tfstate`, with `terraform validate` passing with exit code `0`.

### `REQ-004`: Architecture Governance (`ADR-0046`)
- An Architecture Decision Record `ADR-0046: Scale arm10 to 4 OCPUs / 24 GB RAM on PAYG and Lock Always-Free Tenancy Quotas` MUST be authored in `docs/adr/0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md` following the Nygard format.
- `ADR-0046` and the updated `arm10` hardware specification (`4 OCPUs / 24 GB RAM`) MUST be registered in `docs/README.md`.
