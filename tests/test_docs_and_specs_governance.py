"""Architectural fitness tests for ADR, spec, and rule documentation governance."""

from __future__ import annotations

import re
from pathlib import Path

from conftest import REPO_ROOT

DOCS_DIR = REPO_ROOT / "docs"
ADR_DIR = DOCS_DIR / "adr"
SPECS_DIR = DOCS_DIR / "specs"


def test_adrs_sequential_registered_and_valid_metadata() -> None:
    expected_numbers = [f"{i:04d}" for i in range(1, 62)]
    adr_files = sorted(ADR_DIR.glob("*.md"))
    found_by_num: dict[str, Path] = {}
    for adr_file in adr_files:
        match = re.match(r"^(\d{4})-", adr_file.name)
        assert match, f"ADR filename must start with NNNN-: {adr_file.name}"
        num = match.group(1)
        assert num not in found_by_num, f"Duplicate ADR number {num}: {adr_file.name}"
        found_by_num[num] = adr_file

    missing_nums = [n for n in expected_numbers if n not in found_by_num]
    assert not missing_nums, f"Missing sequential ADRs in docs/adr/: {missing_nums}"

    docs_readme = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
    unregistered: list[str] = []
    missing_metadata: list[str] = []

    for num in expected_numbers:
        adr_file = found_by_num[num]
        if f"adr/{adr_file.name}" not in docs_readme and f"ADR-{num}" not in docs_readme:
            unregistered.append(adr_file.name)

        text = adr_file.read_text(encoding="utf-8")
        has_status = bool(re.search(r"(?im)^[\s*-]*\*{0,2}status\*{0,2}\s*:", text))
        has_date = bool(re.search(r"(?im)^[\s*-]*\*{0,2}date\*{0,2}\s*:", text))
        if not (has_status and has_date):
            missing_metadata.append(f"{adr_file.name} (status={has_status}, date={has_date})")

    assert not unregistered, f"ADRs not registered in docs/README.md: {unregistered}"
    assert not missing_metadata, f"ADRs missing Status or Date metadata headers:\n" + "\n".join(missing_metadata)

    # docs/adr/0049-*.md heading must start with '# ADR-0049' (no duplicate '# ADR-0048')
    adr_0049 = found_by_num["0049"]
    first_line = adr_0049.read_text(encoding="utf-8").lstrip().splitlines()[0]
    assert first_line.startswith("# ADR-0049"), (
        f"{adr_0049.name} heading must start with '# ADR-0049', got {first_line!r}"
    )

    # docs/README.md marks ADR-0026 as 🔴 Deprecated
    adr_0026_lines = [line for line in docs_readme.splitlines() if "ADR-0026" in line]
    assert adr_0026_lines, "ADR-0026 row missing in docs/README.md"
    assert any("🔴 Deprecated" in line for line in adr_0026_lines), (
        f"docs/README.md must mark ADR-0026 as '🔴 Deprecated', got: {adr_0026_lines}"
    )


def test_specs_packages_gates_and_hygiene() -> None:
    index_text = (SPECS_DIR / "INDEX.md").read_text(encoding="utf-8")
    spec_dirs = sorted(p.name for p in SPECS_DIR.iterdir() if p.is_dir())
    assert len(spec_dirs) == 6, f"Expected 6 spec packages under docs/specs/, got {spec_dirs}"

    missing_from_index = [name for name in spec_dirs if f"`{name}`" not in index_text]
    assert not missing_from_index, f"Spec packages missing from docs/specs/INDEX.md: {missing_from_index}"

    missing_gates: list[str] = []
    forbidden_literals: list[str] = []
    for pkg in spec_dirs:
        pkg_dir = SPECS_DIR / pkg
        combined_pkg_text = "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(pkg_dir.glob("*.md"))
        )
        if "Gate 1" not in combined_pkg_text or "Gate 2" not in combined_pkg_text:
            missing_gates.append(pkg)

        for file_path in sorted(pkg_dir.rglob("*")):
            if file_path.is_file():
                content = file_path.read_text(encoding="utf-8")
                for literal in ("userAdminSecret123", "<LOCKED_A1_"):
                    if literal in content:
                        forbidden_literals.append(f"{pkg}/{file_path.name}: contains {literal!r}")

    assert not missing_gates, f"Spec packages missing Gate 1 / Gate 2 tables: {missing_gates}"
    assert not forbidden_literals, "Forbidden placeholder/credential literals in docs/specs/:\n" + "\n".join(
        forbidden_literals
    )

    # pc1-secret-manager-1password-test must cite ADR-0049 (not ADR-0048)
    sm_pkg = SPECS_DIR / "pc1-secret-manager-1password-test"
    sm_files_text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted(sm_pkg.iterdir())
        if p.is_file()
    )
    assert "ADR-0049" in sm_files_text, "pc1-secret-manager-1password-test must cite ADR-0049"
    assert "ADR-0048" not in sm_files_text, "pc1-secret-manager-1password-test must not cite stale ADR-0048"
    assert "ADR-0049" in [line for line in index_text.splitlines() if "pc1-secret-manager-1password-test" in line][0], (
        "docs/specs/INDEX.md must cite ADR-0049 for pc1-secret-manager-1password-test"
    )


def test_root_docs_and_rules_up_to_date() -> None:
    targets = {
        "README.md": (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
        ".agents/rules/adr-governance.md": (
            REPO_ROOT / ".agents" / "rules" / "adr-governance.md"
        ).read_text(encoding="utf-8"),
    }

    for label, text in targets.items():
        assert "24 GB" in text, f"{label} must cite '24 GB' for arm10"
        assert "10 GB" not in text and "10GB" not in text, (
            f"{label} still cites stale 10 GB RAM for arm10"
        )
        assert "main.tf" not in text, f"{label} must not reference nonexistent main.tf"
        assert "Uptime Kuma" not in text, f"{label} must not reference active Uptime Kuma"
