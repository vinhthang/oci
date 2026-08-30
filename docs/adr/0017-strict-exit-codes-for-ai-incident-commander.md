# ADR-0017: Strict Exit Codes for AI Incident Commander Telemetry

## Status
🟢 Accepted

## Context
The AI Incident Commander is an event-driven system that relies exclusively on Grafana alerts (via Prometheus metrics and `kube-state-metrics`) to detect and triage infrastructure failures. 

During an incident involving an immutable `PersistentVolume` patch failure in the `vinhthang-fleet` Helm chart, the `gitops-webhook` pod failed to successfully deploy the update. However, the AI Incident Commander did not trigger because the webhook shell script suppressed the exit code using `|| echo "⚠️ Helm upgrade returned warning."`. By swallowing the error, the `gitops-webhook` pod never restarted, averting a `CrashLoopBackOff` state. To `kube-state-metrics` and Grafana, the system appeared 100% healthy. 

Similar anti-patterns (`|| true`) were found in other critical workflows, including the `nightly-fleet-backup` CronJob, where a failure in the `tar` backup archiving process would be silently ignored, resulting in missing backups while the CronJob reported `Completed`.

## Decision
1. **No Silent Failures in Automation**: All critical shell scripts, CronJobs, and webhooks must strictly propagate non-zero exit codes. The use of `|| true` or output redirection that masks exit codes is forbidden in deployment pipelines and data backups.
2. **Crash-Oriented Webhooks**: Background loops inside pods (such as the GitOps webhook reconcile worker) must actively terminate the parent container (`kill 1` or `exit 1`) if a critical deployment command fails. This forces Kubernetes to restart the pod, quickly entering a `CrashLoopBackOff` state which Grafana monitors.
3. **Audit Results**: 
   - Removed `|| true` from `gitops-webhook.yaml` and implemented `kill 1` to ensure failures trigger pod crashes.
   - Removed `2>/dev/null || true` from the `tar` step and `find` prune step in `nightly-backup-cronjob.yaml` to ensure corrupt backups fail the CronJob.
   - Removed `|| true` from `caddy reload` via SSH in `scripts/gitops-sync.sh` so syntax errors block the script execution.

## Consequences
* **Positive**: The AI Incident Commander will now reliably catch deployment regressions and backup failures since Grafana will correctly detect Pod crashes and failed CronJobs.
* **Negative**: Deployments that fail for transient reasons will crash the webhook pod, requiring intervention (or automated AI triage) instead of silently retrying in the background. Backups that fail due to minor warnings (like file changes during `tar`) will now fail the entire CronJob.
