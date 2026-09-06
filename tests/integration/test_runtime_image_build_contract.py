from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_source_lock_has_exact_three_digest_pinned_builds() -> None:
    lock = json.loads((ROOT / "docker" / "runtime-image-sources.json").read_text(encoding="utf-8"))
    assert lock["target_platform"] == "linux/amd64"
    assert [image["id"] for image in lock["images"]] == ["document_worker", "node_runner", "python_runner"]
    assert [image["repository"] for image in lock["images"]] == [
        "ghcr.io/mhoedt-ai/plwc-document-worker",
        "ghcr.io/mhoedt-ai/plwc-node-runner",
        "ghcr.io/mhoedt-ai/plwc-python-runner",
    ]
    for image in lock["images"]:
        assert re.fullmatch(r"docker\.io/library/.+@sha256:[0-9a-f]{64}", image["base"])


def test_every_runtime_dockerfile_is_pinned_and_labelled() -> None:
    for path in sorted((ROOT / "docker").glob("*-runner/Dockerfile")) + [ROOT / "docker" / "document-worker" / "Dockerfile"]:
        text = path.read_text(encoding="utf-8")
        assert re.match(r"^FROM [^\s]+@sha256:[0-9a-f]{64}$", text.splitlines()[0])
        assert ":latest" not in text
        for label in (
            "org.opencontainers.image.source",
            "org.opencontainers.image.version",
            "org.opencontainers.image.licenses",
            "org.opencontainers.image.created",
            "org.opencontainers.image.revision",
        ):
            assert label in text


def test_document_worker_build_is_offline_for_python_and_snapshot_locked_for_apt() -> None:
    text = (ROOT / "docker" / "document-worker" / "Dockerfile").read_text(encoding="utf-8")
    assert "PIP_NO_INDEX=1" in text
    assert "pip install --no-index" in text
    assert "--require-hashes" in text
    assert "snapshot.debian.org" in text
    install_block = text.split("apt-get install", 1)[1].split("&& rm", 1)[0]
    packages = [
        line.strip().rstrip(" \\")
        for line in install_block.splitlines()
        if line.strip() and not line.strip().startswith("-")
    ]
    assert packages and all("=" in package for package in packages)


def test_build_script_has_no_push_or_registry_login_path() -> None:
    path = ROOT / "scripts" / "build_runtime_images.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert tree is not None
    assert "docker push" not in text
    assert "docker login" not in text
    assert '"push"' not in text
    assert "--no-cache" in text
    assert "--platform" in text and "linux/amd64" in text
    assert "Non-reproducible image build" in text
    assert '"source_clean": source_clean' in text


def test_wheelhouse_builder_and_worker_acceptance_test_exist() -> None:
    assert (ROOT / "scripts" / "build_document_worker_wheelhouse.py").is_file()
    assert (ROOT / "scripts" / "verify_runtime_images.py").is_file()
    assert (ROOT / "scripts" / "finalize_runtime_image_manifest.py").is_file()
    assert (ROOT / "tests" / "integration" / "test_document_worker_mvp.py").is_file()


def test_registry_staging_workflow_is_manual_pinned_and_commit_scoped() -> None:
    path = ROOT / ".github" / "workflows" / "runtime-images.yml"
    text = path.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert not re.search(r"(?m)^\s{2}(?:push|pull_request|schedule):", text)
    assert "PUBLISH_PRIVATE_R27_STAGING" in text
    assert "environment: r27-runtime-images-staging" in text
    assert "packages: write" in text
    assert "r27-staging-${GITHUB_SHA::12}" in text
    assert "docker image push \"${repository}:${staging_tag}\"" in text
    assert "docker image push \"${repository}:0.1.0\"" not in text
    assert "public" not in text.casefold().replace("publish_private", "")
    uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
    assert uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in uses)
