from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = "1.0.0"
CONSENT_TOKEN = "I_ACCEPT_PLWC_RUNTIME_IMAGE_DOWNLOAD_R27"
EXPECTED_IDS = ("document_worker", "node_runner", "python_runner")
EXPECTED_REPOSITORIES = {
    "document_worker": "ghcr.io/mhoedt-ai/plwc-document-worker",
    "node_runner": "ghcr.io/mhoedt-ai/plwc-node-runner",
    "python_runner": "ghcr.io/mhoedt-ai/plwc-python-runner",
}
EXPECTED_PROBES = {
    "document_worker": "document_worker_v1",
    "node_runner": "node_runner_v1",
    "python_runner": "python_runner_v1",
}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
MAX_STREAM_BYTES = 64 * 1024


class RuntimeImageError(RuntimeError):
    exit_code = 40
    category = "unexpected_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.images: list[dict[str, Any]] = []


class ManifestError(RuntimeImageError):
    exit_code = 21
    category = "manifest_invalid"


class DockerUnavailableError(RuntimeImageError):
    exit_code = 22
    category = "docker_unavailable"


class PullVerificationError(RuntimeImageError):
    exit_code = 23
    category = "pull_or_verification_failed"


class InsufficientDiskError(RuntimeImageError):
    exit_code = 23
    category = "insufficient_disk"

    def __init__(self, message: str, *, disk_space: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.disk_space = dict(disk_space)


class ProbeError(RuntimeImageError):
    exit_code = 24
    category = "probe_failed"


class CancelledOrTimedOutError(RuntimeImageError):
    exit_code = 25
    category = "cancelled_or_timed_out"

    def __init__(self, message: str, *, cancelled: bool, timed_out: bool) -> None:
        super().__init__(message)
        self.cancelled = cancelled
        self.timed_out = timed_out


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _with_report_id(value: Mapping[str, Any]) -> dict[str, Any]:
    report = dict(value)
    report.pop("report_id", None)
    report["report_id"] = _sha256_bytes(_canonical_json(report))
    return report


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


_SECRET_PATTERNS = (
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer|basic)\s+[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)((?:token|password|passwd|secret|cookie|auth)\s*[:=]\s*)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "<redacted-github-token>"),
    (re.compile(r"(?i)\b[A-Za-z]:\\Users\\[^\\\s]+"), r"<user-profile>"),
    (re.compile(r"(?i)\b/home/[^/\s]+"), r"<user-profile>"),
)


def _redact_text(value: str) -> str:
    normalized = "".join(character if character in "\r\n\t" or ord(character) >= 32 else "?" for character in value)
    for pattern, replacement in _SECRET_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _read_bounded(path: Path) -> tuple[str, bool]:
    size = path.stat().st_size if path.exists() else 0
    with path.open("rb") as handle:
        value = handle.read(MAX_STREAM_BYTES)
    return _redact_text(value.decode("utf-8", errors="replace")), size > MAX_STREAM_BYTES


def _closed_keys(value: Mapping[str, Any], allowed: set[str], subject: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ManifestError(f"{subject} contains unsupported fields: {', '.join(unknown)}")


def _validate_evidence(value: Any, subject: str) -> None:
    if not isinstance(value, Mapping):
        raise ManifestError(f"{subject} must be an object")
    _closed_keys(value, {"path", "sha256"}, subject)
    path = value.get("path")
    sha256 = value.get("sha256")
    if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise ManifestError(f"{subject}.path must be a safe repository-relative path")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ManifestError(f"{subject}.sha256 must be a lowercase SHA-256")


def validate_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ManifestError("Runtime image manifest must be a JSON object")
    manifest = dict(value)
    _closed_keys(
        manifest,
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
        "manifest",
    )
    expected_header = {
        "$schema": "./runtime-images.schema.json",
        "schema_version": SCHEMA_VERSION,
        "product_version": "1.0.0",
        "installer_revision": "r27",
        "source_repository": "https://github.com/mhoedt-ai/PLwC",
    }
    for key, expected in expected_header.items():
        if manifest.get(key) != expected:
            raise ManifestError(f"manifest.{key} must equal {expected!r}")
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ManifestError("manifest.source_commit must be a lowercase 40-character Git commit")
    platform = manifest.get("platform")
    if platform != {"os": "linux", "architecture": "amd64"}:
        raise ManifestError("manifest.platform must be linux/amd64")
    raw_images = manifest.get("images")
    if not isinstance(raw_images, list) or len(raw_images) != 3:
        raise ManifestError("manifest.images must contain exactly three entries")

    images: list[dict[str, Any]] = []
    seen: set[str] = set()
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
        "vex",
        "provenance",
    }
    for index, raw_image in enumerate(raw_images):
        if not isinstance(raw_image, Mapping):
            raise ManifestError(f"manifest.images[{index}] must be an object")
        image = dict(raw_image)
        _closed_keys(image, allowed_image_keys, f"manifest.images[{index}]")
        image_id = image.get("id")
        if image_id not in EXPECTED_IDS or image_id in seen:
            raise ManifestError(f"manifest.images[{index}].id is missing, duplicate or unsupported")
        seen.add(str(image_id))
        repository = EXPECTED_REPOSITORIES[str(image_id)]
        digest = image.get("digest")
        if image.get("repository") != repository:
            raise ManifestError(f"{image_id} repository is not allowlisted")
        if image.get("version") != "0.1.0":
            raise ManifestError(f"{image_id} version must equal 0.1.0")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            raise ManifestError(f"{image_id} digest must be a lowercase SHA-256")
        if image.get("display_tag") != f"{repository}:0.1.0":
            raise ManifestError(f"{image_id} display_tag does not match repository and version")
        if image.get("reference") != f"{repository}@{digest}":
            raise ManifestError(f"{image_id} reference must be repository@digest")
        if image.get("platform") != {"os": "linux", "architecture": "amd64"}:
            raise ManifestError(f"{image_id} platform must be linux/amd64")
        for size_key in ("download_bytes", "content_bytes"):
            size = image.get(size_key)
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                raise ManifestError(f"{image_id} {size_key} must be a positive integer")
        if image.get("probe_id") != EXPECTED_PROBES[str(image_id)]:
            raise ManifestError(f"{image_id} probe_id is not the fixed probe")
        labels = image.get("oci_labels")
        if not isinstance(labels, Mapping):
            raise ManifestError(f"{image_id} oci_labels must be an object")
        _closed_keys(labels, {"source", "revision", "version", "licenses", "created"}, f"{image_id}.oci_labels")
        if labels.get("source") != expected_header["source_repository"]:
            raise ManifestError(f"{image_id} source label does not match PLwC")
        if labels.get("revision") != source_commit:
            raise ManifestError(f"{image_id} revision label does not match source_commit")
        if labels.get("version") != "0.1.0" or labels.get("licenses") != "Apache-2.0":
            raise ManifestError(f"{image_id} version/licenses label is invalid")
        if not isinstance(labels.get("created"), str) or not labels.get("created"):
            raise ManifestError(f"{image_id} created label is required")
        for evidence_key in ("sbom", "licenses", "vulnerabilities", "provenance"):
            _validate_evidence(image.get(evidence_key), f"{image_id}.{evidence_key}")
        if image.get("vex") is not None:
            _validate_evidence(image.get("vex"), f"{image_id}.vex")
        images.append(image)
    if seen != set(EXPECTED_IDS):
        raise ManifestError("manifest does not contain the exact required image IDs")
    images.sort(key=lambda item: EXPECTED_IDS.index(str(item["id"])))
    manifest["images"] = images
    return manifest


def load_manifest(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ManifestError("Expected manifest hash must be a lowercase SHA-256")
    if not path.is_file():
        raise ManifestError("Runtime image manifest is missing")
    if _sha256_file(path) != expected_sha256:
        raise ManifestError("Runtime image manifest SHA-256 does not match the installer payload")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError("Runtime image manifest is not valid JSON") from exc
    return validate_manifest(value)


def _probe_arguments(image: Mapping[str, Any]) -> list[str]:
    image_id = str(image["id"])
    reference = str(image["reference"])
    user = "10001:10001" if image_id == "document_worker" else "65532:65532"
    arguments = [
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
        reference,
    ]
    if image_id == "document_worker":
        arguments.append("probe")
    elif image_id == "node_runner":
        arguments.extend(("node", "--version"))
    else:
        arguments.extend(("python", "--version"))
    return arguments


def _probe_output_ok(image_id: str, stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}".strip()
    if image_id == "document_worker":
        try:
            payload = json.loads(stdout.strip())
        except json.JSONDecodeError:
            return False
        imports = payload.get("imports") if isinstance(payload, Mapping) else None
        return bool(payload.get("ok") is True and isinstance(imports, Mapping) and imports and all(imports.values()))
    if image_id == "node_runner":
        return re.search(r"\bv22\.\d+\.\d+\b", combined) is not None
    return re.search(r"\bPython 3\.12\.\d+\b", combined) is not None


class ProcessRunner:
    def __init__(
        self,
        report_directory: Path,
        *,
        build_id: str,
        plan_id: str | None = None,
        cancel_file: Path | None = None,
    ) -> None:
        self.report_directory = report_directory
        self.build_id = build_id
        self.plan_id = plan_id or uuid.uuid4().hex
        self.cancel_file = cancel_file
        self.docker_config_directory = (report_directory / ".anonymous-docker-config").resolve(strict=False)
        self.counter = 0

    def _child_environment(self) -> dict[str, str]:
        allowed: dict[str, str] = {}
        for name in ("SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "LANG", "LC_ALL"):
            value = os.environ.get(name)
            if value:
                allowed[name] = value
        self.docker_config_directory.mkdir(parents=True, exist_ok=True)
        allowed["DOCKER_CONFIG"] = str(self.docker_config_directory)
        allowed["DOCKER_CLI_HINTS"] = "false"
        return allowed

    def run(
        self,
        argv: Sequence[str],
        *,
        phase: str,
        command_id: str,
        timeout_seconds: int,
        inactivity_timeout_seconds: int,
    ) -> dict[str, Any]:
        self.counter += 1
        report_path = self.report_directory / f"{self.counter:03d}-{command_id}.json"
        started_at = _utc_now()
        started_monotonic = time.monotonic()
        base: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "build_id": self.build_id,
            "plan_id": self.plan_id,
            "phase": phase,
            "category": "docker" if phase != "image_probe" else "probe",
            "command_id": command_id,
            "command_summary": [Path(argv[0]).name, *argv[1:]],
            "started": False,
            "started_at": started_at,
            "finished_at": None,
            "duration_ms": 0,
            "exit_code": None,
            "timed_out": False,
            "cancelled": False,
            "stdout": "",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "exception_type": None,
            "error_category": None,
            "report_path": str(report_path.resolve(strict=False)),
            "ok": False,
        }
        _atomic_write_json(report_path, _with_report_id(base))
        stdout_path: Path | None = None
        stderr_path: Path | None = None
        process: subprocess.Popen[bytes] | None = None
        try:
            self.report_directory.mkdir(parents=True, exist_ok=True)
            stdout_handle = tempfile.NamedTemporaryFile(prefix="plwc-stdout-", dir=self.report_directory, delete=False)
            stderr_handle = tempfile.NamedTemporaryFile(prefix="plwc-stderr-", dir=self.report_directory, delete=False)
            stdout_path = Path(stdout_handle.name)
            stderr_path = Path(stderr_handle.name)
            try:
                process = subprocess.Popen(
                    list(argv),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    shell=False,
                    env=self._child_environment(),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            finally:
                stdout_handle.close()
                stderr_handle.close()
            base["started"] = True
            _atomic_write_json(report_path, _with_report_id(base))
            last_output_size = 0
            last_activity = time.monotonic()
            while process.poll() is None:
                if self.cancel_file is not None and self.cancel_file.exists():
                    base["cancelled"] = True
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                current_output_size = stdout_path.stat().st_size + stderr_path.stat().st_size
                if current_output_size != last_output_size:
                    last_output_size = current_output_size
                    last_activity = time.monotonic()
                if time.monotonic() - last_activity >= inactivity_timeout_seconds:
                    base["timed_out"] = True
                    base["error_category"] = "inactivity_timed_out"
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                if time.monotonic() - started_monotonic >= timeout_seconds:
                    base["timed_out"] = True
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                time.sleep(0.1)
            process.wait()
            base["exit_code"] = int(process.returncode)
            base["stdout"], base["stdout_truncated"] = _read_bounded(stdout_path)
            base["stderr"], base["stderr_truncated"] = _read_bounded(stderr_path)
            base["ok"] = process.returncode == 0 and not base["cancelled"] and not base["timed_out"]
            if base["cancelled"]:
                base["error_category"] = "cancelled"
            elif base["timed_out"]:
                base["error_category"] = "timed_out"
            elif process.returncode != 0:
                base["error_category"] = "child_exit"
        except Exception as exc:
            base["exception_type"] = type(exc).__name__
            base["error_category"] = "process_start_or_capture_failed"
            base["stderr"] = _redact_text(str(exc))
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
        finally:
            base["finished_at"] = _utc_now()
            base["duration_ms"] = max(0, int((time.monotonic() - started_monotonic) * 1000))
            final = _with_report_id(base)
            _atomic_write_json(report_path, final)
            if stdout_path is not None:
                stdout_path.unlink(missing_ok=True)
            if stderr_path is not None:
                stderr_path.unlink(missing_ok=True)
        return final


class RuntimeImageManager:
    def __init__(
        self,
        manifest: Mapping[str, Any],
        docker: Path,
        runner: ProcessRunner,
        timeout_seconds: int,
        inactivity_timeout_seconds: int,
        *,
        space_probe_path: Path | None = None,
        free_space_provider: Callable[[Path], int] | None = None,
    ) -> None:
        self.manifest = dict(manifest)
        self.docker = docker
        self.runner = runner
        self.timeout_seconds = timeout_seconds
        self.inactivity_timeout_seconds = inactivity_timeout_seconds
        self.space_probe_path = (space_probe_path or _default_space_probe_path()).resolve(strict=False)
        self.free_space_provider = free_space_provider or (lambda path: int(shutil.disk_usage(path).free))

    def _run(self, arguments: Sequence[str], *, phase: str, command_id: str) -> dict[str, Any]:
        return self.runner.run(
            [str(self.docker), *arguments],
            phase=phase,
            command_id=command_id,
            timeout_seconds=self.timeout_seconds,
            inactivity_timeout_seconds=self.inactivity_timeout_seconds,
        )

    def ensure_daemon(self) -> dict[str, Any]:
        result = self._run(
            ["info", "--format", "{{json .ServerVersion}}"],
            phase="image_inventory",
            command_id="docker-daemon",
        )
        if result.get("ok") is not True:
            raise DockerUnavailableError("Docker daemon is unavailable")
        return result

    @staticmethod
    def _inspect_payload(result: Mapping[str, Any]) -> dict[str, Any] | None:
        if result.get("ok") is not True:
            return None
        try:
            payload = json.loads(str(result.get("stdout", "")).strip())
        except json.JSONDecodeError:
            return None
        return dict(payload) if isinstance(payload, Mapping) else None

    @staticmethod
    def _verified(image: Mapping[str, Any], payload: Mapping[str, Any] | None) -> bool:
        if payload is None:
            return False
        repo_digests = payload.get("RepoDigests")
        return bool(
            payload.get("Os") == "linux"
            and payload.get("Architecture") == "amd64"
            and isinstance(repo_digests, list)
            and image["reference"] in repo_digests
        )

    def _inspect(self, image: Mapping[str, Any], suffix: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        result = self._run(
            ["image", "inspect", "--format", "{{json .}}", str(image["reference"])],
            phase="image_inventory",
            command_id=f"inspect-{image['id']}-{suffix}",
        )
        return result, self._inspect_payload(result)

    def inventory(self) -> dict[str, Any]:
        daemon = self.ensure_daemon()
        states: list[dict[str, Any]] = []
        for image in self.manifest["images"]:
            result, payload = self._inspect(image, "inventory")
            states.append(
                {
                    "id": image["id"],
                    "reference": image["reference"],
                    "state": "present" if self._verified(image, payload) else "download_required",
                    "inspect_report": result["report_path"],
                }
            )
        return {"ok": True, "phase": "image_inventory", "daemon_report": daemon["report_path"], "images": states}

    def acquire(self) -> dict[str, Any]:
        daemon = self.ensure_daemon()
        states: list[dict[str, Any]] = []
        acquisition_plan: list[tuple[Mapping[str, Any], dict[str, Any], dict[str, Any] | None]] = []
        disk_space: dict[str, Any] | None = None
        try:
            for image in self.manifest["images"]:
                image_id = str(image["id"])
                inspect_before, payload_before = self._inspect(image, "before")
                state: dict[str, Any] = {
                    "id": image_id,
                    "reference": image["reference"],
                    "state": "present" if self._verified(image, payload_before) else "download_required",
                    "inspect_before_report": inspect_before["report_path"],
                }
                acquisition_plan.append((image, state, payload_before))

            required_bytes = sum(
                int(image["content_bytes"])
                for image, state, _payload in acquisition_plan
                if state["state"] == "download_required"
            )
            if required_bytes > 0:
                try:
                    available_bytes = self.free_space_provider(self.space_probe_path)
                    if (
                        isinstance(available_bytes, bool)
                        or not isinstance(available_bytes, int)
                        or available_bytes < 0
                    ):
                        raise ValueError("free-space provider returned an invalid byte count")
                except (OSError, ValueError) as exc:
                    disk_space = {
                        "probe_path": str(self.space_probe_path),
                        "required_bytes": required_bytes,
                        "available_bytes": None,
                        "sufficient": False,
                    }
                    failed_states = []
                    for _image, state, _payload in acquisition_plan:
                        failed_state = dict(state)
                        if failed_state["state"] == "download_required":
                            failed_state["state"] = "safe_mode"
                        failed_states.append(failed_state)
                    error = InsufficientDiskError(
                        f"Available Docker host storage could not be determined: {type(exc).__name__}",
                        disk_space=disk_space,
                    )
                    error.images = failed_states
                    raise error from exc
                disk_space = {
                    "probe_path": str(self.space_probe_path),
                    "required_bytes": required_bytes,
                    "available_bytes": available_bytes,
                    "sufficient": available_bytes >= required_bytes,
                }
                if available_bytes < required_bytes:
                    failed_states = []
                    for _image, state, _payload in acquisition_plan:
                        failed_state = dict(state)
                        if failed_state["state"] == "download_required":
                            failed_state["state"] = "safe_mode"
                        failed_states.append(failed_state)
                    error = InsufficientDiskError(
                        "Insufficient Docker host storage for the missing PLwC runtime images",
                        disk_space=disk_space,
                    )
                    error.images = failed_states
                    raise error

            for image, state, payload_before in acquisition_plan:
                image_id = str(image["id"])
                if state["state"] == "download_required":
                    pull = self._run(
                        ["pull", "--platform", "linux/amd64", str(image["reference"])],
                        phase="image_pull",
                        command_id=f"pull-{image_id}",
                    )
                    state["pull_report"] = pull["report_path"]
                    if pull.get("cancelled") or pull.get("timed_out"):
                        state["state"] = "safe_mode"
                        states.append(state)
                        raise CancelledOrTimedOutError(
                            f"{image_id} pull was cancelled or timed out",
                            cancelled=bool(pull.get("cancelled")),
                            timed_out=bool(pull.get("timed_out")),
                        )
                    if pull.get("ok") is not True:
                        state["state"] = "safe_mode"
                        states.append(state)
                        raise PullVerificationError(f"{image_id} pull failed")
                    state["state"] = "pulling"
                inspect_after, payload_after = self._inspect(image, "after")
                state["inspect_after_report"] = inspect_after["report_path"]
                if not self._verified(image, payload_after):
                    state["state"] = "safe_mode"
                    states.append(state)
                    raise PullVerificationError(f"{image_id} digest or platform verification failed")
                state["state"] = "verified"
                probe = self._run(
                    _probe_arguments(image),
                    phase="image_probe",
                    command_id=f"probe-{image_id}",
                )
                state["probe_report"] = probe["report_path"]
                if probe.get("cancelled") or probe.get("timed_out"):
                    state["state"] = "safe_mode"
                    states.append(state)
                    raise CancelledOrTimedOutError(
                        f"{image_id} probe was cancelled or timed out",
                        cancelled=bool(probe.get("cancelled")),
                        timed_out=bool(probe.get("timed_out")),
                    )
                if probe.get("ok") is not True or not _probe_output_ok(
                    image_id, str(probe.get("stdout", "")), str(probe.get("stderr", ""))
                ):
                    state["state"] = "safe_mode"
                    states.append(state)
                    raise ProbeError(f"{image_id} offline probe failed")
                state["state"] = "probe_passed"
                state["observed_image_id"] = payload_after.get("Id") if payload_after else None
                states.append(state)
        except RuntimeImageError as exc:
            if not exc.images:
                exc.images = [
                    *states,
                    *(
                        {"id": image["id"], "reference": image["reference"], "state": "unattempted"}
                        for image in self.manifest["images"]
                        if image["id"] not in {state["id"] for state in states}
                    ),
                ]
            raise
        return {
            "ok": True,
            "phase": "image_acquisition",
            "state": "ready",
            "daemon_report": daemon["report_path"],
            "disk_space": disk_space,
            "images": states,
        }


def _default_space_probe_path() -> Path:
    candidates = [os.environ.get("LOCALAPPDATA"), os.environ.get("TEMP"), os.environ.get("TMP")]
    for raw_path in candidates:
        if raw_path:
            path = Path(raw_path).expanduser()
            if path.exists():
                return path
    return Path.home()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PLwC r27 immutable runtime image manager")
    parser.add_argument("operation", choices=("inventory", "acquire"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--docker", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--process-report-dir", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--consent-token", default="")
    parser.add_argument("--cancel-file")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--inactivity-timeout-seconds", type=int, default=120)
    return parser


def _fallback_report(
    args: argparse.Namespace,
    exc: BaseException,
    *,
    exit_code: int,
    started_at: str | None = None,
    started_monotonic: float | None = None,
) -> dict[str, Any]:
    phase = "image_acquisition" if getattr(args, "operation", "") == "acquire" else "image_inventory"
    report = {
        "schema_version": SCHEMA_VERSION,
        "build_id": str(getattr(args, "build_id", "unknown")),
        "plan_id": str(getattr(args, "plan_id", "unknown")),
        "manifest_sha256": str(getattr(args, "manifest_sha256", "")),
        "phase": phase,
        "category": "docker",
        "command_id": f"runtime-image-manager-{getattr(args, 'operation', 'unknown')}",
        "started": True,
        "started_at": started_at or _utc_now(),
        "finished_at": _utc_now(),
        "duration_ms": (
            max(0, int((time.monotonic() - started_monotonic) * 1000))
            if started_monotonic is not None
            else 0
        ),
        "exit_code": exit_code,
        "timed_out": bool(getattr(exc, "timed_out", False)),
        "cancelled": bool(getattr(exc, "cancelled", False)),
        "stdout": "",
        "stderr": "",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "exception_type": type(exc).__name__,
        "error_category": getattr(exc, "category", "unexpected_error"),
        "error": _redact_text(str(exc)),
        "report_path": str(Path(getattr(args, "report", "runtime-image-error.json")).resolve(strict=False)),
        "ok": False,
        "state": "safe_mode",
        "images": list(getattr(exc, "images", [])),
    }
    disk_space = getattr(exc, "disk_space", None)
    if isinstance(disk_space, Mapping):
        report["disk_space"] = dict(disk_space)
    return _with_report_id(report)


def _write_report_with_fallback(report_path: Path, report: Mapping[str, Any]) -> Path | None:
    try:
        _atomic_write_json(report_path, report)
        return report_path
    except OSError:
        fallback = report_path.with_name("r27-runtime-image-fallback.json")
        fallback_report = dict(report)
        fallback_report["report_path"] = str(fallback.resolve(strict=False))
        try:
            _atomic_write_json(fallback, _with_report_id(fallback_report))
            return fallback
        except OSError:
            return None


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    args.plan_id = uuid.uuid4().hex
    report_path = Path(args.report)
    started_at = _utc_now()
    started_monotonic = time.monotonic()
    try:
        if args.timeout_seconds < 1 or args.timeout_seconds > 3600:
            raise ManifestError("timeout-seconds must be between 1 and 3600")
        if args.inactivity_timeout_seconds < 1 or args.inactivity_timeout_seconds > args.timeout_seconds:
            raise ManifestError("inactivity-timeout-seconds must be between 1 and timeout-seconds")
        manifest = load_manifest(Path(args.manifest), args.manifest_sha256)
        docker = Path(args.docker)
        if not docker.is_file():
            raise DockerUnavailableError("Docker CLI executable is unavailable")
        if args.operation == "acquire" and args.consent_token != CONSENT_TOKEN:
            raise ManifestError("Explicit interactive runtime image consent is missing")
        runner = ProcessRunner(
            Path(args.process_report_dir),
            build_id=args.build_id,
            plan_id=args.plan_id,
            cancel_file=Path(args.cancel_file) if args.cancel_file else None,
        )
        manager = RuntimeImageManager(
            manifest,
            docker,
            runner,
            args.timeout_seconds,
            args.inactivity_timeout_seconds,
        )
        result = manager.inventory() if args.operation == "inventory" else manager.acquire()
        result.update(
            {
                "schema_version": SCHEMA_VERSION,
                "build_id": args.build_id,
                "plan_id": args.plan_id,
                "manifest_sha256": args.manifest_sha256,
                "category": "docker",
                "command_id": f"runtime-image-manager-{args.operation}",
                "started": True,
                "started_at": started_at,
                "finished_at": _utc_now(),
                "duration_ms": max(0, int((time.monotonic() - started_monotonic) * 1000)),
                "exit_code": 0,
                "timed_out": False,
                "cancelled": False,
                "stdout": "",
                "stderr": "",
                "stdout_truncated": False,
                "stderr_truncated": False,
                "exception_type": None,
                "error_category": None,
                "report_path": str(report_path.resolve(strict=False)),
            }
        )
        final = _with_report_id(result)
        _atomic_write_json(report_path, final)
        return 0
    except KeyboardInterrupt:
        interrupted = CancelledOrTimedOutError(
            "Runtime image acquisition was cancelled",
            cancelled=True,
            timed_out=False,
        )
        report = _fallback_report(
            args,
            interrupted,
            exit_code=interrupted.exit_code,
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        _write_report_with_fallback(report_path, report)
        return interrupted.exit_code
    except Exception as exc:
        exit_code = int(getattr(exc, "exit_code", 40))
        report = _fallback_report(
            args,
            exc,
            exit_code=exit_code,
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
        _write_report_with_fallback(report_path, report)
        print(f"PLwC runtime image manager failed: {_redact_text(str(exc))}", file=sys.stderr)
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
