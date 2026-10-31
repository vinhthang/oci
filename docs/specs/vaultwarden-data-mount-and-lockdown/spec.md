# Functional Specification: Vaultwarden HostPath Data Mount & Registration Lockdown Remediation

**Feature ID**: `vaultwarden-data-mount-and-lockdown`  
**Status**: Completed  
**Target Host**: `arm10` (`10.0.0.216`)  
**Scope**: Helm Chart (`charts/vinhthang-fleet/templates/vaultwarden.yaml`, `values.yaml`) / Kubernetes `apps` Namespace  

---

## 1. Problem Statement & Context

Vaultwarden (`https://vault.vinhthang.dev`) is currently rejecting login attempts for `thanghv@gmail.com` (`Username or password is incorrect`) because `charts/vinhthang-fleet/templates/vaultwarden.yaml` mounts `hostPath: /opt/vaultwarden` instead of `/opt/vaultwarden/data` into container `/data`. As a result, Vaultwarden initialized a blank SQLite database at `/opt/vaultwarden/db.sqlite3` (`0` users, `0` ciphers), leaving the production SQLite database at `/opt/vaultwarden/data/db.sqlite3` (`thanghv@gmail.com`, `324` ciphers) unmounted. Additionally, `SIGNUPS_ALLOWED` and `INVITATIONS_ALLOWED` are currently set to `true` in `vaultwarden.yaml` and `values.yaml`, contradicting the single-user security lockdown defined in `ADR-0011`.

---

## 2. Normative Requirements

### `REQ-001`: Mount Production Vaultwarden Data Directory (`/opt/vaultwarden/data`)
- `charts/vinhthang-fleet/templates/vaultwarden.yaml` MUST mount hostPath `/opt/vaultwarden/data` (configurable via `.Values.vaultwarden.storagePath` defaulting to `/opt/vaultwarden/data`) into `/data` inside the `vaultwarden` container.
- The active Vaultwarden pod MUST serve the existing SQLite database containing `thanghv@gmail.com` and all `324` ciphers.

### `REQ-002`: Enforce Single-User Registration Lockdown (`ADR-0011`)
- `charts/vinhthang-fleet/values.yaml` MUST set `vaultwarden.signupsAllowed: false` and `vaultwarden.invitationsAllowed: false`.
- `charts/vinhthang-fleet/templates/vaultwarden.yaml` MUST template `SIGNUPS_ALLOWED`, `INVITATIONS_ALLOWED`, and `WEBSOCKET_ENABLED` from `.Values.vaultwarden` using `quote`.
- `GET https://vault.vinhthang.dev/api/config` MUST return `"disableUserRegistration": true`.

### `REQ-003`: Declarative Helm Upgrade & Prelogin Verification
- Changes MUST be deployed declaratively via `helm upgrade fleet ./charts/vinhthang-fleet` (and committed/pushed to Git).
- `POST https://vault.vinhthang.dev/identity/accounts/prelogin` for `thanghv@gmail.com` and pod readiness in namespace `apps` MUST succeed without errors.
