"""Shared pytest fixtures for offline OCI architectural fitness tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = REPO_ROOT / "charts"
CHARTS = (
    "vinhthang-fleet",
    "bec-datastores",
    "qa-router-datastores",
    "vedge-api-local",
)


def render_helm_chart(chart_name: str, use_secrets_example: bool = True) -> list[dict[str, Any]]:
    """Render a Helm chart offline using `helm template` and parse YAML documents.

    If `values.secrets.example.yaml` exists and `use_secrets_example` is True, passes
    `-f <chart>/values.secrets.example.yaml`. Falls back cleanly to default `values.yaml`
    if rendering with the example file fails during early RED phases.
    """
    chart_path = CHARTS_DIR / chart_name
    secrets_example = chart_path / "values.secrets.example.yaml"

    cmd = ["helm", "template", "test", str(chart_path)]
    if use_secrets_example and secrets_example.is_file():
        cmd_with_secrets = [*cmd, "-f", str(secrets_example)]
        proc = subprocess.run(cmd_with_secrets, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    else:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)

    return [doc for doc in yaml.safe_load_all(proc.stdout) if isinstance(doc, dict)]


def load_chart_values(chart_name: str) -> dict[str, Any]:
    """Load `values.yaml` for a given chart."""
    values_path = CHARTS_DIR / chart_name / "values.yaml"
    with values_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


@pytest.fixture(scope="session")
def vinhthang_fleet_docs() -> list[dict[str, Any]]:
    return render_helm_chart("vinhthang-fleet", use_secrets_example=True)


@pytest.fixture(scope="session")
def vinhthang_fleet_default_docs() -> list[dict[str, Any]]:
    return render_helm_chart("vinhthang-fleet", use_secrets_example=False)


@pytest.fixture(scope="session")
def bec_datastores_docs() -> list[dict[str, Any]]:
    return render_helm_chart("bec-datastores", use_secrets_example=True)


@pytest.fixture(scope="session")
def qa_router_datastores_docs() -> list[dict[str, Any]]:
    return render_helm_chart("qa-router-datastores", use_secrets_example=True)


@pytest.fixture(scope="session")
def vedge_api_local_docs() -> list[dict[str, Any]]:
    return render_helm_chart("vedge-api-local", use_secrets_example=True)


@pytest.fixture(scope="session")
def all_rendered_charts(
    vinhthang_fleet_docs: list[dict[str, Any]],
    bec_datastores_docs: list[dict[str, Any]],
    qa_router_datastores_docs: list[dict[str, Any]],
    vedge_api_local_docs: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "vinhthang-fleet": vinhthang_fleet_docs,
        "bec-datastores": bec_datastores_docs,
        "qa-router-datastores": qa_router_datastores_docs,
        "vedge-api-local": vedge_api_local_docs,
    }
