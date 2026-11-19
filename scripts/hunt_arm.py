#!/usr/bin/env python3
"""
Oracle Cloud Infrastructure (OCI) Always Free ARM Capacity Hunter
Automatically polls Oracle Cloud API until a 1-Core / 6 GB RAM (Ampere A1) slot opens up.
"""

import os
import subprocess
import time
import json
import sys
import datetime
import random

COMPARTMENT_ID = os.environ.get("OCI_COMPARTMENT_ID", "")
AVAILABILITY_DOMAIN = os.environ.get("OCI_AVAILABILITY_DOMAIN", "")
SHAPE = "VM.Standard.A1.Flex"
IMAGE_ID = os.environ.get("OCI_IMAGE_ID", "")
SUBNET_ID = os.environ.get("OCI_SUBNET_ID", "")
SSH_KEY_FILE = os.path.expanduser(os.environ.get("OCI_SSH_KEY_FILE", ""))
INSTANCE_NAME = os.environ.get("OCI_INSTANCE_NAME", "arm10")

REQUIRED_ENV_VARS = (
    "OCI_COMPARTMENT_ID",
    "OCI_SUBNET_ID",
    "OCI_IMAGE_ID",
    "OCI_AVAILABILITY_DOMAIN",
    "OCI_SSH_KEY_FILE",
)


def _get_config():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return {
        "compartment_id": os.environ["OCI_COMPARTMENT_ID"],
        "availability_domain": os.environ["OCI_AVAILABILITY_DOMAIN"],
        "image_id": os.environ["OCI_IMAGE_ID"],
        "subnet_id": os.environ["OCI_SUBNET_ID"],
        "ssh_key_file": os.path.expanduser(os.environ["OCI_SSH_KEY_FILE"]),
        "instance_name": os.environ.get("OCI_INSTANCE_NAME", INSTANCE_NAME),
    }

# Target configuration: 1 OCPU, 6 GB RAM (Fastest way to catch open capacity in Tokyo!)
OCPUS = 1
MEMORY_GBS = 6

# Polling interval range (5 to 8 minutes for smooth rate limit compliance)
MIN_INTERVAL = 300  # 5 minutes
MAX_INTERVAL = 480  # 8 minutes

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

def try_launch(cfg=None):
    if cfg is None:
        cfg = _get_config()
    shape_config = json.dumps({"ocpus": OCPUS, "memoryInGBs": MEMORY_GBS})
    cmd = [
        "oci", "compute", "instance", "launch",
        "--compartment-id", cfg["compartment_id"],
        "--availability-domain", cfg["availability_domain"],
        "--shape", SHAPE,
        "--shape-config", shape_config,
        "--display-name", cfg["instance_name"],
        "--image-id", cfg["image_id"],
        "--subnet-id", cfg["subnet_id"],
        "--assign-public-ip", "true",
        "--ssh-authorized-keys-file", cfg["ssh_key_file"],
    ]

    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    try:
        cfg = _get_config()
    except RuntimeError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print("="*70, flush=True)
    print(f"🚀 OCI ARM Capacity Hunter started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"📍 Target: {cfg['availability_domain']} | {OCPUS} OCPUs | {MEMORY_GBS} GB RAM", flush=True)
    print(f"⏱️ Polling interval: Randomized 5 to 8 minutes (300s – 480s)", flush=True)
    print("="*70, flush=True)
    
    attempt = 1
    while True:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Attempt #{attempt:04d}: Requesting {OCPUS} OCPUs / {MEMORY_GBS} GB RAM in {cfg['availability_domain']}...", end="", flush=True)
        
        res = try_launch(cfg)
        
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
            sleep_time = random.randint(MIN_INTERVAL, MAX_INTERVAL)
            
            if "TooManyRequests" in err_output or "429" in err_output:
                sleep_time = 600 + random.randint(0, 60)  # 10 to 11 minutes
                mins = sleep_time // 60
                secs = sleep_time % 60
                print(f" -> Rate limited (429). Cooling down for {mins}m {secs:02d}s...", flush=True)
            elif "Out of host capacity" in err_output or "InternalError" in err_output or "500" in err_output:
                mins = sleep_time // 60
                secs = sleep_time % 60
                print(f" -> Out of capacity. (Next check in {mins}m {secs:02d}s)", flush=True)
            elif "RequestException" in err_output or "Timeout" in err_output or "MaxRetryError" in err_output or "Traceback" in err_output:
                mins = sleep_time // 60
                secs = sleep_time % 60
                print(f" -> Network timeout / API busy. (Retrying in {mins}m {secs:02d}s)", flush=True)
            else:
                mins = sleep_time // 60
                secs = sleep_time % 60
                first_line = err_output.strip().split("\n")[0]
                print(f" -> {first_line[:50]}... (Retrying in {mins}m {secs:02d}s)", flush=True)
        
        attempt += 1
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
