from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit


UPDATE_MANIFEST_SCHEMA_VERSION = "1.0.0"
UPDATE_TRUST_SCHEMA_VERSION = "1.0.0"
SIGNATURE_ALGORITHM = "rsa-sha256-pkcs1v15"
DEFAULT_CHECK_INTERVAL = timedelta(hours=6)
MAX_MANIFEST_BYTES = 1024 * 1024
_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_SAFE_FILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_SEMVER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


class UpdateContractError(ValueError):
    """Raised when update data violates the signed release contract."""


class UpdateSecurityError(UpdateContractError):
    """Raised when authenticity, integrity, or path safety cannot be proven."""


class UpdateConfirmationRequired(UpdateContractError):
    """Raised before every download or install without explicit confirmation."""


class UpdateFetchError(OSError):
    """Raised when a bounded HTTPS fetch cannot be completed."""


FetchBytes = Callable[[str, int], bytes]
InstallRunner = Callable[[Path], int]
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise UpdateContractError(f"{label} must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UpdateContractError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise UpdateContractError(f"{label} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise UpdateContractError(f"Duplicate JSON member is not allowed: {key!r}.")
        result[key] = value
    return result


def parse_manifest_json(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_MANIFEST_BYTES:
        raise UpdateContractError("Release manifest size is invalid.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_without_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateContractError("Release manifest is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise UpdateContractError("Release manifest must be one JSON object.")
    return value


def canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    unsigned = {key: value for key, value in manifest.items() if key != "signature"}
    try:
        text = json.dumps(
            unsigned,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise UpdateContractError("Release manifest cannot be canonically serialized.") from exc
    return text.encode("utf-8")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise UpdateContractError(f"{label} must be an object.")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UpdateContractError(f"{label} must be non-empty text.")
    return value.strip()


def _require_semver(value: Any, label: str) -> str:
    version = _require_text(value, label)
    if _SEMVER_PATTERN.fullmatch(version) is None:
        raise UpdateContractError(f"{label} must be a three-part semantic version.")
    return version


def _require_sha256(value: Any, label: str) -> str:
    digest = _require_text(value, label).casefold()
    if _SHA256_PATTERN.fullmatch(digest) is None:
        raise UpdateContractError(f"{label} must be a lowercase SHA-256 value.")
    return digest


def _require_https_url(value: Any, label: str) -> str:
    url = _require_text(value, label)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise UpdateSecurityError(f"{label} must be an HTTPS URL without credentials or fragment.")
    return url


def load_trusted_release_keys(path: Path) -> dict[str, dict[str, int]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_object_without_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateContractError(f"Release trust store could not be read safely: {exc}") from exc
    root = _require_mapping(value, "release trust store")
    if root.get("schema_version") != UPDATE_TRUST_SCHEMA_VERSION:
        raise UpdateContractError("Unsupported release trust-store schema version.")
    raw_keys = root.get("keys")
    if not isinstance(raw_keys, list):
        raise UpdateContractError("release trust store keys must be an array.")
    keys: dict[str, dict[str, int]] = {}
    for index, raw_key in enumerate(raw_keys):
        key = _require_mapping(raw_key, f"keys[{index}]")
        if key.get("algorithm") != SIGNATURE_ALGORITHM:
            raise UpdateContractError("Unsupported release public-key algorithm.")
        key_id = _require_text(key.get("key_id"), f"keys[{index}].key_id")
        if key_id in keys:
            raise UpdateContractError("Release public-key identifiers must be unique.")
        modulus_hex = _require_text(key.get("modulus_hex"), f"keys[{index}].modulus_hex")
        try:
            modulus = int(modulus_hex, 16)
            exponent = int(key.get("exponent"))
        except (TypeError, ValueError) as exc:
            raise UpdateContractError("Release public key contains invalid RSA parameters.") from exc
        if modulus.bit_length() < 2048 or exponent < 3 or exponent % 2 == 0:
            raise UpdateSecurityError("Release public key does not meet the RSA safety floor.")
        keys[key_id] = {"exponent": exponent, "modulus": modulus}
    return keys


def _verify_rsa_sha256_pkcs1v15(message: bytes, signature: bytes, *, modulus: int, exponent: int) -> bool:
    size = (modulus.bit_length() + 7) // 8
    if len(signature) != size:
        return False
    signature_value = int.from_bytes(signature, "big")
    if signature_value <= 0 or signature_value >= modulus:
        return False
    encoded = pow(signature_value, exponent, modulus).to_bytes(size, "big")
    digest_info = _SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(message).digest()
    padding_length = size - len(digest_info) - 3
    if padding_length < 8:
        return False
    expected = b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info
    return hmac.compare_digest(encoded, expected)


def verify_release_manifest(
    manifest: Mapping[str, Any],
    trusted_keys: Mapping[str, Mapping[str, int]],
) -> dict[str, Any]:
    signature = _require_mapping(manifest.get("signature"), "signature")
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        raise UpdateSecurityError("Release manifest uses an unsupported signature algorithm.")
    key_id = _require_text(signature.get("key_id"), "signature.key_id")
    key = trusted_keys.get(key_id)
    if key is None:
        raise UpdateSecurityError("Release manifest is signed by an untrusted key.")
    try:
        signature_bytes = base64.b64decode(
            _require_text(signature.get("value_base64"), "signature.value_base64"),
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise UpdateSecurityError("Release manifest signature encoding is invalid.") from exc
    if not _verify_rsa_sha256_pkcs1v15(
        canonical_manifest_bytes(manifest),
        signature_bytes,
        modulus=int(key["modulus"]),
        exponent=int(key["exponent"]),
    ):
        raise UpdateSecurityError("Release manifest signature verification failed.")
    return _validate_release_manifest(manifest)


def _validate_release_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") != UPDATE_MANIFEST_SCHEMA_VERSION:
        raise UpdateContractError("Unsupported release-manifest schema version.")
    product = _require_mapping(manifest.get("product"), "product")
    _require_text(product.get("name"), "product.name")
    _require_semver(product.get("version"), "product.version")
    _require_text(product.get("installer_revision"), "product.installer_revision")

    release = _require_mapping(manifest.get("release"), "release")
    _parse_timestamp(release.get("published_at"), "release.published_at")
    if release.get("update_kind") not in {"recommended", "required"}:
        raise UpdateContractError("release.update_kind must be recommended or required.")
    notes = _require_mapping(release.get("notes"), "release.notes")
    _require_text(notes.get("de"), "release.notes.de")
    _require_text(notes.get("en"), "release.notes.en")

    components = manifest.get("components")
    if not isinstance(components, list) or not components:
        raise UpdateContractError("components must be a non-empty array.")
    component_ids: set[str] = set()
    for index, raw_component in enumerate(components):
        component = _require_mapping(raw_component, f"components[{index}]")
        component_id = _require_text(component.get("id"), f"components[{index}].id")
        if component_id in component_ids:
            raise UpdateContractError("Release component identifiers must be unique.")
        component_ids.add(component_id)
        _require_semver(component.get("version"), f"components[{index}].version")
        compatibility = _require_mapping(component.get("compatibility"), f"components[{index}].compatibility")
        _require_semver(compatibility.get("minimum"), f"components[{index}].compatibility.minimum")
        _require_semver(
            compatibility.get("maximum_exclusive"),
            f"components[{index}].compatibility.maximum_exclusive",
        )

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise UpdateContractError("artifacts must be a non-empty array.")
    artifact_ids: set[str] = set()
    for index, raw_artifact in enumerate(artifacts):
        artifact = _require_mapping(raw_artifact, f"artifacts[{index}]")
        artifact_id = _require_text(artifact.get("id"), f"artifacts[{index}].id")
        if artifact_id in artifact_ids:
            raise UpdateContractError("Release artifact identifiers must be unique.")
        artifact_ids.add(artifact_id)
        if artifact.get("kind") != "windows_installer":
            raise UpdateContractError("Only the governed Windows installer artifact is supported.")
        file_name = _require_text(artifact.get("file_name"), f"artifacts[{index}].file_name")
        if _SAFE_FILE_NAME_PATTERN.fullmatch(file_name) is None or not file_name.casefold().endswith(".exe"):
            raise UpdateSecurityError("Release artifact file_name is unsafe.")
        _require_https_url(artifact.get("url"), f"artifacts[{index}].url")
        if type(artifact.get("size")) is not int or not 0 < int(artifact["size"]) <= 2 * 1024 * 1024 * 1024:
            raise UpdateContractError("Release artifact size is outside the supported range.")
        digest = _require_sha256(artifact.get("sha256"), f"artifacts[{index}].sha256")
        identity = _require_mapping(artifact.get("build_identity"), f"artifacts[{index}].build_identity")
        if identity.get("schema_version") != 1:
            raise UpdateContractError("Release artifact build identity schema is unsupported.")
        _require_text(identity.get("build_id"), f"artifacts[{index}].build_identity.build_id")
        _require_semver(identity.get("product_version"), f"artifacts[{index}].build_identity.product_version")
        _require_text(
            identity.get("installer_revision"),
            f"artifacts[{index}].build_identity.installer_revision",
        )
        if _require_sha256(identity.get("sha256"), f"artifacts[{index}].build_identity.sha256") != digest:
            raise UpdateSecurityError("Artifact hash and signed build identity hash do not match.")

    return dict(manifest)


def _default_fetch_bytes(url: str, maximum_bytes: int) -> bytes:
    _require_https_url(url, "download URL")
    request = urllib.request.Request(url, headers={"User-Agent": "PLwC-UpdateCenter/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            final_url = response.geturl()
            _require_https_url(final_url, "redirected download URL")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > maximum_bytes:
                raise UpdateFetchError("Download exceeds its bounded maximum size.")
            data = response.read(maximum_bytes + 1)
    except UpdateSecurityError:
        raise
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise UpdateFetchError(str(exc)) from exc
    if len(data) > maximum_bytes:
        raise UpdateFetchError("Download exceeds its bounded maximum size.")
    return data


class UpdateCenter:
    def __init__(
        self,
        *,
        state_root: Path,
        manifest_url: str,
        trusted_keys: Mapping[str, Mapping[str, int]],
        fetch_bytes: FetchBytes | None = None,
        check_interval: timedelta = DEFAULT_CHECK_INTERVAL,
        clock: Clock = _utc_now,
    ) -> None:
        self.state_root = state_root.resolve(strict=False)
        self.manifest_url = _require_https_url(manifest_url, "manifest URL")
        self.trusted_keys = {key: dict(value) for key, value in trusted_keys.items()}
        self.fetch_bytes = fetch_bytes or _default_fetch_bytes
        self.check_interval = check_interval
        self.clock = clock
        self.update_root = self.state_root / "updates"
        self.status_path = self.update_root / "status.json"
        self.manifest_path = self.update_root / "last-valid-manifest.json"
        self.plan_path = self.update_root / "download-plan.json"
        self.download_root = self.update_root / "downloads"

    def snapshot(self) -> dict[str, Any]:
        status = self._read_json(self.status_path) or self._empty_status()
        status["check_due"] = self._check_due(status)
        status["manifest_url"] = self.manifest_url
        status["telemetry"] = False
        return status

    def check(self, *, force: bool = False) -> dict[str, Any]:
        previous = self._read_json(self.status_path) or self._empty_status()
        if not force and not self._check_due(previous):
            return self.snapshot()
        checked_at = self.clock()
        try:
            raw = self.fetch_bytes(self.manifest_url, MAX_MANIFEST_BYTES)
            parsed = parse_manifest_json(raw)
            verified = verify_release_manifest(parsed, self.trusted_keys)
        except (UpdateSecurityError, UpdateContractError) as exc:
            status = self._failure_status("rejected", str(exc), checked_at, previous)
        except (OSError, TimeoutError, UpdateFetchError) as exc:
            status = self._failure_status("offline", str(exc), checked_at, previous)
        else:
            self._atomic_write_json(self.manifest_path, verified)
            status = {
                "state": "update_available",
                "update_kind": verified["release"]["update_kind"],
                "integrity_verified": True,
                "last_checked_at": _iso(checked_at),
                "last_valid_at": _iso(checked_at),
                "error": None,
                "release": self._release_summary(verified),
            }
        self._atomic_write_json(self.status_path, status)
        return self.snapshot()

    def plan_download(self, artifact_id: str) -> dict[str, Any]:
        manifest = self._load_verified_manifest()
        artifact = self._artifact(manifest, artifact_id)
        plan = {
            "artifact": dict(artifact),
            "confirmation_required": True,
            "created_at": _iso(self.clock()),
            "manifest_sha256": self._manifest_digest(manifest),
            "plan_type": "release_download",
        }
        plan_id = hashlib.sha256(self._canonical_json(plan)).hexdigest()
        result = {**plan, "plan_id": plan_id}
        self._atomic_write_json(self.plan_path, result)
        return result

    def download(self, plan_id: str, *, confirmed: bool) -> dict[str, Any]:
        if confirmed is not True:
            raise UpdateConfirmationRequired("Update download requires explicit confirmation.")
        plan, manifest, artifact = self._validated_plan(plan_id)
        self.download_root.mkdir(parents=True, exist_ok=True)
        target = (self.download_root / str(artifact["file_name"])).resolve(strict=False)
        if not self._is_inside(target, self.download_root):
            raise UpdateSecurityError("Update download target escaped its managed directory.")
        maximum = int(artifact["size"])
        part = target.with_name(f".{target.name}.{uuid.uuid4().hex}.part")
        try:
            data = self.fetch_bytes(str(artifact["url"]), maximum)
            if len(data) != maximum:
                raise UpdateSecurityError("Downloaded artifact size does not match the signed manifest.")
            digest = hashlib.sha256(data).hexdigest()
            if digest != artifact["sha256"]:
                raise UpdateSecurityError("Downloaded artifact hash does not match the signed manifest.")
            part.write_bytes(data)
            os.replace(part, target)
        finally:
            if part.exists():
                part.unlink()
        result = {
            "ok": True,
            "state": "download_verified",
            "plan_id": plan["plan_id"],
            "artifact_path": str(target),
            "size": maximum,
            "sha256": artifact["sha256"],
            "build_identity": dict(artifact["build_identity"]),
            "integrity_verified": True,
            "install_confirmation_required": True,
        }
        self._write_operation_status(result)
        return result

    def install(
        self,
        plan_id: str,
        *,
        confirmed: bool,
        runner: InstallRunner | None = None,
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise UpdateConfirmationRequired("Update installation requires explicit confirmation.")
        plan, _manifest, artifact = self._validated_plan(plan_id)
        target = (self.download_root / str(artifact["file_name"])).resolve(strict=False)
        self._verify_downloaded_artifact(target, artifact)
        invoke = runner or self._run_installer
        return_code = int(invoke(target))
        rollback_report = self.state_root / "installer-r26" / "last-failure.json"
        result = {
            "ok": return_code == 0,
            "state": "installer_completed" if return_code == 0 else "installer_failed",
            "plan_id": plan["plan_id"],
            "artifact_path": str(target),
            "return_code": return_code,
            "integrity_verified": True,
            "build_identity_verified": True,
            "postflight_delegated_to": "installer-r26",
            "rollback_report": str(rollback_report) if rollback_report.is_file() else None,
        }
        self._write_operation_status(result)
        return result

    def _validated_plan(
        self,
        plan_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], Mapping[str, Any]]:
        plan = self._read_json(self.plan_path)
        if plan is None or not isinstance(plan_id, str) or plan.get("plan_id") != plan_id:
            raise UpdateSecurityError("Update plan ID is unknown or stale.")
        stable = {key: value for key, value in plan.items() if key != "plan_id"}
        expected_id = hashlib.sha256(self._canonical_json(stable)).hexdigest()
        if expected_id != plan_id:
            raise UpdateSecurityError("Update plan content no longer matches its plan ID.")
        manifest = self._load_verified_manifest()
        if plan.get("manifest_sha256") != self._manifest_digest(manifest):
            raise UpdateSecurityError("Update plan refers to a different release manifest.")
        plan_artifact = _require_mapping(plan.get("artifact"), "download plan artifact")
        artifact = self._artifact(manifest, _require_text(plan_artifact.get("id"), "artifact.id"))
        if dict(plan_artifact) != dict(artifact):
            raise UpdateSecurityError("Update plan artifact no longer matches the signed manifest.")
        return plan, manifest, artifact

    def _load_verified_manifest(self) -> dict[str, Any]:
        manifest = self._read_json(self.manifest_path)
        if manifest is None:
            raise UpdateSecurityError("No verified release manifest is cached.")
        return verify_release_manifest(manifest, self.trusted_keys)

    @staticmethod
    def _artifact(manifest: Mapping[str, Any], artifact_id: str) -> Mapping[str, Any]:
        for artifact in manifest.get("artifacts", []):
            if isinstance(artifact, Mapping) and artifact.get("id") == artifact_id:
                return artifact
        raise UpdateContractError("Requested release artifact is not present in the verified manifest.")

    @staticmethod
    def _verify_downloaded_artifact(path: Path, artifact: Mapping[str, Any]) -> None:
        if not path.is_file() or path.stat().st_size != int(artifact["size"]):
            raise UpdateSecurityError("Downloaded update is missing or has the wrong size.")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != artifact["sha256"]:
            raise UpdateSecurityError("Downloaded update hash verification failed before installation.")
        identity = _require_mapping(artifact.get("build_identity"), "artifact.build_identity")
        if identity.get("sha256") != digest:
            raise UpdateSecurityError("Signed build identity does not match the downloaded update.")

    @staticmethod
    def _run_installer(path: Path) -> int:
        return subprocess.run([str(path)], check=False).returncode

    def _failure_status(
        self,
        state: str,
        error: str,
        checked_at: datetime,
        previous: Mapping[str, Any],
    ) -> dict[str, Any]:
        cached = self._read_json(self.manifest_path)
        return {
            "state": state,
            "update_kind": previous.get("update_kind"),
            "integrity_verified": False,
            "last_checked_at": _iso(checked_at),
            "last_valid_at": previous.get("last_valid_at"),
            "error": error,
            "cached_release_available": cached is not None,
            "release": self._release_summary(cached) if cached is not None else previous.get("release"),
        }

    def _check_due(self, status: Mapping[str, Any]) -> bool:
        raw = status.get("last_checked_at")
        if not isinstance(raw, str):
            return True
        try:
            checked = _parse_timestamp(raw, "last_checked_at")
        except UpdateContractError:
            return True
        return self.clock() - checked >= self.check_interval

    @staticmethod
    def _empty_status() -> dict[str, Any]:
        return {
            "state": "never_checked",
            "update_kind": None,
            "integrity_verified": False,
            "last_checked_at": None,
            "last_valid_at": None,
            "error": None,
            "release": None,
        }

    @staticmethod
    def _release_summary(manifest: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if manifest is None:
            return None
        product = manifest.get("product")
        release = manifest.get("release")
        artifacts = manifest.get("artifacts")
        if not isinstance(product, Mapping) or not isinstance(release, Mapping) or not isinstance(artifacts, list):
            return None
        return {
            "product": dict(product),
            "published_at": release.get("published_at"),
            "update_kind": release.get("update_kind"),
            "notes": release.get("notes"),
            "artifacts": [
                {
                    "id": artifact.get("id"),
                    "file_name": artifact.get("file_name"),
                    "size": artifact.get("size"),
                    "sha256": artifact.get("sha256"),
                    "build_identity": artifact.get("build_identity"),
                }
                for artifact in artifacts
                if isinstance(artifact, Mapping)
            ],
        }

    def _write_operation_status(self, operation: Mapping[str, Any]) -> None:
        status = self._read_json(self.status_path) or self._empty_status()
        status["last_operation"] = dict(operation)
        self._atomic_write_json(self.status_path, status)

    def _manifest_digest(self, manifest: Mapping[str, Any]) -> str:
        return hashlib.sha256(self._canonical_json(manifest)).hexdigest()

    @staticmethod
    def _canonical_json(value: Any) -> bytes:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _is_inside(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root.resolve(strict=False))
            return True
        except ValueError:
            return False

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object_without_duplicate_keys)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, UpdateContractError):
            return None
        return dict(value) if isinstance(value, dict) else None

    def _atomic_write_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        resolved = path.resolve(strict=False)
        if not self._is_inside(resolved, self.update_root):
            raise UpdateSecurityError("Update state target escaped its managed directory.")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        temporary = resolved.with_name(f".{resolved.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, resolved)
        finally:
            if temporary.exists():
                temporary.unlink()
