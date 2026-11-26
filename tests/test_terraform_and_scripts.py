"""Architectural fitness tests for Terraform, shell scripts, and agy_proxy.py."""

from __future__ import annotations

import ast
import importlib.util
import re
import sqlite3
import subprocess
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient

from conftest import REPO_ROOT


def _extract_hcl_resource_block(text: str, resource_type: str, resource_name: str | None = None) -> str:
    if resource_name is not None:
        pattern = re.compile(
            rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"\s*\{{'
        )
    else:
        pattern = re.compile(rf'resource\s+"{re.escape(resource_type)}"\s+"[^"]+"\s*\{{')
    match = pattern.search(text)
    if not match:
        return ""
    idx = match.end()
    depth = 1
    while idx < len(text) and depth > 0:
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        idx += 1
    return text[match.start() : idx]


def _load_agy_proxy_module() -> ModuleType:
    module_path = REPO_ROOT / "scripts" / "agy_proxy.py"
    spec = importlib.util.spec_from_file_location("agy_proxy_under_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_files_and_dirs_removed() -> None:
    assert not (REPO_ROOT / "cloud-init.sh.tpl").exists(), "cloud-init.sh.tpl must be removed"
    assert not (REPO_ROOT / "k8s").exists(), "legacy k8s/ directory must be removed"
    assert not (REPO_ROOT / "pulsar").exists(), "legacy pulsar/ directory must be removed"


def test_terraform_infra_and_formatting() -> None:
    gcp_main = REPO_ROOT / "infra" / "gcp" / "main.tf"
    assert gcp_main.is_file(), "infra/gcp/main.tf must exist"
    gcp_text = gcp_main.read_text(encoding="utf-8")
    addr_block = _extract_hcl_resource_block(gcp_text, "google_compute_address")
    assert addr_block, "infra/gcp/main.tf must define google_compute_address"
    assert re.search(r'network_tier\s*=\s*"STANDARD"', addr_block), (
        "google_compute_address in infra/gcp/main.tf must enforce network_tier = \"STANDARD\""
    )
    gce_block = _extract_hcl_resource_block(gcp_text, "google_compute_instance")
    assert gce_block, "infra/gcp/main.tf must define google_compute_instance"
    assert re.search(r"prevent_destroy\s*=\s*true", gce_block), (
        "google_compute_instance in infra/gcp/main.tf must set prevent_destroy = true"
    )
    assert re.search(r"deletion_protection\s*=\s*true", gce_block), (
        "google_compute_instance in infra/gcp/main.tf must set deletion_protection = true"
    )
    assert re.search(r'network_tier\s*=\s*"STANDARD"', gce_block), (
        "google_compute_instance access_config in infra/gcp/main.tf must enforce network_tier = \"STANDARD\""
    )

    compute_text = (REPO_ROOT / "compute.tf").read_text(encoding="utf-8")
    for instance_name in ("amd10", "amd11", "arm10"):
        block = _extract_hcl_resource_block(compute_text, "oci_core_instance", instance_name)
        assert block, f"Missing oci_core_instance {instance_name!r} in compute.tf"
        assert re.search(r"preserve_boot_volume\s*=\s*true", block), (
            f"compute.tf {instance_name} must set preserve_boot_volume = true"
        )
        assert re.search(r"prevent_destroy\s*=\s*true", block), (
            f"compute.tf {instance_name} must set prevent_destroy = true"
        )

    network_text = (REPO_ROOT / "network.tf").read_text(encoding="utf-8")
    assert not re.search(r"\bmin\s*=\s*(8080|3000)\b", network_text), (
        "network.tf must not expose security list rules for min = 8080 or min = 3000"
    )

    for tf_dir in (REPO_ROOT, REPO_ROOT / "infra" / "gcp"):
        assert tf_dir.is_dir(), f"Terraform directory missing: {tf_dir}"
        proc = subprocess.run(
            ["terraform", "fmt", "-check", "-no-color"],
            cwd=tf_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, (
            f"terraform fmt -check failed in {tf_dir}:\n{proc.stdout}\n{proc.stderr}"
        )


def test_shell_scripts_syntax_and_policies() -> None:
    sh_files = sorted((REPO_ROOT / "scripts").glob("*.sh"))
    assert sh_files, "Expected shell scripts under scripts/"
    for sh_file in sh_files:
        proc = subprocess.run(
            ["bash", "-n", str(sh_file)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"bash -n failed for {sh_file.name}: {proc.stderr}"

    gitops_sync = (REPO_ROOT / "scripts" / "gitops-sync.sh").read_text(encoding="utf-8")
    assert "-n default" in gitops_sync, "scripts/gitops-sync.sh must pass '-n default'"
    assert "caddy reload" not in gitops_sync, (
        "scripts/gitops-sync.sh must not use 'caddy reload' (use 127.0.0.1:2019/load)"
    )
    assert gitops_sync.count("127.0.0.1:2019/load") >= 2, (
        "scripts/gitops-sync.sh must reload Caddy via 127.0.0.1:2019/load on both amd10 and gce10"
    )

    indexer = (REPO_ROOT / "scripts" / "trigger-gemini-indexer.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in indexer, (
        "scripts/trigger-gemini-indexer.sh must enable 'set -euo pipefail'"
    )
    assert "-n system" in indexer, (
        "scripts/trigger-gemini-indexer.sh must specify '-n system'"
    )


def test_agy_proxy_http_endpoints_and_auth(monkeypatch) -> None:
    monkeypatch.setenv("AGY_PROXY_API_KEY", "test-secret-token")
    agy_proxy = _load_agy_proxy_module()
    client = TestClient(agy_proxy.app)

    health_resp = client.get("/healthz")
    assert health_resp.status_code == 200, (
        f"GET /healthz expected 200 without auth, got {health_resp.status_code}"
    )

    unauth_resp = client.get("/v1/models")
    assert unauth_resp.status_code == 401, (
        f"GET /v1/models without Authorization expected 401, got {unauth_resp.status_code}"
    )

    auth_resp = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer test-secret-token"},
    )
    assert auth_resp.status_code == 200, (
        f"GET /v1/models with valid Bearer token expected 200, got {auth_resp.status_code}"
    )


def test_agy_proxy_discover_conversation_id(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "conversation_summaries.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE conversation_summaries (conversation_id TEXT, last_modified_time INTEGER)"
    )
    conn.execute(
        "INSERT INTO conversation_summaries VALUES ('conv-11111111', 1000)"
    )
    conn.commit()
    conn.close()

    agy_proxy = _load_agy_proxy_module()
    monkeypatch.setattr(agy_proxy, "_SUMMARIES_DB", str(db_path))

    # Same pre_id -> must return None rather than attributing the old conversation
    assert agy_proxy._discover_conversation_id("conv-11111111") is None
    # Different pre_id -> must return the new conversation ID
    assert agy_proxy._discover_conversation_id("conv-00000000") == "conv-11111111"


def test_agy_proxy_ast_no_blocking_subprocess_and_localhost_bind() -> None:
    source = (REPO_ROOT / "scripts" / "agy_proxy.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    blocking_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if (
                        isinstance(child.func.value, ast.Name)
                        and child.func.value.id == "subprocess"
                        and child.func.attr in {"run", "Popen"}
                    ):
                        blocking_calls.append(
                            f"async def {node.name} line {child.lineno}: subprocess.{child.func.attr}"
                        )

    assert not blocking_calls, (
        "Async endpoints/coroutines in agy_proxy.py must not call blocking subprocess.run/Popen:\n"
        + "\n".join(blocking_calls)
    )

    # Default bind host must be 127.0.0.1 (never unconditional 0.0.0.0)
    assert 'host="0.0.0.0"' not in source and "host='0.0.0.0'" not in source, (
        "scripts/agy_proxy.py must default bind host to 127.0.0.1, not 0.0.0.0"
    )
    assert "127.0.0.1" in source, "scripts/agy_proxy.py must default bind host to 127.0.0.1"
