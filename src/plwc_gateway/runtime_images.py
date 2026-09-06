"""Immutable PLwC runtime-image lock loading and resolution.

The Windows installer owns the installed lock. Runtime code accepts only the
three reviewed GHCR repositories and returns complete repository@sha256
references. It never downloads an image and never accepts a model-supplied
reference.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


RUNTIME_IMAGES_ENV_VAR = "PLWC_RUNTIME_IMAGES_MANIFEST"
RUNTIME_IMAGES_SHA256_ENV_VAR = "PLWC_RUNTIME_IMAGES_MANIFEST_SHA256"
RUNTIME_IMAGE_IDS = ("document_worker", "node_runner", "python_runner")
RUNTIME_IMAGE_REPOSITORIES = {
    "document_worker": "ghcr.io/mhoedt-ai/plwc-document-worker",
    "node_runner": "ghcr.io/mhoedt-ai/plwc-node-runner",
    "python_runner": "ghcr.io/mhoedt-ai/plwc-python-runner",
}
LEGACY_RUNTIME_IMAGES = {
    "document_worker": {"plwc-document-worker:0.1.0"},
    "node_runner": {"plwc-node-runner:0.1.0"},
    "python_runner": {"python:3.12-slim", "python:3.12-slim-bookworm"},
}
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FILE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class RuntimeImageLockError(ValueError):
    """The installed image lock is missing, untrusted or malformed."""


@dataclass(frozen=True)
class RuntimeImageLock:
    path: Path
    sha256: str
    source_commit: str
    references: Mapping[str, str]
    display_tags: Mapping[str, str]

    def reference(self, image_id: str) -> str:
        try:
            return self.references[image_id]
        except KeyError as exc:
            raise RuntimeImageLockError(f"Unknown runtime image ID: {image_id}") from exc

    def resolve_configured(self, image_id: str, configured: str | None) -> str:
        reference = self.reference(image_id)
        display_tag = self.display_tags[image_id]
        normalized = (configured or "").strip()
        if not normalized or normalized == reference or normalized == display_tag:
            return reference
        if normalized in LEGACY_RUNTIME_IMAGES[image_id]:
            return reference
        raise RuntimeImageLockError(
            f"Configured {image_id} image is not the installed PLwC lock entry."
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _closed_keys(value: Mapping[str, Any], allowed: set[str], subject: str) -> None:
    extra = sorted(set(value) - allowed)
    if extra:
        raise RuntimeImageLockError(
            f"{subject} contains unsupported fields: {', '.join(extra)}"
        )


def _validate_lock(value: Any, path: Path, sha256: str) -> RuntimeImageLock:
    if not isinstance(value, Mapping):
        raise RuntimeImageLockError("Runtime image lock must be a JSON object.")
    _closed_keys(
        value,
        {
            "$schema",
            "schema_version",
            "product_version",
            "installer_revision",
            "source_repository",
            "source_commit",
            "platform",
            "images",
        },
        "runtime image lock",
    )
    required = {
        "$schema": "./runtime-images.schema.json",
        "schema_version": "1.0.0",
        "product_version": "1.0.0",
        "installer_revision": "r27",
        "source_repository": "https://github.com/mhoedt-ai/PLwC",
        "platform": {"os": "linux", "architecture": "amd64"},
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise RuntimeImageLockError(f"Invalid runtime image lock field: {key}.")
    source_commit = value.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise RuntimeImageLockError("Runtime image lock has an invalid source commit.")
    images = value.get("images")
    if not isinstance(images, list) or len(images) != 3:
        raise RuntimeImageLockError("Runtime image lock must contain exactly three images.")

    references: dict[str, str] = {}
    display_tags: dict[str, str] = {}
    allowed_image_keys = {
        "id",
        "repository",
        "version",
        "display_tag",
        "digest",
        "reference",
        "platform",
        "download_bytes",
        "content_bytes",
        "probe_id",
        "oci_labels",
        "sbom",
        "licenses",
        "vulnerabilities",
        "provenance",
    }
    expected_probes = {
        "document_worker": "document_worker_v1",
        "node_runner": "node_runner_v1",
        "python_runner": "python_runner_v1",
    }
    for raw_image in images:
        if not isinstance(raw_image, Mapping):
            raise RuntimeImageLockError("Runtime image entry must be an object.")
        _closed_keys(raw_image, allowed_image_keys, "runtime image entry")
        image_id = raw_image.get("id")
        if image_id not in RUNTIME_IMAGE_IDS or image_id in references:
            raise RuntimeImageLockError("Runtime image ID is missing, duplicate or unsupported.")
        repository = RUNTIME_IMAGE_REPOSITORIES[str(image_id)]
        digest = raw_image.get("digest")
        reference = raw_image.get("reference")
        display_tag = raw_image.get("display_tag")
        if raw_image.get("repository") != repository:
            raise RuntimeImageLockError(f"Runtime image repository is not allowlisted: {image_id}.")
        if raw_image.get("version") != "0.1.0":
            raise RuntimeImageLockError(f"Runtime image version is invalid: {image_id}.")
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            raise RuntimeImageLockError(f"Runtime image digest is invalid: {image_id}.")
        if reference != f"{repository}@{digest}":
            raise RuntimeImageLockError(f"Runtime image reference is not digest-locked: {image_id}.")
        if display_tag != f"{repository}:0.1.0":
            raise RuntimeImageLockError(f"Runtime image display tag is invalid: {image_id}.")
        if raw_image.get("platform") != {"os": "linux", "architecture": "amd64"}:
            raise RuntimeImageLockError(f"Runtime image platform is invalid: {image_id}.")
        if raw_image.get("probe_id") != expected_probes[str(image_id)]:
            raise RuntimeImageLockError(f"Runtime image probe is invalid: {image_id}.")
        for size_key in ("download_bytes", "content_bytes"):
            size = raw_image.get(size_key)
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                raise RuntimeImageLockError(
                    f"Runtime image {size_key} is invalid: {image_id}."
                )
        labels = raw_image.get("oci_labels")
        if not isinstance(labels, Mapping):
            raise RuntimeImageLockError(f"Runtime image OCI labels are invalid: {image_id}.")
        _closed_keys(labels, {"source", "revision", "version", "licenses", "created"}, "OCI labels")
        if (
            labels.get("source") != "https://github.com/mhoedt-ai/PLwC"
            or labels.get("revision") != source_commit
            or labels.get("version") != "0.1.0"
            or labels.get("licenses") != "Apache-2.0"
            or not isinstance(labels.get("created"), str)
            or not labels.get("created")
        ):
            raise RuntimeImageLockError(f"Runtime image OCI labels are invalid: {image_id}.")
        for evidence_key in ("sbom", "licenses", "vulnerabilities", "provenance"):
            evidence = raw_image.get(evidence_key)
            if not isinstance(evidence, Mapping):
                raise RuntimeImageLockError(
                    f"Runtime image evidence is invalid: {image_id}.{evidence_key}."
                )
            _closed_keys(evidence, {"path", "sha256"}, "runtime image evidence")
            evidence_path = evidence.get("path")
            evidence_sha256 = evidence.get("sha256")
            if (
                not isinstance(evidence_path, str)
                or not evidence_path
                or Path(evidence_path).is_absolute()
                or ".." in Path(evidence_path).parts
                or not isinstance(evidence_sha256, str)
                or not _FILE_HASH_RE.fullmatch(evidence_sha256)
            ):
                raise RuntimeImageLockError(
                    f"Runtime image evidence is invalid: {image_id}.{evidence_key}."
                )
        references[str(image_id)] = str(reference)
        display_tags[str(image_id)] = str(display_tag)
    if set(references) != set(RUNTIME_IMAGE_IDS):
        raise RuntimeImageLockError("Runtime image lock does not contain the exact required IDs.")
    return RuntimeImageLock(
        path=path,
        sha256=sha256,
        source_commit=source_commit,
        references=references,
        display_tags=display_tags,
    )


def _expected_installed_hash(project_root: Path, lock_path: Path) -> str:
    override_path = os.environ.get(RUNTIME_IMAGES_ENV_VAR, "").strip()
    if override_path:
        expected = os.environ.get(RUNTIME_IMAGES_SHA256_ENV_VAR, "").strip().lower()
        if not _FILE_HASH_RE.fullmatch(expected):
            raise RuntimeImageLockError(
                f"{RUNTIME_IMAGES_SHA256_ENV_VAR} is required for an explicit development lock."
            )
        return expected

    payload_manifest = project_root / "app" / "installation" / "payload-manifest.json"
    if not payload_manifest.is_file():
        raise RuntimeImageLockError("Installed payload manifest is missing.")
    try:
        payload = json.loads(payload_manifest.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeImageLockError("Installed payload manifest is unreadable.") from exc
    matches = [
        entry
        for entry in payload.get("files", [])
        if isinstance(entry, Mapping)
        and entry.get("path") == "common/installation/runtime-images.json"
    ]
    if len(matches) != 1:
        raise RuntimeImageLockError("Installed payload manifest does not own the runtime image lock.")
    expected = matches[0].get("sha256")
    if not isinstance(expected, str) or not _FILE_HASH_RE.fullmatch(expected):
        raise RuntimeImageLockError("Installed runtime image lock hash is invalid.")
    if lock_path != project_root / "app" / "installation" / "runtime-images.json":
        raise RuntimeImageLockError("Installed runtime image lock is outside the application payload.")
    return expected


def load_runtime_image_lock(project_root: Path) -> RuntimeImageLock:
    root = project_root.resolve(strict=False)
    override_path = os.environ.get(RUNTIME_IMAGES_ENV_VAR, "").strip()
    path = (
        Path(override_path).expanduser().resolve(strict=False)
        if override_path
        else (root / "app" / "installation" / "runtime-images.json").resolve(strict=False)
    )
    if not path.is_file():
        raise RuntimeImageLockError(f"Runtime image lock is missing: {path}")
    expected_sha256 = _expected_installed_hash(root, path)
    actual_sha256 = _sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise RuntimeImageLockError("Runtime image lock SHA-256 does not match its trusted owner.")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeImageLockError("Runtime image lock is not valid JSON.") from exc
    return _validate_lock(value, path, actual_sha256)
