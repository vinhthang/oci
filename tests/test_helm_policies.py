"""Architectural fitness tests for Helm charts across the repository."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from conftest import CHARTS, CHARTS_DIR, load_chart_values

FORBIDDEN_PLAINTEXT_LITERALS = (
    "super_secret_",
    "Secret123",
    "postgres_master_pass_",
    "review-secret-token",
    "agy-local-key",
    "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
)

WORKLOAD_KINDS = {
    "Deployment",
    "StatefulSet",
    "DaemonSet",
    "Job",
    "CronJob",
    "RedisReplication",
    "PerconaServerMongoDB",
    "Redis",
}


def _iter_pod_specs(doc: dict[str, Any]) -> list[dict[str, Any]]:
    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind in {"Deployment", "StatefulSet", "DaemonSet", "Job"}:
        tpl = (spec.get("template") or {}).get("spec") or {}
        return [tpl] if tpl else []
    if kind == "CronJob":
        tpl = (
            ((spec.get("jobTemplate") or {}).get("spec") or {})
            .get("template", {})
            .get("spec")
            or {}
        )
        return [tpl] if tpl else []
    return []


def _extract_images(doc: dict[str, Any]) -> list[str]:
    images: list[str] = []
    kind = doc.get("kind")
    if kind not in WORKLOAD_KINDS:
        return images

    for pod_spec in _iter_pod_specs(doc):
        for container_key in ("containers", "initContainers"):
            for container in pod_spec.get(container_key) or []:
                img = container.get("image")
                if isinstance(img, str) and img.strip():
                    images.append(img.strip())

    # Operator CRs (RedisReplication, PerconaServerMongoDB, Redis)
    if kind in {"RedisReplication", "PerconaServerMongoDB", "Redis"}:
        spec = doc.get("spec") or {}
        if isinstance(spec.get("image"), str):
            images.append(spec["image"].strip())
        for sub_key in ("kubernetesConfig", "redisExporter", "sentinel", "pmm", "backup"):
            sub = spec.get(sub_key)
            if isinstance(sub, dict) and isinstance(sub.get("image"), str):
                images.append(sub["image"].strip())

    return images


def _is_pinned_image(image: str) -> bool:
    if "@sha256:" in image:
        return True
    last_segment = image.rsplit("/", 1)[-1]
    if ":" not in last_segment:
        return False
    tag = last_segment.split(":", 1)[1]
    return bool(tag) and tag != "latest"


def test_all_charts_helm_lint_clean() -> None:
    failures: list[str] = []
    for chart_name in CHARTS:
        chart_path = CHARTS_DIR / chart_name
        secrets_example = chart_path / "values.secrets.example.yaml"
        cmd = ["helm", "lint", str(chart_path)]
        if secrets_example.is_file():
            cmd.extend(["-f", str(secrets_example)])
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        combined = f"{proc.stdout}\n{proc.stderr}"
        if proc.returncode != 0:
            failures.append(f"{chart_name}: helm lint exited {proc.returncode}: {combined.strip()}")
        if "deprecated" in combined.lower():
            failures.append(f"{chart_name}: helm lint reported deprecated API warning: {combined.strip()}")
    assert not failures, "\n".join(failures)


def test_no_latest_or_untagged_images(all_rendered_charts: dict[str, list[dict[str, Any]]]) -> None:
    unpinned: list[str] = []
    for chart_name, docs in all_rendered_charts.items():
        for doc in docs:
            kind = doc.get("kind", "")
            name = (doc.get("metadata") or {}).get("name", "<unknown>")
            for image in _extract_images(doc):
                if not _is_pinned_image(image):
                    unpinned.append(f"{chart_name} {kind}/{name}: {image}")
    assert not unpinned, f"Unpinned or :latest container images found:\n" + "\n".join(unpinned)


def test_vinhthang_fleet_no_default_secrets_and_no_plaintext_credentials(
    vinhthang_fleet_default_docs: list[dict[str, Any]],
) -> None:
    secrets = [
        (doc.get("metadata") or {}).get("name", "<unnamed>")
        for doc in vinhthang_fleet_default_docs
        if doc.get("kind") == "Secret"
    ]
    assert not secrets, f"Default vinhthang-fleet render must produce 0 Secrets, found: {secrets}"

    leaks: list[str] = []
    for yaml_file in sorted(CHARTS_DIR.rglob("*.yaml")):
        rel = yaml_file.relative_to(CHARTS_DIR)
        # Skip subchart dependency archives/directories under charts/<chart>/charts/
        if len(rel.parts) >= 3 and rel.parts[1] == "charts":
            continue
        content = yaml_file.read_text(encoding="utf-8")
        for literal in FORBIDDEN_PLAINTEXT_LITERALS:
            if literal in content:
                leaks.append(f"{rel}: contains forbidden literal {literal!r}")
    assert not leaks, "Plaintext credential literals found in charts:\n" + "\n".join(leaks)


def test_no_custom_port_8080(all_rendered_charts: dict[str, list[dict[str, Any]]]) -> None:
    fleet_docs = all_rendered_charts["vinhthang-fleet"]

    # 1. VietCalendar must run on port 8087 (containerPort, PORT env, and Service port/targetPort)
    vietcal_deployments = [
        d for d in fleet_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "vietcalendar"
    ]
    assert len(vietcal_deployments) == 1, "Expected Deployment/vietcalendar in vinhthang-fleet"
    vc_container = vietcal_deployments[0]["spec"]["template"]["spec"]["containers"][0]
    vc_cports = [p.get("containerPort") for p in (vc_container.get("ports") or [])]
    assert vc_cports == [8087], f"vietcalendar containerPorts expected [8087], got {vc_cports}"
    vc_env = {e.get("name"): e.get("value") for e in (vc_container.get("env") or [])}
    assert vc_env.get("PORT") == "8087", f"vietcalendar PORT env expected '8087', got {vc_env.get('PORT')!r}"

    vietcal_services = [
        d for d in fleet_docs
        if d.get("kind") == "Service" and (d.get("metadata") or {}).get("name") == "vietcalendar"
    ]
    assert len(vietcal_services) == 1, "Expected Service/vietcalendar in vinhthang-fleet"
    vc_svc_ports = vietcal_services[0]["spec"]["ports"]
    assert all(p.get("port") == 8087 and p.get("targetPort") == 8087 for p in vc_svc_ports), (
        f"Service/vietcalendar ports must be 8087, got {vc_svc_ports}"
    )

    # 2. Pulsar HTTP port across vinhthang-fleet, bec-datastores, and qa-router-datastores must be 8088 (never 8080)
    pulsar_charts = ("vinhthang-fleet", "bec-datastores", "qa-router-datastores")
    pulsar_violations: list[str] = []
    pulsar_8088_seen: dict[str, bool] = {c: False for c in pulsar_charts}

    for chart_name in pulsar_charts:
        for doc in all_rendered_charts[chart_name]:
            kind = doc.get("kind")
            name = (doc.get("metadata") or {}).get("name", "")
            labels = (doc.get("metadata") or {}).get("labels") or {}
            is_pulsar = "pulsar" in name.lower() or "pulsar" in str(labels).lower()
            if not is_pulsar:
                continue

            if kind in {"Deployment", "StatefulSet"}:
                for pod_spec in _iter_pod_specs(doc):
                    for container in pod_spec.get("containers") or []:
                        for p in container.get("ports") or []:
                            cp = p.get("containerPort")
                            if cp == 8080:
                                pulsar_violations.append(f"{chart_name} {kind}/{name} uses containerPort 8080")
                            if cp == 8088:
                                pulsar_8088_seen[chart_name] = True
            elif kind == "Service":
                for p in (doc.get("spec") or {}).get("ports") or []:
                    port_val = p.get("port")
                    target_val = p.get("targetPort")
                    if port_val == 8080 or target_val == 8080:
                        pulsar_violations.append(
                            f"{chart_name} Service/{name} port={port_val} targetPort={target_val} uses 8080"
                        )
                    if port_val == 8088 or target_val == 8088:
                        pulsar_8088_seen[chart_name] = True

    assert not pulsar_violations, "Pulsar port 8080 violations:\n" + "\n".join(pulsar_violations)
    missing_8088 = [c for c, seen in pulsar_8088_seen.items() if not seen]
    assert not missing_8088, f"Expected Pulsar HTTP port 8088 in charts: {missing_8088}"

    # 3. No non-upstream custom service or container in vinhthang-fleet may bind port 8080
    allowed_upstream_8080 = ("weaviate", "kube-state-metrics")
    custom_8080: list[str] = []
    for doc in fleet_docs:
        kind = doc.get("kind")
        name = (doc.get("metadata") or {}).get("name", "")
        if any(name == allow or name.startswith(allow) or allow in name for allow in allowed_upstream_8080):
            continue
        if kind in {"Deployment", "StatefulSet", "DaemonSet"}:
            for pod_spec in _iter_pod_specs(doc):
                for container in pod_spec.get("containers") or []:
                    for p in container.get("ports") or []:
                        if p.get("containerPort") == 8080:
                            custom_8080.append(f"{kind}/{name} containerPort 8080")
        elif kind == "Service":
            for p in (doc.get("spec") or {}).get("ports") or []:
                if p.get("port") == 8080 or p.get("targetPort") == 8080:
                    custom_8080.append(f"Service/{name} port={p.get('port')} targetPort={p.get('targetPort')}")
    assert not custom_8080, "Custom workloads binding forbidden port 8080:\n" + "\n".join(custom_8080)


def test_rbac_resources_and_namespaces(vinhthang_fleet_docs: list[dict[str, Any]]) -> None:
    expected_namespaces = {"ai", "apps", "data", "observability", "openviking", "operators", "system"}

    # 1. Unique Namespace objects with helm.sh/resource-policy: keep
    ns_docs = [d for d in vinhthang_fleet_docs if d.get("kind") == "Namespace"]
    ns_counts: dict[str, int] = {}
    missing_keep_policy: list[str] = []
    for doc in ns_docs:
        meta = doc.get("metadata") or {}
        name = meta.get("name", "")
        ns_counts[name] = ns_counts.get(name, 0) + 1
        annotations = meta.get("annotations") or {}
        if annotations.get("helm.sh/resource-policy") != "keep":
            missing_keep_policy.append(name)

    for ns in sorted(expected_namespaces):
        assert ns_counts.get(ns) == 1, f"Namespace {ns!r} count expected 1, got {ns_counts.get(ns, 0)}"
    assert not missing_keep_policy, (
        f"Namespaces missing annotation 'helm.sh/resource-policy: keep': {missing_keep_policy}"
    )

    # 2. ClusterRole/gitops-deployer must have zero '*' in verbs or resources
    gitops_roles = [
        d for d in vinhthang_fleet_docs
        if d.get("kind") == "ClusterRole" and (d.get("metadata") or {}).get("name") == "gitops-deployer"
    ]
    assert len(gitops_roles) == 1, "Expected ClusterRole/gitops-deployer"
    wildcards: list[str] = []
    for idx, rule in enumerate(gitops_roles[0].get("rules") or []):
        if "*" in (rule.get("verbs") or []):
            wildcards.append(f"rule[{idx}].verbs contains '*'")
        if "*" in (rule.get("resources") or []):
            wildcards.append(f"rule[{idx}].resources contains '*'")
    assert not wildcards, f"ClusterRole/gitops-deployer wildcard permissions: {wildcards}"

    # 3. Deployment/ai-incident-commander uses dedicated SA and defines memory limit
    commander_deps = [
        d for d in vinhthang_fleet_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "ai-incident-commander"
    ]
    assert len(commander_deps) == 1, "Expected Deployment/ai-incident-commander"
    cmd_pod_spec = commander_deps[0]["spec"]["template"]["spec"]
    assert cmd_pod_spec.get("serviceAccountName") == "ai-incident-commander", (
        f"Expected serviceAccountName 'ai-incident-commander', got {cmd_pod_spec.get('serviceAccountName')!r}"
    )
    cmd_limits = ((cmd_pod_spec["containers"][0].get("resources") or {}).get("limits") or {})
    assert cmd_limits.get("memory"), "Deployment/ai-incident-commander must define resources.limits.memory"

    # 4. Deployment/anythingllm memory limit matches values.yaml (not hardcoded 3072Mi)
    fleet_values = load_chart_values("vinhthang-fleet")
    expected_anythingllm_mem = fleet_values["anythingllm"]["resources"]["limits"]["memory"]
    anythingllm_deps = [
        d for d in vinhthang_fleet_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "anythingllm"
    ]
    assert len(anythingllm_deps) == 1, "Expected Deployment/anythingllm"
    actual_anythingllm_mem = (
        anythingllm_deps[0]["spec"]["template"]["spec"]["containers"][0]
        .get("resources", {})
        .get("limits", {})
        .get("memory")
    )
    assert actual_anythingllm_mem == expected_anythingllm_mem, (
        f"Deployment/anythingllm memory limit {actual_anythingllm_mem!r} != values.yaml {expected_anythingllm_mem!r}"
    )

    # 5. Service/filebrowser is NodePort with nodePort == 30002
    fb_svcs = [
        d for d in vinhthang_fleet_docs
        if d.get("kind") == "Service" and (d.get("metadata") or {}).get("name") == "filebrowser"
    ]
    assert len(fb_svcs) == 1, "Expected Service/filebrowser"
    fb_spec = fb_svcs[0]["spec"]
    assert fb_spec.get("type") == "NodePort", f"Service/filebrowser type expected 'NodePort', got {fb_spec.get('type')!r}"
    fb_node_ports = [p.get("nodePort") for p in (fb_spec.get("ports") or [])]
    assert 30002 in fb_node_ports, f"Service/filebrowser expected nodePort 30002, got {fb_node_ports}"

    # 6. vinhthang-fleet/templates/ directory organization
    templates_dir = CHARTS_DIR / "vinhthang-fleet" / "templates"
    expected_dirs = {"ai", "apps", "data", "observability", "operators", "system"}
    actual_dirs = {p.name for p in templates_dir.iterdir() if p.is_dir()}
    assert expected_dirs.issubset(actual_dirs), (
        f"Missing template domain subdirectories: {sorted(expected_dirs - actual_dirs)}"
    )
    assert (templates_dir / "namespaces.yaml").is_file(), "Expected templates/namespaces.yaml at templates root"
    loose_root_yaml = [
        p.name for p in templates_dir.glob("*.yaml")
        if p.name != "namespaces.yaml"
    ]
    assert not loose_root_yaml, f"Loose workload YAML files at templates/ root: {loose_root_yaml}"

    # 7. vedge-api-local db-init-job quotes "$db" and deployment.yaml defines readinessProbe
    db_init_text = (CHARTS_DIR / "vedge-api-local" / "templates" / "db-init-job.yaml").read_text(encoding="utf-8")
    assert '"$db"' in db_init_text, "vedge-api-local db-init-job.yaml must quote \"$db\" in CREATE DATABASE"
    vedge_deploy_text = (CHARTS_DIR / "vedge-api-local" / "templates" / "deployment.yaml").read_text(encoding="utf-8")
    assert "readinessProbe:" in vedge_deploy_text, "vedge-api-local deployment.yaml must define readinessProbe"


def test_grafana_ingress_5xx_alert_uses_real_caddy_metric_and_preserves_labels(
    vinhthang_fleet_default_docs: list[dict[str, Any]],
) -> None:
    alert_cms = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "ConfigMap" and (d.get("metadata") or {}).get("name") == "grafana-alert-rules"
    ]
    assert len(alert_cms) == 1, "Expected ConfigMap/grafana-alert-rules"

    rules_data = yaml.safe_load(alert_cms[0]["data"]["rules.yaml"])
    ingress_rules = [
        rule
        for group in rules_data.get("groups") or []
        for rule in group.get("rules") or []
        if rule.get("uid") == "ingress_5xx_error"
    ]
    assert len(ingress_rules) == 1, "Expected ingress_5xx_error alert rule"
    rule = ingress_rules[0]

    model_a = next((d["model"] for d in rule["data"] if d.get("refId") == "A"), {})
    expr = model_a.get("expr", "")
    assert "caddy_http_response_status_count_total" not in expr, (
        f"ingress_5xx_error still uses nonexistent metric: {expr}"
    )
    assert "caddy_http_request_duration_seconds_count" in expr, (
        f"ingress_5xx_error must query caddy_http_request_duration_seconds_count: {expr}"
    )
    assert 'code=~"5.."' in expr, f"ingress_5xx_error must filter code=~\"5..\": {expr}"
    assert "sum by (host, instance, code)" in expr, (
        f"ingress_5xx_error must preserve host, instance, and code labels: {expr}"
    )

    desc = (rule.get("annotations") or {}).get("description", "")
    for label_ref in ("$labels.host", "$labels.instance", "$labels.code"):
        assert label_ref in desc, (
            f"ingress_5xx_error description must reference {label_ref}: {desc}"
        )


def test_ai_commander_hardening_and_grafana_webhook_auth(
    vinhthang_fleet_default_docs: list[dict[str, Any]],
) -> None:
    # 1. deploy.yaml triggers CI on pull_request to main
    deploy_wf = yaml.safe_load(
        (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "deploy.yaml").read_text(encoding="utf-8")
    )
    # Note: PyYAML parses unquoted `on:` as boolean True
    on_block = deploy_wf.get(True) or deploy_wf.get("on") or {}
    pr_block = on_block.get("pull_request") or {}
    assert "main" in (pr_block.get("branches") or []), (
        f".github/workflows/deploy.yaml must trigger pull_request CI on main, got: {on_block}"
    )

    # 2. Deployment/ai-incident-commander hardening
    commander_deps = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "ai-incident-commander"
    ]
    assert len(commander_deps) == 1, "Expected Deployment/ai-incident-commander"
    pod_spec = commander_deps[0]["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]

    # Memory limit >= 1 GiB (1536Mi expected)
    mem_limit = ((container.get("resources") or {}).get("limits") or {}).get("memory", "")
    assert mem_limit.endswith("Mi") and int(mem_limit[:-2]) >= 1024, (
        f"ai-incident-commander memory limit must be >= 1024Mi, got {mem_limit!r}"
    )

    # Env vars: OTLP endpoint, AGY_MODEL, AGY_HOST_AUTH_DIR, WEBHOOK_AUTH_TOKEN, no GEMINI_API_KEY
    env_map = {e.get("name"): e for e in (container.get("env") or [])}
    assert "GEMINI_API_KEY" not in env_map, "Unused GEMINI_API_KEY env var should be removed"
    assert env_map.get("OTEL_EXPORTER_OTLP_ENDPOINT", {}).get("value") == "otel-collector.observability.svc.cluster.local:4317"
    assert env_map.get("AGY_MODEL", {}).get("value") == "gemini-3.8-flash-medium"
    assert env_map.get("AGY_HOST_AUTH_DIR", {}).get("value") == "/mnt/host-gemini-cli"
    webhook_secret_ref = (env_map.get("WEBHOOK_AUTH_TOKEN") or {}).get("valueFrom", {}).get("secretKeyRef", {})
    assert webhook_secret_ref.get("name") == "ai-commander-webhook-secret"
    assert webhook_secret_ref.get("key") == "WEBHOOK_AUTH_TOKEN"

    # Probes: HTTP GET /healthz instead of TCP socket
    for probe_name in ("livenessProbe", "readinessProbe"):
        probe = container.get(probe_name) or {}
        http_get = probe.get("httpGet") or {}
        assert http_get.get("path") == "/healthz", (
            f"{probe_name} must use HTTP GET /healthz, got: {probe}"
        )

    # Volumes & mounts: host auth mounted read-only at /mnt/host-gemini-cli, /root/.gemini is emptyDir
    vol_map = {v.get("name"): v for v in (pod_spec.get("volumes") or [])}
    mount_map = {m.get("name"): m for m in (container.get("volumeMounts") or [])}

    auth_mount = next((m for m in mount_map.values() if m.get("mountPath") == "/mnt/host-gemini-cli"), None)
    assert auth_mount is not None, "Expected read-only host auth mount at /mnt/host-gemini-cli"
    assert auth_mount.get("readOnly") is True, "/mnt/host-gemini-cli must be mounted readOnly: true"
    auth_vol = vol_map.get(auth_mount["name"], {})
    assert (auth_vol.get("hostPath") or {}).get("path") == "/home/opc/.gemini/antigravity-cli"

    runtime_mount = next((m for m in mount_map.values() if m.get("mountPath") == "/root/.gemini"), None)
    assert runtime_mount is not None, "Expected ephemeral emptyDir mount at /root/.gemini"
    assert "emptyDir" in vol_map.get(runtime_mount["name"], {}), "/root/.gemini must use emptyDir, not hostPath"

    # 3. Grafana Deployment & alerting contact point Bearer auth
    grafana_deps = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "grafana"
    ]
    assert len(grafana_deps) == 1, "Expected Deployment/grafana"
    gf_env = {e.get("name"): e for e in (grafana_deps[0]["spec"]["template"]["spec"]["containers"][0].get("env") or [])}
    gf_secret_ref = (gf_env.get("AI_COMMANDER_WEBHOOK_TOKEN") or {}).get("valueFrom", {}).get("secretKeyRef", {})
    assert gf_secret_ref.get("name") == "ai-commander-webhook-secret"
    assert gf_secret_ref.get("key") == "WEBHOOK_AUTH_TOKEN"

    alerting_cms = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "ConfigMap" and (d.get("metadata") or {}).get("name") == "grafana-alerting"
    ]
    assert len(alerting_cms) == 1, "Expected ConfigMap/grafana-alerting"
    alerting_data = yaml.safe_load(alerting_cms[0]["data"]["alerting.yaml"])
    settings = alerting_data["contactPoints"][0]["receivers"][0]["settings"]
    assert settings.get("authorization_scheme") == "Bearer"
    assert settings.get("authorization_credentials") == "${AI_COMMANDER_WEBHOOK_TOKEN}"

    # 4. Retained secret template renders in both system and observability with keep policy when enabled
    proc = subprocess.run(
        [
            "helm",
            "template",
            "test",
            str(CHARTS_DIR / "vinhthang-fleet"),
            "--set",
            "aiIncidentCommander.createWebhookSecret=true",
            "--set",
            "aiIncidentCommander.webhookToken=test-only-placeholder",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rendered_with_secret = [d for d in yaml.safe_load_all(proc.stdout) if isinstance(d, dict)]
    webhook_secrets = [
        d for d in rendered_with_secret
        if d.get("kind") == "Secret" and (d.get("metadata") or {}).get("name") == "ai-commander-webhook-secret"
    ]
    assert {(d.get("metadata") or {}).get("namespace") for d in webhook_secrets} == {"system", "observability"}
    for sec in webhook_secrets:
        anns = (sec.get("metadata") or {}).get("annotations") or {}
        assert anns.get("helm.sh/resource-policy") == "keep"


def test_ai_commander_v050_soak_human_gate_and_daily_report_cronjob(
    vinhthang_fleet_default_docs: list[dict[str, Any]],
) -> None:
    # 1. Deployment env vars for diagnostic soak, human-gated PRs, VictoriaMetrics, and Memos DB
    commander_deps = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "ai-incident-commander"
    ]
    assert len(commander_deps) == 1, "Expected Deployment/ai-incident-commander"
    env_map = {
        e.get("name"): e.get("value")
        for e in (commander_deps[0]["spec"]["template"]["spec"]["containers"][0].get("env") or [])
    }
    assert env_map.get("SOAK_DURATION") == "60s"
    assert env_map.get("AUTO_MERGE") == "false"
    assert env_map.get("VICTORIAMETRICS_URL") == "http://victoriametrics.observability.svc.cluster.local:8428"
    memos_dsn = env_map.get("MEMOS_DB_DSN") or ""
    assert "$(POSTGRES_PASSWORD)" in memos_dsn and "/memos" in memos_dsn, (
        f"MEMOS_DB_DSN must reference $(POSTGRES_PASSWORD) and /memos, got {memos_dsn!r}"
    )

    # 2. ClusterRole/ai-incident-commander-reader must retain zero Secret permissions
    roles = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "ClusterRole" and (d.get("metadata") or {}).get("name") == "ai-incident-commander-reader"
    ]
    assert len(roles) == 1, "Expected ClusterRole/ai-incident-commander-reader"
    for idx, rule in enumerate(roles[0].get("rules") or []):
        assert "secrets" not in (rule.get("resources") or []), (
            f"ClusterRole/ai-incident-commander-reader rule[{idx}] must NOT grant access to secrets"
        )

    # 3. CronJob/ai-commander-daily-report triggers POST /daily-report at 15 0 * * *
    cronjobs = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "CronJob" and (d.get("metadata") or {}).get("name") == "ai-commander-daily-report"
    ]
    assert len(cronjobs) == 1, "Expected CronJob/ai-commander-daily-report in system namespace"
    cj = cronjobs[0]
    assert (cj.get("metadata") or {}).get("namespace") == "system"
    cj_spec = cj["spec"]
    assert cj_spec.get("schedule") == "15 0 * * *"
    assert cj_spec.get("concurrencyPolicy") == "Forbid"

    pod_spec = cj_spec["jobTemplate"]["spec"]["template"]["spec"]
    assert (pod_spec.get("nodeSelector") or {}).get("kubernetes.io/hostname") == "arm10"
    container = pod_spec["containers"][0]
    assert _is_pinned_image(container.get("image", ""))
    cj_env = {e.get("name"): e for e in (container.get("env") or [])}
    token_ref = (cj_env.get("WEBHOOK_AUTH_TOKEN") or {}).get("valueFrom", {}).get("secretKeyRef", {})
    assert token_ref.get("name") == "ai-commander-webhook-secret"
    assert token_ref.get("key") == "WEBHOOK_AUTH_TOKEN"
    joined_args = " ".join(container.get("command") or []) + " " + " ".join(container.get("args") or [])
    assert "/daily-report" in joined_args, f"CronJob must POST /daily-report, got cmd={joined_args!r}"
    assert "-sS --fail-with-body" in joined_args, (
        f"CronJob curl must use -sS --fail-with-body, got cmd={joined_args!r}"
    )
    assert "-fsS --fail-with-body" not in joined_args, (
        f"CronJob curl must NOT combine -f/-fsS with --fail-with-body, got cmd={joined_args!r}"
    )


def test_forgejo_deployment_secret_hygiene_and_backup(
    vinhthang_fleet_default_docs: list[dict[str, Any]],
) -> None:
    # 1. Deployment/forgejo invariants
    forgejo_deps = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "Deployment" and (d.get("metadata") or {}).get("name") == "forgejo"
    ]
    assert len(forgejo_deps) == 1, "Expected Deployment/forgejo"
    dep = forgejo_deps[0]
    assert (dep.get("metadata") or {}).get("namespace") == "apps"
    assert (dep.get("spec") or {}).get("strategy", {}).get("type") == "Recreate"

    pod_spec = dep["spec"]["template"]["spec"]
    assert (pod_spec.get("nodeSelector") or {}).get("kubernetes.io/hostname") == "arm10"

    init_map = {c.get("name"): c for c in (pod_spec.get("initContainers") or [])}
    assert "init-permissions" in init_map, "Deployment/forgejo must include init-permissions initContainer"
    perm_cmd = " ".join(init_map["init-permissions"].get("command") or []) + " " + " ".join(init_map["init-permissions"].get("args") or [])
    assert "1000:1000" in perm_cmd and "/var/lib/gitea" in perm_cmd and "/etc/gitea" in perm_cmd

    assert "init-postgres-db" in init_map, "Deployment/forgejo must include init-postgres-db initContainer"
    db_cmd = " ".join(init_map["init-postgres-db"].get("command") or []) + " " + " ".join(init_map["init-postgres-db"].get("args") or [])
    assert "postgres-primary.data.svc.cluster.local" in db_cmd and "forgejo" in db_cmd

    containers = pod_spec.get("containers") or []
    assert len(containers) == 1
    c = containers[0]
    assert c.get("image") == "codeberg.org/forgejo/forgejo:17.0.2-rootless"
    sec_ctx = c.get("securityContext") or {}
    assert sec_ctx.get("runAsUser") == 1000 and sec_ctx.get("runAsGroup") == 1000

    cports = {p.get("name"): p.get("containerPort") for p in (c.get("ports") or [])}
    assert cports == {"http": 3000}, f"Forgejo must expose HTTP 3000 only (DISABLE_SSH=true), got {cports!r}"
    assert 8080 not in cports.values()

    res = c.get("resources") or {}
    assert (res.get("limits") or {}).get("memory") == "512Mi"
    assert (res.get("requests") or {}).get("memory") == "128Mi"

    env_map = {e.get("name"): e for e in (c.get("env") or [])}
    expected_env = {
        "FORGEJO__server__DOMAIN": "git.vinhthang.dev",
        "FORGEJO__server__ROOT_URL": "https://git.vinhthang.dev/",
        "FORGEJO__server__HTTP_PORT": "3000",
        "FORGEJO__server__DISABLE_SSH": "true",
        "FORGEJO__database__DB_TYPE": "postgres",
        "FORGEJO__database__NAME": "forgejo",
        "FORGEJO__security__INSTALL_LOCK": "true",
        "FORGEJO__service__DISABLE_REGISTRATION": "true",
        "FORGEJO__service__REQUIRE_SIGNIN_VIEW": "true",
        "FORGEJO__repository__DEFAULT_MERGE_STYLE": "squash",
        "FORGEJO__actions__ENABLED": "true",
    }
    for key, val in expected_env.items():
        assert (env_map.get(key) or {}).get("value") == val, f"Expected env {key}={val!r}, got {env_map.get(key)!r}"

    for probe_name in ("livenessProbe", "readinessProbe"):
        http_get = (c.get(probe_name) or {}).get("httpGet") or {}
        assert http_get.get("path") == "/api/healthz", f"{probe_name} must target /api/healthz"
        assert http_get.get("port") == "http", f"{probe_name} must target port 'http'"

    # 2. Service/forgejo NodePort 30017
    forgejo_svcs = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "Service" and (d.get("metadata") or {}).get("name") == "forgejo"
    ]
    assert len(forgejo_svcs) == 1, "Expected Service/forgejo"
    svc = forgejo_svcs[0]
    assert (svc.get("metadata") or {}).get("namespace") == "apps"
    assert (svc.get("spec") or {}).get("type") == "NodePort"
    svc_ports = svc["spec"].get("ports") or []
    assert len(svc_ports) == 1, f"Service/forgejo must expose HTTP 3000 -> 30017 only, got {svc_ports!r}"
    http_port = next((p for p in svc_ports if p.get("port") == 3000), None)
    assert http_port is not None
    assert http_port.get("targetPort") == 3000
    assert http_port.get("nodePort") == 30017

    # 3. Retained Secret renders only when forgejo.createSecret=true with keep policy
    proc = subprocess.run(
        [
            "helm",
            "template",
            "test",
            str(CHARTS_DIR / "vinhthang-fleet"),
            "--set",
            "forgejo.createSecret=true",
            "--set",
            "forgejo.adminPassword=test-only-pw",
            "--set",
            "forgejo.secretKey=test-only-sk",
            "--set",
            "forgejo.internalToken=test-only-it",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rendered_with_secret = [d for d in yaml.safe_load_all(proc.stdout) if isinstance(d, dict)]
    forgejo_secrets = [
        d for d in rendered_with_secret
        if d.get("kind") == "Secret" and (d.get("metadata") or {}).get("name") == "forgejo-secrets"
    ]
    assert len(forgejo_secrets) == 1
    assert (forgejo_secrets[0].get("metadata") or {}).get("namespace") == "apps"
    anns = (forgejo_secrets[0].get("metadata") or {}).get("annotations") or {}
    assert anns.get("helm.sh/resource-policy") == "keep"

    # 4. CronJob/nightly-fleet-backup includes /opt/forgejo (custom + gitea data) read-only
    backup_jobs = [
        d for d in vinhthang_fleet_default_docs
        if d.get("kind") == "CronJob" and (d.get("metadata") or {}).get("name") == "nightly-fleet-backup"
    ]
    assert len(backup_jobs) == 1
    b_pod = backup_jobs[0]["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    b_c = b_pod["containers"][0]
    b_mounts = {m.get("mountPath"): m for m in (b_c.get("volumeMounts") or [])}
    assert "/backup-src/forgejo" in b_mounts and b_mounts["/backup-src/forgejo"].get("readOnly") is True
    b_vols = {v.get("name"): v for v in (b_pod.get("volumes") or [])}
    forgejo_vol = b_vols.get(b_mounts["/backup-src/forgejo"]["name"], {})
    assert (forgejo_vol.get("hostPath") or {}).get("path") == "/opt/forgejo"
    b_script = " ".join(b_c.get("command") or []) + " " + " ".join(b_c.get("args") or [])
    assert "forgejo" in b_script

    # 5. scripts/gitops-sync.sh deploys with --no-hooks so Helm does not re-run install hooks on fleet upgrades
    sync_script = (CHARTS_DIR.parent / "scripts" / "gitops-sync.sh").read_text(encoding="utf-8")
    helm_lines = [ln for ln in sync_script.splitlines() if "helm upgrade" in ln]
    assert helm_lines and all("--no-hooks" in ln for ln in helm_lines), (
        f"Expected --no-hooks on helm upgrade in scripts/gitops-sync.sh, got {helm_lines!r}"
    )
