# Architecture Decisions: Vaultwarden HostPath Data Mount & Registration Lockdown Remediation

**Feature ID**: `vaultwarden-data-mount-and-lockdown`  
**Status**: In-Progress  

---

## ADR-0011: Remount `/opt/vaultwarden/data` & Enforce Single-User Lockdown via Helm

- **Context**: `ADR-0011` specified that Vaultwarden persists its SQLite WAL database under `/opt/vaultwarden/data` and enforces `SIGNUPS_ALLOWED=false` and `INVITATIONS_ALLOWED=false`. During cluster manifest squashing, `charts/vinhthang-fleet/templates/vaultwarden.yaml` was written with `hostPath.path: /opt/vaultwarden` and hardcoded `SIGNUPS_ALLOWED: "true"`. This caused Vaultwarden to create an empty database at `/opt/vaultwarden/db.sqlite3` (`0` users, `0` ciphers) while ignoring `/opt/vaultwarden/data/db.sqlite3` (`thanghv@gmail.com`, `324` ciphers).
- **Decision**: Update `charts/vinhthang-fleet/templates/vaultwarden.yaml` and `charts/vinhthang-fleet/values.yaml` to mount `/opt/vaultwarden/data` at `/data` and enforce `signupsAllowed: false` and `invitationsAllowed: false` via Helm values.
- **Trade-offs & Risks**:
  - **Pros**: Zero data migration risk; points the container directly to the existing `/opt/vaultwarden/data` directory where `db.sqlite3`, `db.sqlite3-wal` (`399 KB`), `rsa_key.pem`, and `icon_cache` already reside. Closes public account registration exposure immediately.
  - **Cons / Risks**: File ownership inside `/opt/vaultwarden/data` had UID `501:wheel` from initial restoration; normalizing ownership to `root:root` on `arm10` ensures consistent container write permissions across SQLite WAL checkpoints.
- **Rejected Alternatives**:
  - **Alternative 1 (Copy `/opt/vaultwarden/data/*` up into `/opt/vaultwarden/`)**: Rejected because it diverges from `ADR-0011` (`/opt/vaultwarden/data`) and risks clobbering the active SQLite WAL/SHM journal if copied while mounted.
  - **Alternative 2 (Enable Bitwarden Enterprise OIDC SSO)**: Rejected because Bitwarden SSO still requires the client-side Master Password (or a separate key connector) to decrypt zero-knowledge vault ciphers, and `ADR-0011` explicitly establishes native zero-knowledge authentication for single-user operation.
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`
