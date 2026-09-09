from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_LOCK = ROOT / "docker" / "runtime-image-sources.json"


def _run(arguments: Sequence[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )


def _git(*arguments: str) -> str:
    return _run(("git", *arguments), capture=True).stdout.strip()


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def _source_identity(allow_dirty: bool) -> tuple[str, int, str, bool]:
    source_clean = not bool(_git("status", "--porcelain"))
    if not allow_dirty and not source_clean:
        raise RuntimeError("Release image builds require a clean Git checkout")
    commit = _git("rev-parse", "HEAD")
    epoch = int(_git("show", "-s", "--format=%ct", "HEAD"))
    created = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return commit, epoch, created, source_clean


def _metadata_identity(path: Path) -> tuple[str, str]:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    digest = metadata.get("containerimage.digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
        raise RuntimeError(f"Build metadata does not contain an image digest: {path}")
    config_digest = metadata.get("containerimage.config.digest")
    if not isinstance(config_digest, str) or not config_digest.startswith("sha256:") or len(config_digest) != 71:
        raise RuntimeError(f"Build metadata does not contain a config digest: {path}")
    descriptor = metadata.get("containerimage.descriptor")
    if not isinstance(descriptor, dict) or descriptor.get("platform") != {"architecture": "amd64", "os": "linux"}:
        raise RuntimeError(f"Build metadata platform is not linux/amd64: {path}")
    return digest, config_digest


def _license_inventory(sbom_path: Path) -> dict[str, Any]:
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    packages = []
    for value in sbom.get("packages", []):
        if not isinstance(value, dict):
            continue
        packages.append(
            {
                "name": value.get("name"),
                "version": value.get("versionInfo"),
                "license_concluded": value.get("licenseConcluded"),
                "license_declared": value.get("licenseDeclared"),
                "supplier": value.get("supplier"),
            }
        )
    packages.sort(key=lambda item: (str(item["name"]), str(item["version"])))
    return {"schema_version": "1.0.0", "source_sbom_sha256": _sha256(sbom_path), "packages": packages}


def _build_once(
    image: dict[str, Any],
    *,
    round_number: int,
    output_root: Path,
    commit: str,
    epoch: int,
    created: str,
) -> dict[str, Any]:
    image_id = image["id"]
    round_root = output_root / f"round-{round_number}" / image_id
    round_root.mkdir(parents=True, exist_ok=True)
    metadata_path = round_root / "build-metadata.json"
    archive_path = round_root / "image.docker.tar"
    archive_cli_path = archive_path.relative_to(ROOT).as_posix() if archive_path.is_relative_to(ROOT) else str(archive_path)
    tag = f"{image['repository']}:r27-build-{round_number}"
    arguments = [
        "docker",
        "buildx",
        "build",
        "--no-cache",
        "--platform",
        "linux/amd64",
        "--provenance=false",
        "--sbom=false",
        "--build-arg",
        f"SOURCE_REVISION={commit}",
        "--build-arg",
        f"SOURCE_DATE_EPOCH={epoch}",
        "--build-arg",
        f"OCI_CREATED={created}",
        "--metadata-file",
        str(metadata_path),
        "--output",
        f"type=docker,dest={archive_cli_path},rewrite-timestamp=true,name={tag}",
        "--tag",
        tag,
        str(ROOT / image["context"]),
    ]
    _run(arguments)
    digest, config_digest = _metadata_identity(metadata_path)
    _run(("docker", "load", "--input", str(archive_path)))
    observed = json.loads(
        _run(("docker", "image", "inspect", tag, "--format", "{{json .}}"), capture=True).stdout
    )
    if (
        observed.get("Os") != "linux"
        or observed.get("Architecture") != "amd64"
        or observed.get("Id") not in {digest, config_digest}
    ):
        raise RuntimeError(f"Loaded {image_id} does not match its build identity/platform")
    return {
        "round": round_number,
        "tag": tag,
        "digest": digest,
        "config_digest": config_digest,
        "content_bytes": int(observed["Size"]),
        "archive_path": str(archive_path.relative_to(output_root)),
        "archive_sha256": _sha256(archive_path),
        "metadata_path": str(metadata_path.relative_to(output_root)),
        "metadata_sha256": _sha256(metadata_path),
    }


def _probe_image(image: dict[str, Any], tag: str) -> dict[str, Any]:
    image_id = image["id"]
    user = "10001:10001" if image_id == "document_worker" else "65532:65532"
    arguments = [
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
        user,
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
    ]
    if image_id == "document_worker":
        arguments.extend((tag, "probe"))
    elif image_id == "node_runner":
        arguments.extend(
            (
                "--entrypoint",
                "sh",
                tag,
                "-c",
                'node --version && for x in npm npx corepack yarn yarnpkg; do '
                'if command -v "$x" >/dev/null 2>&1; then exit 19; fi; done',
            )
        )
    elif image_id == "python_runner":
        arguments.extend(("--entrypoint", "sh", tag, "-c", 'python --version && test "$(id -u)" = 65532'))
    else:
        raise RuntimeError(f"No governed runtime probe exists for {image_id}")
    completed = _run(arguments, capture=True)
    stdout = completed.stdout.strip()
    if image_id == "document_worker":
        payload = json.loads(stdout)
        if payload.get("ok") is not True or payload.get("operation") != "probe":
            raise RuntimeError("Document Worker probe did not return the governed success contract")
    elif not stdout:
        raise RuntimeError(f"Runtime probe returned no version output for {image_id}")
    return {
        "id": f"{image_id}_v1",
        "status": "pass",
        "pull_policy": "never",
        "network": "none",
        "user": user,
        "stdout": stdout,
    }


def _security_evidence(image: dict[str, Any], tag: str, output_root: Path, digest: str, commit: str) -> dict[str, Any]:
    image_id = image["id"]
    evidence_root = output_root / "evidence" / image_id
    evidence_root.mkdir(parents=True, exist_ok=True)
    sbom_path = evidence_root / "sbom.spdx.json"
    licenses_path = evidence_root / "licenses.json"
    vulnerabilities_path = evidence_root / "vulnerabilities.sarif.json"
    provenance_path = evidence_root / "provenance.intoto.json"

    _run(("docker", "scout", "sbom", "--format", "spdx", "--output", str(sbom_path), f"local://{tag}"))
    _atomic_json(licenses_path, _license_inventory(sbom_path))

    vulnerability_status = "complete"
    try:
        _run(("docker", "scout", "cves", "--format", "sarif", "--output", str(vulnerabilities_path), f"local://{tag}"))
    except subprocess.CalledProcessError as exc:
        vulnerability_status = "unavailable"
        _atomic_json(
            vulnerabilities_path,
            {
                "schema_version": "1.0.0",
                "ok": False,
                "status": "unavailable",
                "tool": "docker scout cves",
                "exit_code": exc.returncode,
            },
        )

    metadata = json.loads((output_root / "round-2" / image_id / "build-metadata.json").read_text(encoding="utf-8"))
    provenance = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": image["repository"], "digest": {"sha256": digest.removeprefix("sha256:")}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "https://mobyproject.org/buildkit@v1",
                "externalParameters": {"platform": "linux/amd64", "source_commit": commit},
                "resolvedDependencies": metadata.get("buildx.build.provenance", {}).get("materials", []),
            },
            "runDetails": {"builder": {"id": "docker-buildx-local-verification"}},
        },
    }
    _atomic_json(provenance_path, provenance)
    return {
        "sbom": {"path": str(sbom_path.relative_to(output_root)), "sha256": _sha256(sbom_path)},
        "licenses": {"path": str(licenses_path.relative_to(output_root)), "sha256": _sha256(licenses_path)},
        "vulnerabilities": {
            "path": str(vulnerabilities_path.relative_to(output_root)),
            "sha256": _sha256(vulnerabilities_path),
            "status": vulnerability_status,
        },
        "provenance": {"path": str(provenance_path.relative_to(output_root)), "sha256": _sha256(provenance_path)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and compare the three PLwC r27 runtime images")
    parser.add_argument("--output-root", type=Path, default=ROOT / "build" / "runtime-images")
    parser.add_argument("--allow-dirty", action="store_true", help="Development only; cannot satisfy the release gate")
    parser.add_argument("--allow-missing-vulnerability-scan", action="store_true")
    args = parser.parse_args()

    source_lock = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
    if source_lock.get("target_platform") != "linux/amd64" or len(source_lock.get("images", [])) != 3:
        raise RuntimeError("Runtime image source lock is invalid")
    commit, epoch, created, source_clean = _source_identity(args.allow_dirty)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for image in source_lock["images"]:
        first = _build_once(image, round_number=1, output_root=output_root, commit=commit, epoch=epoch, created=created)
        second = _build_once(image, round_number=2, output_root=output_root, commit=commit, epoch=epoch, created=created)
        if (
            first["digest"] != second["digest"]
            or first["config_digest"] != second["config_digest"]
            or first["content_bytes"] != second["content_bytes"]
        ):
            raise RuntimeError(f"Non-reproducible image build: {image['id']}")
        release_tag = f"{image['repository']}:{image['version']}"
        _run(("docker", "image", "tag", second["tag"], release_tag))
        probe = _probe_image(image, release_tag)
        evidence = _security_evidence(image, release_tag, output_root, second["digest"], commit)
        if evidence["vulnerabilities"]["status"] != "complete" and not args.allow_missing_vulnerability_scan:
            raise RuntimeError(
                f"Vulnerability scan is unavailable for {image['id']}; install/authenticate an approved scanner or use the development-only override"
            )
        results.append(
            {
                "id": image["id"],
                "repository": image["repository"],
                "version": image["version"],
                "platform": "linux/amd64",
                "digest": second["digest"],
                "config_digest": second["config_digest"],
                "content_bytes": second["content_bytes"],
                "rounds": [first, second],
                "probe": probe,
                "evidence": evidence,
            }
        )
    report = {
        "schema_version": "1.0.0",
        "status": (
            "pass"
            if source_clean and all(item["evidence"]["vulnerabilities"]["status"] == "complete" for item in results)
            else "development_only"
        ),
        "source_clean": source_clean,
        "source_commit": commit,
        "source_date_epoch": epoch,
        "created": created,
        "target_platform": "linux/amd64",
        "source_lock_sha256": _sha256(SOURCE_LOCK),
        "images": results,
    }
    _atomic_json(output_root / "image-build-report.json", report)
    print(json.dumps({"status": report["status"], "source_commit": commit, "images": [{"id": item["id"], "digest": item["digest"]} for item in results]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
