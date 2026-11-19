"""Architectural fitness tests for declarative Caddy edge ingress security."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

CADDYFILE_PATH = REPO_ROOT / "caddy" / "Caddyfile"


def _parse_caddy_blocks(text: str) -> dict[str, str]:
    """Extract top-level Caddyfile site/snippet blocks keyed by header line."""
    blocks: dict[str, str] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if stripped.endswith("{") and not stripped.startswith("{"):
            header = stripped[:-1].strip()
            depth = 1
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and depth > 0:
                line = lines[i]
                code_part = line.split("#", 1)[0]
                depth += code_part.count("{") - code_part.count("}")
                if depth > 0:
                    body_lines.append(line)
                i += 1
            blocks[header] = "\n".join(body_lines)
        else:
            i += 1
    return blocks


def test_caddy_security_snippets_and_routes() -> None:
    content = CADDYFILE_PATH.read_text(encoding="utf-8")
    blocks = _parse_caddy_blocks(content)

    # 1. Required reusable snippets
    assert "(strip_auth_headers)" in blocks, "Caddyfile must define (strip_auth_headers) snippet"
    assert "(sso_auth)" in blocks, "Caddyfile must define (sso_auth) snippet"

    # 2. status.vinhthang.dev imports strip_auth_headers and blocks /login* & /admin*
    status_block = blocks.get("status.vinhthang.dev", "")
    assert status_block, "Missing status.vinhthang.dev site block"
    assert "import strip_auth_headers" in status_block, (
        "status.vinhthang.dev must import strip_auth_headers"
    )
    assert "/login*" in status_block and "/admin*" in status_block, (
        "status.vinhthang.dev must block /login* and /admin*"
    )

    # 3. AdGuard dashboard imports sso_auth
    adguard_block = blocks.get("adguard.vinhthang.dev, dns.vinhthang.dev", "")
    assert adguard_block, "Missing 'adguard.vinhthang.dev, dns.vinhthang.dev' site block"
    assert "import sso_auth" in adguard_block, (
        "adguard.vinhthang.dev, dns.vinhthang.dev must import sso_auth"
    )

    # 4. FileBrowser proxies to arm10/K3s NodePort 10.0.0.216:30002
    files_block = blocks.get("files.vinhthang.dev", "")
    assert files_block, "Missing files.vinhthang.dev site block"
    assert "10.0.0.216:30002" in files_block, (
        "files.vinhthang.dev must reverse_proxy to 10.0.0.216:30002"
    )

    # 5. No self-signed 'tls internal' anywhere in Caddyfile
    assert "tls internal" not in content, "Caddyfile must not contain 'tls internal'"

    # 6. weaviate.vinhthang.dev imports security_headers
    weaviate_block = blocks.get("weaviate.vinhthang.dev", "")
    assert weaviate_block, "Missing weaviate.vinhthang.dev site block"
    assert "import security_headers" in weaviate_block, (
        "weaviate.vinhthang.dev must import security_headers"
    )


def test_caddy_per_host_metrics_enabled() -> None:
    content = CADDYFILE_PATH.read_text(encoding="utf-8")
    assert re.search(r"metrics\s*\{\s*per_host\s*\}", content), (
        "caddy/Caddyfile must enable 'metrics { per_host }' so 5xx alerts include host labels"
    )
    assert not re.search(r"servers\s*\{\s*metrics\s*\}", content), (
        "caddy/Caddyfile must not use deprecated nested 'servers { metrics }' block"
    )
    assert ":2019 {" in content, "caddy/Caddyfile must preserve :2019 metrics listener"
