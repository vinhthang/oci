# Verification Evidence: Online `arm10` Boot Volume Expansion to 100 GB

**Feature ID**: `arm10-boot-volume-expansion`  
**Execution Timestamp**: `2026-10-25T07:57:07Z` – `2026-10-25T08:01:38Z`  
**Status**: Passed (All Acceptance Criteria Met)

---

## 1. Traceability Matrix

| Requirement ID | Description | Acceptance Criteria | Live Command / Evidence | Status |
| :--- | :--- | :--- | :--- | :---: |
| `REQ-001` | Online OCI Boot Volume Expansion | Boot volume resized to 100 GB; Tenancy storage = 194 GB / 200 GB (6 GB remaining) | `rtk oci bv boot-volume update` & `rtk oci limits resource-availability get` | **PASS** |
| `REQ-002` | Zero-Downtime Kernel Rescan & LVM/XFS Growth | Kernel sees 100 GB without reboot; Root XFS size >= 95 GB; Usage <= 45% | `rtk ssh arm10 "echo 1 > .../rescan && oci-growfs -y && df -Th /"` | **PASS** |
| `REQ-003` | Declarative Terraform Update & State Import | `boot_volume_size_in_gbs = 100` declared in `compute.tf`; instance imported into state; config valid | `rtk terraform validate` & `rtk terraform import oci_core_instance.arm10` | **PASS** |
| `REQ-004` | K3s Ephemeral Storage & Containerd Hygiene | Completed pods purged; Node reports `ephemeral-storage` ~100 GiB; `DiskPressure=False` | `k3s kubectl delete pod -A` & `k3s kubectl describe node arm10` | **PASS** |
| `REQ-005` | Architecture Governance (ADR-0045) | ADR-0045 authored in Nygard format; registered in `docs/README.md` | `docs/adr/0045-expand-arm10-boot-volume-storage.md` & `docs/README.md` | **PASS** |

---

## 2. Verbatim Verification Outputs

### `REQ-001`: Online OCI Boot Volume Expansion & Always Free Quota Verification

#### 1.1 Boot Volume Update Command
```bash
$ rtk oci bv boot-volume update \
  --boot-volume-id ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca \
  --size-in-gbs 100 \
  --wait-for-state AVAILABLE
```
**Output**:
```json
{
  "data": {
    "auto-tuned-vpus-per-gb": null,
    "autotune-policies": [],
    "availability-domain": "tTNg:AP-TOKYO-1-AD-1",
    "boot-volume-replicas": null,
    "cluster-placement-group-id": null,
    "compartment-id": "ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq",
    "display-name": "arm10 (Boot Volume)",
    "id": "ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca",
    "image-id": "ocid1.image.oc1.ap-tokyo-1.aaaaaaaa3s2rfaecsenoi3dtku4mkgxjgxqfugtpbpcmdnyhwur7rembctva",
    "is-auto-tune-enabled": false,
    "is-hydrated": false,
    "lifecycle-state": "AVAILABLE",
    "size-in-gbs": 100,
    "size-in-mbs": 102400,
    "system-tags": {
      "orcl-cloud": {
        "free-tier-retained": "true"
      }
    },
    "time-created": "2026-08-24T02:53:22.045000+00:00",
    "vpus-per-gb": 10
  }
}
```

#### 1.2 Tenancy Boot Volume Quota Verification
```bash
$ rtk oci bv boot-volume list \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq \
  --availability-domain tTNg:AP-TOKYO-1-AD-1 \
  --query 'data[*].{Name:"display-name",SizeGB:"size-in-gbs",VPUs:"vpus-per-gb",State:"lifecycle-state",ID:id}' \
  --output table
```
**Output**:
```
+----------------------------------------------------------------------------------------------+----------------------------------------+--------+-----------+------+
| ID                                                                                           | Name                                   | SizeGB | State     | VPUs |
+----------------------------------------------------------------------------------------------+----------------------------------------+--------+-----------+------+
| ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrwidebddtdrnffthps6i35m6ixmag3655n5dllcvrajhlhqbqatia | instance-oracle-linux-10 (Boot Volume) | 47     | AVAILABLE | 10   |
| ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljr2bmr74xvmip6xytygxwhoi6bi6cax47yr2o4hynux3kpry25u5ua | amd11 (Boot Volume)                    | 47     | AVAILABLE | 10   |
| ocid1.bootvolume.oc1.ap-tokyo-1.abxhiljrhktr73l7neuytuukt2a2yyvbher7soj3ndrkylx2y4uj6ugavtca | arm10 (Boot Volume)                    | 100    | AVAILABLE | 10   |
+----------------------------------------------------------------------------------------------+----------------------------------------+--------+-----------+------+
```

#### 1.3 Always Free Block Storage Availability
```bash
$ rtk oci limits resource-availability get \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq \
  --service-name block-storage \
  --limit-name total-free-storage-gb \
  --availability-domain tTNg:AP-TOKYO-1-AD-1 \
  --output table
```
**Output**:
```
+-----------+-----------------------+-------------------------+------------------+------+
| available | effective-quota-value | fractional-availability | fractional-usage | used |
+-----------+-----------------------+-------------------------+------------------+------+
| 6         | None                  | 6.0                     | 194.0            | 194  |
+-----------+-----------------------+-------------------------+------------------+------+
```

---

### `REQ-002`: Zero-Downtime Kernel Block Rescan & Online LVM/XFS Expansion

```bash
$ rtk ssh arm10 "echo 1 | sudo tee /sys/class/block/sda/device/rescan && sudo /usr/libexec/oci-growfs -y && lsblk && sudo lvs && df -Th /"
```
**Output**:
```
1
Volume Group: ocivolume
Volume Path: /dev/ocivolume/root
Mountpoint Data     
---------------
          mountpoint: /
              source: /dev/mapper/ocivolume-root
     filesystem type: xfs
         source size: 44.4G
                type: lvm
                size: 44.5G
    physical devices: ['/dev/sda3']
    physical volumes: ['/dev/sda', '/dev/sda']
    partition number: ['3']
   volume group name: ocivolume
   volume group path: /dev/ocivolume/root
Partition dry run expansion "/dev/sda3" succeeded.
CHANGE: partition=3 start=4401152 old: size=93325312 end=97726463 new: size=205314015 end=209715166
Expanding partition /dev/sda3: Confirm?  Partition expand expansion "/dev/sda3" succeeded.
update-partition set to true
FLOCK: try exec open fd 9, on failure exec exits this program
FLOCK: /dev/sda: obtained exclusive lock
resizing 3 on /dev/sda using resize_sfdisk_gpt
209715200 sectors of 512. total size=107374182400 bytes
label: gpt
device: /dev/sda
unit: sectors
first-lba: 34
last-lba: 97727250
sector-size: 512
/dev/sda1 : start=        2048, size=      204800, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B, uuid=30D15CD7-9600-4863...
/dev/sda2 : start=      206848, size=     4194304, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4, uuid=0C1FC9EA-E2E8-4611...
/dev/sda3 : start=     4401152, size=    93325312, type=E6D6D379-F507-44C2-A23C-238F2A3DF928, uuid=F57B997E-B7D7-4026...
padding 33 sectors for gpt secondary header
max_end=209715166 tot=209715200 pt_end=97726463 pt_start=4401152 pt_size=93325312
resize of /dev/sda returned 0.
FLOCK: /dev/sda: releasing exclusive lock
CHANGED: partition=3 start=4401152 old: size=93325312 end=97726463 new: size=205314015 end=209715166
Extending /dev/sda3 succeeded.
Device /dev/sda3 extended successfully.
Logical volume /dev/ocivolume/root extended successfully.
NAME               MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
sda                  8:0    0  100G  0 disk 
├─sda1               8:1    0  100M  0 part /boot/efi
├─sda2               8:2    0    2G  0 part /boot
└─sda3               8:3    0 97.9G  0 part 
  └─ocivolume-root 252:0    0 97.9G  0 lvm  /

  LV   VG        Attr       LSize   Pool Origin Data%  Meta%  Move Log Cpy%Sync Convert
  root ocivolume -wi-ao---- <97.90g                                                    

Filesystem                 Type  Size  Used Avail Use% Mounted on
/dev/mapper/ocivolume-root xfs    98G   42G   56G  43% /
```

---

### `REQ-003`: Declarative Terraform Codification & State Alignment

#### 3.1 Declarative Configuration in `compute.tf`
```hcl
  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.oracle_linux_10_arm.images[0].id
    boot_volume_size_in_gbs = 100
  }
```

#### 3.2 Terraform Configuration Validation
```bash
$ cd /Users/thanghoang/github/oci && rtk terraform validate
```
**Output**:
```
Success! The configuration is valid.
```

#### 3.3 State Import
```bash
$ cd /Users/thanghoang/github/oci && rtk terraform import oci_core_instance.arm10 ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna
```
**Output**:
```
oci_core_instance.arm10: Importing from ID "ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna"...
oci_core_instance.arm10: Import prepared!
  Prepared oci_core_instance for import
oci_core_instance.arm10: Refreshing state... [id=ocid1.instance.oc1.ap-tokyo-1.anxhiljrnfuvvryc6oko53rm4ye7fjpo5xv7qybcbmm6p5pzjie66xtnqsna]

Import successful!

The resources that were imported are shown above. These resources are now in
your Terraform state and will henceforth be managed by Terraform.
```

#### 3.4 State Verification
```bash
$ cd /Users/thanghoang/github/oci && rtk terraform state list | grep arm10
```
**Output**:
```
oci_core_instance.arm10
```

---

### `REQ-004`: K3s Ephemeral Storage & Containerd Space Hygiene

#### 4.1 Pod & Image Pruning
```bash
$ rtk ssh arm10 "sudo /usr/local/bin/k3s kubectl delete pod -A --field-selector=status.phase==Succeeded && sudo /usr/local/bin/k3s crictl rmi --prune"
```
**Output**:
```
pod "fleet-pulsar-bookie-init-6t9m7" deleted from data namespace
pod "fleet-pulsar-pulsar-init-w6lkt" deleted from data namespace
pod "test-pod-arm10" deleted from default namespace
pod "anythingllm-indexer-cron-29878565-mbd5h" deleted from system namespace
pod "anythingllm-indexer-cron-29880005-snplg" deleted from system namespace
pod "anythingllm-indexer-cron-29881445-wvtsw" deleted from system namespace
pod "daily-ai-briefing-29878560-st5nn" deleted from system namespace
pod "daily-ai-briefing-29880000-kcg9f" deleted from system namespace
pod "daily-ai-briefing-29881440-rrrww" deleted from system namespace
pod "nightly-fleet-backup-29878260-jqrmn" deleted from system namespace
pod "nightly-fleet-backup-29879700-lh9fc" deleted from system namespace
pod "nightly-fleet-backup-29881140-8l9zg" deleted from system namespace
```

#### 4.2 K3s Node Status & Refreshed Ephemeral Storage
```bash
$ rtk ssh arm10 "sudo /usr/local/bin/k3s kubectl describe node arm10 | grep -E 'Capacity:|Allocatable:|ephemeral-storage:|DiskPressure|Ready' -A 2"
```
**Output**:
```
  DiskPressure     False   Sun, 25 Oct 2026 08:01:20 +0000   Mon, 24 Aug 2026 07:37:21 +0000   KubeletHasNoDiskPressu...
  PIDPressure      False   Sun, 25 Oct 2026 08:01:20 +0000   Mon, 24 Aug 2026 07:37:21 +0000   KubeletHasSufficientPI...
  Ready            True    Sun, 25 Oct 2026 08:01:20 +0000   Mon, 24 Aug 2026 07:37:21 +0000   KubeletReady          ...
Addresses:
  InternalIP:  10.0.0.216
--
Capacity:
  cpu:                2
  ephemeral-storage:  100184Mi
  hugepages-1Gi:      0
  hugepages-2Mi:      0
--
Allocatable:
  cpu:                2
  ephemeral-storage:  99798011007
  hugepages-1Gi:      0
  hugepages-2Mi:      0
```

---

### `REQ-005`: Architecture Governance (ADR-0045)

- **ADR Document**: [`docs/adr/0045-expand-arm10-boot-volume-storage.md`](../../adr/0045-expand-arm10-boot-volume-storage.md) authored in Nygard format.
- **Master Registry**: Registered in [`docs/README.md`](../../README.md#architecture-decision-records-adrs) under table entry `ADR-0045`.
