from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = ROOT / "docker" / "runtime-image-sources.json"
MANAGER = ROOT / "installer" / "windows" / "assets" / "runtime-image-manager.py"
SECRET_PATTERNS = (
    re.compile(r"(?i)authorization\s*[:=]\s*(?:bearer|basic)\s+\S+"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)(?:password|passwd|secret|token)\s*[:=]\s*[^\s,;]+"),
)


class VerificationError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Invalid JSON evidence: {path}") from exc


def _load_manager():
    spec = importlib.util.spec_from_file_location("plwc_runtime_image_manager_verifier", MANAGER)
    if spec is None or spec.loader is None:
        raise VerificationError("Runtime image manager could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git_head() -> str:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return result.stdout.strip()


def verify_source_lock() -> dict[str, Any]:
    source = _read_json(SOURCE_LOCK)
    if not isinstance(source, Mapping):
        raise VerificationError("Runtime image source lock must be an object")
    manager = _load_manager()
    images = source.get("images")
    if (
        source.get("schema_version") != "1.0.0"
        or source.get("target_platform") != "linux/amd64"
        or source.get("source_repository") != "https://github.com/mhoedt-ai/PLwC"
        or not isinstance(images, list)
        or len(images) != 3
    ):
        raise VerificationError("Runtime image source lock header is invalid")
    observed_ids: list[str] = []
    for image in images:
        if not isinstance(image, Mapping):
            raise VerificationError("Runtime image source entry must be an object")
        image_id = str(image.get("id", ""))
        observed_ids.append(image_id)
        if image.get("repository") != manager.EXPECTED_REPOSITORIES.get(image_id):
            raise VerificationError(f"Unexpected repository for {image_id}")
        if image.get("version") != "0.1.0" or "@sha256:" not in str(image.get("base", "")):
            raise VerificationError(f"Unpinned version or base for {image_id}")
        context = ROOT / str(image.get("context", ""))
        dockerfile = context / "Dockerfile"
        if not dockerfile.is_file():
            raise VerificationError(f"Dockerfile missing for {image_id}")
        first_line = dockerfile.read_text(encoding="utf-8").splitlines()[0]
        normalized_base = str(image["base"]).removeprefix("docker.io/library/")
        if first_line != f"FROM {normalized_base}":
            raise VerificationError(f"Dockerfile base differs from source lock for {image_id}")
    if tuple(observed_ids) != tuple(manager.EXPECTED_IDS):
        raise VerificationError("Runtime image source IDs/order are not canonical")
    return dict(source)


def _resolve_evidence(root: Path, descriptor: Any, subject: str) -> Path:
    if not isinstance(descriptor, Mapping):
        raise VerificationError(f"Missing evidence descriptor: {subject}")
    raw_path = descriptor.get("path")
    expected_hash = descriptor.get("sha256")
    if not isinstance(raw_path, str) or not raw_path or not isinstance(expected_hash, str):
        raise VerificationError(f"Invalid evidence descriptor: {subject}")
    candidate = (root / raw_path).resolve(strict=False)
    try:
        candidate.relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise VerificationError(f"Evidence path escaped its root: {subject}") from exc
    if not candidate.is_file() or _sha256(candidate) != expected_hash:
        raise VerificationError(f"Evidence file/hash mismatch: {subject}")
    if candidate.stat().st_size <= 0:
        raise VerificationError(f"Evidence file is empty: {subject}")
    if candidate.suffix.lower() in {".json", ".sarif"}:
        text = candidate.read_text(encoding="utf-8-sig")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise VerificationError(f"Possible secret in evidence: {subject}")
    return candidate


def _severity_values(value: Any, *, key: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            normalized = str(child_key).casefold().replace("_", "-")
            if normalized in {"severity", "security-severity", "tags"}:
                found.append(json.dumps(child, ensure_ascii=False))
            found.extend(_severity_values(child, key=normalized))
    elif isinstance(value, list):
        for child in value:
            found.extend(_severity_values(child, key=key))
    return found


def _verify_vulnerability_report(path: Path) -> None:
    payload = _read_json(path)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("runs"), list):
        raise VerificationError("Vulnerability report is not SARIF")
    if payload.get("ok") is False or payload.get("status") == "unavailable":
        raise VerificationError("Vulnerability scan was unavailable")
    severity_text = " ".join(_severity_values(payload)).upper()
    if re.search(r"\b(?:CRITICAL|HIGH)\b", severity_text):
        raise VerificationError("Unaccepted critical/high vulnerability finding")
    for score in re.findall(r"(?<!\d)(?:10(?:\.0+)?|[0-9](?:\.\d+)?)(?!\d)", severity_text):
        if float(score) >= 7.0:
            raise VerificationError("Unaccepted vulnerability score >= 7.0")


def _verify_sbom(path: Path) -> None:
    payload = _read_json(path)
    if not isinstance(payload, Mapping) or not (
        isinstance(payload.get("spdxVersion"), str) or payload.get("bomFormat") == "CycloneDX"
    ):
        raise VerificationError("SBOM is neither SPDX nor CycloneDX JSON")


def _verify_licenses(path: Path) -> None:
    payload = _read_json(path)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("packages"), list):
        raise VerificationError("Licence inventory is invalid")


def _verify_provenance(path: Path, *, subject_digest: str, source_commit: str) -> None:
    payload = _read_json(path)
    if not isinstance(payload, Mapping) or payload.get("predicateType") != "https://slsa.dev/provenance/v1":
        raise VerificationError("Provenance is not SLSA v1")
    subjects = payload.get("subject")
    if not isinstance(subjects, list) or not any(
        isinstance(item, Mapping)
        and isinstance(item.get("digest"), Mapping)
        and item["digest"].get("sha256") == subject_digest.removeprefix("sha256:")
        for item in subjects
    ):
        raise VerificationError("Provenance subject does not match image digest")
    parameters = payload.get("predicate", {}).get("buildDefinition", {}).get("externalParameters", {})
    if not isinstance(parameters, Mapping) or parameters.get("source_commit") != source_commit:
        raise VerificationError("Provenance source commit does not match")


def _verify_evidence_set(
    root: Path,
    evidence: Mapping[str, Any],
    *,
    subject_digest: str,
    source_commit: str,
    prefix: str,
    allow_incomplete_vulnerability_scan: bool = False,
) -> None:
    paths = {
        name: _resolve_evidence(root, evidence.get(name), f"{prefix}.{name}")
        for name in ("sbom", "licenses", "vulnerabilities", "provenance")
    }
    _verify_sbom(paths["sbom"])
    _verify_licenses(paths["licenses"])
    vulnerability_status = evidence.get("vulnerabilities", {}).get("status")
    if vulnerability_status in (None, "complete"):
        _verify_vulnerability_report(paths["vulnerabilities"])
    elif allow_incomplete_vulnerability_scan:
        unavailable = _read_json(paths["vulnerabilities"])
        if unavailable.get("status") != "unavailable" or unavailable.get("ok") is not False:
            raise VerificationError("Incomplete vulnerability evidence is not an explicit unavailable report")
    else:
        raise VerificationError("Vulnerability scan was unavailable")
    _verify_provenance(paths["provenance"], subject_digest=subject_digest, source_commit=source_commit)


def verify_build_report(path: Path, *, allow_development_only: bool = False) -> dict[str, Any]:
    report = _read_json(path)
    if not isinstance(report, Mapping):
        raise VerificationError("Image build report must be an object")
    if report.get("status") != "pass" and not (allow_development_only and report.get("status") == "development_only"):
        raise VerificationError("Image build report is not release-grade PASS")
    if report.get("source_clean") is not True and not (
        allow_development_only and report.get("source_clean") is False
    ):
        raise VerificationError("Release image evidence requires a clean source checkout")
    source_commit = str(report.get("source_commit", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise VerificationError("Image build report source commit is invalid")
    source_lock = verify_source_lock()
    if report.get("source_lock_sha256") != _sha256(SOURCE_LOCK):
        raise VerificationError("Image build report source-lock hash differs")
    expected = {item["id"]: item for item in source_lock["images"]}
    images = report.get("images")
    if not isinstance(images, list) or len(images) != 3:
        raise VerificationError("Image build report must contain exactly three images")
    for image in images:
        if not isinstance(image, Mapping) or image.get("id") not in expected:
            raise VerificationError("Image build report contains an unknown image")
        image_id = str(image["id"])
        if image.get("repository") != expected[image_id]["repository"] or image.get("version") != "0.1.0":
            raise VerificationError(f"Image build identity mismatch: {image_id}")
        rounds = image.get("rounds")
        if not isinstance(rounds, list) or len(rounds) != 2:
            raise VerificationError(f"Two independent build rounds required: {image_id}")
        digests = {item.get("digest") for item in rounds if isinstance(item, Mapping)}
        sizes = {item.get("content_bytes") for item in rounds if isinstance(item, Mapping)}
        if len(digests) != 1 or len(sizes) != 1 or image.get("digest") not in digests or image.get("content_bytes") not in sizes:
            raise VerificationError(f"Image builds are not reproducible: {image_id}")
        evidence = image.get("evidence")
        if not isinstance(evidence, Mapping):
            raise VerificationError(f"Image evidence missing: {image_id}")
        if evidence.get("vulnerabilities", {}).get("status") != "complete" and not allow_development_only:
            raise VerificationError(f"Vulnerability scan incomplete: {image_id}")
        _verify_evidence_set(
            path.parent,
            evidence,
            subject_digest=str(image["digest"]),
            source_commit=source_commit,
            prefix=image_id,
            allow_incomplete_vulnerability_scan=allow_development_only,
        )
    return dict(report)


def verify_manifest(path: Path, *, require_current_commit: bool = True) -> dict[str, Any]:
    manager = _load_manager()
    raw = _read_json(path)
    try:
        manifest = manager.validate_manifest(raw)
    except Exception as exc:
        raise VerificationError(f"Runtime image manifest contract failed: {exc}") from exc
    source_commit = str(manifest["source_commit"])
    if require_current_commit and source_commit != _git_head():
        raise VerificationError("Runtime image manifest does not belong to current Git HEAD")
    for image in manifest["images"]:
        _verify_evidence_set(
            path.parent,
            image,
            subject_digest=str(image["digest"]),
            source_commit=source_commit,
            prefix=str(image["id"]),
        )
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify PLwC r27 runtime-image sources and release evidence")
    parser.add_argument("--build-report", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--allow-development-only", action="store_true")
    parser.add_argument("--allow-foreign-commit", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: dict[str, Any] = {"source_lock": "pass"}
    try:
        verify_source_lock()
        if args.build_report:
            report = verify_build_report(args.build_report, allow_development_only=args.allow_development_only)
            result["build_report"] = {"status": "pass", "source_commit": report["source_commit"]}
        if args.manifest:
            manifest = verify_manifest(args.manifest, require_current_commit=not args.allow_foreign_commit)
            result["manifest"] = {
                "status": "pass",
                "sha256": _sha256(args.manifest),
                "source_commit": manifest["source_commit"],
            }
    except (OSError, subprocess.SubprocessError, VerificationError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"status": "pass", **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
