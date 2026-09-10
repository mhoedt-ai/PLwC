from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = ROOT / "docker" / "runtime-image-sources.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_runtime_images import VerificationError, verify_build_report  # noqa: E402


Runner = Callable[..., subprocess.CompletedProcess[str]]
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
STAGING_REPOSITORY_PREFIX_RE = re.compile(r"^ghcr\.io/mhoedt-ai/[a-z0-9][a-z0-9_.-]{0,127}$")


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


def _staging_repository(image_id: str, prefix: str) -> str:
    if not STAGING_REPOSITORY_PREFIX_RE.fullmatch(prefix):
        raise VerificationError("Staging repository prefix is not an approved GHCR path")
    component = image_id.replace("_", "-")
    if component not in {"document-worker", "node-runner", "python-runner"}:
        raise VerificationError(f"Unexpected runtime image id for staging: {image_id}")
    return f"{prefix}-{component}"


def _metadata_identity(path: Path) -> tuple[str, str]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Direct-push metadata is unavailable or invalid: {path}") from exc
    digest = metadata.get("containerimage.digest")
    config_digest = metadata.get("containerimage.config.digest")
    descriptor = metadata.get("containerimage.descriptor")
    if not isinstance(digest, str) or DIGEST_RE.fullmatch(digest) is None:
        raise VerificationError(f"Direct-push metadata has no manifest digest: {path}")
    if not isinstance(config_digest, str) or DIGEST_RE.fullmatch(config_digest) is None:
        raise VerificationError(f"Direct-push metadata has no config digest: {path}")
    if not isinstance(descriptor, Mapping) or descriptor.get("platform") != {
        "architecture": "amd64",
        "os": "linux",
    }:
        raise VerificationError(f"Direct-push metadata platform is not linux/amd64: {path}")
    return digest, config_digest


def _run(runner: Runner, argv: Sequence[str]) -> None:
    result = runner(list(argv), cwd=ROOT, check=False, text=True)
    if result.returncode != 0:
        stderr = str(result.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise VerificationError(f"Direct BuildKit registry push failed{detail}")


def push_verified_images(
    build_report_path: Path,
    output_path: Path,
    *,
    staging_repository_prefix: str,
    staging_suffix: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    report = verify_build_report(build_report_path)
    source_commit = str(report["source_commit"])
    current_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current_commit != source_commit:
        raise VerificationError("Build report does not belong to the checked-out commit")
    suffix = staging_suffix or f"r27-staging-{source_commit[:12]}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,127}", suffix):
        raise VerificationError("Staging tag suffix is not registry-safe")

    source_lock = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
    locked_images = {str(item["id"]): item for item in source_lock["images"]}
    pushed: list[dict[str, str]] = []
    for image in report["images"]:
        image_id = str(image["id"])
        locked = locked_images[image_id]
        staging_repository = _staging_repository(image_id, staging_repository_prefix)
        staging_reference = f"{staging_repository}:{suffix}"
        metadata_path = output_path.parent / "push" / image_id / "build-metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        arguments = (
            "docker",
            "buildx",
            "build",
            "--no-cache",
            "--platform",
            "linux/amd64",
            "--provenance=false",
            "--sbom=false",
            "--build-arg",
            f"SOURCE_REVISION={source_commit}",
            "--build-arg",
            f"SOURCE_DATE_EPOCH={report['source_date_epoch']}",
            "--build-arg",
            f"OCI_CREATED={report['created']}",
            "--metadata-file",
            str(metadata_path),
            "--output",
            f"type=registry,name={staging_reference},rewrite-timestamp=true",
            str(ROOT / str(locked["context"])),
        )
        _run(runner, arguments)
        digest, config_digest = _metadata_identity(metadata_path)
        if digest != image["digest"] or config_digest != image["config_digest"]:
            raise VerificationError(f"Direct GHCR push is not identical to the two verified builds: {image_id}")
        pushed.append(
            {
                "id": image_id,
                "staging_reference": staging_reference,
                "digest": digest,
                "config_digest": config_digest,
            }
        )

    result = {
        "schema_version": "1.0.0",
        "status": "pass",
        "source_commit": source_commit,
        "staging_repository_prefix": staging_repository_prefix,
        "staging_suffix": suffix,
        "images": pushed,
    }
    _atomic_json(output_path, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Push verified PLwC r27 images directly with BuildKit")
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--staging-repository-prefix", required=True)
    parser.add_argument("--staging-suffix")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = push_verified_images(
            args.build_report.resolve(),
            args.output.resolve(),
            staging_repository_prefix=args.staging_repository_prefix,
            staging_suffix=args.staging_suffix,
        )
    except (OSError, subprocess.SubprocessError, VerificationError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
