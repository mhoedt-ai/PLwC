from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MANAGER_PATH = ROOT / "installer" / "windows" / "assets" / "runtime-image-manager.py"


def _load_manager():
    spec = importlib.util.spec_from_file_location("plwc_runtime_image_manager_manifest_tests", MANAGER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


manager = _load_manager()


def valid_manifest() -> dict:
    commit = "a" * 40
    images = []
    for index, image_id in enumerate(manager.EXPECTED_IDS, start=1):
        repository = manager.EXPECTED_REPOSITORIES[image_id]
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
                "download_bytes": 1000 * index,
                "content_bytes": 2000 * index,
                "probe_id": manager.EXPECTED_PROBES[image_id],
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


def test_valid_manifest_has_exact_allowlisted_contract() -> None:
    value = manager.validate_manifest(valid_manifest())
    assert [image["id"] for image in value["images"]] == list(manager.EXPECTED_IDS)
    assert all("@sha256:" in image["reference"] for image in value["images"])
    assert all(":latest" not in image["reference"] for image in value["images"])


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"unexpected": True}), "unsupported fields"),
        (lambda value: value.update({"platform": {"os": "linux", "architecture": "arm64"}}), "linux/amd64"),
        (lambda value: value["images"].pop(), "exactly three"),
        (lambda value: value["images"][0].update({"repository": "docker.io/foreign/image"}), "allowlisted"),
        (lambda value: value["images"][0].update({"digest": "latest"}), "lowercase SHA-256"),
        (lambda value: value["images"][0].update({"reference": value["images"][0]["display_tag"]}), "repository@digest"),
        (lambda value: value["images"][1].update({"id": "document_worker"}), "duplicate or unsupported"),
        (lambda value: value["images"][2].update({"probe_id": "arbitrary"}), "fixed probe"),
        (lambda value: value["images"][0]["sbom"].update({"path": "../secret"}), "repository-relative"),
    ],
)
def test_manifest_rejects_unsafe_mutations(mutation, message: str) -> None:
    value = copy.deepcopy(valid_manifest())
    mutation(value)
    with pytest.raises(manager.ManifestError, match=message):
        manager.validate_manifest(value)


def test_load_manifest_requires_installer_pinned_file_hash(tmp_path: Path) -> None:
    path = tmp_path / "runtime-images.json"
    path.write_text(json.dumps(valid_manifest()), encoding="utf-8")
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert manager.load_manifest(path, expected)["installer_revision"] == "r27"
    with pytest.raises(manager.ManifestError, match="does not match"):
        manager.load_manifest(path, "0" * 64)


def test_source_lock_and_dockerfiles_pin_every_base() -> None:
    source_lock = json.loads((ROOT / "docker" / "runtime-image-sources.json").read_text(encoding="utf-8"))
    assert source_lock["target_platform"] == "linux/amd64"
    assert len(source_lock["images"]) == 3
    for image in source_lock["images"]:
        assert "@sha256:" in image["base"]
        dockerfile = (ROOT / image["context"] / "Dockerfile").read_text(encoding="utf-8")
        first_line = dockerfile.splitlines()[0]
        assert first_line.startswith("FROM ")
        assert "@sha256:" in first_line
        assert ":latest" not in dockerfile


def test_document_worker_uses_fixed_snapshot_and_direct_versions() -> None:
    dockerfile = (ROOT / "docker" / "document-worker" / "Dockerfile").read_text(encoding="utf-8")
    assert "snapshot.debian.org/archive/debian/20260909T000000Z" in dockerfile
    assert "snapshot.debian.org/archive/debian-security/20260909T000000Z" in dockerfile
    for package in (
        "fonts-dejavu-core=2.37-6",
        "libcairo2=1.16.0-7",
        "libffi8=3.4.4-1",
        "libgdk-pixbuf-2.0-0=2.42.10+dfsg-1+deb12u4",
        "libglib2.0-0=2.74.6-2+deb12u9",
        "libpango-1.0-0=1.50.12+ds-1",
        "libpangoft2-1.0-0=1.50.12+ds-1",
        "libpcre2-8-0=10.42-1+deb12u1",
        "shared-mime-info=2.2-1",
    ):
        assert package in dockerfile
