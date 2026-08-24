# ADR-0002: Caddy Edge Gateway & Central Google OAuth2 SSO

* **Status**: 🟢 Accepted & In Production
* **Date**: 2026-08-24
* **Authors**: Thang Hoang & Antigravity

---

## 1. Context & Problem Statement
Hosting multiple administrative and private web services (Grafana, Uptime Kuma, AnythingLLM, FileBrowser, Umami Analytics) poses significant security risks if exposed publicly. Having individual authentication for each service creates password sprawl and friction.

---

## 2. Decision
1. **Edge Gateway (Caddy)**: Deployed Caddy on `amd10` (`152.70.101.162`) to handle automatic TLS termination, Let's Encrypt / Google Trust Services certificates, and reverse proxying to internal NodePorts (`30001-30009`).
2. **Central SSO Gateway (`auth.vinhthang.dev`)**: Deployed `oauth2-proxy` connected to Google OAuth2 API (`thanghv@gmail.com`).
3. **Forward-Auth Architecture**: Private subdomains use Caddy's `forward_auth 10.0.0.216:30004` directive to validate user session cookies. Unauthenticated requests are redirected to `https://auth.vinhthang.dev/oauth2/start`.
4. **Auth Proxy Delegation**:
   * For **Grafana**: Injected `X-Auth-Request-Email` and `X-Auth-Request-User` headers into Grafana's `auth.proxy` module for instant passwordless Admin login.
   * For **Uptime Kuma**: Disabled internal login (`disableAuth: true` in `kuma.db`), delegating 100% of perimeter authentication to Google SSO.
5. **Security Headers**: Injected global headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `-Server`).

---

## 3. Consequences
### Positive:
* Single Sign-On across all private tools with Google OAuth2.
* Zero credentials stored inside individual applications.
* Strict edge perimeter protection with modern TLS and security headers.

### Negative / Trade-offs:
* If Google OAuth2 or `oauth2-proxy` experiences downtime, private dashboards are inaccessible until restored.
