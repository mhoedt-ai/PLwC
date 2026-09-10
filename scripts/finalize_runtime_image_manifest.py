from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_runtime_images import VerificationError, verify_build_report, verify_manifest  # noqa: E402


Runner = Callable[..., subprocess.CompletedProcess[bytes]]
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _run_bytes(runner: Runner, argv: Sequence[str]) -> bytes:
    result = runner(
        list(argv),
        cwd=ROOT,
        check=False,
        capture_output=True,
        shell=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else str(result.stderr)
        raise VerificationError(f"Registry inspection failed: {' '.join(argv)}: {stderr.strip()}")
    return result.stdout if isinstance(result.stdout, bytes) else str(result.stdout).encode("utf-8")


def inspect_remote_image(reference: str, *, runner: Runner = subprocess.run) -> dict[str, Any]:
    summary = _run_bytes(runner, ("docker", "buildx", "imagetools", "inspect", reference)).decode(
        "utf-8", errors="replace"
    )
    match = re.search(r"(?im)^Digest:\s*(sha256:[0-9a-f]{64})\s*$", summary)
    if match is None:
        raise VerificationError(f"Registry did not return an immutable digest for {reference}")
    registry_digest = match.group(1)
    raw = _run_bytes(runner, ("docker", "buildx", "imagetools", "inspect", "--raw", reference))
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Registry manifest is invalid JSON for {reference}") from exc
    if not isinstance(manifest, Mapping) or not isinstance(manifest.get("config"), Mapping):
        raise VerificationError(f"Registry tag must resolve directly to one linux/amd64 image manifest: {reference}")
    config = manifest["config"]
    layers = manifest.get("layers")
    if not isinstance(layers, list) or not layers:
        raise VerificationError(f"Registry manifest has no layers: {reference}")
    descriptor_sizes = [config.get("size"), *(item.get("size") for item in layers if isinstance(item, Mapping))]
    if any(not isinstance(size, int) or isinstance(size, bool) or size <= 0 for size in descriptor_sizes):
        raise VerificationError(f"Registry manifest has invalid descriptor sizes: {reference}")
    config_digest = config.get("digest")
    if not isinstance(config_digest, str) or not DIGEST_RE.fullmatch(config_digest):
        raise VerificationError(f"Registry manifest has no valid config digest: {reference}")
    return {
        "reference": reference,
        "digest": registry_digest,
        "config_digest": config_digest,
        "download_bytes": sum(int(value) for value in descriptor_sizes),
        "media_type": manifest.get("mediaType"),
        "raw_sha256": _sha256_bytes(raw),
    }


def _registry_provenance(
    *,
    repository: str,
    registry_digest: str,
    config_digest: str,
    source_commit: str,
    staging_reference: str,
    build_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": repository, "digest": {"sha256": registry_digest.removeprefix("sha256:")}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://github.com/mhoedt-ai/PLwC/runtime-images-r27@v1",
                "externalParameters": {
                    "source_commit": source_commit,
                    "platform": "linux/amd64",
                    "staging_reference": staging_reference,
                },
                "resolvedDependencies": [
                    {"uri": f"oci:{repository}", "digest": {"sha256": config_digest.removeprefix("sha256:")}},
                    {
                        "uri": str(build_provenance.get("path", "")),
                        "digest": {"sha256": str(build_provenance.get("sha256", ""))},
                    },
                ],
            },
            "runDetails": {"builder": {"id": "github-actions:runtime-images-r27"}},
        },
    }


def finalize(
    build_report_path: Path,
    output_path: Path,
    *,
    staging_suffix: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    report = verify_build_report(build_report_path)
    source_commit = str(report["source_commit"])
    suffix = staging_suffix or f"r27-staging-{source_commit[:12]}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,127}", suffix):
        raise VerificationError("Staging tag suffix is not registry-safe")
    images: list[dict[str, Any]] = []
    for image in report["images"]:
        repository = str(image["repository"])
        staging_reference = f"{repository}:{suffix}"
        registry = inspect_remote_image(staging_reference, runner=runner)
        if registry["digest"] != image["digest"]:
            raise VerificationError(f"GHCR manifest digest does not match reproducible local build: {image['id']}")
        if registry["config_digest"] != image["config_digest"]:
            raise VerificationError(f"GHCR config digest does not match reproducible local build: {image['id']}")
        evidence = image["evidence"]
        provenance_path = build_report_path.parent / "evidence" / str(image["id"]) / "registry-provenance.intoto.json"
        registry_provenance = _registry_provenance(
            repository=repository,
            registry_digest=registry["digest"],
            config_digest=registry["config_digest"],
            source_commit=source_commit,
            staging_reference=staging_reference,
            build_provenance=evidence["provenance"],
        )
        _atomic_json(provenance_path, registry_provenance)
        relative_provenance = provenance_path.relative_to(build_report_path.parent).as_posix()
        manifest_image = {
            "id": image["id"],
            "repository": repository,
            "version": image["version"],
            "display_tag": f"{repository}:{image['version']}",
            "digest": registry["digest"],
            "reference": f"{repository}@{registry['digest']}",
            "platform": {"os": "linux", "architecture": "amd64"},
            "download_bytes": registry["download_bytes"],
            "content_bytes": image["content_bytes"],
            "probe_id": f"{image['id']}_v1",
            "oci_labels": {
                "source": "https://github.com/mhoedt-ai/PLwC",
                "revision": source_commit,
                "version": image["version"],
                "licenses": "Apache-2.0",
                "created": report["created"],
            },
            "sbom": {key: evidence["sbom"][key] for key in ("path", "sha256")},
            "licenses": {key: evidence["licenses"][key] for key in ("path", "sha256")},
            "vulnerabilities": {key: evidence["vulnerabilities"][key] for key in ("path", "sha256")},
            "provenance": {"path": relative_provenance, "sha256": _sha256_file(provenance_path)},
        }
        if evidence.get("vex") is not None:
            manifest_image["vex"] = {key: evidence["vex"][key] for key in ("path", "sha256")}
        images.append(manifest_image)
    manifest = {
        "$schema": "./runtime-images.schema.json",
        "schema_version": "1.0.0",
        "product_version": "1.0.0",
        "installer_revision": "r27",
        "source_repository": "https://github.com/mhoedt-ai/PLwC",
        "source_commit": source_commit,
        "platform": {"os": "linux", "architecture": "amd64"},
        "images": images,
    }
    _atomic_json(output_path, manifest)
    verify_manifest(output_path)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bind reproducible PLwC r27 builds to exact staged GHCR digests")
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--staging-suffix")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = finalize(
            args.build_report.resolve(),
            args.output.resolve(),
            staging_suffix=args.staging_suffix,
        )
    except (OSError, subprocess.SubprocessError, VerificationError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "pass",
                "manifest": str(args.output.resolve()),
                "sha256": _sha256_file(args.output.resolve()),
                "images": [{"id": image["id"], "reference": image["reference"]} for image in manifest["images"]],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
