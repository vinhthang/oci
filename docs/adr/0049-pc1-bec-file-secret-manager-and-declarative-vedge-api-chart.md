# ADR-0048: Declarative `vedge-api-local` Chart & File-Backed Secret Manager (`ANO-16455` / `kube_vedge!2597`) Across `pc1-bec1` and `pc1-bec2`

* **Status**: 🟢 Accepted
* **Date**: 2026-11-02
* **Deciders**: Sam Hoang, Antigravity AI
* **Category**: Architecture / Security & Multi-Cluster Microservices

---

## 1. Context

GitLab Merge Request [`kube_vedge!2597`](https://gitlab.com/axon-networks2/axon-orchestrator/kube_vedge/-/merge_requests/2597) (`ANO-16455`) replaces GCP Secret Manager (`saGcpK8sBindingEnabled`, `vedge-api-sm-sa-secret`) with a file-backed `FileSecretManagerServiceImpl` / `FileSecretStore` in `vedge-api-secret-manager-service` across `cloud-qa2`, `cloud-qa-f1` (`bec1`), and `cloud-qa-f2` (`bec2`). Under `kube_vedge!2597`:
1. `ExternalSecret/ao-encryption-keys` syncs `ao-encryption-keys` (`property: secrets.json`) from 1Password into `Secret/ao-encryption-keys`.
2. `vedge-api-secret-manager-service` mounts `Secret/ao-encryption-keys` read-only at `/etc/ao/encryption-keys` and runs with JVM arguments:
   ```text
   -Dvedge.secret-manager.external-secret-manager=file -Dvedge.secret-manager.secret-file-path=/etc/ao/encryption-keys/secrets.json
   ```
3. In Federation BEC environments (`cloud-qa-f1` and `cloud-qa-f2`), `vedge-api-secret-manager-service` (port `17000`) and `vedge-api-device-encryption-key-service` (port `17100`) connect to the **shared Federation PostgreSQL and Redis datastores** (`qa-fed-router-pg.corp.intranet:5432/secret_manager_data` and `router-rds-lb-qa-fed.corp.intranet:12000`) on `arm10` (`10.0.0.216`) so that encryption key metadata registered on `bec1` is immediately synchronized with `bec2`.

On the `pc-1` multi-cluster K3s topology (`ADR-0047`), `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`) run the `vedge-api-local` Helm chart (`vedge-api-bec1` and `vedge-api-bec2`), which previously lacked:
- Declarative version control under `charts/vedge-api-local/` in `/Users/thanghoang/github/oci`.
- Support in `templates/deployment.yaml` for per-service `volumes`, `volumeMounts`, and per-service `redisHosts` overrides (`global.databases.redis.hosts` defaults to the BEC-local Redis instance `redb-cloud-qa-f*-headless:12000`, whereas `vedge-api-secret-manager-service` requires shared Federation Redis `router-rds-lb-qa-fed.corp.intranet:12000`).
- Chart-managed `Secret/ao-encryption-keys` (`templates/secret.yaml`) for K3s clusters without External Secrets Operator CRDs.

---

## 2. Decision

1. **Codify `charts/vedge-api-local/` in Repository**:
   - Store the declarative `vedge-api-local` Helm chart in `charts/vedge-api-local/` (`Chart.yaml`, `values.yaml`, `values-bec1.yaml`, `values-bec2.yaml`, `templates/deployment.yaml`, `templates/service.yaml`, `templates/configmap.yaml`, `templates/secret.yaml`) in accordance with the Mandatory Helm-Only Kubernetes Policy (`RULE[adr-governance]`).
2. **Extend `charts/vedge-api-local/templates/deployment.yaml` & `templates/secret.yaml`**:
   - Add per-service `redisHosts` override support (`$svc.redisHosts | default $.Values.global.databases.redis.hosts`) alongside existing `postgresHost` override support.
   - Add per-service `volumeMounts` and `volumes` rendering in `templates/deployment.yaml`.
   - Add `templates/secret.yaml` to declaratively render `Secret/ao-encryption-keys` (`secrets.json`) when `.Values.encryptionKeysSecret.enabled` is `true`.
3. **Onboard `vedge-api-secret-manager-service` (Port `17000`) & `vedge-api-device-encryption-key-service` (Port `17100`) on `pc1-bec1` and `pc1-bec2`**:
   - Configure `vedge-api-secret-manager-service` on dedicated port `17000` (avoiding generic port `8080`) with `postgresHost: qa-fed-router-pg.corp.intranet`, `dbName: secret_manager_data`, `redisHosts: router-rds-lb-qa-fed.corp.intranet:12000`, `extraJvmArgs: "-Dvedge.secret-manager.external-secret-manager=file -Dvedge.secret-manager.secret-file-path=/etc/ao/encryption-keys/secrets.json"`, and read-only volume mount `/etc/ao/encryption-keys` from `Secret/ao-encryption-keys`.
   - Configure `vedge-api-device-encryption-key-service` on dedicated port `17100` with `postgresHost: qa-fed-router-pg.corp.intranet`, `dbName: deviceencryptionkey_data`, and `redisHosts: router-rds-lb-qa-fed.corp.intranet:12000`.

---

## 3. Consequences

* **Positive**:
  * Enables end-to-end functional verification of `kube_vedge!2597` (`ANO-16455`) across both `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`) against the shared Federation PostgreSQL 18 and Redis datastores on `arm10` (`10.0.0.216`).
  * Brings `vedge-api-local` under declarative Helm version control (`charts/vedge-api-local/`) with zero imperative `kubectl` mutations.
* **Negative / Trade-offs**:
  * Because `pc1-bec1` and `pc1-bec2` do not run the External Secrets Operator (`external-secrets.io/v1beta1`) or connect to corporate 1Password vaults, `Secret/ao-encryption-keys` is rendered directly by `charts/vedge-api-local/templates/secret.yaml` while `ExternalSecret/ao-encryption-keys` in `kube_vedge!2597` is verified via `helm template` rendering.
