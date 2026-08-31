# ADR-0011: Deployment of Vaultwarden Self-Hosted Password Manager

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-26
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Managing sensitive credentials, API keys, 2FA tokens, and passkeys across desktop, mobile, and cloud environments requires an end-to-end encrypted, zero-knowledge password management solution. While commercial cloud offerings exist, hosting a private vault ensures 100% data sovereignty and eliminates recurring subscription costs. 

However, running the official Bitwarden stack requires heavy Java/.NET and MSSQL runtimes (> 2–3 GB RAM), which would violate our cluster's memory boundary invariants.

---

## 2. Decision
We chose to deploy **Vaultwarden** (Rust-based Bitwarden-compatible server) onto the **Vinh Thang Cloud & AI Fleet (`vinhthang.dev`)**:

1. **Ultra-Low Footprint (< 30 MB RAM)**:
   * Vaultwarden is written in pure Rust and consumes only ~20–30 MB of RAM under load.
   * Scheduled onto the `amd11` worker node (`nodeSelector: kubernetes.io/arch: amd64`) on NodePort `30010`.
2. **Persistence & Concurrency**:
   * Uses SQLite with Write-Ahead Logging (`ENABLE_DB_WAL=true`) mounted via HostPath to `/opt/vaultwarden/data`.
3. **Single-User Lockdown & Security Model**:
   * `SIGNUPS_ALLOWED=false` and `INVITATIONS_ALLOWED=false` are enforced to prevent public account creation.
   * Client authentication utilizes native Bitwarden zero-knowledge cryptography (Argon2id master key derivation + client-side AES-256 encryption).
4. **Client & Browser Integration**:
   * Fully compatible with official Bitwarden browser extensions (Chrome, Firefox, Safari), mobile apps (iOS, Android), and CLI tools via custom Server URL `https://vault.vinhthang.dev`.
   * Real-time sync via integrated WebSockets on port `80`.
5. **Edge Ingress**:
   * Routed via Caddy on `amd10` (`vault.vinhthang.dev` ➔ `10.0.0.125:30010` / `NodePort: 30010`) with automated TLS termination and HTTP/3 support.

---

## 3. Consequences

### Positive:
* **Zero Cloud Lock-in**: Full zero-knowledge password, passkey, and 2FA synchronization across all user devices.
* **Minimal Resource Consumption**: Rust runtime uses less than 30 MB RAM, running smoothly on the 1 GB AMD worker node without starving other services.
* **Full Ecosystem Compatibility**: Directly integrates with official Bitwarden apps and browser extensions.

### Negative / Trade-offs:
* Requires manual database volume backups via `/opt/vaultwarden/data` to prevent data loss upon host failure.
