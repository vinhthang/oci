"""Unit and HTTP handler tests for charts/vinhthang-fleet/files/receiver.py."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from conftest import CHARTS_DIR, REPO_ROOT

RECEIVER_PATH = CHARTS_DIR / "vinhthang-fleet" / "files" / "receiver.py"
VALUES_PATH = CHARTS_DIR / "vinhthang-fleet" / "values.yaml"


def _load_receiver() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gitops_receiver_under_test", RECEIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sign(secret: bytes, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()


def test_verify_hmac_signature() -> None:
    mod = _load_receiver()
    secret = b"super-webhook-secret"
    body = b'{"ref":"refs/heads/main"}'

    assert mod.verify_hmac_signature(b"", body, _sign(secret, body)) == (
        False,
        503,
        "Webhook secret not configured\n",
    )
    assert mod.verify_hmac_signature(secret, body, "")[0:2] == (False, 401)
    assert mod.verify_hmac_signature(secret, body, "sha1=deadbeef")[0:2] == (False, 401)
    assert mod.verify_hmac_signature(secret, body, "sha256=" + "0" * 64)[0:2] == (False, 403)
    assert mod.verify_hmac_signature(secret, body, _sign(secret, body)) == (True, 200, "OK")


def test_verify_bearer_or_hmac() -> None:
    mod = _load_receiver()
    secret = b"super-webhook-secret"
    body = b'{"service":"vietcalendar"}'

    assert mod.verify_bearer_or_hmac(b"", body, {"Authorization": "Bearer x"})[0:2] == (False, 503)
    assert mod.verify_bearer_or_hmac(secret, body, {})[0:2] == (False, 401)
    assert mod.verify_bearer_or_hmac(secret, body, {"Authorization": "Bearer wrong"})[0:2] == (
        False,
        403,
    )
    assert mod.verify_bearer_or_hmac(
        secret, body, {"Authorization": "Bearer super-webhook-secret"}
    ) == (True, 200, "OK")
    assert mod.verify_bearer_or_hmac(
        secret, body, {"X-Hub-Signature-256": _sign(secret, body)}
    ) == (True, 200, "OK")


def test_parse_github_webhook_ping_push_and_package_events() -> None:
    mod = _load_receiver()

    assert mod.parse_github_webhook("ping", {}) == (200, "Pong\n", None)

    code, _, job = mod.parse_github_webhook(
        "push",
        {"ref": "refs/heads/main", "repository": {"full_name": "vinhthang/oci"}},
    )
    assert code == 200 and job == {"kind": "gitops_sync"}

    code, _, job = mod.parse_github_webhook(
        "push",
        {"ref": "refs/heads/feature", "repository": {"full_name": "vinhthang/oci"}},
    )
    assert code == 200 and job is None

    code, _, job = mod.parse_github_webhook(
        "push",
        {"ref": "refs/heads/main", "repository": {"full_name": "vinhthang/vietcalendar"}},
    )
    assert code == 200 and job is None

    sha = "a" * 64
    pkg_payload = {
        "action": "published",
        "package": {
            "name": "collab-mcp",
            "package_type": "container",
            "owner": {"login": "vinhthang"},
            "package_version": {
                "version": f"sha256:{sha}",
                "container_metadata": {"tag": {"name": "v0.5.2"}},
            },
        },
    }
    code, _, job = mod.parse_github_webhook("package", pkg_payload)
    assert code == 200
    assert job == {
        "kind": "image_rollout",
        "source": "github_package",
        "service": "collab-mcp",
        "tag": "v0.5.2",
        "digest": f"sha256:{sha}",
    }

    reg_payload = {
        "action": "updated",
        "registry_package": {
            "name": "vinhthang/vietcalendar",
            "package_type": "CONTAINER",
            "owner": {"login": "vinhthang"},
            "package_version": {
                "name": f"sha256:{sha}",
                "container_metadata": {"tag": {"name": "latest"}},
            },
        },
    }
    code, _, job = mod.parse_github_webhook("registry_package", reg_payload)
    assert code == 200
    assert job == {
        "kind": "image_rollout",
        "source": "github_package",
        "service": "vietcalendar",
        "tag": "latest",
        "digest": f"sha256:{sha}",
    }

    # Ignored cases: non-allowlisted package, foreign owner, non-published action
    ignored_pkg = {
        "action": "published",
        "package": {
            "name": "postgres",
            "package_type": "container",
            "owner": {"login": "vinhthang"},
            "package_version": {"container_metadata": {"tag": {"name": "18"}}},
        },
    }
    assert mod.parse_github_webhook("package", ignored_pkg)[2] is None

    foreign_pkg = {
        "action": "published",
        "package": {
            "name": "vietcalendar",
            "package_type": "container",
            "owner": {"login": "attacker"},
            "package_version": {"container_metadata": {"tag": {"name": "latest"}}},
        },
    }
    assert mod.parse_github_webhook("package", foreign_pkg)[2] is None

    deleted_pkg = {**pkg_payload, "action": "deleted"}
    assert mod.parse_github_webhook("package", deleted_pkg)[2] is None

    # Malformed tag rejected with 400
    bad_tag_pkg = {
        "action": "published",
        "package": {
            "name": "collab-mcp",
            "package_type": "container",
            "owner": {"login": "vinhthang"},
            "package_version": {"container_metadata": {"tag": {"name": "v1; rm -rf /"}}},
        },
    }
    assert mod.parse_github_webhook("package", bad_tag_pkg)[0] == 400


def test_parse_deploy_request_allowlist_and_validation() -> None:
    mod = _load_receiver()

    for svc in (
        "vietcalendar",
        "collab-mcp",
        "review-server",
        "attention-metrics-server",
        "ai-incident-commander",
    ):
        code, _, job = mod.parse_deploy_request({"service": svc})
        assert code == 200
        assert job == {
            "kind": "image_rollout",
            "source": "deploy_api",
            "service": svc,
            "tag": "",
            "digest": "",
        }

    assert mod.parse_deploy_request({"service": "postgres"})[0] == 400
    assert mod.parse_deploy_request({})[0] == 400
    assert mod.parse_deploy_request({"service": "collab-mcp", "tag": "v1;id"})[0] == 400
    assert mod.parse_deploy_request({"service": "collab-mcp", "digest": "sha256:short"})[0] == 400

    sha = "b" * 64
    code, _, job = mod.parse_deploy_request(
        {"service": "review-server", "tag": "v1.0.2", "digest": f"sha256:{sha}"}
    )
    assert code == 200 and job["tag"] == "v1.0.2" and job["digest"] == f"sha256:{sha}"


def test_read_baseline_service_images_from_repo_values() -> None:
    mod = _load_receiver()
    baselines = mod.read_baseline_service_images(VALUES_PATH)
    assert set(baselines.keys()) == {
        "vietcalendar",
        "collab-mcp",
        "review-server",
        "attention-metrics-server",
        "ai-incident-commander",
    }
    assert baselines["vietcalendar"] == "ghcr.io/vinhthang/vietcalendar:latest"
    assert baselines["collab-mcp"].startswith("ghcr.io/vinhthang/collab-mcp:")
    assert baselines["review-server"].startswith("ghcr.io/vinhthang/review-server:")
    assert baselines["attention-metrics-server"].startswith(
        "ghcr.io/vinhthang/attention-metrics-server:"
    )
    assert baselines["ai-incident-commander"].startswith(
        "ghcr.io/vinhthang/ai-incident-commander@"
    )


def test_read_baseline_service_images_handles_quotes_comments_and_sibling_keys(
    tmp_path: Path,
) -> None:
    mod = _load_receiver()
    sample = tmp_path / "values.yaml"
    sample.write_text(
        """
vietcalendar:
  image: 'ghcr.io/vinhthang/vietcalendar:1' # single quoted with comment
collabMcp:
  image:
    repository: "ghcr.io/vinhthang/collab-mcp"
    tag: 'v0.5#1' # hash inside single quotes must be preserved
    digest: ""
  tag: sibling-at-same-indent-must-exit-image-map
reviewServer:
  image:
    repository: ghcr.io/vinhthang/review-server
    tag: "v1.0#2" # hash inside double quotes must be preserved
    digest: ''
  nodeSelector: arm10
attentionMetricsServer:
  image:
    repository: ghcr.io/vinhthang/attention-metrics-server
    tag: 9
aiIncidentCommander:
  image:
    repository: ghcr.io/vinhthang/ai-incident-commander
    tag: 0.5.2
    digest: sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
""",
        encoding="utf-8",
    )
    baselines = mod.read_baseline_service_images(sample)
    assert baselines["vietcalendar"] == "ghcr.io/vinhthang/vietcalendar:1"
    assert baselines["collab-mcp"] == "ghcr.io/vinhthang/collab-mcp:v0.5#1"
    assert baselines["review-server"] == "ghcr.io/vinhthang/review-server:v1.0#2"
    assert baselines["attention-metrics-server"] == "ghcr.io/vinhthang/attention-metrics-server:9"
    assert (
        baselines["ai-incident-commander"]
        == "ghcr.io/vinhthang/ai-incident-commander@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    assert mod._strip_yaml_scalar("'") == "'"


def test_compute_service_override_and_gitops_reconciliation() -> None:
    mod = _load_receiver()
    sha = "c" * 64
    ts = "2026-11-23T04:00:00Z"

    # 1. vietcalendar (:latest baseline) keeps :latest + Always + rolloutTimestamp
    ov_vc = mod.compute_service_override(
        "vietcalendar",
        "ghcr.io/vinhthang/vietcalendar:latest",
        "latest",
        f"sha256:{sha}",
        "github_package",
        ts,
    )
    assert ov_vc["baseline_git_image"] == "ghcr.io/vinhthang/vietcalendar:latest"
    assert ov_vc["values"] == {
        "image": "ghcr.io/vinhthang/vietcalendar:latest",
        "imagePullPolicy": "Always",
        "rolloutTimestamp": ts,
    }

    # 2. Explicit tag on collab-mcp clears digest and bumps tag
    ov_cm = mod.compute_service_override(
        "collab-mcp",
        "ghcr.io/vinhthang/collab-mcp:v0.5.1",
        "v0.5.2",
        f"sha256:{sha}",
        "deploy_api",
        ts,
    )
    assert ov_cm["values"] == {
        "image": {"tag": "v0.5.2", "digest": ""},
        "rolloutTimestamp": ts,
    }

    # 3. GitHub package :latest on pinned map service pins digest directly
    ov_am = mod.compute_service_override(
        "attention-metrics-server",
        "ghcr.io/vinhthang/attention-metrics-server:914b6fa",
        "latest",
        f"sha256:{sha}",
        "github_package",
        ts,
    )
    assert ov_am["values"] == {
        "image": {"digest": f"sha256:{sha}"},
        "rolloutTimestamp": ts,
    }

    # 4. Explicit deploy_api tag="latest" on review-server sets latest + pullPolicy Always
    ov_rs = mod.compute_service_override(
        "review-server",
        "ghcr.io/vinhthang/review-server:v1.0.1",
        "latest",
        "",
        "deploy_api",
        ts,
    )
    assert ov_rs["values"] == {
        "image": {"tag": "latest", "digest": "", "pullPolicy": "Always"},
        "rolloutTimestamp": ts,
    }

    # 5. Smart reconciliation drops override when Git values.yaml changed that service, preserves untouched ones
    state = {"overrides": {"collab-mcp": ov_cm, "vietcalendar": ov_vc}}
    new_baselines = {
        "vietcalendar": "ghcr.io/vinhthang/vietcalendar:latest",
        "collab-mcp": "ghcr.io/vinhthang/collab-mcp:v0.5.3",
    }
    reconciled = mod.reconcile_state_on_gitops_push(state, new_baselines)
    assert "collab-mcp" not in reconciled["overrides"]
    assert "vietcalendar" in reconciled["overrides"]

    rendered = mod.render_helm_overrides(reconciled["overrides"])
    assert rendered == {"vietcalendar": ov_vc["values"]}

    cmd = mod.build_helm_upgrade_cmd("/tmp/repo/charts/vinhthang-fleet", "/tmp/overrides.yaml")
    assert cmd == [
        "helm",
        "upgrade",
        "--install",
        "fleet",
        "/tmp/repo/charts/vinhthang-fleet",
        "-n",
        "default",
        "--no-hooks",
        "--reset-values",
        "-f",
        "/tmp/overrides.yaml",
    ]
    assert mod.build_helm_upgrade_cmd("/tmp/repo/charts/vinhthang-fleet", None) == [
        "helm",
        "upgrade",
        "--install",
        "fleet",
        "/tmp/repo/charts/vinhthang-fleet",
        "-n",
        "default",
        "--no-hooks",
        "--reset-values",
    ]


def test_run_reconcile_job_executes_git_helm_and_edge_sync(tmp_path: Path) -> None:
    mod = _load_receiver()
    clone_dir = tmp_path / "repo"
    state_path = tmp_path / "state.json"
    commands: list[list[str]] = []

    class _FakeProc:
        def __init__(self, returncode: int = 0, stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = stderr

    def fake_run(cmd: list[str], **kwargs: Any) -> _FakeProc:
        commands.append(cmd)
        if cmd[:2] == ["git", "clone"]:
            chart_dir = Path(cmd[-1]) / "charts" / "vinhthang-fleet"
            chart_dir.mkdir(parents=True, exist_ok=True)
            (chart_dir / "values.yaml").write_text(
                VALUES_PATH.read_text(encoding="utf-8"), encoding="utf-8"
            )
        return _FakeProc(0)

    state = mod.run_reconcile_job(
        {
            "kind": "image_rollout",
            "source": "deploy_api",
            "service": "collab-mcp",
            "tag": "v0.5.9",
            "digest": "",
        },
        state_path=state_path,
        repo_url="https://github.com/vinhthang/oci.git",
        clone_dir=clone_dir,
        edge_sync_url="http://10.0.0.235:8999/",
        run_cmd=fake_run,
        now_fn=lambda: "2026-11-23T04:10:00Z",
    )

    assert state["overrides"]["collab-mcp"]["values"]["image"]["tag"] == "v0.5.9"
    assert state_path.is_file()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert saved == state
    # image_rollout must run git clone and helm upgrade --reset-values -f ..., NOT edge_sync_url curl
    assert commands[0][:2] == ["git", "clone"]
    assert commands[1][:4] == ["helm", "upgrade", "--install", "fleet"]
    assert "--reset-values" in commands[1] and "-f" in commands[1]
    assert len(commands) == 2

    # gitops_sync runs edge sync curl as 3rd command
    commands.clear()
    mod.run_reconcile_job(
        {"kind": "gitops_sync"},
        state_path=state_path,
        repo_url="https://github.com/vinhthang/oci.git",
        clone_dir=clone_dir,
        edge_sync_url="http://10.0.0.235:8999/",
        run_cmd=fake_run,
        now_fn=lambda: "2026-11-23T04:12:00Z",
    )
    assert len(commands) == 3 and commands[2] == [
        "curl",
        "-fsS",
        "-X",
        "POST",
        "http://10.0.0.235:8999/",
    ]

    # Non-zero helm command raises RuntimeError (fail-fast ADR-0017)
    def failing_run(cmd: list[str], **kwargs: Any) -> _FakeProc:
        fake_run(cmd, **kwargs)
        if cmd[0] == "helm":
            return _FakeProc(1, "helm error")
        return _FakeProc(0)

    with pytest.raises(RuntimeError, match="helm"):
        mod.run_reconcile_job(
            {"kind": "gitops_sync"},
            state_path=state_path,
            repo_url="https://github.com/vinhthang/oci.git",
            clone_dir=clone_dir,
            edge_sync_url="http://10.0.0.235:8999/",
            run_cmd=failing_run,
            now_fn=lambda: "2026-11-23T04:15:00Z",
        )


def test_http_handler_routes_auth_and_size_limits() -> None:
    mod = _load_receiver()
    secret = b"test-secret-123"
    enqueued: list[dict[str, Any]] = []
    handler_cls = mod.create_webhook_app_handler(
        secret=secret,
        enqueue_job=enqueued.append,
        max_body_bytes=256,
    )
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"

        with urllib.request.urlopen(f"{base}/healthz") as resp:
            assert resp.status == 200 and resp.read() == b"OK\n"

        head_req = urllib.request.Request(f"{base}/healthz", method="HEAD")
        with urllib.request.urlopen(head_req) as resp:
            assert resp.status == 200

        # Unauthenticated POST /webhook -> 401
        req_no_sig = urllib.request.Request(f"{base}/webhook", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req_no_sig)
        assert exc.value.code == 401

        # Invalid HMAC -> 403
        req_bad_sig = urllib.request.Request(
            f"{base}/webhook",
            data=b"{}",
            headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req_bad_sig)
        assert exc.value.code == 403

        # Valid HMAC package event -> 200 + enqueues job
        pkg_bytes = json.dumps(
            {
                "action": "published",
                "package": {
                    "name": "vietcalendar",
                    "package_type": "container",
                    "owner": {"login": "vinhthang"},
                    "package_version": {"container_metadata": {"tag": {"name": "latest"}}},
                },
            }
        ).encode("utf-8")
        req_pkg = urllib.request.Request(
            f"{base}/webhook",
            data=pkg_bytes,
            headers={
                "X-Hub-Signature-256": _sign(secret, pkg_bytes),
                "X-GitHub-Event": "package",
            },
            method="POST",
        )
        with urllib.request.urlopen(req_pkg) as resp:
            assert resp.status == 200
        assert len(enqueued) == 1 and enqueued[0]["service"] == "vietcalendar"

        # POST /deploy without auth -> 401
        req_deploy_noauth = urllib.request.Request(
            f"{base}/deploy",
            data=b'{"service":"collab-mcp"}',
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req_deploy_noauth)
        assert exc.value.code == 401

        # POST /deploy with valid Bearer -> 200 + enqueues job
        req_deploy = urllib.request.Request(
            f"{base}/deploy",
            data=b'{"service":"collab-mcp","tag":"v0.5.2"}',
            headers={"Authorization": "Bearer test-secret-123"},
            method="POST",
        )
        with urllib.request.urlopen(req_deploy) as resp:
            assert resp.status == 200
        assert len(enqueued) == 2 and enqueued[1]["tag"] == "v0.5.2"

        # Oversized body -> 413
        big_body = b'{"service":"vietcalendar","tag":"' + (b"a" * 300) + b'"}'
        req_big = urllib.request.Request(
            f"{base}/deploy",
            data=big_body,
            headers={"Authorization": "Bearer test-secret-123"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req_big)
        assert exc.value.code == 413
    finally:
        server.shutdown()
        server.server_close()
