# Verification Evidence: Scale `arm10` to 4 OCPUs / 24 GB RAM & Lock Always-Free PAYG Quotas

**Feature ID**: `arm10-payg-scale-and-quota-lock`  
**Execution Timestamp**: `2026-10-31T05:13:03Z` – `2026-10-31T05:21:24Z`  
**Status**: Passed (All Acceptance Criteria Met)

---

## 1. Traceability Matrix

| Requirement ID | Description | Acceptance Criteria | Live Command / Evidence | Status |
| :--- | :--- | :--- | :--- | :---: |
| `REQ-001` | Scale `arm10` Compute Shape to 4 OCPUs / 24 GB RAM | Instance updated to 4 OCPUs / 24 GB RAM; boots up to `RUNNING`; `lscpu` reports 4 vCPUs; `free -h` reports ~22 GiB RAM; all K3s nodes `Ready` | `rtk oci compute instance update ...` & `rtk ssh arm10 "lscpu ... && free -h && kubectl get nodes -o wide"` | **PASS** |
| `REQ-002` | Enforce Always-Free Tenancy Quota Lock (`$0/month` Guardrail) | Root tenancy quota `always-free-payg-guardrail` active locking cores (4), memory (24), storage (200); `available = 0` for additional A1 cores and memory; storage quota = 200 GB | `rtk oci limits quota create ...` & `rtk oci limits resource-availability get ...` | **PASS** |
| `REQ-003` | Declarative Terraform Codification & State Alignment | `compute.tf` declares `ocpus = 4`, `memory_in_gbs = 24`, and `oci_limits_quota.always_free_guardrail`; imported into state; `terraform validate` passes exit 0 | `rtk terraform validate` & `rtk terraform import oci_limits_quota.always_free_guardrail ...` | **PASS** |
| `REQ-004` | Architecture Governance (`ADR-0046`) | `ADR-0046` authored in Nygard format; registered in `docs/README.md`; hardware invariant updated to 4 OCPUs / 24 GB RAM | `docs/adr/0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md` & `docs/README.md` | **PASS** |

---

## 2. Verbatim Verification Outputs

### `REQ-002`: Enforce Hard Always-Free Compartment Quota Lock (`$0/month` Guardrail)

#### 1. Quota Creation in Root Tenancy
```bash
$ rtk oci limits quota create \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq \
  --name "always-free-payg-guardrail" \
  --description "Hard lock on Compute A1 and Block Storage to prevent usage beyond OCI Always Free PAYG tier ($0/mo)" \
  --statements '["set compute-core quota standard-a1-core-count to 4 in tenancy", "set compute-memory quota standard-a1-memory-count to 24 in tenancy", "set block-storage quota total-storage-gb to 200 in tenancy"]' \
  --wait-for-state ACTIVE
```
**Output**:
```json
{
  "data": {
    "compartment-id": "ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq",
    "defined-tags": {
      "Oracle-Tags": {
        "CreatedBy": "default/thanghv@gmail.com",
        "CreatedOn": "2026-10-31T05:13:03.400Z"
      }
    },
    "description": "Hard lock on Compute A1 and Block Storage to prevent usage beyond OCI Always Free PAYG tier ($0/mo)",
    "freeform-tags": {},
    "id": "ocid1.quota.oc1..aaaaaaaahnzmzwpwzaajvzkqg4etbjdmosizfzt6mizwjht2wczqcmlxbodq",
    "lifecycle-state": "ACTIVE",
    "locks": [],
    "name": "always-free-payg-guardrail",
    "statements": [
      "set compute-core quota standard-a1-core-count to 4 in tenancy",
      "set compute-memory quota standard-a1-memory-count to 24 in tenancy",
      "set block-storage quota total-storage-gb to 200 in tenancy"
    ],
    "time-created": "2026-10-31T05:13:03.483000+00:00"
  },
  "etag": "894afbd0766b7b3665edc5f78ffe6bda853e8819--gzip"
}
```

#### 2. Resource Availability Verification (`standard-a1-core-count`)
```bash
$ rtk oci limits resource-availability get \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq \
  --service-name compute \
  --limit-name standard-a1-core-count \
  --availability-domain "tTNg:AP-TOKYO-1-AD-1"
```
**Output**:
```json
{
  "data": {
    "available": 0,
    "effective-quota-value": 4.0,
    "fractional-availability": 0.0,
    "fractional-usage": 4.0,
    "used": 4
  }
}
```

#### 3. Resource Availability Verification (`standard-a1-memory-count`)
```bash
$ rtk oci limits resource-availability get \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq \
  --service-name compute \
  --limit-name standard-a1-memory-count \
  --availability-domain "tTNg:AP-TOKYO-1-AD-1"
```
**Output**:
```json
{
  "data": {
    "available": 0,
    "effective-quota-value": 24.0,
    "fractional-availability": 0.0,
    "fractional-usage": 24.0,
    "used": 24
  }
}
```

#### 4. Resource Availability Verification (`total-storage-gb`)
```bash
$ rtk oci limits resource-availability get \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq \
  --service-name block-storage \
  --limit-name total-storage-gb \
  --availability-domain "tTNg:AP-TOKYO-1-AD-1"
```
**Output**:
```json
{
  "data": {
    "available": 6,
    "effective-quota-value": 200.0,
    "fractional-availability": 6.0,
    "fractional-usage": 194.0,
    "used": 194
  }
}
```

---

### `REQ-001`: Scale `arm10` Compute Shape to 4 OCPUs and 24 GB RAM

#### 1. In-Place Shape Update Command
```bash
$ rtk oci compute instance update \
  --instance-id ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna \
  --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
  --force \
  --wait-for-state RUNNING
```
**Output**:
```json
{
  "data": {
    "display-name": "arm10",
    "id": "ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna",
    "lifecycle-state": "RUNNING",
    "shape": "VM.Standard.A1.Flex",
    "shape-config": {
      "baseline-ocpu-utilization": null,
      "gpu-description": null,
      "gpus": 0,
      "local-disk-description": null,
      "local-disks": 0,
      "local-disks-total-size-in-gbs": null,
      "local-volume-size-in-gbs": null,
      "max-vnic-attachments": 4,
      "memory-in-gbs": 24.0,
      "networking-bandwidth-in-gbps": 4.0,
      "ocpus": 4.0,
      "processor-description": "3.0 GHz Ampere® Altra™",
      "resource-management": null,
      "vcpus": 4
    }
  }
}
```

#### 2. Live SSH Host Hardware & K3s Node Fleet Verification
```bash
$ rtk ssh -o ConnectTimeout=20 arm10 "lscpu | grep -E 'Architecture|CPU\(s\):|Model name' && free -h && sudo /usr/local/bin/k3s kubectl get nodes -o wide"
```
**Output**:
```
Architecture:                            aarch64
CPU(s):                                  4
Model name:                              Neoverse-N1
NUMA node0 CPU(s):                       0-3
               total        used        free      shared  buff/cache   available
Mem:            22Gi       2.5Gi        18Gi        16Mi       1.8Gi        19Gi
Swap:             0B          0B          0B
NAME           STATUS   ROLES           AGE   VERSION        INTERNAL-IP      EXTERNAL-IP     OS-IMAGE               KERNEL-VERSION                    CONTAINER-RUNTIME
amd11          Ready    worker          67d   v1.36.3+k3s1   10.0.0.10        <none>          Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.x86_64   containerd://1.7.28-k3s1
arm10          Ready    control-plane   67d   v1.36.3+k3s1   10.0.0.216       <none>          Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.aarch64   containerd://1.7.28-k3s1
gce10          Ready    worker          64d   v1.36.3+k3s1   10.10.0.4        136.111.37.17   Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.x86_64   containerd://1.7.28-k3s1
k3s-worker-1   Ready    <none>          58d   v1.36.4+k3s1   172.26.249.215   <none>          Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.x86_64   containerd://1.7.28-k3s1
k3s-worker-2   Ready    <none>          58d   v1.36.4+k3s1   172.26.247.30    <none>          Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.x86_64   containerd://1.7.28-k3s1
k3s-worker-3   Ready    <none>          58d   v1.36.4+k3s1   172.26.254.150   <none>          Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.x86_64   containerd://1.7.28-k3s1
k3s-worker-4   Ready    <none>          58d   v1.36.4+k3s1   172.26.243.229   <none>          Oracle Linux Server 10.2   6.12.0-101.40.1.el10uek.x86_64   containerd://1.7.28-k3s1
```

---

### `REQ-003`: Declarative Terraform Codification & State Alignment

#### 1. Configuration in `compute.tf`
```hcl
# ==============================================================================
# Node 3: arm10 (K3s Master Powerhouse - 4 OCPUs, 24 GB RAM Ampere A1)
# ==============================================================================
resource "oci_core_instance" "arm10" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = local.compartment_id
  display_name        = "arm10"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.oracle_linux_10_arm.images[0].id
    boot_volume_size_in_gbs = 100
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.private_subnet.id
    display_name     = "vnic-arm10"
    assign_public_ip = false
    hostname_label   = "arm10"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  preserve_boot_volume = false
}

# ==============================================================================
# Always Free PAYG Compartment Quota Guardrail ($0/month Hard Lock)
# ==============================================================================
resource "oci_limits_quota" "always_free_guardrail" {
  compartment_id = var.tenancy_ocid
  name           = "always-free-payg-guardrail"
  description    = "Hard lock on Compute A1 and Block Storage to prevent usage beyond OCI Always Free PAYG tier ($0/mo)"
  statements = [
    "set compute-core quota standard-a1-core-count to 4 in tenancy",
    "set compute-memory quota standard-a1-memory-count to 24 in tenancy",
    "set block-storage quota total-storage-gb to 200 in tenancy",
  ]
}
```

#### 2. Terraform Configuration Validation
```bash
$ cd /Users/thanghoang/github/oci && rtk terraform validate
```
**Output**:
```
Success! The configuration is valid.
```

#### 3. Terraform State Import of Quota Resource
```bash
$ cd /Users/thanghoang/github/oci && rtk terraform import oci_limits_quota.always_free_guardrail ocid1.quota.oc1..aaaaaaaahnzmzwpwzaajvzkqg4etbjdmosizfzt6mizwjht2wczqcmlxbodq
```
**Output**:
```
oci_limits_quota.always_free_guardrail: Importing from ID "ocid1.quota.oc1..aaaaaaaahnzmzwpwzaajvzkqg4etbjdmosizfzt6mizwjht2wczqcmlxbodq"...
oci_limits_quota.always_free_guardrail: Import prepared!
  Prepared oci_limits_quota for import
oci_limits_quota.always_free_guardrail: Refreshing state... [id=ocid1.quota.oc1..aaaaaaaahnzmzwpwzaajvzkqg4etbjdmosizfzt6mizwjht2wczqcmlxbodq]

Import successful!
```

#### 4. Terraform Plan Clean Alignment Check
```bash
$ cd /Users/thanghoang/github/oci && rtk terraform plan -target=oci_limits_quota.always_free_guardrail
```
**Output**:
```
oci_limits_quota.always_free_guardrail: Refreshing state... [id=ocid1.quota.oc1..aaaaaaaahnzmzwpwzaajvzkqg4etbjdmosizfzt6mizwjht2wczqcmlxbodq]
No changes. Your infrastructure matches the configuration.
Terraform has compared your real infrastructure against your configuration
and found no differences, so no changes are needed.
```

---

### `REQ-004`: Architecture Governance (`ADR-0046`)

- **ADR Document**: [`docs/adr/0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md`](../../adr/0046-scale-arm10-4ocpu-24gb-and-lock-payg-quotas.md) authored in Nygard format.
- **Master Registry**: Registered in [`docs/README.md`](../../README.md#architecture-decision-records-adrs) under table entry `ADR-0046`.
- **System Invariant Updated**: Registered updated `arm10` hardware profile (`4 OCPUs and 24 GB RAM`, `100 GB Boot Volume`, locked to the OCI Always Free PAYG ceiling via `always-free-payg-guardrail`) in `docs/README.md`.
