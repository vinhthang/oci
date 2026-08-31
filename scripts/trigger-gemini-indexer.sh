#!/usr/bin/env bash
set -e

echo "=================================================="
echo "🚀 Manual Gemini Batch Indexer Trigger"
echo "=================================================="
JOB_NAME="manual-gemini-index-$(date +%s)"
kubectl create job --from=cronjob/anythingllm-indexer-cron "$JOB_NAME" --context oci-k3s
echo "📋 Job launched: $JOB_NAME"
echo "🔍 Streaming logs..."
sleep 3
kubectl logs -f "job/$JOB_NAME" --context oci-k3s
