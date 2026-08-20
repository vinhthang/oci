#!/usr/bin/env python3
"""
Oracle Cloud Infrastructure (OCI) Always Free ARM Capacity Hunter
Automatically polls Oracle Cloud API until a 4-Core / 24 GB RAM (Ampere A1) slot opens up.
"""

import subprocess
import time
import json
import sys
import datetime
import random

COMPARTMENT_ID = "ocid1.tenancy.oc1..aaaaaaaagquicpnspzg47upmylb7zsjibo5oixmtddcxalh6hagvuvaj26jq"
AVAILABILITY_DOMAIN = "tTNg:AP-TOKYO-1-AD-1"
SHAPE = "VM.Standard.A1.Flex"
IMAGE_ID = "ocid1.image.oc1.ap-tokyo-1.aaaaaaaa3s2rfaecsenoi3dtku4mkgxjgxqfugtpbpcmdnyhwur7rembctva"
SUBNET_ID = "ocid1.subnet.oc1.ap-tokyo-1.aaaaaaaa5t4jmnwgxe4ffr523py245mdfuzz6g5nhwhn6tog6cuyqakrqtfq"
SSH_KEY_FILE = "/Users/thanghoang/.ssh/id_ed25519.pub"
INSTANCE_NAME = "instance-oracle-linux-10-arm"

# Default configuration: 4 OCPUs, 24 GB RAM
OCPUS = 4
MEMORY_GBS = 24

# Base interval between attempts (seconds)
BASE_INTERVAL = 60

def notify_success(instance_id):
    msg = f"🎉 ARM Instance Successfully Created! ID: {instance_id}"
    print("\n" + "="*70, flush=True)
    print(msg, flush=True)
    print("="*70 + "\n", flush=True)
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "Instance {instance_id} is ready!" with title "OCI ARM Hunter: SUCCESS!" sound name "Glass"'
        ], check=False)
    except Exception:
        pass

def try_launch():
    shape_config = json.dumps({"ocpus": OCPUS, "memoryInGBs": MEMORY_GBS})
    cmd = [
        "oci", "compute", "instance", "launch",
        "--compartment-id", COMPARTMENT_ID,
        "--availability-domain", AVAILABILITY_DOMAIN,
        "--shape", SHAPE,
        "--shape-config", shape_config,
        "--display-name", INSTANCE_NAME,
        "--image-id", IMAGE_ID,
        "--subnet-id", SUBNET_ID,
        "--assign-public-ip", "true",
        "--ssh-authorized-keys-file", SSH_KEY_FILE
    ]
    
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    print("="*70, flush=True)
    print(f"🚀 OCI ARM Capacity Hunter started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"📍 Target: Tokyo ({AVAILABILITY_DOMAIN}) | {OCPUS} OCPUs | {MEMORY_GBS} GB RAM", flush=True)
    print(f"⏱️ Polling interval: ~{BASE_INTERVAL}s", flush=True)
    print("="*70, flush=True)
    
    attempt = 1
    while True:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Attempt #{attempt:04d}: Requesting 4 OCPUs / 24 GB RAM in Tokyo...", end="", flush=True)
        
        res = try_launch()
        
        if res.returncode == 0:
            print(" SUCCESS! 🎉", flush=True)
            try:
                data = json.loads(res.stdout)
                instance_id = data.get("data", {}).get("id", "Unknown")
            except Exception:
                instance_id = "Success"
            
            with open("arm_instance.json", "w") as f:
                f.write(res.stdout)
                
            notify_success(instance_id)
            break
        else:
            err_output = res.stderr or res.stdout
            if "Out of host capacity" in err_output or "InternalError" in err_output:
                print(" -> Out of capacity. Retrying...", flush=True)
            elif "TooManyRequests" in err_output:
                print(" -> Rate limited by Oracle API. Backing off 60s...", flush=True)
                time.sleep(60)
            else:
                print(f" -> Error: {err_output[:90]}...", flush=True)
        
        attempt += 1
        sleep_time = BASE_INTERVAL + random.randint(-5, 5)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
