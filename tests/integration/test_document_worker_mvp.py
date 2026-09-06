from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.docker_acceptance
IMAGE = os.environ.get("PLWC_DOCUMENT_WORKER_IMAGE", "plwc-document-worker:0.1.0")


def _docker_available() -> bool:
    if os.environ.get("PLWC_RUN_DOCKER_ACCEPTANCE") != "1" or shutil.which("docker") is None:
        return False
    completed = subprocess.run(["docker", "info"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    return completed.returncode == 0


@pytest.fixture(scope="module", autouse=True)
def require_docker_image() -> None:
    if not _docker_available():
        pytest.skip("Set PLWC_RUN_DOCKER_ACCEPTANCE=1 on a Docker-capable host.")
    completed = subprocess.run(["docker", "image", "inspect", IMAGE], check=False, capture_output=True, text=True, timeout=15)
    if completed.returncode != 0:
        pytest.fail(f"Required Document Worker image is missing: {IMAGE}")


def _run(*arguments: str, workspace: Path | None = None) -> dict:
    command = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "1",
        "--user",
        "10001:10001",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
    ]
    if workspace is not None:
        command.extend(("--mount", f"type=bind,source={workspace.resolve()},target=/work"))
    command.extend((IMAGE, *arguments))
    completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=90)
    assert completed.returncode == 0, completed.stderr or completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    return payload


def test_probe_imports_all_locked_capabilities() -> None:
    result = _run("probe")
    assert result["operation"] == "probe"
    assert result["imports"] and all(result["imports"].values())


@pytest.mark.parametrize(
    ("command", "filename", "magic"),
    [
        ("create-docx", "sample.docx", b"PK"),
        ("create-xlsx", "sample.xlsx", b"PK"),
        ("create-pptx", "sample.pptx", b"PK"),
        ("create-pdf", "sample.pdf", b"%PDF"),
    ],
)
def test_create_office_and_pdf_outputs(tmp_path: Path, command: str, filename: str, magic: bytes) -> None:
    output = tmp_path / filename
    result = _run(command, "--output", f"/work/{filename}", workspace=tmp_path)
    assert result["operation"] == command
    assert output.is_file() and output.read_bytes().startswith(magic)


def test_zip_create_inspect_and_extract(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "hello.txt").write_text("PLwC r27 synthetic fixture", encoding="utf-8")
    _run("create-zip", "--inputs-json", '["/work/source"]', "--output", "/work/test.zip", workspace=tmp_path)
    inspected = _run("inspect-zip", "--input", "/work/test.zip", workspace=tmp_path)
    assert inspected["operation"] == "inspect_zip"
    _run("extract-zip", "--input", "/work/test.zip", "--output-dir", "/work/extracted", workspace=tmp_path)
    assert (tmp_path / "extracted" / "source" / "hello.txt").read_text(encoding="utf-8") == "PLwC r27 synthetic fixture"
