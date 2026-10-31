# ADR-0046: Scale `arm10` to 4 OCPUs / 24 GB RAM on PAYG and Lock Always-Free Tenancy Quotas

* **Status**: Accepted
* **Date**: 2026-10-31
* **Category**: Infrastructure / Compute & Billing Governance
* **Related Spec**: [`docs/specs/arm10-payg-scale-and-quota-lock/`](../specs/arm10-payg-scale-and-quota-lock/spec.md)

---

## Context

Following the upgrade of the Oracle Cloud Infrastructure tenancy (`thanghv`, `ap-tokyo-1`) from the Free Tier to **Pay-As-You-Go (`PAYG`)**, the regional service limits in `tTNg:AP-TOKYO-1-AD-1` automatically expanded to **250 OCPUs** (`standard-a1-core-count`), **1,666 GB RAM** (`standard-a1-memory-count`), and **61,440 GB** (`total-storage-gb`).

Under OCI PAYG billing rules:
- The first **3,000 OCPU-hours** and **18,000 GB-hours** per month of `VM.Standard.A1.Flex` compute—equivalent to **4 OCPUs and 24 GB RAM running 24/7**—are **100% free (`$0.00/month`)**.
- The first **200 GB** of Block and Boot Volume storage across the tenancy (`47 GB amd10 + 47 GB amd11 + 100 GB arm10 = 194 GB`) are **100% free (`$0.00/month`)**.

Previously, `arm10` (`10.0.0.216`) was running at `2 OCPUs / 12 GB RAM`, with `8.3 GiB / 10 GiB` (`83%`) of memory consumed by the K3s control plane, databases, vector engine, and observability stack. However, because PAYG removes the hard Free Tier provisioning ceiling, any resource accidentally created or scaled beyond `4 OCPUs / 24 GB RAM` or `200 GB` block storage would incur paid hourly or monthly charges.

---

## Decision

1. **Enforce Root Compartment Quota Lock First (`always-free-payg-guardrail`)**:
   - Before modifying any compute shapes, provision an OCI Compartment Quota policy (`always-free-payg-guardrail`) in the root tenancy (`ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq`) locking `compute-core` (`standard-a1-core-count`), `compute-memory` (`standard-a1-memory-count`), and `block-storage` (`total-storage-gb` to `200`) to the exact Always Free thresholds.
   - If OCI's internal `standard-a1-*` counter excludes the original 1 OCPU / 6 GB Free Tier baseline (`used = 3` cores / `18` GB for a 4 OCPU / 24 GB instance), tighten the quota statements post-resize so `available = 0`.
2. **Scale `arm10` In-Place to 4 OCPUs and 24 GB RAM**:
   - Vertically scale `arm10` (`ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna`) in-place to `ocpus = 4` and `memoryInGBs = 24` (`VM.Standard.A1.Flex`), doubling CPU cores, doubling RAM, and increasing primary VNIC bandwidth from 2 Gbps to 4 Gbps at `$0.00/month`.
3. **Declarative Terraform Alignment**:
   - Codify `oci_limits_quota.always_free_guardrail` and `ocpus = 4`, `memory_in_gbs = 24` in [`compute.tf`](../../compute.tf) and import the quota resource into `terraform.tfstate`.

---

## Consequences

### Positive
* **2x Control-Plane CPU & Memory at `$0.00/Month`**: `arm10` scales from `2 OCPUs / 12 GB RAM` to `4 OCPUs / 24 GB RAM`, cutting memory pressure in half (`~38%` utilization) and providing ample headroom for K3s, PostgreSQL, Weaviate, OpenViking, and VictoriaMetrics.
* **Hard API-Level Billing Protection**: OCI's admission controller mechanically rejects any CLI, Terraform, or Console request that attempts to provision Ampere A1 cores/memory beyond `arm10`'s 4 OCPUs / 24 GB RAM (`available = 0`) or block storage beyond `200 GB`.
* **Zero Terraform Drift**: Both the instance shape and the root quota guardrail are tracked declaratively in `compute.tf` and `terraform.tfstate`.

### Negative / Trade-offs
* **Brief In-Place Reboot (~60–90s)**: Applying the `shape_config` update on `arm10` triggers an automatic hardware-level reboot while OCI migrates the instance to a 4-OCPU / 24-GB allocation.
* **Intentional Unlock Required for Future Paid Scaling**: If paid capacity above 4 OCPUs / 24 GB RAM or 200 GB storage is desired in the future, `oci_limits_quota.always_free_guardrail` must be explicitly updated first.
