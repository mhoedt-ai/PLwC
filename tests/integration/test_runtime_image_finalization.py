from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


verifier = _load("plwc_verify_runtime_images_test", ROOT / "scripts" / "verify_runtime_images.py")
finalizer = _load("plwc_finalize_runtime_images_test", ROOT / "scripts" / "finalize_runtime_image_manifest.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return {"path": path.as_posix(), "sha256": _sha256(path)}


def _build_report(tmp_path: Path) -> Path:
    commit = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    source = json.loads((ROOT / "docker" / "runtime-image-sources.json").read_text(encoding="utf-8"))
    images = []
    for index, locked in enumerate(source["images"], start=1):
        image_id = locked["id"]
        digest = "sha256:" + str(index) * 64
        config_digest = "sha256:" + str(index + 3) * 64
        root = tmp_path / "evidence" / image_id
        sbom = _write_json(root / "sbom.spdx.json", {"spdxVersion": "SPDX-2.3", "packages": []})
        licenses = _write_json(root / "licenses.json", {"schema_version": "1.0.0", "packages": []})
        vulnerabilities = _write_json(
            root / "vulnerabilities.sarif.json",
            {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "fixture"}}, "results": []}]},
        )
        provenance = _write_json(
            root / "provenance.intoto.json",
            {
                "_type": "https://in-toto.io/Statement/v1",
                "subject": [{"name": locked["repository"], "digest": {"sha256": digest.removeprefix("sha256:")}}],
                "predicateType": "https://slsa.dev/provenance/v1",
                "predicate": {
                    "buildDefinition": {
                        "externalParameters": {"source_commit": commit, "platform": "linux/amd64"}
                    }
                },
            },
        )
        evidence = {
            "sbom": {**sbom, "path": Path(sbom["path"]).relative_to(tmp_path).as_posix()},
            "licenses": {**licenses, "path": Path(licenses["path"]).relative_to(tmp_path).as_posix()},
            "vulnerabilities": {
                **vulnerabilities,
                "path": Path(vulnerabilities["path"]).relative_to(tmp_path).as_posix(),
                "status": "complete",
            },
            "provenance": {**provenance, "path": Path(provenance["path"]).relative_to(tmp_path).as_posix()},
        }
        round_value = {
            "digest": digest,
            "config_digest": config_digest,
            "content_bytes": index * 10_000,
            "tag": f"fixture-{index}",
        }
        images.append(
            {
                "id": image_id,
                "repository": locked["repository"],
                "version": "0.1.0",
                "platform": "linux/amd64",
                "digest": digest,
                "config_digest": config_digest,
                "content_bytes": index * 10_000,
                "rounds": [dict(round_value), dict(round_value)],
                "probe": {
                    "id": f"{image_id}_v1",
                    "status": "pass",
                    "pull_policy": "never",
                    "network": "none",
                    "user": "10001:10001" if image_id == "document_worker" else "65532:65532",
                    "stdout": "fixture probe passed",
                },
                "evidence": evidence,
            }
        )
    report = {
        "schema_version": "1.0.0",
        "status": "pass",
        "source_clean": True,
        "source_commit": commit,
        "source_date_epoch": 1,
        "created": "2026-09-06T00:00:00Z",
        "target_platform": "linux/amd64",
        "source_lock_sha256": _sha256(ROOT / "docker" / "runtime-image-sources.json"),
        "images": images,
    }
    path = tmp_path / "image-build-report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def test_source_lock_and_release_build_report_verify(tmp_path: Path) -> None:
    assert verifier.verify_source_lock()["target_platform"] == "linux/amd64"
    report = verifier.verify_build_report(_build_report(tmp_path))
    assert report["status"] == "pass"
    assert len(report["images"]) == 3


def test_high_vulnerability_fails_closed(tmp_path: Path) -> None:
    report_path = _build_report(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    descriptor = report["images"][0]["evidence"]["vulnerabilities"]
    vulnerability_path = tmp_path / descriptor["path"]
    vulnerability_path.write_text(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "fixture"}},
                        "results": [{"ruleId": "CVE-test", "properties": {"severity": "HIGH"}}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    descriptor["sha256"] = _sha256(vulnerability_path)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    try:
        verifier.verify_build_report(report_path)
    except verifier.VerificationError as exc:
        assert "critical/high" in str(exc)
        assert "document_worker" in str(exc)
        assert "CVE-test" in str(exc)
    else:
        raise AssertionError("A HIGH vulnerability must fail the release gate")


def test_high_vulnerability_diagnostic_extracts_package_from_purl() -> None:
    payload = {
        "runs": [
            {
                "tool": {
                    "driver": {
                        "rules": [
                            {
                                "id": "CVE-test-purl",
                                "properties": {
                                    "cvssV3_severity": "HIGH",
                                    "fixed_version": "2.0",
                                    "purls": ["pkg:deb/debian/example-package@1.0?os_distro=bookworm"],
                                },
                            }
                        ]
                    }
                },
                "results": [],
            }
        ]
    }

    assert verifier._sarif_gate_findings(payload) == [
        "CVE-test-purl severity=HIGH package=example-package fixed=2.0"
    ]


def test_dirty_or_unscanned_build_is_development_only_and_never_release_grade(tmp_path: Path) -> None:
    report_path = _build_report(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["status"] = "development_only"
    report["source_clean"] = False
    for image in report["images"]:
        descriptor = image["evidence"]["vulnerabilities"]
        vulnerability_path = tmp_path / descriptor["path"]
        vulnerability_path.write_text(
            json.dumps({"schema_version": "1.0.0", "ok": False, "status": "unavailable"}),
            encoding="utf-8",
        )
        descriptor["sha256"] = _sha256(vulnerability_path)
        descriptor["status"] = "unavailable"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    try:
        verifier.verify_build_report(report_path)
    except verifier.VerificationError as exc:
        assert "release-grade PASS" in str(exc)
    else:
        raise AssertionError("Development-only evidence must not pass the release gate")
    verified = verifier.verify_build_report(report_path, allow_development_only=True)
    assert verified["source_clean"] is False


def test_finalizer_binds_remote_manifest_digest_and_reverifies(tmp_path: Path) -> None:
    report_path = _build_report(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    local_by_repository = {
        image["repository"]: {"digest": image["digest"], "config_digest": image["config_digest"]}
        for image in report["images"]
    }

    def runner(argv, **_kwargs):
        reference = argv[-1]
        repository = reference.split(":r27-staging-", 1)[0]
        if "--raw" in argv:
            payload = {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "config": {"digest": local_by_repository[repository]["config_digest"], "size": 512},
                "layers": [{"digest": "sha256:" + "f" * 64, "size": 2048}],
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload).encode(), stderr=b"")
        summary = f"Name: {reference}\nDigest: {local_by_repository[repository]['digest']}\n"
        return subprocess.CompletedProcess(argv, 0, stdout=summary.encode(), stderr=b"")

    manifest_path = tmp_path / "runtime-images.json"
    manifest = finalizer.finalize(report_path, manifest_path, runner=runner)
    assert len(manifest["images"]) == 3
    assert all("@sha256:" in image["reference"] for image in manifest["images"])
    assert all(image["download_bytes"] == 2560 for image in manifest["images"])
    verified = verifier.verify_manifest(manifest_path)
    assert verified["installer_revision"] == "r27"


def test_finalizer_rejects_changed_remote_manifest_digest(tmp_path: Path) -> None:
    report_path = _build_report(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    local_by_repository = {
        image["repository"]: {"digest": image["digest"], "config_digest": image["config_digest"]}
        for image in report["images"]
    }

    def runner(argv, **_kwargs):
        reference = argv[-1]
        repository = reference.split(":r27-staging-", 1)[0]
        if "--raw" in argv:
            payload = {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "config": {"digest": local_by_repository[repository]["config_digest"], "size": 512},
                "layers": [{"digest": "sha256:" + "f" * 64, "size": 2048}],
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload).encode(), stderr=b"")
        return subprocess.CompletedProcess(
            argv, 0, stdout=f"Name: {reference}\nDigest: sha256:{'9' * 64}\n".encode(), stderr=b""
        )

    try:
        finalizer.finalize(report_path, tmp_path / "runtime-images.json", runner=runner)
    except finalizer.VerificationError as exc:
        assert "manifest digest" in str(exc)
    else:
        raise AssertionError("A changed GHCR manifest digest must fail finalization")


def test_finalizer_rejects_changed_remote_config_digest(tmp_path: Path) -> None:
    report_path = _build_report(tmp_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    local_by_repository = {image["repository"]: image["digest"] for image in report["images"]}

    def runner(argv, **_kwargs):
        reference = argv[-1]
        repository = reference.split(":r27-staging-", 1)[0]
        if "--raw" in argv:
            payload = {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "config": {"digest": "sha256:" + "8" * 64, "size": 512},
                "layers": [{"digest": "sha256:" + "f" * 64, "size": 2048}],
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload).encode(), stderr=b"")
        return subprocess.CompletedProcess(
            argv, 0, stdout=f"Name: {reference}\nDigest: {local_by_repository[repository]}\n".encode(), stderr=b""
        )

    try:
        finalizer.finalize(report_path, tmp_path / "runtime-images.json", runner=runner)
    except finalizer.VerificationError as exc:
        assert "config digest" in str(exc)
    else:
        raise AssertionError("A changed GHCR config digest must fail finalization")
