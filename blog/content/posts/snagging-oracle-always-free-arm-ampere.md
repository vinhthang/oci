---
title: "How to Snag the Elusive Oracle Cloud Always Free ARM64 Ampere A1 Instance"
date: 2026-08-24T18:45:00+07:00
draft: false
tags: ["Oracle Cloud", "OCI", "ARM64", "Ampere A1", "Python", "DevOps", "Automation", "Always Free"]
categories: ["Cloud Infrastructure", "DevOps"]
author: "Thang Hoang & Antigravity"
showToc: true
TocOpen: true
---

If you have ever tried to launch an **ARM64 Ampere A1 Flex** compute instance on **Oracle Cloud Infrastructure (OCI) Always Free**, you have almost certainly encountered this dreaded error message:

> `500-InternalError: Out of host capacity for shape VM.Standard.A1.Flex in availability domain...`

Oracle's Always Free tier offers one of the most generous compute allowances in the industry—**up to 4 OCPUs and 24 GB RAM** on enterprise-grade Ampere Altra ARM64 processors. Because of this, capacity in popular data centers (like Tokyo, Seoul, Ashburn, Frankfurt, and Singapore) is constantly saturated.

Clicking "Create" manually in the web console is an exercise in futility. In this post, I will share the exact automated strategy and Python script we used to reliably capture our **`arm10`** powerhouse instance.

---

## 🎯 The Strategy: Why Manual Creation Fails

Cloud capacity fluctuates dynamically. When other users terminate test instances, decommission pods, or resize workloads, capacity becomes available for mere seconds before being claimed.

To catch these capacity windows, you need an automated process that:
1. **Polls OCI Compute APIs continuously** in a loop.
2. **Handles rate limits and API backoff** gracefully.
3. **Pre-provisions all networking, cloud-init scripts, and SSH keys** so the instance immediately boots into a ready state the instant capacity appears.

---

## 🛠️ The Automated Python Provisioner Script

Here is the clean, production-ready Python script using the official `oci` Python SDK:

```python
#!/usr/bin/env python3
"""
Oracle Cloud Infrastructure (OCI) ARM64 Ampere A1 Automated Provisioner
Continuously attempts to create an A1.Flex compute instance until capacity is secured.
"""

import time
import sys
import oci

# ==============================================================================
# Configuration Parameters (Replace with your compartment and subnet OCIDs)
# ==============================================================================
COMPARTMENT_ID = "ocid1.compartment.oc1..example_compartment_ocid"
SUBNET_ID      = "ocid1.subnet.oc1..example_subnet_ocid"
IMAGE_ID       = "ocid1.image.oc1..example_oracle_linux_arm64_image_ocid"
SSH_PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@workstation"

INSTANCE_NAME  = "arm10"
OCPUS          = 2       # 2 OCPUs (out of 4 free allowed)
MEMORY_IN_GBS  = 12      # 12 GB RAM (out of 24 GB free allowed)
BOOT_VOLUME_GB = 50      # Boot volume size in GB

def create_instance_client():
    # Load configuration from ~/.oci/config
    config = oci.config.from_file()
    return oci.core.ComputeClient(config), config

def launch_arm_instance():
    compute_client, config = create_instance_client()
    
    # 1. Discover Availability Domain
    identity_client = oci.identity.IdentityClient(config)
    ads = identity_client.list_availability_domains(COMPARTMENT_ID).data
    target_ad = ads[0].name
    print(f"🎯 Target Availability Domain: {target_ad}")

    # 2. Build Instance Launch Details
    launch_details = oci.core.models.LaunchInstanceDetails(
        compartment_id=COMPARTMENT_ID,
        availability_domain=target_ad,
        display_name=INSTANCE_NAME,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS,
            memory_in_gbs=MEMORY_IN_GBS
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            image_id=IMAGE_ID,
            boot_volume_size_in_gbs=BOOT_VOLUME_GB
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=SUBNET_ID,
            assign_public_ip=False  # Routed internally via our Gateway node
        ),
        metadata={
            "ssh_authorized_keys": SSH_PUBLIC_KEY
        }
    )

    # 3. Continuous Provisioning Loop
    attempt = 1
    delay_seconds = 30  # Polling interval

    print(f"🚀 Starting automated provisioning for {INSTANCE_NAME} ({OCPUS} OCPU / {MEMORY_IN_GBS}GB RAM)...")

    while True:
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Attempt #{attempt}: Requesting VM.Standard.A1.Flex...")
            response = compute_client.launch_instance(launch_details)
            instance_id = response.data.id
            print(f"\n🎉 SUCCESS! Instance provisioned successfully!")
            print(f"📋 Instance OCID: {instance_id}")
            break

        except oci.exceptions.ServiceError as e:
            if e.status == 500 and "Out of host capacity" in e.message:
                print(f"   ⏳ Capacity full. Retrying in {delay_seconds}s...")
            elif e.status == 429:
                print(f"   ⚠️ Rate limited (HTTP 429). Backing off for 60s...")
                time.sleep(30)
            else:
                print(f"   ❌ Unexpected Error [{e.status}]: {e.message}")
            
            time.sleep(delay_seconds)
            attempt += 1

if __name__ == "__main__":
    launch_arm_instance()
```

---

## 💡 4 Essential Tips for Maximum Success

### 1. Don't Request All 4 OCPUs / 24 GB in a Single Chunk
* While Oracle allows up to 4 OCPUs and 24 GB RAM for free, requesting a smaller shape (such as **2 OCPUs and 12 GB RAM**) has a **substantially higher probability of succeeding** because smaller memory blocks are freed up more frequently.
* You can always resize the instance later or run a secondary worker!

### 2. Run the Script on an Existing Free Micro Instance
* Instead of running the script on your local laptop (which goes to sleep when closed), run the provisioning script in a `tmux` or `systemd` background session on an existing **AMD64 E2.1.Micro (`amd10`)** instance within the same Oracle Cloud region.
* This ensures 24/7 uninterrupted execution with **0ms regional network latency** to OCI API endpoints!

### 3. Sizing Your Boot Volume
* Oracle Cloud gives you **200 GB of free total boot volume storage**.
* Allocate 50 GB to each of your two AMD instances and 50–100 GB to your ARM instance to stay comfortably within the 200 GB limit.

### 4. Keep VNIC Private if Using an Ingress Gateway
* If you run a dedicated edge gateway (like our `amd10` running Caddy), set `assign_public_ip=False` on the ARM instance. 
* This saves your 1 free public IPv4 address for your edge gateway and routes internal traffic securely across the Oracle VCN private subnet (`10.0.0.0/16`).

---

## 🏆 The Result: Our `arm10` Powerhouse is Live!

Using this exact method, our script caught a capacity window and successfully spun up **`arm10`**:
* **Architecture**: `aarch64` Ampere Altra
* **Specs**: 2 OCPUs / 12 GB RAM / 50 GB NVMe Storage
* **Role**: K3s Kubernetes Control Plane, PostgreSQL 18.6 with `pgvector`, AnythingLLM Document RAG, and Memos AI Journal.

With a little patience and automation, you can unlock enterprise-grade cloud compute completely for free! 🚀☁️
