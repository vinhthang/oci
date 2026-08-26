#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "🚀 OCI Fleet Helm & GitOps Synchronizer"
echo "=================================================="

echo "📦 1. Upgrading entire fleet via Helm Chart (charts/vinhthang-fleet)..."
helm upgrade --install fleet ./charts/vinhthang-fleet --kube-context oci-k3s

echo "📝 2. Synchronizing Blog to Edge Gateway (amd10)..."
ssh -i ~/.ssh/id_ed25519 opc@152.70.101.162 "
  mkdir -p /opt/hugo-blog/content/posts
"
rsync -avz -e "ssh -i ~/.ssh/id_ed25519" blog/content/posts/ opc@152.70.101.162:/opt/hugo-blog/content/posts/

echo "🔨 3. Rebuilding Hugo Static Site on amd10..."
ssh -i ~/.ssh/id_ed25519 opc@152.70.101.162 "
  cd /opt/hugo-blog && hugo --minify
"

echo "🌐 4. Synchronizing Declarative Caddyfile to Edge Gateway (amd10)..."
scp -i ~/.ssh/id_ed25519 caddy/Caddyfile opc@152.70.101.162:/tmp/Caddyfile
ssh -i ~/.ssh/id_ed25519 opc@152.70.101.162 "
  sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile
  sudo /usr/local/bin/caddy reload --config /etc/caddy/Caddyfile
"

echo "=================================================="
echo "✅ Helm Fleet & Edge Ingress Synchronization Complete! All services live!"
echo "=================================================="

