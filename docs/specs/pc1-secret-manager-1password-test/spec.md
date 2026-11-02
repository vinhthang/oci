# Specification: End-to-End Verification of `kube_vedge!2597` (`ANO-16455` File-Backed Secret Manager) on `pc-1` Multi-Cluster Federation Topology

- **Feature ID**: `pc1-secret-manager-1password-test`
- **Status**: `Completed`
- **Date**: 2026-11-02
- **Repositories**: `/Users/thanghoang/github/oci`, `axon-networks2/axon-orchestrator/kube_vedge` (`!2597`), `axon-networks2/axon-orchestrator/vedge_api` (`ANO-16455`)
- **Governing ADRs**: `ADR-0047`, `ADR-0048`

---

## 1. Overview & Architectural Scope

Validate GitLab Merge Request [`kube_vedge!2597`](https://gitlab.com/axon-networks2/axon-orchestrator/kube_vedge/-/merge_requests/2597) (`ANO-16455`: 1Password / file-backed encryption keys for `vedge-api-secret-manager-service` across `cloud-qa2`, `cloud-qa-f1`, and `cloud-qa-f2`) both via offline Helm template rendering of the MR branch (`codex/ano-16455-oci-qa-fed-encryption`) and via live multi-cluster execution across `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`) backed by the shared Federation PostgreSQL 18 (`qa-fed-router-pg.corp.intranet:5432`) and Redis (`router-rds-lb-qa-fed.corp.intranet:12000`) datastores on `arm10` (`10.0.0.216`).

---

## 2. Normative Requirements

### `REQ-001`: Offline Helm Template Verification of `kube_vedge!2597` (`cloud-qa2`, `cloud-qa-f1`, `cloud-qa-f2`)
- **Description**: Checkout branch `codex/ano-16455-oci-qa-fed-encryption` in `C:\Users\thang\gitlab\kube_vedge` on `pc-1` and render Helm templates for `vedge-mv/vedge-api` (`oci-cloud-qa2-values.yaml`) and `vedge-mv-unify-singleapp/placeholder` (`oci-cloud-qa-f1-values.yaml`, `oci-cloud-qa-f2-values.yaml`, `oci-cloud-qa-f1-extsec.yaml`, `oci-cloud-qa-f2-extsec.yaml`) to verify that:
  1. `ExternalSecret/ao-encryption-keys` renders with `secretStoreRef.name: onepassword-cluster-store`, `target.name: ao-encryption-keys`, and `remoteRef: { key: ao-encryption-keys, property: secrets.json }`.
  2. `Deployment/vedge-api-secret-manager-service` renders with `-Dvedge.secret-manager.external-secret-manager=file -Dvedge.secret-manager.secret-file-path=/etc/ao/encryption-keys/secrets.json`, mounts volume `ao-encryption-keys` (`Secret/ao-encryption-keys`) read-only at `/etc/ao/encryption-keys`, and contains zero legacy `vedge-api-sm-sa-secret` mounts or `GOOGLE_APPLICATION_CREDENTIALS` env vars.
- **Acceptance Criteria**:
  1. `helm template` exits with code `0` for `cloud-qa2`, `cloud-qa-f1`, and `cloud-qa-f2`.
  2. Rendered manifests match all 5 file changes in `kube_vedge!2597` without YAML or Go-template errors.

### `REQ-002`: Build & Import `vedge-api-secret-manager-service` and `vedge-api-device-encryption-key-service` Images on `pc-1`
- **Description**: Compile and build container images `vedge-api-secret-manager-service:ANO-17479` and `vedge-api-device-encryption-key-service:ANO-17479` from `C:\Users\thang\gitlab\vedge_api` (containing `ANO-16455` commit `9dd4acc8` with `FileSecretManagerServiceImpl` and `FileSecretStore`) on `pc-1`, and import both images into containerd (`k8s.io` namespace) across all 4 BEC K3s nodes (`k3s-bec1-server`, `k3s-bec1-worker`, `k3s-bec2-server`, `k3s-bec2-worker`).
- **Acceptance Criteria**:
  1. `vedge-api-secret-manager-service:ANO-17479` and `vedge-api-device-encryption-key-service:ANO-17479` build with exit code `0`.
  2. `sudo k3s ctr images ls` on `k3s-bec1-server`, `k3s-bec1-worker`, `k3s-bec2-server`, and `k3s-bec2-worker` confirms both images are present.

### `REQ-003`: Codify Declarative `charts/vedge-api-local/` & Deploy `Secret/ao-encryption-keys` + Secret Manager Services via Helm
- **Description**: Create `charts/vedge-api-local/` in `/Users/thanghoang/github/oci` with support for `encryptionKeysSecret` (`Secret/ao-encryption-keys` containing `secrets.json`), per-service `redisHosts`, `volumes`, and `volumeMounts`. Upgrade `vedge-api-bec1` (`pc1-bec1`, namespace `cloud-qa-f1`) and `vedge-api-bec2` (`pc1-bec2`, namespace `cloud-qa-f2`) strictly via `helm upgrade` (`RULE[no-kubectl-mutation]`, `RULE[adr-governance]`) to deploy `Secret/ao-encryption-keys`, `vedge-api-secret-manager-service` (port `17000`), and `vedge-api-device-encryption-key-service` (port `17100`).
- **Acceptance Criteria**:
  1. `helm lint charts/vedge-api-local` passes with 0 errors.
  2. `helm --kube-context pc1-bec1 -n cloud-qa-f1 upgrade vedge-api-bec1 ./charts/vedge-api-local -f ./charts/vedge-api-local/values-bec1.yaml` and `helm --kube-context pc1-bec2 -n cloud-qa-f2 upgrade vedge-api-bec2 ./charts/vedge-api-local -f ./charts/vedge-api-local/values-bec2.yaml` succeed (`STATUS: deployed`).
  3. `vedge-api-secret-manager-service` and `vedge-api-device-encryption-key-service` reach `1/1 Running` (`Ready`) in both `cloud-qa-f1` (`pc1-bec1`) and `cloud-qa-f2` (`pc1-bec2`).

### `REQ-004`: Verify `FileSecretStore` Initialization, Shared Federation DB Schema, & Cross-BEC Key Synchronization
- **Description**: Verify end-to-end runtime behavior of `vedge-api-secret-manager-service` and `vedge-api-device-encryption-key-service` across `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`):
  1. Startup logs in both `cloud-qa-f1` and `cloud-qa-f2` emit `Loaded [1] secrets from file [/etc/ao/encryption-keys/secrets.json].` from `FileSecretStore`.
  2. Liquibase automatically creates `encryption_key_metadata` in shared Federation PostgreSQL `secret_manager_data` on `arm10` (`10.0.0.216:5432`).
  3. Triggering `POST http://vedge-api-secret-manager-service:17000/secret-manager` (`{"name":"ao-encryption-key","version":"1"}`) on `pc1-bec1` (`cloud-qa-f1`) fetches version `1` from `/etc/ao/encryption-keys/secrets.json`, persists the `EncryptionKeyMetadata` row (`name=ao-encryption-key`, `version=1`, `current_version=true`) in `arm10` `secret_manager_data`, and publishes `SecretKeyChangeTask` via shared Federation Redis (`router-rds-lb-qa-fed.corp.intranet:12000`) so that both `pc1-bec1` and `pc1-bec2` return the active key on `GET /secret-manager/all` and `GET /secret-manager/name/ao-encryption-key`.
- **Acceptance Criteria**:
  1. `kubectl logs` on both `pc1-bec1` and `pc1-bec2` `vedge-api-secret-manager-service` pods show `Loaded [1] secrets from file [/etc/ao/encryption-keys/secrets.json].`
  2. `POST /secret-manager` on `pc1-bec1` returns HTTP 200 with `name: "ao-encryption-key"`, `version: "1"`, `currentVersion: true`.
  3. `GET /secret-manager/name/ao-encryption-key` on `pc1-bec2` (`cloud-qa-f2`) returns the exact same key and secret value loaded from `/etc/ao/encryption-keys/secrets.json`, and `SELECT name, version, current_version FROM encryption_key_metadata;` on `arm10` `secret_manager_data` confirms the persisted metadata row.
