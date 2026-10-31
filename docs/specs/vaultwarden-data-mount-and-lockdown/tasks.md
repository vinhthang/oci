# Implementation Tasks: Vaultwarden HostPath Data Mount & Registration Lockdown Remediation

**Feature ID**: `vaultwarden-data-mount-and-lockdown`  
**Status**: Completed  

---

## Task Checklist

- [x] **Task 1: Update `charts/vinhthang-fleet/values.yaml` and `templates/vaultwarden.yaml`**
  - Set `signupsAllowed: false`, `invitationsAllowed: false`, and `storagePath: /opt/vaultwarden/data` in `charts/vinhthang-fleet/values.yaml`.
  - Wire `.Values.vaultwarden.signupsAllowed`, `.Values.vaultwarden.invitationsAllowed`, `.Values.vaultwarden.websocketEnabled`, and `.Values.vaultwarden.storagePath` in `charts/vinhthang-fleet/templates/vaultwarden.yaml`.
  - Traceability: `REQ-001`, `REQ-002`

- [x] **Task 2: Deploy via Helm & Verify Live Vaultwarden Database and Endpoints**
  - Normalize file ownership on `/opt/vaultwarden/data` on `arm10` and deploy via `helm upgrade fleet ./charts/vinhthang-fleet` (and GitOps commit/push).
  - Verify `vaultwarden` pod is `1/1 Running`, mounts `/opt/vaultwarden/data`, serves `thanghv@gmail.com` (`324` ciphers), and reports `"disableUserRegistration": true` on `/api/config`.
  - Traceability: `REQ-001`, `REQ-002`, `REQ-003`
