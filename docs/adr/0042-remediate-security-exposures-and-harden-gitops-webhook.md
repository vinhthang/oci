# ADR 0042: Remediate Security Exposures, Rotate WireGuard Keys, and Harden GitOps Webhook

## Status
🟢 Accepted

## Context
A security review identified critical and high vulnerabilities in the repository:
1. **Critical Secret Leak**: WireGuard keypairs (`privatekey`, `pc1_private`, `wg1-client.conf`, `wg1-client-qr.txt`) were tracked at the repository root due to an insufficiently broad `.gitignore`. The client key for `gce10` (`wg1`, ADR-0041) was active, enabling unauthorized full-tunnel VPN routing and access to internal subnets (`10.66.0.0/24`, `10.10.0.0/24`, `10.0.0.0/16`).
2. **High Credential Exposure**: Weaviate native API key was hardcoded in `charts/vinhthang-fleet/values.yaml` (`AUTHENTICATION_APIKEY_ALLOWED_KEYS: "oci-weaviate-secure-key"`), leaving the public vector DB ingress (`weaviate.vinhthang.dev`) effectively unauthenticated.
3. **High Unauthenticated GitOps Webhook**: `charts/vinhthang-fleet/templates/gitops-webhook.yaml` executed an unauthenticated raw `nc -l -p 9000` listener loop. Any TCP/HTTP connection triggered an automatic `git pull` and `helm upgrade fleet` under a cluster-admin `ClusterRole`.
4. **Agent Clutter**: Ephemeral one-off scratch scripts (`fix_yaml.py`, `patch-*.py`, `revert.py`, etc.) accumulated at the repository root.

## Decision
1. **WireGuard Key Rotation**:
   - Immediately regenerate server and client keypairs on `gce10` (`wg1`).
   - Rewrite `/etc/wireguard/wg1.conf` with new keys and reload `wg-quick@wg1`. The compromised client key is permanently revoked.
   - Stage deletion of all root key, conf, and QR artifacts from Git tracking.
   - Expand `.gitignore` to match `*.key`, `*.conf`, `*private*`, `*public*`, `*client-qr*`, and `wireguard/` at all directory levels.
2. **Weaviate Secret Decoupling**:
   - Transition `AUTHENTICATION_APIKEY_ALLOWED_KEYS` in `charts/vinhthang-fleet/templates/weaviate.yaml` to source from `secretKeyRef` pointing to `weaviate-secret:api-key`.
   - Remove plaintext API key from `values.yaml` and configure `createSecret: false` / `existingSecret: "weaviate-secret"`.
3. **GitOps Webhook HMAC Hardening**:
   - Replace the raw `nc -l -p 9000` listener with a Python 3 HTTP daemon (`receiver.py`) mounted via ConfigMap `gitops-webhook-script`.
   - Validate GitHub webhook signatures via `X-Hub-Signature-256` using constant-time HMAC SHA-256 comparison against `GITHUB_WEBHOOK_SECRET`.
   - Implement dedicated `/healthz` HTTP probes for liveness and readiness.
   - Filter push payloads to trigger reconcile strictly on commits to `refs/heads/main`.
4. **Repository Cleanup**:
   - Remove temporary scratch scripts and log files from the root directory and add ignore patterns to `.gitignore`.

## Consequences
- **Eliminated Public VPN Ingress**: Compromised WireGuard keys are revoked; unauthorized traffic is rejected at the handshake level.
- **Hardened Vector DB**: Weaviate authentication secret is isolated in Kubernetes and absent from version control.
- **Tamper-Proof GitOps**: Redundant, arbitrary, or unauthenticated redeploys are rejected with `401 Unauthorized` / `403 Forbidden`. Reconcile runs strictly on verified GitHub push events.
- **Clean Repository Root**: Scratch files removed; sensitive file patterns guarded by hardened `.gitignore`.
