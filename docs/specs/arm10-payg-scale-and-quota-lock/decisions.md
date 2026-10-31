# Architecture Decisions: Scale `arm10` to 4 OCPUs / 24 GB RAM & Lock Always-Free PAYG Quotas

**Feature ID**: `arm10-payg-scale-and-quota-lock`  
**Status**: Planning  

---

## ADR-0046: Scale `arm10` to Full 4 OCPUs / 24 GB RAM Allowance & Enforce Root Compartment Quota Lock on PAYG

### Context
Upgrading the OCI tenancy (`thanghv`) to Pay-As-You-Go (`PAYG`) unlocked the full Always Free Ampere A1 monthly pool (`3,000 OCPU-hours` and `18,000 GB-hours`, equal to **4 OCPUs and 24 GB RAM** 24/7 at `$0.00/month`), while simultaneously lifting hard tenancy service limits to `250 OCPUs`, `1,666 GB RAM`, and `61,440 GB` block storage. Meanwhile, `arm10` was constrained at `2 OCPUs / 12 GB RAM` (`83%` RAM utilization across 25+ K3s pods).

### Decision
1. **Lock Tenancy Quotas First**: Provision a root OCI Compartment Quota policy (`always-free-payg-guardrail`) locking `standard-a1-core-count` (`4`), `standard-a1-memory-count` (`24`), and `total-storage-gb` (`200 GB`) *before* modifying any compute instances, ensuring the tenancy ceiling is enforced at the OCI API admission layer prior to scaling.
2. **Scale `arm10` Inside the Locked Envelope**: Vertically scale `arm10` in-place from `2 OCPUs / 12 GB RAM` to **`4 OCPUs / 24 GB RAM`** (`VM.Standard.A1.Flex`), consuming 100% of the Always Free Ampere A1 allowance on the single K3s control-plane and database node. If OCI's quota counter excludes the initial 1 OCPU / 6 GB Free Tier baseline (`used = 3` / `18`), tighten the quota statements post-resize so `available = 0`.
3. **Declarative Terraform State**: Codify both `oci_limits_quota.always_free_guardrail` and the `4 OCPU / 24 GB` shape in `compute.tf`.

### Trade-offs & Risks
- **Brief Control-Plane Reboot (~60–90s)**: Updating `shape_config` (`ocpus` and `memory_in_gbs`) on an OCI `VM.Standard.A1.Flex` instance triggers an automated in-place instance reboot. All K3s StatefulSets/Deployments on `arm10` automatically recover via `k3s.service` systemd startup and Kubernetes liveness/readiness probes.
- **Hard Quota Ceiling**: While `always-free-payg-guardrail` is active, attempts to launch additional Ampere A1 VMs or expand block storage beyond `200 GB` will be denied by OCI with a `QuotaExceeded` error until the user intentionally updates or removes the quota policy.

### Rejected Alternatives
- **Alternative 1: Split 4 OCPUs / 24 GB RAM Across Two 2-OCPU / 12-GB A1 Instances**: Rejected because a second boot volume (minimum 47 GB) would require `47 + 47 + 100 + 47 = 241 GB` of boot storage, exceeding the `200 GB` Always Free Block Storage limit by `41 GB` and incurring monthly storage charges.
- **Alternative 2: Rely Only on Billing Budget Email Alerts Without Compartment Quotas**: Rejected because budget alerts are asynchronous and notify *after* billable resources are provisioned, whereas OCI Compartment Quotas enforce synchronous pre-provisioning admission control at the IAM/Limits API layer.

- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`
