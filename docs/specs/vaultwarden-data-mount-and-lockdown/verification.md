# Verification Evidence: Vaultwarden HostPath Data Mount & Registration Lockdown Remediation

**Feature ID**: `vaultwarden-data-mount-and-lockdown`  
**Execution Timestamp**: `2026-10-31T04:54:05Z` – `2026-10-31T04:55:45Z`  
**Status**: Passed (All Acceptance Criteria Met)

---

## 1. Traceability Matrix

| Requirement ID | Description | Acceptance Criteria | Live Command / Evidence | Status |
| :--- | :--- | :--- | :--- | :---: |
| `REQ-001` | Mount Production Vaultwarden Data Directory (`/opt/vaultwarden/data`) | Pod mounts hostPath `/opt/vaultwarden/data`; serves `thanghv@gmail.com` with `324` ciphers | `kubectl get deploy vaultwarden -n apps -o jsonpath='{.spec.template.spec.volumes[0].hostPath.path}'` & SQLite count | **PASS** |
| `REQ-002` | Enforce Single-User Registration Lockdown (`ADR-0011`) | `signupsAllowed: false`, `invitationsAllowed: false`; `/api/config` returns `"disableUserRegistration": true` | `curl -sS https://vault.vinhthang.dev/api/config` | **PASS** |
| `REQ-003` | Declarative Helm Upgrade & Prelogin Verification | GitOps reconcile succeeds; pod `1/1 Running`; `/identity/accounts/prelogin` returns 200 OK | GitOps webhook logs, `kubectl get pods`, and prelogin curl | **PASS** |

---

## 2. Verbatim Verification Outputs

### `REQ-001`: Mount Production Vaultwarden Data Directory

#### 1.1 Local Helm Template Validation
```bash
$ rtk helm template fleet charts/vinhthang-fleet -s templates/vaultwarden.yaml
```
**Output**:
```yaml
      volumes:
        - name: vaultwarden-data
          hostPath:
            path: /opt/vaultwarden/data
            type: Directory
```

#### 1.2 Remote Deployment HostPath Inspection
```bash
$ rtk proxy ssh -o ConnectTimeout=5 -J opc@152.70.101.162 opc@10.0.0.216 "sudo /usr/local/bin/k3s kubectl get deploy vaultwarden -n apps -o jsonpath='{.spec.template.spec.volumes[0].hostPath.path}{\"\n\"}'"
```
**Output**:
```
/opt/vaultwarden/data
```

#### 1.3 Production SQLite Database Contents
```bash
$ rtk proxy ssh -o ConnectTimeout=5 -J opc@152.70.101.162 opc@10.0.0.216 "sudo python3 -c 'import sqlite3; con = sqlite3.connect(\"/opt/vaultwarden/data/db.sqlite3\"); cur = con.cursor(); print(\"Users:\", cur.execute(\"SELECT email FROM users\").fetchall()); print(\"Ciphers count:\", cur.execute(\"SELECT count(*) FROM ciphers\").fetchone()[0])'"
```
**Output**:
```
Users: [('thanghv@gmail.com',)]
Ciphers count: 324
```

---

### `REQ-002`: Enforce Single-User Registration Lockdown (`ADR-0011`)

#### 2.1 Pod Environment Configuration
```bash
$ rtk helm template fleet charts/vinhthang-fleet -s templates/vaultwarden.yaml
```
**Output**:
```yaml
          env:
            - name: WEBSOCKET_ENABLED
              value: "true"
            - name: SIGNUPS_ALLOWED
              value: "false"
            - name: INVITATIONS_ALLOWED
              value: "false"
            - name: DOMAIN
              value: "https://vault.vinhthang.dev"
            - name: ROCKET_PORT
              value: "80"
```

#### 2.2 Public API Config Endpoint Verification
```bash
$ rtk proxy curl -sS https://vault.vinhthang.dev/api/config
```
**Output**:
```json
{"version":"2026.6.0","gitHash":"46d71107","server":{"name":"Vaultwarden","url":"https://github.com/dani-garcia/vaultwarden"},"settings":{"disableUserRegistration":true,"suppressOnboardingInterstitials":false},"environment":{"vault":"https://vault.vinhthang.dev","api":"https://vault.vinhthang.dev/api","identity":"https://vault.vinhthang.dev/identity","notifications":"https://vault.vinhthang.dev/notifications","sso":"","cloudRegion":null},"push":{"pushTechnology":0,"vapidPublicKey":null},"featureStates":{"pm-19148-innovation-archive":true},"communication":null,"object":"config"}
```

---

### `REQ-003`: Declarative Helm Upgrade & Prelogin Verification

#### 3.1 GitOps Webhook Reconcile Logs
```bash
$ rtk proxy ssh -o ConnectTimeout=5 -J opc@152.70.101.162 opc@10.0.0.216 "sudo /usr/local/bin/k3s kubectl logs -n system -l app=gitops-webhook --tail=20"
```
**Output**:
```
⚡ [Sat Oct 31 04:54:05 UTC 2026] Authenticated GitHub Webhook push event triggered! Starting GitOps reconcile...
Cloning into '/tmp/vinhthang-fleet'...
📥 Repository pulled successfully. Upgrading Helm Fleet...
Release "fleet" has been upgraded. Happy Helming!
NAME: fleet
LAST DEPLOYED: Sat Oct 31 04:54:09 2026
NAMESPACE: default
STATUS: deployed
REVISION: 220662
TEST SUITE: None
✅ [Sat Oct 31 04:54:28 UTC 2026] GitOps reconcile finished successfully!
```

#### 3.2 Vaultwarden Pod Running Status
```bash
$ rtk proxy ssh -o ConnectTimeout=5 -J opc@152.70.101.162 opc@10.0.0.216 "sudo /usr/local/bin/k3s kubectl get pods -n apps -l app=vaultwarden -o wide"
```
**Output**:
```
NAME                           READY   STATUS    RESTARTS   AGE   IP            NODE    NOMINATED NODE   READINESS GATES
vaultwarden-5d94654846-tkggh   1/1     Running   0          15s   10.42.0.134   arm10   <none>           <none>
```

#### 3.3 Live Prelogin Endpoint Verification
```bash
$ rtk proxy curl -sS -X POST https://vault.vinhthang.dev/identity/accounts/prelogin -H "Content-Type: application/json" -d '{"email":"thanghv@gmail.com"}'
```
**Output**:
```json
{"kdf":0,"kdfIterations":600000,"kdfMemory":null,"kdfParallelism":null,"kdfSettings":{"iterations":600000,"kdfType":0,"memory":null,"parallelism":null},"salt":null}
```
