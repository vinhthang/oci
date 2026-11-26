#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "🚀 Multi-Cloud Fleet Helm & GitOps Synchronizer"
echo "=================================================="

echo "📦 1. Upgrading entire fleet via Helm Chart (charts/vinhthang-fleet)..."
helm upgrade --install fleet ./charts/vinhthang-fleet -n default --kube-context oci-k3s --no-hooks

echo "📝 2. Synchronizing Blog & Analytics Tracker to Edge Gateway (amd10)..."
ssh amd10 "mkdir -p /opt/hugo-blog/content/posts /opt/hugo-blog/layouts/partials"
rsync -avz blog/content/posts/ amd10:/opt/hugo-blog/content/posts/
rsync -avz blog/layouts/ amd10:/opt/hugo-blog/layouts/
scp blog/hugo.toml amd10:/opt/hugo-blog/hugo.toml

echo "🔨 3. Rebuilding Hugo Static Site on amd10 (Tokyo Edge)..."
ssh amd10 "cd /opt/hugo-blog && hugo --minify"

echo "🌍 4. Synchronizing Built Static Blog to gce10 (US-Central Edge)..."
ssh amd10 "tar -czf - -C /opt/hugo-blog public" | ssh gce10 "tar -xzf - -C /opt/hugo-blog"

echo "🌐 5. Synchronizing Declarative Caddyfile to Edge Gateways (amd10 + gce10)..."
# NOTE: Do NOT use the caddy CLI reload subcommand on amd10 or gce10 — the global
# `servers { metrics }` block binds :2019 to a metrics catch-all, and "localhost"
# resolves to ::1 which hits that catch-all instead of the real admin API
# (127.0.0.1:2019). Validate first, then load via 127.0.0.1:2019/load directly.
scp caddy/Caddyfile amd10:/tmp/Caddyfile
ssh amd10 "
  set -e
  /usr/local/bin/caddy validate --config /tmp/Caddyfile --adapter caddyfile
  sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
  curl -fsS -X POST http://127.0.0.1:2019/load -H 'Content-Type: text/caddyfile' --data-binary @/etc/caddy/Caddyfile
"
scp caddy/Caddyfile gce10:/tmp/Caddyfile
ssh gce10 "
  set -e
  /usr/bin/caddy validate --config /tmp/Caddyfile --adapter caddyfile
  sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
  curl -fsS -X POST http://127.0.0.1:2019/load -H 'Content-Type: text/caddyfile' --data-binary @/etc/caddy/Caddyfile
"

echo "🔍 6. Post-Sync Edge Ingress & Service Health Verification..."
curl -fsS -I --max-time 5 "http://35.209.149.46:8088/anon/" >/dev/null || {
  echo "❌ ERROR: File server on gce10 (:8088/anon/) is DOWN after sync!" >&2
  exit 1
}
curl -fsS -I --max-time 5 "https://vinhthang.dev" >/dev/null || {
  echo "❌ ERROR: https://vinhthang.dev is unreachable after sync!" >&2
  exit 1
}
echo "  [OK] Edge health checks passed!"

echo "=================================================="
echo "✅ Active-Active Dual-Edge Blog & Fleet Sync Complete!"
echo "=================================================="
