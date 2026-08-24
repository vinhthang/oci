#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo "🚀 OCI Fleet GitOps Synchronizer"
echo "=================================================="

echo "📦 1. Applying all Kubernetes manifests to oci-k3s..."
kubectl apply -f k8s/ --context oci-k3s

echo "📝 2. Synchronizing Blog to Edge Gateway (amd10)..."
ssh -i ~/.ssh/id_ed25519 opc@152.70.101.162 "
  mkdir -p /opt/hugo-blog/content/posts
"
rsync -avz -e "ssh -i ~/.ssh/id_ed25519" blog/content/posts/ opc@152.70.101.162:/opt/hugo-blog/content/posts/

echo "🔨 3. Rebuilding Hugo Static Site on amd10..."
ssh -i ~/.ssh/id_ed25519 opc@152.70.101.162 "
  cd /opt/hugo-blog && hugo --minify
"

echo "=================================================="
echo "✅ GitOps Synchronization Complete! All services live!"
echo "=================================================="
