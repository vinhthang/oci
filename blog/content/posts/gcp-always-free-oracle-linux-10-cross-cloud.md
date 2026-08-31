---
title: "🌐 Expanding to Multi-Cloud: Provisioning Oracle Linux 10 on Google Cloud's $0 Always Free Tier & Joining K3s"
date: 2026-08-27T19:45:00+07:00
draft: false
tags: ["Google Cloud", "Oracle Linux", "K3s", "Kubernetes", "Multi-Cloud", "DevOps", "Benchmarking", "Always Free"]
categories: ["Cloud Infrastructure"]
author: "Thang Hoang"
showToc: true
TocOpen: true
weight: 1
---

Why settle for one free cloud provider when you can build an automated, resilient **multi-cloud Kubernetes cluster across Oracle Cloud (OCI) and Google Cloud Platform (GCP)** — completely for **$0/month**?

In this post, I walk through the end-to-end process of:
1. Provisioning an **Oracle Linux Server 10.1** instance on Google Cloud's **Always Free Tier (`gce10`)**.
2. Applying kernel and daemon memory hardening to reclaim ~250 MB of RAM.
3. Joining `gce10` as a worker node into our central **K3s Kubernetes cluster** across a secure **WireGuard mesh**.
4. Running a head-to-head performance benchmark comparing **Apple Silicon M1**, **OCI Ampere ARM (`arm10`)**, **GCP Intel Xeon (`gce10`)**, and **OCI AMD EPYC (`amd10`/`amd11`)**.

---

## 🏛️ 1. Multi-Cloud K3s Kubernetes Fleet Architecture

Our fleet previously lived entirely in OCI Tokyo. Adding **`gce10`** in GCP Iowa (`us-central1`) creates a geo-distributed cross-cloud presence with a dedicated US edge outpost.

```mermaid
flowchart TD
    subgraph OCI APAC Region [Oracle Cloud Infrastructure - Tokyo]
        AMD10["amd10 (OCI AMD 1GB)<br>• Caddy Ingress Gateway<br>• Public IPv4: 152.70.101.162<br>• Google SSO Forward-Auth & WireGuard Hub"]
        AMD11["amd11 (OCI AMD 1GB • K3s Worker)<br>• Pod CIDR: 10.42.1.0/24<br>• Navidrome, VietCalendar, FileBrowser"]
        ARM10["arm10 (OCI Ampere ARM 10GB • K3s Master)<br>• Pod CIDR: 10.42.0.0/24<br>• PostgreSQL 18 + pgvector, VictoriaMetrics"]
    end

    subgraph GCP US-Central Region [Google Cloud Platform - Iowa]
        GCE10["gce10 (GCP e2-micro 1GB • K3s Worker)<br>• Pod CIDR: 10.42.2.0/24 (Flannel over WireGuard)<br>• Public IPv4: 136.111.37.17<br>• Vector Log Shipper & US Edge Bridge"]
    end

    AMD10 <-->|Internal VCN| ARM10
    AMD10 <-->|Internal VCN| AMD11
    GCE10 <-->|WireGuard Mesh wg0 (10.10.0.4 <-> 10.10.0.1)| AMD10
    GCE10 <-->|Cross-Cloud Flannel vxlan / Pod Routing| ARM10
```

---

## 🎁 2. Google Cloud Always Free Tier: Rules & Gotchas

Google Cloud provides one of the most generous persistent free tiers, but you must configure your VM **strictly** within these boundaries to avoid unexpected billing:

| Parameter | Always Free Limit | Our Selected Config | Gotcha to Avoid |
| :--- | :--- | :--- | :--- |
| **Machine Type** | 1 non-preemptible `e2-micro` / month | `e2-micro` (2 vCPU, 1 GB RAM) | Do NOT pick `e2-small` or `e2-medium`. |
| **Region** | `us-central1`, `us-east1`, or `us-west1` | `us-central1-a` (Iowa) | Non-US regions (Singapore, Tokyo) are **NOT** free! |
| **Boot Disk** | Up to **30 GB** Standard Persistent Disk | 30 GB `pd-standard` | Do NOT choose `pd-balanced` or `pd-ssd`. |
| **Outbound Egress** | 1 GB/month to all destinations | Standard egress | Bulk media streaming will exceed 1 GB. |

### Provisioning Command via gcloud CLI

```bash
gcloud compute instances create gce-free-vm \
    --project=vietcalendar \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --image-family=oracle-linux-10 \
    --image-project=oracle-linux-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --boot-disk-auto-delete \
    --metadata-from-file=ssh-keys=/path/to/ssh-keys.txt \
    --tags=http-server,https-server
```

---

## 🧠 3. Memory Optimization Playbook on a 1 GB Enterprise VM

Oracle Linux 10 boots with the **Unbreakable Enterprise Kernel (UEK 6.12)** and standard enterprise daemons. Out-of-the-box, it consumed **~600 MiB of RAM**, leaving only ~350 MiB for user workloads.

Here is how we reclaimed memory and stabilized the baseline before starting K3s:

### Step 1: Disable `kdump` & Reclaim Kernel `crashkernel` RAM
```bash
sudo systemctl disable --now kdump
sudo grubby --update-kernel=ALL --remove-args="crashkernel crash_kexec_post_notifiers"
```

### Step 2: Decommission Heavy & Redundant Background Daemons
* **Google Guest Agent Suite (~81 MiB freed)**: Masked `google-guest-agent-manager`, `google-guest-compat-manager`, and `core_plugin`.
* **Redundant Linux Daemons (~60 MiB freed)**: Masked `firewalld`, `tuned`, `google-osconfig-agent`, `rsyslog`, `rngd`, `dtprobed`, `auditd`, and `rpcbind`.

### Step 3: Setup 2.0 GB Swapfile with Low Swappiness
```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl -p /etc/sysctl.d/99-swap.conf
```

---

## ☸️ 4. Joining K3s Kubernetes Over a WireGuard Mesh

With `gce10` connected to `amd10` over WireGuard (`10.10.0.4` $\leftrightarrow$ `10.10.0.1`), we joined `gce10` to the master on `arm10` (`10.0.0.216`):

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_SKIP_SELINUX_RPM=true \
  INSTALL_K3S_VERSION='v1.36.3+k3s1' \
  K3S_URL='https://10.0.0.216:6443' \
  K3S_TOKEN='<MASTER_NODE_TOKEN>' \
  sh -s - agent \
  --node-name gce10 \
  --node-ip 10.10.0.4 \
  --node-external-ip 136.111.37.17 \
  --flannel-iface wg0
```

### Verification on `arm10` Master
```text
NAME    STATUS   ROLES           AGE    VERSION        INTERNAL-IP   EXTERNAL-IP     OS-IMAGE                   KERNEL-VERSION
amd11   Ready    worker          3d6h   v1.36.3+k3s1   10.0.0.10     <none>          Oracle Linux Server 10.2   6.12.0-204.92.4.4.3.el10uek.x86_64
arm10   Ready    control-plane   3d6h   v1.36.3+k3s1   10.0.0.216    <none>          Oracle Linux Server 10.2   6.12.0-204.92.4.4.3.el10uek.aarch64
gce10   Ready    worker          2m     v1.36.3+k3s1   10.10.0.4     136.111.37.17   Oracle Linux Server 10.1   6.12.0-202.76.4.1.el10uek.x86_64
```

The cluster's `vector` daemonset instantly scheduled onto `gce10` (`Pod IP: 10.42.2.2`), immediately harvesting logs and streaming them back to VictoriaLogs on `arm10`!

---

## ⚡ 5. The 5-Node Benchmark Showdown

We ran an identical, standardized benchmark suite across **5 environments**:

1. 🍎 **Apple MacBook Air (M1, 8 Cores, 16 GB Unified Memory)**
2. 🚀 **`arm10` (OCI Ampere Altra ARM64, 2 OCPUs, 10.9 GB RAM)**
3. 🌐 **`gce10` (GCP Intel Xeon x86_64, 2 vCPUs, 1 GB RAM)**
4. 🛡️ **`amd10` (OCI AMD EPYC 7551 x86_64, 2 vCPUs, 1 GB RAM)**
5. 🛡️ **`amd11` (OCI AMD EPYC 7551 x86_64, 2 vCPUs, 1 GB RAM)**

### A. CPU Compute (Prime Calculation — *Lower is Faster*)

| Node | Processor | Single-Core Time | 2-Core Multi-Thread | Relative Speed |
| :--- | :--- | :--- | :--- | :--- |
| 🍎 **Mac (M1)** | Apple M1 (ARM64) | **0.028 s** 🏆 | **0.192 s** | **6.4x faster** than AMD |
| **`arm10`** | Ampere Altra (ARM64) | **0.049 s** 🥈 | **0.211 s** | **3.6x faster** than AMD |
| **`gce10`** | Intel Xeon (x86_64) | **0.066 s** 🥉 | **0.194 s** 🥇 | **3.0x faster** than AMD |
| **`amd10`** | AMD EPYC 7551 (x86_64) | **0.178 s** | **0.587 s** | Baseline |
| **`amd11`** | AMD EPYC 7551 (x86_64) | **0.201 s** | **0.600 s** | Baseline |

---

### B. Direct Disk I/O (*Bypassing RAM Cache — Higher is Better*)

| Node | Direct Write (128 MB) | Direct Read (128 MB) | Storage Medium |
| :--- | :--- | :--- | :--- |
| 🍎 **Mac (M1)** | **464.8 MB/s** 🏆 | **13,724 MB/s** 🏆 | Apple Internal PCIe NVMe SSD |
| **`gce10`** | **87.2 MB/s** 🥇 | **140.6 MB/s** 🥇 | GCP Standard Persistent Disk (30 GB) |
| **`amd10`** | **47.5 MB/s** 🥈 | **73.5 MB/s** 🥈 | OCI Block Storage (50 GB) |
| **`amd11`** | **27.7 MB/s** | **49.8 MB/s** | OCI Block Storage (50 GB) |
| **`arm10`** | **17.7 MB/s** | **10.0 MB/s** | OCI Block Storage *(Active cluster I/O)* |

---

## 🎯 6. Fleet Specialization Matrix

* **`arm10` (OCI ARM 10 GB)**: The **Core Engine**. Houses our PostgreSQL 18 database with `pgvector`, Spring Boot microservices, VictoriaMetrics TSDB, and K3s control plane.
* **`gce10` (GCP Intel 1 GB)**: The **US Outpost & Worker**. High single-core clock speed, fast **140 MB/s storage I/O**, and K3s worker node in North America.
* **`amd10` & `amd11` (OCI AMD 1 GB)**: The **Gatekeepers & Shields**.
  * **Caddy Ingress & TLS Termination**: Caddy uses < 30 MB RAM and < 2% CPU to handle all public domain routing.
  * **2 Free Dedicated Public IPv4s**: OCI includes static public IPs for free.
  * **Zero-Trust Bastion & WireGuard Mesh**: Encrypted overlay networking between private subnets and cross-cloud nodes.
