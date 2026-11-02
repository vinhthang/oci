# Execution Tasks: End-to-End Verification of `kube_vedge!2597` (`ANO-16455`) on `pc-1`

- **Feature ID**: `pc1-secret-manager-1password-test`
- **Status**: `Completed`
- **Date**: 2026-11-02
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`

---

## Task Checklist

- [x] **Task 1: Offline Helm Template Validation of `kube_vedge!2597`** (`REQ-001`)
  - [x] Checkout `origin/codex/ano-16455-oci-qa-fed-encryption` in `C:\Users\thang\gitlab\kube_vedge` on `pc-1` and run `helm template` for `cloud-qa2`, `cloud-qa-f1`, and `cloud-qa-f2` (`REQ-001`).
  - [x] Verify rendered `ExternalSecret/ao-encryption-keys` and `Deployment/vedge-api-secret-manager-service` args, volumeMounts, and volumes (`REQ-001`).

- [x] **Task 2: Build & Import `vedge-api-secret-manager-service` and `vedge-api-device-encryption-key-service` Images on `pc-1`** (`REQ-002`)
  - [x] Build `vedge-api-secret-manager-service:ANO-17479` and `vedge-api-device-encryption-key-service:ANO-17479` from `C:\Users\thang\gitlab\vedge_api` on `pc-1` (`REQ-002`).
  - [x] Import both images into K3s containerd across `k3s-bec1-server`, `k3s-bec1-worker`, `k3s-bec2-server`, and `k3s-bec2-worker` (`REQ-002`).

- [x] **Task 3: Codify `charts/vedge-api-local/` & Deploy to `pc1-bec1` and `pc1-bec2` via `helm upgrade`** (`REQ-003`)
  - [x] Create `/Users/thanghoang/github/oci/charts/vedge-api-local/` (`Chart.yaml`, `values.yaml`, `values-bec1.yaml`, `values-bec2.yaml`, `templates/deployment.yaml`, `templates/service.yaml`, `templates/configmap.yaml`, `templates/secret.yaml`) and run `helm lint` (`REQ-003`).
  - [x] Upgrade `vedge-api-bec1` (`pc1-bec1`, `cloud-qa-f1`) and `vedge-api-bec2` (`pc1-bec2`, `cloud-qa-f2`) via `helm upgrade` and verify all pods reach `1/1 Running` (`REQ-003`).

- [x] **Task 4: Verify `FileSecretStore` Startup, Shared Federation DB Schema, & Cross-BEC Key Synchronization** (`REQ-004`)
  - [x] Verify `Loaded [1] secrets from file [/etc/ao/encryption-keys/secrets.json].` in pod logs on `pc1-bec1` and `pc1-bec2` and verify Liquibase table creation in `arm10` PostgreSQL `secret_manager_data` (`REQ-004`).
  - [x] Execute `POST /secret-manager` (`{"name":"ao-encryption-key","version":"1"}`) on `pc1-bec1` (`cloud-qa-f1`) and verify cross-BEC synchronization via `GET /secret-manager/name/ao-encryption-key` and `GET /secret-manager/all` on `pc1-bec2` (`cloud-qa-f2`) (`REQ-004`).
  - [x] Record all verbatim verification evidence in `docs/specs/pc1-secret-manager-1password-test/verification.md` (`REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`).
