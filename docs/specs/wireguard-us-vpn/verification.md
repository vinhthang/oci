# Verification Criteria & Evidence: WireGuard US VPN Server on GCP Host (`gce10`)

**Feature ID**: `wireguard-us-vpn`  
**Status**: Verified  

---

## Acceptance Criteria & Falsifiable Gates

| Requirement ID | Verification Gate | Expected Outcome | Status | Verbatim Evidence |
| :--- | :--- | :--- | :---: | :--- |
| `REQ-001` | `sudo wg show wg1` on `gce10` | Interface `wg1` active, listening on UDP port `51820`, peer configured for `10.66.0.2/32`. | Passed | `interface: wg1\n  public key: 9Er02GuoFoUPuVe1Hvyn748BXcutX1Y4bcbVRz8DWg8=\n  listening port: 51820\npeer: 7oERdbxmxC4wVGVCX0QnYsx/9OX17yVG8YgKeBFwd2Q=\n  allowed ips: 10.66.0.2/32` |
| `REQ-002` | `systemctl is-enabled wg-quick@wg1` | Returns `enabled` and `active`. | Passed | `enabled\nactive` |
| `REQ-003` | `sysctl net.ipv4.ip_forward` & `iptables -t nat -S` | Forwarding enabled (`= 1`), `MASQUERADE` present for `10.66.0.0/24` on `eth0`. | Passed | `net.ipv4.ip_forward = 1\n-A POSTROUTING -s 10.66.0.0/24 -o eth0 -j MASQUERADE` |
| `REQ-004` | `gcloud compute firewall-rules describe allow-wireguard-vpn` | Firewall rule exists with `ALLOW udp:51820` and target tag `http-server`. | Passed | `allowed:\n- IPProtocol: udp\n  ports:\n  - '51820'\ndirection: INGRESS\nname: allow-wireguard-vpn\nsourceRanges:\n- 0.0.0.0/0\ntargetTags:\n- http-server` |
| `REQ-005` | Client `.conf` generation & QR code check | File `wg1-client.conf` exists with endpoint `136.111.37.17:51820`, valid keys, and readable QR. | Passed | Config file `wg1-client.conf` and terminal QR artifact `wg1-client-qr.txt` created successfully. |
| `REQ-006` | Git inspection of ADR registry | `docs/adr/0041-wireguard-us-vpn-server-on-gce10.md` registered in `docs/README.md`. | Passed | `\| [**ADR-0041**](adr/0041-wireguard-us-vpn-server-on-gce10.md) \| **In-Kernel WireGuard US VPN Server on GCP Host (\`gce10\`)** \| 🟢 Accepted \| Networking / VPN \|` |
