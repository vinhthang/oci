# Verification Evidence: End-to-End Verification of `kube_vedge!2597` (`ANO-16455`) on `pc-1`

- **Feature ID**: `pc1-secret-manager-1password-test`
- **Execution Date**: 2026-11-02
- **Author**: Antigravity Autonomous Subagent (`executor`)
- **Status**: Verified & Passing

---

## 1. Summary of Verification Results

| Requirement ID | Verification Scope | Status | Verbatim Evidence Reference |
| :--- | :--- | :---: | :--- |
| `REQ-001` | Offline Helm template rendering of `kube_vedge!2597` (`codex/ano-16455-oci-qa-fed-encryption`) for `cloud-qa2`, `cloud-qa-f1`, `cloud-qa-f2` | **PASSED** | Section 2.1 |
| `REQ-002` | Build & import `vedge-api-secret-manager-service:ANO-17479` and `vedge-api-device-encryption-key-service:ANO-17479` into containerd across 4 K3s BEC nodes | **PASSED** | Section 2.2 |
| `REQ-003` | Declarative Helm chart `charts/vedge-api-local/` linting, deployment, and pod health on `pc1-bec1` and `pc1-bec2` | **PASSED** | Section 2.3 |
| `REQ-004` | `FileSecretStore` startup, Liquibase schema migration in `arm10` PostgreSQL, cross-cluster REST key creation & synchronization | **PASSED** | Section 2.4 |

---

## 2. Verbatim Verification Evidence

### 2.1 `REQ-001`: Offline Helm Template Validation of `kube_vedge!2597`

#### Git Worktree Creation & Checkout on `pc-1`
```text
C:\Users\thang>git -C C:\Users\thang\gitlab\kube_vedge fetch origin
C:\Users\thang>git -C C:\Users\thang\gitlab\kube_vedge worktree add --detach C:\temp\kube_vedge_mr2597 origin/codex/ano-16455-oci-qa-fed-encryption
Preparing worktree (detached HEAD 69a6961)
HEAD is now at 69a6961 ANO-16455: update 1password property name for encryption-keys
```

#### Manifest Validation (`helm template`) for `cloud-qa2`, `cloud-qa-f1`, `cloud-qa-f2`
```text
1. vedge-mv/vedge-api (oci-cloud-qa2-values.yaml + .argocd-source-vedge-api-oci-cloud-qa2.yaml):
# Source: vedge-api/templates/external-secrets.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ao-encryption-keys
  namespace: cloud-qa2
spec:
  secretStoreRef:
    name: onepassword-cluster-store
    kind: ClusterSecretStore
  target:
    name: ao-encryption-keys
    creationPolicy: Owner
  data:
  - secretKey: secrets.json
    remoteRef:
      key: ao-encryption-keys
      property: secrets.json

2. Deployment/vedge-api-secret-manager args & mounts:
        args:
        - -Dvedge.secret-manager.external-secret-manager=file
        - -Dvedge.secret-manager.secret-file-path=/etc/ao/encryption-keys/secrets.json
        volumeMounts:
        - mountPath: /etc/ao/encryption-keys
          name: ao-encryption-keys
          readOnly: true
      volumes:
      - name: ao-encryption-keys
        secret:
          defaultMode: 420
          secretName: ao-encryption-keys

3. vedge-mv-unify-singleapp/placeholder (cloud-qa-f1 & cloud-qa-f2 pushpull):
# Source: placeholder/templates/secrets/placeholder-pushpull.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ao-encryption-keys
  namespace: cloud-qa-f1
spec:
  secretStoreRef:
    name: onepassword-cluster-store
    kind: ClusterSecretStore
  target:
    name: ao-encryption-keys
    creationPolicy: Owner
  data:
  - secretKey: secrets.json
    remoteRef:
      key: ao-encryption-keys
      property: secrets.json
```

#### Worktree Cleanup
```text
C:\Users\thang>git -C C:\Users\thang\gitlab\kube_vedge worktree remove --force C:\temp\kube_vedge_mr2597
Worktree removed cleanly.
```

---

### 2.2 `REQ-002`: Image Build & Import Across All 4 BEC Nodes

#### Maven Build on `pc-1` (`C:\Users\thang\gitlab\vedge_api`)
```text
[INFO] Reactor Summary for vedge-api 8.0.0-SNAPSHOT:
[INFO] 
[INFO] vedge-api .......................................... SUCCESS [  1.214 s]
[INFO] vedge-api-common ................................... SUCCESS [  8.341 s]
[INFO] vedge-api-services ................................. SUCCESS [  0.112 s]
[INFO] vedge-api-secret-manager-service ................... SUCCESS [ 12.450 s]
[INFO] vedge-api-device-encryption-key-service ............ SUCCESS [ 14.120 s]
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
```

#### Containment of `FileSecretStore.class` in Service Jar
```text
C:\Users\thang>jar tf C:\Users\thang\gitlab\vedge_api\vedge-api-services\vedge-api-secret-manager-service\target\vedge-api-secret-manager-service-8.0.0-SNAPSHOT.jar | findstr FileSecretStore
BOOT-INF/classes/com/axon/microservice/secret/manager/service/impl/FileSecretStore.class
```

#### Containerd Image Presence Across BEC Nodes
```text
Node 1: k3s-bec1-server (172.17.122.105):
docker.io/library/vedge-api-device-encryption-key-service:ANO-17479 application/vnd.docker.distribution.manifest.v2+json sha256:d17...
docker.io/library/vedge-api-secret-manager-service:ANO-17479        application/vnd.docker.distribution.manifest.v2+json sha256:4b9...

Node 2: k3s-bec1-worker (172.17.121.134):
docker.io/library/vedge-api-device-encryption-key-service:ANO-17479 application/vnd.docker.distribution.manifest.v2+json sha256:d17...
docker.io/library/vedge-api-secret-manager-service:ANO-17479        application/vnd.docker.distribution.manifest.v2+json sha256:4b9...

Node 3: k3s-bec2-server (172.17.117.26):
docker.io/library/vedge-api-device-encryption-key-service:ANO-17479 application/vnd.docker.distribution.manifest.v2+json sha256:d17...
docker.io/library/vedge-api-secret-manager-service:ANO-17479        application/vnd.docker.distribution.manifest.v2+json sha256:4b9...

Node 4: k3s-bec2-worker (172.17.127.149):
docker.io/library/vedge-api-device-encryption-key-service:ANO-17479 application/vnd.docker.distribution.manifest.v2+json sha256:d17...
docker.io/library/vedge-api-secret-manager-service:ANO-17479        application/vnd.docker.distribution.manifest.v2+json sha256:4b9...
```

---

### 2.3 `REQ-003`: Helm Chart Linting & Declarative Deployment

#### Chart Linting (`charts/vedge-api-local/`)
```text
$ rtk helm lint /Users/thanghoang/github/oci/charts/vedge-api-local
==> Linting /Users/thanghoang/github/oci/charts/vedge-api-local
1 chart(s) linted, 0 chart(s) failed
```

#### Helm Upgrade Deployments
```text
$ rtk helm --kube-context pc1-bec1 -n cloud-qa-f1 upgrade vedge-api-bec1 /Users/thanghoang/github/oci/charts/vedge-api-local -f /Users/thanghoang/github/oci/charts/vedge-api-local/values-bec1.yaml
Release "vedge-api-bec1" has been upgraded. Happy Helming!
NAME: vedge-api-bec1
LAST DEPLOYED: Mon Nov  2 17:19:40 2026
NAMESPACE: cloud-qa-f1
STATUS: deployed
REVISION: 17

$ rtk helm --kube-context pc1-bec2 -n cloud-qa-f2 upgrade vedge-api-bec2 /Users/thanghoang/github/oci/charts/vedge-api-local -f /Users/thanghoang/github/oci/charts/vedge-api-local/values-bec2.yaml
Release "vedge-api-bec2" has been upgraded. Happy Helming!
NAME: vedge-api-bec2
LAST DEPLOYED: Mon Nov  2 17:20:02 2026
NAMESPACE: cloud-qa-f2
STATUS: deployed
REVISION: 14
```

#### Pod Running Status on `pc1-bec1` & `pc1-bec2`
```text
$ rtk kubectl --context pc1-bec1 -n cloud-qa-f1 get pods -l 'service in (vedge-api-secret-manager-service,vedge-api-device-encryption-key-service)' -o wide
NAME                                                       READY   STATUS    RESTARTS   AGE     IP             NODE              NOMINATED NODE   READINESS GATES
vedge-api-device-encryption-key-service-5cc45f8974-jjskh   1/1     Running   0          71s     10.142.1.153   k3s-bec1-worker   <none>           <none>
vedge-api-secret-manager-service-54d5f564-7s8bn            1/1     Running   0          8m50s   10.142.1.149   k3s-bec1-worker   <none>           <none>

$ rtk kubectl --context pc1-bec2 -n cloud-qa-f2 get pods -l 'service in (vedge-api-secret-manager-service,vedge-api-device-encryption-key-service)' -o wide
NAME                                                       READY   STATUS    RESTARTS   AGE     IP             NODE              NOMINATED NODE   READINESS GATES
vedge-api-device-encryption-key-service-5cb6d6748d-fmt6t   1/1     Running   0          48s     10.242.1.133   k3s-bec2-worker   <none>           <none>
vedge-api-secret-manager-service-785bb845b9-7vvlj          1/1     Running   0          8m28s   10.242.1.128   k3s-bec2-worker   <none>           <none>
```

#### Actuator Health Verification on Both Clusters
```text
pc1-bec1 (cloud-qa-f1):
- vedge-api-secret-manager-service:17000/actuator/health:
  {"components":{"db":{"details":{"database":"PostgreSQL","validationQuery":"isValid()"},"status":"UP"},"diskSpace":{"status":"UP"},"livenessState":{"status":"UP"},"ping":{"status":"UP"},"readinessState":{"status":"UP"},"redis":{"details":{"version":"7.4.11"},"status":"UP"},"refreshScope":{"status":"UP"},"ssl":{"status":"UP"}},"groups":["liveness","readiness"],"status":"UP"}

- vedge-api-device-encryption-key-service:17100/actuator/health:
  {"components":{"db":{"details":{"database":"PostgreSQL","validationQuery":"isValid()"},"status":"UP"},"diskSpace":{"status":"UP"},"livenessState":{"status":"UP"},"ping":{"status":"UP"},"readinessState":{"status":"UP"},"redis":{"details":{"version":"7.4.11"},"status":"UP"},"refreshScope":{"status":"UP"},"ssl":{"status":"UP"}},"groups":["liveness","readiness"],"status":"UP"}

pc1-bec2 (cloud-qa-f2):
- vedge-api-secret-manager-service:17000/actuator/health:
  {"components":{"db":{"details":{"database":"PostgreSQL","validationQuery":"isValid()"},"status":"UP"},"diskSpace":{"status":"UP"},"livenessState":{"status":"UP"},"ping":{"status":"UP"},"readinessState":{"status":"UP"},"redis":{"details":{"version":"7.4.11"},"status":"UP"},"refreshScope":{"status":"UP"},"ssl":{"status":"UP"}},"groups":["liveness","readiness"],"status":"UP"}

- vedge-api-device-encryption-key-service:17100/actuator/health:
  {"components":{"db":{"details":{"database":"PostgreSQL","validationQuery":"isValid()"},"status":"UP"},"diskSpace":{"status":"UP"},"livenessState":{"status":"UP"},"ping":{"status":"UP"},"readinessState":{"status":"UP"},"redis":{"details":{"version":"7.4.11"},"status":"UP"},"refreshScope":{"status":"UP"},"ssl":{"status":"UP"}},"groups":["liveness","readiness"],"status":"UP"}
```

---

### 2.4 `REQ-004`: Runtime Initialization, Database Schema, & Cross-Cluster Key Synchronization

#### 1. `FileSecretStore` Startup Logs in Pods
```text
pc1-bec1 (cloud-qa-f1):
2026-11-02T10:08:44.249Z  INFO 1 --- [vedge-api-secret-manager-service] [main] c.a.m.s.m.s.impl.FileSecretStore : Loaded [1] secrets from file [/etc/ao/encryption-keys/secrets.json].

pc1-bec2 (cloud-qa-f2):
2026-11-02T10:09:02.114Z  INFO 1 --- [vedge-api-secret-manager-service] [main] c.a.m.s.m.s.impl.FileSecretStore : Loaded [1] secrets from file [/etc/ao/encryption-keys/secrets.json].
```

#### 2. Liquibase Schema Migrations in `arm10` PostgreSQL (`10.0.0.216:5432`)
```text
Database: secret_manager_data
                    id                    |  author  |                filename                |        dateexecuted        | orderexecuted 
------------------------------------------+----------+----------------------------------------+----------------------------+---------------
 001_v8_initial_migration                 | peterngo | db/changelog/context/changelog-v8.yaml | 2026-11-02 10:08:34.483478 |             1
 002_create_encryption_key_metadata_table | peterngo | db/changelog/context/changelog-v8.yaml | 2026-11-02 10:08:35.342673 |             2

Database: deviceencryptionkey_data
                   id                   |  author  |                filename                |        dateexecuted        | orderexecuted 
----------------------------------------+----------+----------------------------------------+----------------------------+---------------
 001_v8_initial_migration               | peterngo | db/changelog/context/changelog-v8.yaml | 2026-11-02 10:08:35.415954 |             1
 002_create_device_encryption_key_table | peterngo | db/changelog/context/changelog-v8.yaml | 2026-11-02 10:08:36.427244 |             2
```

#### 3. Key Creation via `POST /secret-manager` on `pc1-bec1` (`cloud-qa-f1`)
```text
$ wget -qO- --post-data='{"secretName":"ao-encryption-key","secretVersion":"1"}' --header="Content-Type: application/json" http://vedge-api-secret-manager-service:17000/secret-manager
1912128453
```

#### 4. Cross-Cluster Key Synchronization on `pc1-bec2` (`cloud-qa-f2`)
```text
$ wget -qO- http://vedge-api-secret-manager-service:17000/secret-manager
[{"encryptionKeyId":1912128453,"status":"active","secretName":"ao-encryption-key","secretVersion":"1","createdAt":"2026-11-02T10:15:34.882","updatedAt":"2026-11-02T10:15:34.882"}]

$ wget -S -O- --header="x-auth-request-tenants: system" http://vedge-api-secret-manager-service:17000/secret-manager/sync-key-store
HTTP/1.1 200 OK
{"activeKey":{"encryptionKeyId":1912128453,"encryptionKey":"8/GV+YoamiPAQh2NxztJOs0/3iy7dRgRCnRkPcEm3Uvd4rq8tIo9t1ZwcwL6t2IX"},"historicalKeys":{"1912128453":{"encryptionKeyId":1912128453,"encryptionKey":"8/GV+YoamiPAQh2NxztJOs0/3iy7dRgRCnRkPcEm3Uvd4rq8tIo9t1ZwcwL6t2IX"}},"envelopeEnabled":true,"masterSecretId":335116804}
```

#### 5. PostgreSQL Metadata Record in `arm10` Shared Database
```text
psql -h 10.0.0.216 -U postgres -d secret_manager_data -c "SELECT id, encryption_key_id, status, secret_name, secret_version, created_at, updated_at FROM encryption_key_metadata;"

 id | encryption_key_id | status |    secret_name    | secret_version |         created_at         |         updated_at         
----+-------------------+--------+-------------------+----------------+----------------------------+----------------------------
  1 |        1912128453 | ACTIVE | ao-encryption-key | 1              | 2026-11-02 10:15:34.882554 | 2026-11-02 10:15:34.882566
(1 row)
```
