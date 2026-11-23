"""In-cluster GitOps & GHCR custom service rollout webhook receiver (ADR-0060).

Runs strictly on Python 3 standard library inside alpine/k8s alongside git, helm, and curl.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping

MAX_BODY_BYTES = 1_048_576
DEFAULT_PORT = 9000
DEFAULT_REPO_URL = "https://github.com/vinhthang/oci.git"
DEFAULT_CLONE_DIR = "/tmp/vinhthang-fleet"
DEFAULT_STATE_PATH = "/var/lib/gitops-webhook/state.json"
DEFAULT_EDGE_SYNC_URL = "http://10.0.0.235:8999/"

ALLOWED_CUSTOM_SERVICES: dict[str, dict[str, str]] = {
    "vietcalendar": {"values_key": "vietcalendar", "mode": "scalar"},
    "collab-mcp": {"values_key": "collabMcp", "mode": "map"},
    "review-server": {"values_key": "reviewServer", "mode": "map"},
    "attention-metrics-server": {"values_key": "attentionMetricsServer", "mode": "map"},
    "ai-incident-commander": {"values_key": "aiIncidentCommander", "mode": "map"},
}

_TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_VALUES_KEY_TO_SERVICE = {meta["values_key"]: svc for svc, meta in ALLOWED_CUSTOM_SERVICES.items()}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strip_yaml_scalar(raw: str) -> str:
    """Strip inline YAML comments (outside quotes) and outer single/double quotes."""
    in_single = False
    in_double = False
    chars: list[str] = []
    for ch in raw:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        chars.append(ch)
    val = "".join(chars).strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in {"'", '"'}:
        return val[1:-1]
    return val


def _validate_tag_and_digest(tag: str, digest: str) -> str | None:
    if tag and not _TAG_RE.match(tag):
        return f"Invalid image tag: {tag!r}\n"
    if digest and not _DIGEST_RE.match(digest):
        return f"Invalid image digest: {digest!r}\n"
    return None


def verify_hmac_signature(secret: bytes, body: bytes, signature_header: str) -> tuple[bool, int, str]:
    """Verify GitHub X-Hub-Signature-256 HMAC-SHA256 header using constant-time compare."""
    if not secret:
        return False, 503, "Webhook secret not configured\n"
    if not signature_header.startswith("sha256="):
        return False, 401, "Missing or invalid signature header\n"
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        return False, 403, "Signature verification failed\n"
    return True, 200, "OK"


def verify_bearer_or_hmac(
    secret: bytes, body: bytes, headers: Mapping[str, str]
) -> tuple[bool, int, str]:
    """Authenticate POST /deploy via Authorization: Bearer or X-Hub-Signature-256."""
    if not secret:
        return False, 503, "Webhook secret not configured\n"

    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip().encode("utf-8")
        if not hmac.compare_digest(token, secret):
            return False, 403, "Invalid bearer token\n"
        return True, 200, "OK"

    sig_header = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256") or ""
    if sig_header:
        return verify_hmac_signature(secret, body, sig_header)

    return False, 401, "Missing authorization header or signature\n"


def parse_github_webhook(event: str, payload: dict[str, Any]) -> tuple[int, str, dict[str, Any] | None]:
    """Parse GitHub ping, main push, and GHCR package/registry_package events."""
    if event == "ping":
        return 200, "Pong\n", None

    if event == "push":
        repo_full = ((payload.get("repository") or {}).get("full_name") or "").strip()
        if repo_full and repo_full != "vinhthang/oci":
            return 200, f"Ignored non-fleet repository {repo_full!r}\n", None
        ref = (payload.get("ref") or "").strip()
        if ref and ref != "refs/heads/main":
            return 200, "Ignored non-main branch\n", None
        return 200, "GitOps Deploy Triggered\n", {"kind": "gitops_sync"}

    if event in ("package", "registry_package"):
        action = (payload.get("action") or "").strip().lower()
        if action not in ("published", "updated"):
            return 200, f"Ignored package action {action!r}\n", None

        pkg = payload.get("package") or payload.get("registry_package") or {}
        pkg_type = (pkg.get("package_type") or "").strip().lower()
        if pkg_type and pkg_type != "container":
            return 200, f"Ignored non-container package {pkg_type!r}\n", None

        owner = (
            (pkg.get("owner") or {}).get("login")
            or ((payload.get("repository") or {}).get("owner") or {}).get("login")
            or ""
        ).strip()
        if owner and owner.lower() != "vinhthang":
            return 200, f"Ignored foreign package owner {owner!r}\n", None

        raw_name = (pkg.get("name") or "").strip()
        service = raw_name.split("/", 1)[-1] if raw_name.startswith("vinhthang/") else raw_name
        if service not in ALLOWED_CUSTOM_SERVICES:
            return 200, f"Ignored non-allowlisted package {raw_name!r}\n", None

        pkg_version = pkg.get("package_version") or {}
        container_meta = pkg_version.get("container_metadata") or {}
        tag = ((container_meta.get("tag") or {}).get("name") or pkg_version.get("tag") or "").strip()

        digest = ""
        for candidate in (
            pkg_version.get("digest"),
            pkg_version.get("manifest_digest"),
            pkg_version.get("version"),
            pkg_version.get("name"),
        ):
            if isinstance(candidate, str) and candidate.strip().startswith("sha256:"):
                digest = candidate.strip()
                break

        err = _validate_tag_and_digest(tag, digest)
        if err:
            return 400, err, None

        return (
            200,
            f"Image Rollout Triggered: {service}\n",
            {
                "kind": "image_rollout",
                "source": "github_package",
                "service": service,
                "tag": tag,
                "digest": digest,
            },
        )

    return 200, f"Ignored GitHub event {event!r}\n", None


def parse_deploy_request(payload: dict[str, Any]) -> tuple[int, str, dict[str, Any] | None]:
    """Validate direct POST /deploy JSON payload against the custom service allowlist."""
    if not isinstance(payload, dict):
        return 400, "JSON object payload required\n", None

    service = str(payload.get("service") or "").strip()
    if service not in ALLOWED_CUSTOM_SERVICES:
        return 400, f"Unsupported or non-allowlisted service: {service!r}\n", None

    tag = str(payload.get("tag") or "").strip()
    digest = str(payload.get("digest") or "").strip()
    err = _validate_tag_and_digest(tag, digest)
    if err:
        return 400, err, None

    return (
        200,
        f"Image Rollout Triggered: {service}\n",
        {
            "kind": "image_rollout",
            "source": "deploy_api",
            "service": service,
            "tag": tag,
            "digest": digest,
        },
    )


def read_baseline_service_images(values_path: Path) -> dict[str, str]:
    """Extract canonical image strings for allowlisted services from values.yaml using stdlib."""
    baselines: dict[str, str] = {}
    current_service: str | None = None
    in_image_map = False
    image_map_indent = -1
    map_fields: dict[str, str] = {}

    def _flush_map() -> None:
        if current_service and ALLOWED_CUSTOM_SERVICES[current_service]["mode"] == "map":
            repo = map_fields.get("repository", "")
            tag = map_fields.get("tag", "")
            digest = map_fields.get("digest", "")
            if repo:
                if digest:
                    baselines[current_service] = f"{repo}@{digest}"
                elif tag:
                    baselines[current_service] = f"{repo}:{tag}"
                else:
                    baselines[current_service] = repo

    for raw_line in values_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if indent == 0:
            _flush_map()
            key = stripped.split(":", 1)[0].strip()
            current_service = _VALUES_KEY_TO_SERVICE.get(key)
            in_image_map = False
            image_map_indent = -1
            map_fields = {}
            continue

        if not current_service or ":" not in stripped:
            continue

        key, raw_val = stripped.split(":", 1)
        key = key.strip()
        val = _strip_yaml_scalar(raw_val)
        mode = ALLOWED_CUSTOM_SERVICES[current_service]["mode"]

        if mode == "scalar":
            if indent == 2 and key == "image" and val:
                baselines[current_service] = val
            continue

        if in_image_map and indent <= image_map_indent:
            in_image_map = False

        if key == "image" and not val:
            in_image_map = True
            image_map_indent = indent
            map_fields = {}
        elif in_image_map and indent > image_map_indent and key in {"repository", "tag", "digest"}:
            map_fields[key] = val

    _flush_map()
    return baselines


def _extract_repo(current_git_image: str, service: str) -> str:
    if "@sha256:" in current_git_image:
        return current_git_image.split("@", 1)[0]
    last_segment = current_git_image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return current_git_image.rsplit(":", 1)[0]
    return current_git_image or f"ghcr.io/vinhthang/{service}"


def compute_service_override(
    service: str,
    current_git_image: str,
    tag: str,
    digest: str,
    source: str,
    timestamp: str,
) -> dict[str, Any]:
    """Compute Helm values override entry for a webhook-triggered custom service rollout."""
    if service not in ALLOWED_CUSTOM_SERVICES:
        raise ValueError(f"Unsupported service: {service}")

    mode = ALLOWED_CUSTOM_SERVICES[service]["mode"]
    if mode == "scalar":
        repo = _extract_repo(current_git_image, service)
        if digest and (not tag or tag != "latest") and source == "deploy_api":
            image = f"{repo}@{digest}"
            pull_policy = "IfNotPresent"
        elif tag and tag != "latest":
            image = f"{repo}:{tag}"
            pull_policy = "IfNotPresent"
        else:
            image = f"{repo}:latest"
            pull_policy = "Always"
        return {
            "baseline_git_image": current_git_image,
            "values": {
                "image": image,
                "imagePullPolicy": pull_policy,
                "rolloutTimestamp": timestamp,
            },
        }

    img_values: dict[str, str] = {}
    if source == "github_package" and (not tag or tag == "latest") and digest:
        img_values["digest"] = digest
    elif tag and tag != "latest":
        img_values["tag"] = tag
        img_values["digest"] = ""
    elif source == "deploy_api" and tag == "latest":
        img_values["tag"] = "latest"
        img_values["digest"] = ""
        img_values["pullPolicy"] = "Always"
    elif digest:
        img_values["digest"] = digest
    elif current_git_image.endswith(":latest"):
        img_values["pullPolicy"] = "Always"

    values: dict[str, Any] = {"rolloutTimestamp": timestamp}
    if img_values:
        values["image"] = img_values
    return {"baseline_git_image": current_git_image, "values": values}


def reconcile_state_on_gitops_push(
    state: dict[str, Any], git_baselines: dict[str, str]
) -> dict[str, Any]:
    """Drop webhook overrides whose Git baseline changed; keep untouched service overrides."""
    kept: dict[str, Any] = {}
    for svc, entry in (state.get("overrides") or {}).items():
        if svc not in ALLOWED_CUSTOM_SERVICES:
            continue
        if git_baselines.get(svc) == entry.get("baseline_git_image"):
            kept[svc] = entry
    return {"overrides": kept}


def render_helm_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Convert stored override state into Helm chart values keyed by values.yaml section."""
    rendered: dict[str, Any] = {}
    for svc, entry in overrides.items():
        meta = ALLOWED_CUSTOM_SERVICES.get(svc)
        if meta and isinstance(entry, dict) and isinstance(entry.get("values"), dict):
            rendered[meta["values_key"]] = entry["values"]
    return rendered


def build_helm_upgrade_cmd(chart_path: str, overrides_path: str | None = None) -> list[str]:
    """Construct canonical Helm upgrade command list (zero shell interpolation)."""
    cmd = [
        "helm",
        "upgrade",
        "--install",
        "fleet",
        chart_path,
        "-n",
        "default",
        "--no-hooks",
        "--reset-values",
    ]
    if overrides_path:
        cmd.extend(["-f", overrides_path])
    return cmd


def _load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.is_file():
        return {"overrides": {}}
    try:
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict) and isinstance(loaded.get("overrides"), dict):
            return {"overrides": loaded["overrides"]}
    except Exception as exc:
        sys.stderr.write(f"Warning: resetting unreadable webhook state {state_path}: {exc}\n")
    return {"overrides": {}}


def _save_state_atomic(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".state-", suffix=".json", dir=str(state_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        os.replace(tmp_name, state_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _default_run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def run_reconcile_job(
    job: dict[str, Any],
    *,
    state_path: Path,
    repo_url: str,
    clone_dir: Path,
    edge_sync_url: str,
    run_cmd: Callable[[list[str]], Any] | None = None,
    now_fn: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Clone vinhthang/oci, update/reconcile overrides, and execute Helm fleet upgrade."""
    runner = run_cmd or _default_run_cmd
    now = now_fn or _utc_now_iso

    shutil.rmtree(clone_dir, ignore_errors=True)
    clone_proc = runner(["git", "clone", "--depth", "1", repo_url, str(clone_dir)])
    if clone_proc.returncode != 0:
        raise RuntimeError(f"git clone failed ({clone_proc.returncode}): {clone_proc.stderr}")

    chart_dir = clone_dir / "charts" / "vinhthang-fleet"
    baselines = read_baseline_service_images(chart_dir / "values.yaml")
    state = _load_state(state_path)

    kind = job.get("kind")
    if kind == "image_rollout":
        svc = str(job["service"])
        state.setdefault("overrides", {})[svc] = compute_service_override(
            svc,
            baselines.get(svc, ""),
            str(job.get("tag") or ""),
            str(job.get("digest") or ""),
            str(job.get("source") or "deploy_api"),
            now(),
        )
    elif kind == "gitops_sync":
        state = reconcile_state_on_gitops_push(state, baselines)
    else:
        raise ValueError(f"Unknown reconcile job kind: {kind!r}")

    helm_values = render_helm_overrides(state.get("overrides") or {})
    overrides_file: Path | None = None
    try:
        if helm_values:
            fd, tmp_name = tempfile.mkstemp(prefix="fleet-overrides-", suffix=".yaml")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(helm_values, indent=2, sort_keys=True) + "\n")
            overrides_file = Path(tmp_name)

        helm_proc = runner(
            build_helm_upgrade_cmd(str(chart_dir), str(overrides_file) if overrides_file else None)
        )
        if helm_proc.returncode != 0:
            raise RuntimeError(f"helm upgrade failed ({helm_proc.returncode}): {helm_proc.stderr}")

        _save_state_atomic(state_path, state)

        if kind == "gitops_sync" and edge_sync_url:
            edge_proc = runner(["curl", "-fsS", "-X", "POST", edge_sync_url])
            if edge_proc.returncode != 0:
                raise RuntimeError(
                    f"Caddy edge sync webhook failed ({edge_proc.returncode}): {edge_proc.stderr}"
                )
    finally:
        if overrides_file and overrides_file.exists():
            overrides_file.unlink()

    return state


def create_webhook_app_handler(
    *,
    secret: bytes,
    enqueue_job: Callable[[dict[str, Any]], None],
    max_body_bytes: int = MAX_BODY_BYTES,
) -> type[BaseHTTPRequestHandler]:
    """Create HTTP handler class bound to webhook secret, queue callback, and body cap."""

    class WebhookHandler(BaseHTTPRequestHandler):
        def _send_text(self, code: int, body: str, *, head_only: bool = False) -> None:
            encoded = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            if not head_only:
                self.wfile.write(encoded)

        def do_HEAD(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/healthz", "/"):
                self._send_text(200, "OK\n", head_only=True)
            else:
                self._send_text(404, "Not Found\n", head_only=True)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/healthz", "/"):
                self._send_text(200, "OK\n")
            else:
                self._send_text(404, "Not Found\n")

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path not in ("/", "/webhook", "/deploy"):
                self._send_text(404, "Not Found\n")
                return

            try:
                content_len = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_text(400, "Invalid Content-Length\n")
                return

            if content_len < 0 or content_len > max_body_bytes:
                self._send_text(413, "Payload Too Large\n")
                return

            body = self.rfile.read(content_len)
            if path == "/deploy":
                ok, code, msg = verify_bearer_or_hmac(secret, body, self.headers)
            else:
                sig = self.headers.get("X-Hub-Signature-256") or ""
                ok, code, msg = verify_hmac_signature(secret, body, sig)

            if not ok:
                self._send_text(code, msg)
                return

            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                self._send_text(400, "Invalid JSON payload\n")
                return

            if path == "/deploy":
                code, msg, job = parse_deploy_request(payload)
            else:
                event = (self.headers.get("X-GitHub-Event") or "push").strip()
                code, msg, job = parse_github_webhook(event, payload)

            if job is not None:
                enqueue_job(job)
            self._send_text(code, msg)

        def log_message(self, format: str, *args: Any) -> None:
            sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    return WebhookHandler


def _worker_loop(
    job_queue: queue.Queue[dict[str, Any]],
    *,
    state_path: Path,
    repo_url: str,
    clone_dir: Path,
    edge_sync_url: str,
) -> None:
    while True:
        job = job_queue.get()
        try:
            sys.stderr.write(f"Executing webhook reconcile job: {json.dumps(job, sort_keys=True)}\n")
            run_reconcile_job(
                job,
                state_path=state_path,
                repo_url=repo_url,
                clone_dir=clone_dir,
                edge_sync_url=edge_sync_url,
            )
            sys.stderr.write("GitOps/Image reconcile completed successfully.\n")
        except Exception as exc:
            # Fail fast so Kubernetes restarts the pod and triggers Grafana alert (ADR-0017).
            sys.stderr.write(f"Reconcile failed fatally: {exc}\n")
            os._exit(1)
        finally:
            job_queue.task_done()


def main() -> None:
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "").encode("utf-8")
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    state_path = Path(os.environ.get("WEBHOOK_STATE_PATH", DEFAULT_STATE_PATH))
    repo_url = os.environ.get("GITOPS_REPO_URL", DEFAULT_REPO_URL)
    clone_dir = Path(os.environ.get("GITOPS_CLONE_DIR", DEFAULT_CLONE_DIR))
    edge_sync_url = os.environ.get("EDGE_SYNC_URL", DEFAULT_EDGE_SYNC_URL)

    job_queue: queue.Queue[dict[str, Any]] = queue.Queue()
    worker = threading.Thread(
        target=_worker_loop,
        args=(job_queue,),
        kwargs={
            "state_path": state_path,
            "repo_url": repo_url,
            "clone_dir": clone_dir,
            "edge_sync_url": edge_sync_url,
        },
        daemon=True,
    )
    worker.start()

    handler_cls = create_webhook_app_handler(secret=secret, enqueue_job=job_queue.put)
    server = HTTPServer(("0.0.0.0", port), handler_cls)
    sys.stderr.write(f"Authenticated GitOps & GHCR Webhook Receiver listening on port {port}...\n")
    server.serve_forever()


if __name__ == "__main__":
    main()
