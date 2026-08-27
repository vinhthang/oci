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
scp caddy/Caddyfile amd10:/tmp/Caddyfile
ssh amd10 "
  sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
  sudo /usr/local/bin/caddy reload --config /etc/caddy/Caddyfile
"
ssh gce10 "
  sudo /usr/bin/caddy reload --config /etc/caddy/Caddyfile || true
"

echo "=================================================="
echo "✅ Active-Active Dual-Edge Blog & Fleet Sync Complete!"
echo "=================================================="
