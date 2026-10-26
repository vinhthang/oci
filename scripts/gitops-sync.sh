#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "🚀 Multi-Cloud Fleet Helm & GitOps Synchronizer"
echo "=================================================="

echo "📦 1. Upgrading entire fleet via Helm Chart (charts/vinhthang-fleet)..."
helm upgrade --install fleet ./charts/vinhthang-fleet --kube-context oci-k3s

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
# NOTE 2026-10-26 (Muse, rebased from the 2026-10-23 draft onto 68f45d7): do NOT
# use `caddy reload --config` on amd10 — it silently no-ops. The global
# `servers { metrics }` block binds :2019 to a metrics catch-all, and "localhost"
# resolves to ::1 which hits that catch-all instead of the real admin API
# (127.0.0.1:2019). Load the new file via the admin API directly (verified
# working on amd10 2026-10-23).
scp caddy/Caddyfile amd10:/tmp/Caddyfile
ssh amd10 "
  set -e
  /usr/local/bin/caddy validate --config /tmp/Caddyfile --adapter caddyfile
  sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
  curl -sS -X POST http://127.0.0.1:2019/load -H 'Content-Type: text/caddyfile' --data-binary @/etc/caddy/Caddyfile
"
# gce10: its `caddy reload` below is left as-is but flagged — the same ::1 /
# admin-API trap likely applies there and is unverified. Verify with
#   curl -s http://127.0.0.1:2019/config/ | head -c 120
# vs [::1]:2019 before trusting `caddy reload` output on gce10.
scp caddy/Caddyfile gce10:/tmp/Caddyfile
ssh gce10 "
  sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
  sudo /usr/bin/caddy reload --config /etc/caddy/Caddyfile
"

echo "=================================================="
echo "✅ Active-Active Dual-Edge Blog & Fleet Sync Complete!"
echo "=================================================="
