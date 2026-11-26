# 62. GCP STANDARD Network Tier Migration, Billing Cleanup & Least-Privilege Compute IAM

* **Status**: Accepted
* **Date**: 2026-11-26

## Context

On 2026-11-26, billing was temporarily disabled on GCP project `vietcalendar` (`0146A6-977951-5F413A`), causing GCP instance `gce-free-vm` (`gce10`, `us-central1-a`, `e2-micro`, `30 GB pd-standard`) to stop (`TERMINATED`). That outage severed the WireGuard `wg0` tunnel to `amd10`, dropped `gce10` from the K3s cluster (`NotReady`), broke `https://reader.vinhthang.dev/` (`HTTP 502` from `amd10` trying to reach `10.10.0.4:3000`), and took down the `wg1` US VPN outpost.

A pre-flight billing, networking, and IAM audit of project `vietcalendar` revealed four structural risks:

1. **`PREMIUM` Network Tier on Ephemeral External IP**: `gce-free-vm` used an unreserved ephemeral IPv4 (`136.111.37.17`) on the `PREMIUM` Network Tier, which carries only `1 GiB/month` of free internet egress and excludes APAC destinations—while `wg0` traffic to `amd10` (Tokyo) had already transferred `10.54 GiB` in one session. By contrast, GCP's Always Free tier grants `200 GiB/month` free outbound transfer only on `STANDARD` Network Tier (`us-central1`), and 1 reserved static external IPv4 attached to a running `e2-micro` VM incurs no monthly charge.
2. **Missing Compute Deletion Protection**: Live `gce-free-vm` had `deletionProtection: false` despite `infra/gcp/main.tf` declaring `deletion_protection = true`.
3. **Unused Billing-Linked Project & APIs**: Billing account `0146A6-977951-5F413A` was also linked to an unused sandbox project (`project-9caa3b6d-08cd-4baf-b43`), and unused paid-capable APIs such as `backupdr.googleapis.com` were enabled in `vietcalendar`.
4. **Over-Privileged Default Compute Service Account**: `1066159853629-compute@developer.gserviceaccount.com` held project-wide `roles/editor`.

## Decision

We execute and codify the following GCP hardening and IP migration changes:

1. **Migrate `gce-free-vm` to `STANDARD` Network Tier with Reserved Static IP `35.209.149.46`**:
   - Reserve `gce10-static-ip` (`35.209.149.46`) in `us-central1` with `network_tier = "STANDARD"`.
   - Replace the `PREMIUM` `external-nat` access config on `gce-free-vm` `nic0` with `external-nat` on `STANDARD` Network Tier bound to `35.209.149.46`.
   - Enforce `network_tier = "STANDARD"` on both `google_compute_address.gce10_static_ip` and `google_compute_instance.gce10` (`access_config`) in `infra/gcp/main.tf`, align resource `name = "gce-free-vm"` and `tags = ["http-server", "https-server"]`, and update `35.209.149.46` across `infra/gcp/variables.tf`, `infra/gcp/terraform.tfvars.example`, `scripts/gitops-sync.sh`, `wireguard/gce10-wg1.conf.example`, `wireguard/README.md`, `README.md`, and `docs/README.md`.
2. **Enforce VM & K3s Alignment**:
   - Enable `--deletion-protection` (`deletionProtection: true`) on live `gce-free-vm` to match Terraform.
   - Update `--node-external-ip` in `/etc/systemd/system/k3s-agent.service` on `gce-free-vm` from `136.111.37.17` to `35.209.149.46` and restart `k3s-agent`.
3. **Harden Billing, APIs & Service Account IAM**:
   - Unlink unused `project-9caa3b6d-08cd-4baf-b43` from billing account `0146A6-977951-5F413A`.
   - Disable `backupdr.googleapis.com` on `vietcalendar` (note: `sql-component.googleapis.com`, `dataplex.googleapis.com`, and `dataform.googleapis.com` remain gated by the `cloudapis.googleapis.com` dependency graph and were left untouched rather than force-disabling core umbrella APIs).
   - Replace `roles/editor` on `1066159853629-compute@developer.gserviceaccount.com` with least-privilege `roles/logging.logWriter` and `roles/monitoring.metricWriter`.
4. **Prevent Regression in Offline CI**:
   - Extend `tests/test_terraform_and_scripts.py` to assert `network_tier = "STANDARD"` on both `google_compute_address` and `google_compute_instance` `access_config`, alongside `deletion_protection = true` and `prevent_destroy = true`.

## Consequences

- **Positive**: `gce-free-vm` (`gce10`) qualifies for the Always Free `200 GiB/month` `STANDARD` Tier egress quota across regions, eliminating surprise APAC/cross-cloud `wg0` egress charges, with `35.209.149.46` statically pinned across reboots and protected against accidental deletion or `roles/editor` credential blast radius.
- **Follow-Up (User-Managed Perimeter)**: Cloudflare DNS records pointing to the US edge IP, local WireGuard client `Endpoint = 35.209.149.46:51820`, local `~/.ssh/config`, and a GCP Billing Budget alert (e.g., `25,000 VND`) in the Cloud Billing Console must be updated outside Git by the repository owner.
