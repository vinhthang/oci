# ADR-0013: Private Subnet Isolation & NAT Gateway Architecture

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-26
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Previously, all cluster nodes (`amd10`, `amd11`, and `arm10`) were provisioned on a single public subnet with individual public IPv4 addresses assigned to each VNIC.

While this allowed direct outbound internet access and direct SSH connectivity, it unnecessarily exposed the control plane (`arm10`) and worker storage node (`amd11`) to public internet port scanners and automated brute-force attempts on ports 22 (SSH) and 6443 (Kubernetes API).

---

## 2. Decision
We transitioned to a **Zero-Trust Multi-Subnet VCN Architecture** with strict network perimeter isolation:

1. **Private Subnet Isolation (`10.0.1.0/24`)**:
   * Created `oci_core_subnet.private_subnet` with `prohibit_public_ip_on_vnic = true` and `prohibit_internet_ingress = true`.
   * Migrated **`arm10`** (K3s Control Plane & PostgreSQL Hub) and **`amd11`** (Worker & Navidrome Node) into the private subnet, **removing their public IPv4 addresses**.
2. **OCI NAT Gateway & Service Gateway for Egress**:
   * Provisioned `oci_core_nat_gateway.main_nat_gateway` to allow private nodes to initiate outbound connections (`dnf`, container image pulls from Docker Hub / GHCR, K3s installation, GitOps sync) without accepting unsolicited inbound internet connections.
   * Provisioned `oci_core_service_gateway.main_service_gateway` for direct private access to Oracle Services Network.
3. **Single Public Ingress & Bastion Entrypoint (`amd10`)**:
   * **`amd10` (`152.70.101.162`)** remains the sole node in the public subnet (`10.0.0.0/24`), serving as both the **Caddy Edge Gateway** (handling TLS, HTTP/3, and Google SSO) and the **SSH Bastion Host** (enabling transparent SSH administration via `ProxyJump`).
4. **Transparent Admin Access**:
   * Configured SSH `ProxyJump` (`ssh -o ProxyJump=opc@152.70.101.162 opc@10.0.1.x`) so developers and automation scripts interact with `arm10` and `amd11` seamlessly.

---

## 3. Consequences

### Positive:
* **Zero Public Attack Surface**: Ports 22, 6443, and internal node ports on `arm10` and `amd11` are 100% invisible to the public internet.
* **Full Outbound Capability**: The Always-Free OCI NAT Gateway provides uninterrupted package downloads, container pulls, and Git repository syncs.
* **Streamlined Ingress**: All user traffic is strictly funneled through Caddy on `amd10` with Google OAuth2 forward-auth and security headers.
* **Cost Efficiency**: Utilizes OCI Always Free NAT Gateway and Service Gateway at **\$0 cost**.

### Negative / Trade-offs:
* Direct SSH connections to `arm10` require hopping through `amd10` via SSH `ProxyJump` or an active VPN/tunnel.
