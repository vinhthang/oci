# Technical Design: Vaultwarden HostPath Data Mount & Registration Lockdown Remediation

**Feature ID**: `vaultwarden-data-mount-and-lockdown`  
**Status**: In-Progress  

---

## 1. Helm Values & Template Alignment (`REQ-001`, `REQ-002`)

### 1.1 `charts/vinhthang-fleet/values.yaml` (`REQ-001`, `REQ-002`)
Configure `vaultwarden` values in [`charts/vinhthang-fleet/values.yaml`](file:///Users/thanghoang/github/oci/charts/vinhthang-fleet/values.yaml#L320-L332):
```yaml
vaultwarden:
  enabled: true
  image: docker.io/vaultwarden/server:1.37.2-alpine
  invitationsAllowed: false
  nodePort: 30010
  resources:
    limits:
      memory: 128Mi
    requests:
      cpu: 10m
      memory: 20Mi
  signupsAllowed: false
  storagePath: /opt/vaultwarden/data
  websocketEnabled: true
```

### 1.2 `charts/vinhthang-fleet/templates/vaultwarden.yaml` (`REQ-001`, `REQ-002`)
Bind environment variables and `hostPath` dynamically from `.Values.vaultwarden`:
```yaml
          env:
            - name: WEBSOCKET_ENABLED
              value: {{ .Values.vaultwarden.websocketEnabled | quote }}
            - name: SIGNUPS_ALLOWED
              value: {{ .Values.vaultwarden.signupsAllowed | quote }}
            - name: INVITATIONS_ALLOWED
              value: {{ .Values.vaultwarden.invitationsAllowed | quote }}
            - name: DOMAIN
              value: "https://vault.vinhthang.dev"
            - name: ROCKET_PORT
              value: "80"
```
and volume definition:
```yaml
      volumes:
        - name: vaultwarden-data
          hostPath:
            path: {{ .Values.vaultwarden.storagePath | default "/opt/vaultwarden/data" }}
            type: Directory
```

---

## 2. Deployment & Verification Flow (`REQ-003`)

1. Normalize `/opt/vaultwarden/data` ownership (`chown -R root:root /opt/vaultwarden/data`) on `arm10` so SQLite WAL (`db.sqlite3-wal`) and `rsa_key.pem` have clean root permissions.
2. Upgrade the Helm release (`helm upgrade fleet ./charts/vinhthang-fleet`) and wait for `deployment/vaultwarden` rollout in namespace `apps`.
3. Verify `GET https://vault.vinhthang.dev/api/config` returns `"disableUserRegistration": true` and `POST https://vault.vinhthang.dev/identity/accounts/prelogin` succeeds for `thanghv@gmail.com`.
