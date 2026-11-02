# Architecture Decisions: End-to-End Verification of `kube_vedge!2597` (`ANO-16455`) on `pc-1`

- **Feature ID**: `pc1-secret-manager-1password-test`
- **Status**: `In-Progress`
- **Date**: 2026-11-02
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`

---

## ADR-0048: Declarative `vedge-api-local` Chart & File-Backed Secret Manager (`ANO-16455` / `kube_vedge!2597`) Across `pc1-bec1` and `pc1-bec2`

- **Status**: Accepted
- **Date**: 2026-11-02
- **Addresses**: `REQ-001`, `REQ-002`, `REQ-003`, `REQ-004`

### Context
GitLab MR `kube_vedge!2597` (`ANO-16455`) migrates `vedge-api-secret-manager-service` in `cloud-qa2`, `cloud-qa-f1` (`bec1`), and `cloud-qa-f2` (`bec2`) from GCP Secret Manager to a local JSON file (`/etc/ao/encryption-keys/secrets.json`) mounted from `Secret/ao-encryption-keys` (populated in OCI QA via `ExternalSecret/ao-encryption-keys` from 1Password). In Federation BEC clusters (`cloud-qa-f1` and `cloud-qa-f2`), `vedge-api-secret-manager-service` (`port: 17000`) and `vedge-api-device-encryption-key-service` (`port: 17100`) share the Federation Router PostgreSQL (`qa-fed-router-pg.corp.intranet:5432`) and Redis (`router-rds-lb-qa-fed.corp.intranet:12000`) instances hosted on `arm10` (`10.0.0.216`).

To test `kube_vedge!2597` on the `pc-1` multi-cluster QA-Router topology (`pc1-bec1` and `pc1-bec2`) while strictly adhering to `RULE[no-kubectl-mutation]` and `RULE[adr-governance]` (Helm-only Kubernetes policy, zero generic port `8080`), the `vedge-api-local` chart must be codified in `/Users/thanghoang/github/oci/charts/vedge-api-local/` and extended to support `Secret/ao-encryption-keys`, per-service `redisHosts`, `volumes`, and `volumeMounts`.

### Decision
1. **Verify `kube_vedge!2597` Chart Templates Offline (`REQ-001`)**:
   - Checkout `codex/ano-16455-oci-qa-fed-encryption` in `C:\Users\thang\gitlab\kube_vedge` on `pc-1` and run `helm template` across `vedge-mv/vedge-api` (`oci-cloud-qa2-values.yaml`) and `vedge-mv-unify-singleapp/placeholder` (`oci-cloud-qa-f1-values.yaml`, `oci-cloud-qa-f2-values.yaml`, `oci-cloud-qa-f1-extsec.yaml`, `oci-cloud-qa-f2-extsec.yaml`).
2. **Build & Import `ANO-16455` Service Images on `pc-1` (`REQ-002`)**:
   - Build `vedge-api-secret-manager-service:ANO-17479` and `vedge-api-device-encryption-key-service:ANO-17479` from `C:\Users\thang\gitlab\vedge_api` on `pc-1` and import them into `k3s ctr` across `k3s-bec1-server`, `k3s-bec1-worker`, `k3s-bec2-server`, and `k3s-bec2-worker`.
3. **Codify `charts/vedge-api-local/` & Deploy via `helm upgrade` (`REQ-003`)**:
   - Store `charts/vedge-api-local/` in `/Users/thanghoang/github/oci/charts/vedge-api-local/` with `templates/secret.yaml` (`Secret/ao-encryption-keys`), per-service `redisHosts` override, and per-service `volumes`/`volumeMounts` in `templates/deployment.yaml`.
   - Deploy `vedge-api-secret-manager-service` (`port: 17000`) and `vedge-api-device-encryption-key-service` (`port: 17100`) to `pc1-bec1` (`cloud-qa-f1`) and `pc1-bec2` (`cloud-qa-f2`) via `helm upgrade`.
4. **End-to-End Cross-BEC Functional Verification (`REQ-004`)**:
   - Verify `FileSecretStore` loads `/etc/ao/encryption-keys/secrets.json` at startup, Liquibase initializes `encryption_key_metadata` in `arm10` PostgreSQL (`secret_manager_data`), and registering key `ao-encryption-key` version `1` via `POST /secret-manager` on `pc1-bec1` synchronizes across `arm10` Postgres/Redis to `pc1-bec2`.

### Trade-offs & Risks
- **Native Kubernetes `Secret/ao-encryption-keys` vs. Live 1Password Operator Sync**:
  - `pc1-bec1` and `pc1-bec2` do not have the External Secrets Operator (`external-secrets.io`) or corporate 1Password Connect credentials installed.
  - *Mitigation*: `ExternalSecret/ao-encryption-keys` syntax and schema are verified via `helm template` against `kube_vedge!2597` (`REQ-001`), while `charts/vedge-api-local/templates/secret.yaml` renders the exact resulting `Secret/ao-encryption-keys` (`data["secrets.json"]`) consumed by `vedge-api-secret-manager-service` (`REQ-003`, `REQ-004`).
- **BEC Cluster Memory Headroom**:
  - Adding 2 Spring Boot pods (`vedge-api-secret-manager-service` and `vedge-api-device-encryption-key-service` with `-Xms64m -Xmx384m`) per BEC cluster adds ~500–700 MiB RAM per cluster across 44 GB RAM per BEC cluster (`k3s-bec*-server` 16 GB + `k3s-bec*-worker` 28 GB), well within capacity.

### Rejected Alternatives
1. **Imperative `kubectl create secret` or `kubectl set volume` on `pc1-bec1` and `pc1-bec2`**:
   - *Rejected*: Violates `RULE[no-kubectl-mutation]` and `RULE[adr-governance]` (Mandatory Helm-Only Kubernetes Policy). All Kubernetes state changes must be performed via `helm upgrade`.
2. **Point `vedge-api-secret-manager-service` to BEC-Local PostgreSQL/Redis**:
   - *Rejected*: In `kube_vedge/vedge-mv-unify-singleapp/placeholder/oci-cloud-qa-f1-values.yaml` and `oci-cloud-qa-f2-values.yaml`, `vedge-api-secret-manager-service` explicitly uses `qa-fed-router-pg.corp.intranet` (`secret_manager_data`) and `router-rds-lb-qa-fed.corp.intranet:12000` so encryption keys are shared across all BECs in the federation.
