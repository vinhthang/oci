# Specifications Index: Vinh Thang Cloud & AI Fleet

This index tracks formal engineering specifications authored under `docs/specs/<feature-id>/` following the 5-Document Architecture per `RULE[spec-standard]`.

---

| Feature ID | Title | Status | Req Range | Key Decisions | Specification Package |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `wireguard-us-vpn` | **WireGuard US VPN Server on GCP Host (`gce10`)** | Completed | `REQ-001–006` | ADR-0041 | [`wireguard-us-vpn`](wireguard-us-vpn/spec.md) |
| `arm10-boot-volume-expansion` | **Online `arm10` Boot Volume Expansion to 100 GB (OCI Always Free Tier)** | Completed | `REQ-001–005` | ADR-0045 | [`arm10-boot-volume-expansion`](arm10-boot-volume-expansion/spec.md) |
| `arm10-payg-scale-and-quota-lock` | **Scale `arm10` to 4 OCPUs / 24 GB RAM & Lock Always-Free PAYG Quotas** | Completed | `REQ-001–004` | ADR-0046 | [`arm10-payg-scale-and-quota-lock`](arm10-payg-scale-and-quota-lock/spec.md) |
| `vaultwarden-data-mount-and-lockdown` | **Vaultwarden HostPath Data Mount & Registration Lockdown Remediation** | Completed | `REQ-001–003` | ADR-0011 | [`vaultwarden-data-mount-and-lockdown`](vaultwarden-data-mount-and-lockdown/spec.md) |
| `pc1-qa-router-multicluster-refactor` | **`pc-1` Multi-Cluster K3s Refactor & Hybrid Federation Datastores** | Completed | `REQ-001–006` | ADR-0047 | [`pc1-qa-router-multicluster-refactor`](pc1-qa-router-multicluster-refactor/spec.md) |
