from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from plwc_gateway.config import load_gateway_config
from plwc_gateway.runtime_images import (
    RUNTIME_IMAGES_ENV_VAR,
    RUNTIME_IMAGES_SHA256_ENV_VAR,
    RuntimeImageLockError,
    load_runtime_image_lock,
)


def _manifest() -> dict:
    commit = "a" * 40
    repositories = {
        "document_worker": "ghcr.io/mhoedt-ai/plwc-document-worker",
        "node_runner": "ghcr.io/mhoedt-ai/plwc-node-runner",
        "python_runner": "ghcr.io/mhoedt-ai/plwc-python-runner",
    }
    images = []
    for index, (image_id, repository) in enumerate(repositories.items(), start=1):
        digest = "sha256:" + str(index) * 64
        evidence = {"path": f"evidence/{image_id}.json", "sha256": str(index + 3) * 64}
        images.append(
            {
                "id": image_id,
                "repository": repository,
                "version": "0.1.0",
                "display_tag": f"{repository}:0.1.0",
                "digest": digest,
                "reference": f"{repository}@{digest}",
                "platform": {"os": "linux", "architecture": "amd64"},
                "download_bytes": index * 1000,
                "content_bytes": index * 2000,
                "probe_id": f"{image_id}_v1",
                "oci_labels": {
                    "source": "https://github.com/mhoedt-ai/PLwC",
                    "revision": commit,
                    "version": "0.1.0",
                    "licenses": "Apache-2.0",
                    "created": "2026-09-05T00:00:00Z",
                },
                "sbom": dict(evidence),
                "licenses": dict(evidence),
                "vulnerabilities": dict(evidence),
                "provenance": dict(evidence),
            }
        )
    return {
        "$schema": "./runtime-images.schema.json",
        "schema_version": "1.0.0",
        "product_version": "1.0.0",
        "installer_revision": "r27",
        "source_repository": "https://github.com/mhoedt-ai/PLwC",
        "source_commit": commit,
        "platform": {"os": "linux", "architecture": "amd64"},
        "images": images,
    }


def _write_lock(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_manifest(), sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_explicit_development_lock_requires_matching_hash(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "runtime-images.json"
    expected = _write_lock(path)
    monkeypatch.setenv(RUNTIME_IMAGES_ENV_VAR, str(path))
    monkeypatch.delenv(RUNTIME_IMAGES_SHA256_ENV_VAR, raising=False)
    with pytest.raises(RuntimeImageLockError, match="is required"):
        load_runtime_image_lock(tmp_path)
    monkeypatch.setenv(RUNTIME_IMAGES_SHA256_ENV_VAR, expected)
    lock = load_runtime_image_lock(tmp_path)
    assert lock.sha256 == expected
    assert lock.reference("document_worker").startswith(
        "ghcr.io/mhoedt-ai/plwc-document-worker@sha256:"
    )


def test_legacy_tags_resolve_only_through_the_lock(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "runtime-images.json"
    expected = _write_lock(path)
    monkeypatch.setenv(RUNTIME_IMAGES_ENV_VAR, str(path))
    monkeypatch.setenv(RUNTIME_IMAGES_SHA256_ENV_VAR, expected)
    lock = load_runtime_image_lock(tmp_path)
    assert lock.resolve_configured("python_runner", "python:3.12-slim") == lock.reference(
        "python_runner"
    )
    assert lock.resolve_configured("node_runner", "plwc-node-runner:0.1.0") == lock.reference(
        "node_runner"
    )
    with pytest.raises(RuntimeImageLockError, match="not the installed PLwC lock"):
        lock.resolve_configured("node_runner", "registry.example.invalid/foreign:1")


def test_installed_lock_is_owned_by_hashed_payload_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv(RUNTIME_IMAGES_ENV_VAR, raising=False)
    monkeypatch.delenv(RUNTIME_IMAGES_SHA256_ENV_VAR, raising=False)
    lock_path = tmp_path / "app" / "installation" / "runtime-images.json"
    expected = _write_lock(lock_path)
    payload_path = tmp_path / "app" / "installation" / "payload-manifest.json"
    payload_path.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "common/installation/runtime-images.json",
                        "sha256": expected,
                        "size": lock_path.stat().st_size,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_runtime_image_lock(tmp_path).path == lock_path
    lock_path.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeImageLockError, match="does not match"):
        load_runtime_image_lock(tmp_path)


def test_gateway_uses_exact_refs_or_disables_all_docker_execution(tmp_path: Path, monkeypatch) -> None:
    missing = load_gateway_config(project_root=tmp_path / "missing", create_directories=False)
    assert missing.docker.enabled is False
    assert missing.runtime_images_locked is False
    assert missing.document_worker_image is None
    assert any("runtime image lock unavailable" in item.casefold() for item in missing.setup_warnings)

    path = tmp_path / "fixture" / "runtime-images.json"
    expected = _write_lock(path)
    monkeypatch.setenv(RUNTIME_IMAGES_ENV_VAR, str(path))
    monkeypatch.setenv(RUNTIME_IMAGES_SHA256_ENV_VAR, expected)
    locked = load_gateway_config(project_root=tmp_path / "locked", create_directories=False)
    assert locked.docker.enabled is True
    assert locked.runtime_images_locked is True
    assert "@sha256:" in locked.docker.image
    assert "@sha256:" in locked.docker.node_image
    assert locked.document_worker_image and "@sha256:" in locked.document_worker_image
