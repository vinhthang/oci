# WireGuard Overlay & US VPN Configuration Templates

This directory stores **sanitized WireGuard configuration templates** (`*.conf.example`). Live private keys and active tunnel configs (`*.conf`, `*.key`) are strictly gitignored.

## 1. Mesh Overlay (`wg0` — `10.10.0.0/24`)

Hub-and-spoke WireGuard overlay anchored on `amd10` (`152.70.101.162:51820/UDP`), bridging OCI Tokyo VCN (`10.0.0.0/16`), GCP Iowa (`gce10`), and operator workstations.

| Mesh IP | Node / Client | Role | Notes |
| --- | --- | --- | --- |
| `10.10.0.1/24` | `amd10` | WireGuard Hub & OCI Edge Gateway | Public endpoint `152.70.101.162:51820` |
| `10.10.0.2/24` | `oracle10` (retired) | Legacy peer slot (decommissioned) | Reserved / unused |
| `10.10.0.3/24` | `thang-mac` | Operator macOS workstation | Split tunnel (`10.10.0.0/24`) |
| `10.10.0.4/24` | `gce10` | GCP `e2-micro` worker & US edge | Connects to `amd10` hub; serves `web-reader` (`:3000`) |
| `10.10.0.5/24` | `arm10` | OCI ARM Master control-plane peer | Registered on `amd10` `wg0` (`10.0.0.216`) |
| `10.10.0.6/24` | `pc-1` | Operator Windows/WSL workstation | Split tunnel (`10.10.0.0/24`); reassigned from `.5` to avoid `arm10` collision; Windows tunnel service `WireGuardTunnel$wg0`, SSH via `ProxyJump` through `amd10` |

## 2. GCP US Road-Warrior VPN (`wg1` — `10.66.0.0/24`)

In-kernel WireGuard server on `gce10` (`136.111.37.17:51820/UDP`) providing full-tunnel US IP egress (`0.0.0.0/0, ::/0`) via `eth0` NAT masquerade without interfering with `wg0` or K3s Flannel interfaces (`cni0`, `flannel.1`).

| VPN IP | Peer | Role |
| --- | --- | --- |
| `10.66.0.1/24` | `gce10` (`wg1`) | Server interface with `PostUp`/`PostDown` `iptables` NAT masquerading |
| `10.66.0.2/32`+ | Road-warrior clients | Full-tunnel mobile/desktop client peers |

## Usage

1. Copy the relevant `*.conf.example` file to `*.conf` (gitignored).
2. Generate keys locally with `wg genkey | tee privatekey | wg pubkey > publickey` and replace all `<...>` placeholders.
3. Restrict permissions: `chmod 600 wireguard/*.conf`.
