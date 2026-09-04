from __future__ import annotations

import argparse
import configparser
import hashlib
import hmac
import importlib.metadata as importlib_metadata
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit


def _bootstrap_gateway_import_path() -> None:
    candidates: list[Path] = []
    arguments = sys.argv[1:]
    if "--gateway-root" in arguments:
        index = arguments.index("--gateway-root")
        if index + 1 < len(arguments):
            candidates.append(Path(arguments[index + 1]))
    configured = os.environ.get("PLWC_CONFIG_GATEWAY_ROOT")
    if configured:
        candidates.append(Path(configured))
    app_root = Path(__file__).resolve().parent.parent
    candidates.append(app_root / "gateway")
    candidates.extend(sorted(app_root.glob("gateway-*"), reverse=True))
    for root in candidates:
        source_root = root.expanduser().resolve(strict=False) / "src"
        if (source_root / "plwc_gateway" / "__init__.py").is_file():
            sys.path.insert(0, str(source_root))
            return


_bootstrap_gateway_import_path()

from plwc_gateway import __version__
from plwc_gateway.adapters.docker_cli import resolve_docker_executable
from plwc_gateway.adapters.document_worker import DOCUMENT_WORKER_IMAGE
from plwc_gateway.config.settings import SHARED_SETTINGS_FILE_NAME, default_app_root, load_gateway_config
from plwc_gateway.installation.component_inventory import (
    InventoryContractError,
    build_component_inventory,
    load_compatibility_matrix,
)
from plwc_gateway.installation.doctor import DoctorContractError, InstallationDoctor
from plwc_gateway.installation.update_center import (
    UpdateCenter,
    UpdateContractError,
    load_trusted_release_keys,
)
from plwc_gateway.mcp.server import (
    clu_doctor_diagnose,
    plwc_governor,
    runtime_status_diagnose,
)


EDITABLE_SETTING_KEYS = {
    "memory_write_threshold",
    "persona_write_threshold",
    "temperament_write_threshold",
    "qdrant_enabled",
    "persona_layer_enabled",
}
INSTALLATION_SETTING_KEYS = EDITABLE_SETTING_KEYS | {"workspace_path"}
SHARED_SETTING_KEYS = {
    "workspace_path",
    "profiles_path",
    "active_profile_name",
    "security_config",
    "memory_write_threshold",
    "persona_write_threshold",
    "temperament_write_threshold",
    "qdrant_enabled",
    "persona_layer_disabled",
}
THRESHOLD_KEYS = {
    "memory_write_threshold",
    "persona_write_threshold",
    "temperament_write_threshold",
}
ONBOARDING_FIELD_KEYS = (
    "profile_name",
    "role_use_case",
    "preferred_name",
    "form_of_address",
    "tone",
    "working_style",
    "strictness",
    "memory_scope",
    "confirmation_boundaries",
    "project_context",
    "language_preference",
    "special_instructions",
)
MAX_JSON_BYTES = 64 * 1024
SESSION_COOKIE = "plwc_config_session"
DEFAULT_RELEASE_MANIFEST_URL = (
    "https://github.com/mhoedt-ai/PLwC/releases/latest/download/plwc-release-manifest.json"
)


class ConfigurationError(ValueError):
    pass


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _atomic_write_json(path: Path, payload: dict[str, Any], *, root: Path) -> None:
    resolved_root = root.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    if not _is_inside(resolved_path, resolved_root):
        raise ConfigurationError("Shared settings path escapes the PLwC configuration root.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp")
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _atomic_write_text(path: Path, content: str, *, root: Path) -> None:
    resolved_root = root.resolve(strict=False)
    resolved_path = path.resolve(strict=False)
    if not _is_inside(resolved_path, resolved_root):
        raise ConfigurationError("Generated configuration path escapes its allowed root.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _read_generated_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def _normalize_workspace_path(value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("Choose an absolute workspace path.")
    text = value.strip()
    if any(ord(character) < 32 for character in text):
        raise ConfigurationError("The workspace path contains unsupported control characters.")
    path = Path(text).expanduser()
    if not path.is_absolute():
        raise ConfigurationError("The workspace path must be absolute.")
    return path.resolve(strict=False)


def _normalize_settings(value: Any) -> dict[str, int | bool]:
    if not isinstance(value, dict) or set(value) != EDITABLE_SETTING_KEYS:
        raise ConfigurationError("Settings must contain exactly the supported PLwC controls.")
    normalized: dict[str, int | bool] = {}
    for key in THRESHOLD_KEYS:
        raw = value.get(key)
        if type(raw) is not int or raw < 1 or raw > 1_000_000:
            raise ConfigurationError(f"{key} must be a whole number from 1 through 1000000.")
        normalized[key] = raw
    for key in ("qdrant_enabled", "persona_layer_enabled"):
        raw = value.get(key)
        if type(raw) is not bool:
            raise ConfigurationError(f"{key} must be true or false.")
        normalized[key] = raw
    return normalized


def _normalize_installation_settings(value: Any) -> dict[str, int | bool | str]:
    if not isinstance(value, dict) or set(value) != INSTALLATION_SETTING_KEYS:
        raise ConfigurationError("Installation settings must contain exactly the supported PLwC controls.")
    normalized: dict[str, int | bool | str] = {
        **_normalize_settings({key: value.get(key) for key in EDITABLE_SETTING_KEYS}),
        "workspace_path": str(_normalize_workspace_path(value.get("workspace_path"))),
    }
    return normalized


def _canonical_digest(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _workspace_plan_digest(data: dict[str, Any]) -> str:
    return _canonical_digest(
        {
            "plan_type": data.get("plan_type"),
            "current_workspace_path": data.get("current_workspace_path"),
            "requested_workspace_path": data.get("requested_workspace_path"),
            "path_exists": data.get("path_exists"),
            "nearest_existing_parent": data.get("nearest_existing_parent"),
            "writable": data.get("writable"),
            "valid": data.get("valid"),
            "planned_writes": list(data.get("planned_writes") or []),
            "data_migration": data.get("data_migration"),
        }
    )


def _sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _observed_source(kind: str, detail: str | None = None) -> dict[str, Any]:
    source: dict[str, Any] = {
        "kind": kind,
        "trust": "observed_local",
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if detail:
        source["detail"] = detail
    return source


def _unavailable_source(kind: str, detail: str | None = None) -> dict[str, Any]:
    source: dict[str, Any] = {
        "kind": kind,
        "trust": "unavailable",
        "observed_at": None,
    }
    if detail:
        source["detail"] = detail
    return source


def _run_local_probe(
    args: list[str],
    *,
    runner: Any = None,
    timeout: int = 5,
) -> subprocess.CompletedProcess[str] | None:
    command_runner = runner or subprocess.run
    try:
        return command_runner(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _docker_component_observations(
    docker_path: str | None,
    *,
    installer_selected: bool,
    runner: Any = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Observe Docker and the prepared worker image without changing local state."""

    if not docker_path:
        docker_source = (
            _unavailable_source("docker_cli", "installer selection reports Docker")
            if installer_selected
            else _observed_source("docker_cli", "not detected")
        )
        docker_observation = {
            "present": None if installer_selected else False,
            "source": docker_source,
        }
        worker_observation = {
            "present": None if installer_selected else False,
            "source": (
                _unavailable_source("docker_image_inspect", DOCUMENT_WORKER_IMAGE)
                if installer_selected
                else _observed_source("docker_image_inspect", "Docker CLI not detected")
            ),
        }
        return docker_observation, worker_observation

    cli_result = _run_local_probe([docker_path, "--version"], runner=runner)
    cli_text = "\n".join(
        part for part in ((cli_result.stdout if cli_result else ""), (cli_result.stderr if cli_result else "")) if part
    )
    cli_match = re.search(r"\bDocker version\s+([0-9]+\.[0-9]+\.[0-9]+)", cli_text)
    cli_version = cli_match.group(1) if cli_match else None

    daemon_result = _run_local_probe(
        [docker_path, "version", "--format", "{{.Server.Version}}"],
        runner=runner,
    )
    daemon_version = (
        daemon_result.stdout.strip()
        if daemon_result is not None and daemon_result.returncode == 0
        else ""
    )
    daemon_ready = bool(
        daemon_version
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", daemon_version)
    )
    docker_observation = {
        "present": True,
        "semantic_version": cli_version or (daemon_version if daemon_ready else None),
        "postflight_verified": daemon_ready,
        "source": _observed_source(
            "docker_cli",
            f"{docker_path}; daemon={'running' if daemon_ready else 'unavailable'}",
        ),
    }

    if not daemon_ready:
        return docker_observation, {
            "present": None,
            "source": _unavailable_source("docker_image_inspect", DOCUMENT_WORKER_IMAGE),
        }

    inspect_result = _run_local_probe(
        [docker_path, "image", "inspect", DOCUMENT_WORKER_IMAGE, "--format", "{{.Id}}"],
        runner=runner,
    )
    if inspect_result is None:
        return docker_observation, {
            "present": None,
            "source": _unavailable_source("docker_image_inspect", DOCUMENT_WORKER_IMAGE),
        }
    if inspect_result.returncode != 0:
        return docker_observation, {
            "present": False,
            "source": _observed_source("docker_image_inspect", DOCUMENT_WORKER_IMAGE),
        }

    image_id = inspect_result.stdout.strip()
    image_version = DOCUMENT_WORKER_IMAGE.rpartition(":")[2] or None
    return docker_observation, {
        "present": True,
        "semantic_version": image_version,
        "build_id": image_id or None,
        "postflight_verified": bool(image_id),
        "source": _observed_source(
            "docker_image_inspect",
            f"{DOCUMENT_WORKER_IMAGE}@{image_id}" if image_id else DOCUMENT_WORKER_IMAGE,
        ),
    }


def _python_distribution_observation(distribution: str, *, enabled: bool) -> dict[str, Any]:
    """Report the package installed in the configuration UI's active Python runtime."""

    detail = f"{distribution}; enabled={'true' if enabled else 'false'}"
    try:
        version = importlib_metadata.version(distribution)
    except importlib_metadata.PackageNotFoundError:
        return {
            "present": False,
            "source": _observed_source("python_distribution", detail),
        }
    except (OSError, ValueError):
        return {
            "present": None,
            "source": _unavailable_source("python_distribution", detail),
        }
    return {
        "present": True,
        "semantic_version": version,
        "source": _observed_source("python_distribution", detail),
    }


def _normalize_onboarding_answers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ConfigurationError("Profile onboarding answers must be a JSON object.")
    unknown = set(value) - set(ONBOARDING_FIELD_KEYS)
    if unknown:
        names = ", ".join(sorted(str(name) for name in unknown))
        raise ConfigurationError(f"Profile onboarding contains unsupported fields: {names}.")
    normalized: dict[str, str] = {}
    for key in ONBOARDING_FIELD_KEYS:
        raw = value.get(key, "")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            raise ConfigurationError(f"Profile onboarding field {key} must be text.")
        text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
        if any(character == "\x00" or (ord(character) < 32 and character not in "\n\t") for character in text):
            raise ConfigurationError(f"Profile onboarding field {key} contains unsupported control characters.")
        if len(text) > 2_000:
            raise ConfigurationError(f"Profile onboarding field {key} is too long.")
        normalized[key] = text
    if not normalized["profile_name"]:
        raise ConfigurationError("Choose a name for the new profile.")
    return normalized


def _profile_plan_digest(data: dict[str, Any]) -> str:
    validation = data.get("validation") if isinstance(data.get("validation"), dict) else {}
    stable_plan = {
        "plan_type": data.get("plan_type"),
        "current_active_profile": data.get("current_active_profile"),
        "requested_active_profile": data.get("requested_active_profile"),
        "target_profile_directory": data.get("target_profile_directory"),
        "missing_files": list(data.get("missing_files") or []),
        "planned_writes": list(data.get("planned_writes") or []),
        "validation": {
            "valid": validation.get("valid"),
            "reason": validation.get("reason"),
            "target_profile_exists": validation.get("target_profile_exists"),
            "required_profile_files_present": validation.get("required_profile_files_present"),
            "missing_files": list(validation.get("missing_files") or []),
        },
    }
    return _canonical_digest(stable_plan)


def _profile_creation_plan_digest(data: dict[str, Any]) -> str:
    previews = data.get("file_previews") if isinstance(data.get("file_previews"), dict) else {}
    preview_hashes = {
        str(name): hashlib.sha256(str(content).encode("utf-8")).hexdigest()
        for name, content in previews.items()
    }
    activation = data.get("activation_after_apply") if isinstance(data.get("activation_after_apply"), dict) else {}
    stable_plan = {
        "plan_type": data.get("plan_type"),
        "target_profile": data.get("target_profile"),
        "profile_directory": data.get("profile_directory"),
        "decision": data.get("decision"),
        "approved_for_apply": data.get("approved_for_apply"),
        "normalized_onboarding_answers": data.get("normalized_onboarding_answers"),
        "missing_required_fields": list(data.get("missing_required_fields") or []),
        "target_files": list(data.get("target_files") or []),
        "planned_writes": list(data.get("planned_writes") or []),
        "file_preview_sha256": preview_hashes,
        "activation_after_apply": {
            "active_profile_name": activation.get("active_profile_name"),
            "active_state_write_planned": activation.get("active_state_write_planned"),
            "activation_effective_after_apply": activation.get("activation_effective_after_apply"),
            "activation_blocked_reason": activation.get("activation_blocked_reason"),
            "active_profile_source_after": activation.get("active_profile_source_after"),
        },
    }
    return _canonical_digest(stable_plan)


class PlwcConfigurationService:
    def __init__(
        self,
        project_root: Path,
        *,
        installer_config_root: Path | None = None,
        gateway_root: Path | None = None,
        language: str = "en",
        doctor_system_probes: bool = True,
        update_center: UpdateCenter | None = None,
    ) -> None:
        self.project_root = project_root.resolve(strict=False)
        self.installer_config_root = (
            installer_config_root.resolve(strict=False)
            if installer_config_root is not None
            else self.project_root / "config"
        )
        self.gateway_root = gateway_root.resolve(strict=False) if gateway_root is not None else None
        self.language = "de" if language.casefold().startswith("de") else "en"
        self.doctor_system_probes = doctor_system_probes
        self.settings_path = self.project_root / "config" / SHARED_SETTINGS_FILE_NAME
        self.selection_path = self.installer_config_root / "installer" / "selection.ini"
        self._write_lock = threading.Lock()
        self._doctor_diagnoses: dict[str, dict[str, Any]] = {}
        self._doctor_plans: dict[str, dict[str, Any]] = {}
        self.update_center = update_center or self._create_update_center()

    def _compatibility_matrix_path(self) -> Path | None:
        candidates: list[Path] = []
        if self.gateway_root is not None:
            candidates.append(self.gateway_root / "config" / "compatibility-matrix.json")
        candidates.extend(
            (
                self.project_root / "app" / "gateway" / "config" / "compatibility-matrix.json",
                self.project_root / "config" / "compatibility-matrix.json",
                Path(__file__).resolve().parents[4] / "config" / "compatibility-matrix.json",
            )
        )
        return next((path for path in candidates if path.is_file()), None)

    def _release_trust_path(self) -> Path | None:
        candidates: list[Path] = []
        if self.gateway_root is not None:
            candidates.append(self.gateway_root / "config" / "release-trust.json")
        candidates.extend(
            (
                self.project_root / "app" / "gateway" / "config" / "release-trust.json",
                self.project_root / "config" / "release-trust.json",
                Path(__file__).resolve().parents[4] / "config" / "release-trust.json",
            )
        )
        return next((path for path in candidates if path.is_file()), None)

    def _create_update_center(self) -> UpdateCenter:
        trust_path = self._release_trust_path()
        trusted_keys = load_trusted_release_keys(trust_path) if trust_path is not None else {}
        return UpdateCenter(
            state_root=self.project_root / "state",
            manifest_url=DEFAULT_RELEASE_MANIFEST_URL,
            trusted_keys=trusted_keys,
        )

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        return dict(value) if isinstance(value, dict) else None

    def _last_launcher_result(self, selection: configparser.ConfigParser | None = None) -> dict[str, Any] | None:
        parser = selection or self._read_installer_selection()
        candidates = [self.project_root / "state" / "chat-bridge" / "launcher-last-result.json"]
        state_root = parser.get("PLwC", "StatePath", fallback="").strip()
        if state_root:
            candidates.insert(0, Path(state_root) / "chat-bridge" / "launcher-last-result.json")
        for path in candidates:
            result = self._read_json_object(path)
            if result is not None:
                result["state_file"] = str(path)
                return result
        return None

    def _browser_extension_contact(
        self,
        selection: configparser.ConfigParser | None = None,
    ) -> dict[str, Any] | None:
        parser = selection or self._read_installer_selection()
        candidates = [self.project_root / "state" / "chat-bridge" / "browser-extension-last-contact.json"]
        state_root = parser.get("PLwC", "StatePath", fallback="").strip()
        if state_root:
            candidates.insert(0, Path(state_root) / "chat-bridge" / "browser-extension-last-contact.json")
        for path in candidates:
            contact = self._read_json_object(path)
            if contact is None:
                continue
            received_at = contact.get("receivedAt")
            age_seconds: int | None = None
            if isinstance(received_at, str):
                try:
                    observed = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
                    if observed.tzinfo is None:
                        observed = observed.replace(tzinfo=timezone.utc)
                    age_seconds = max(0, int((datetime.now(timezone.utc) - observed).total_seconds()))
                except ValueError:
                    age_seconds = None
            contact["age_seconds"] = age_seconds
            contact["stale"] = age_seconds is None or age_seconds > 24 * 60 * 60
            contact["state_file"] = str(path)
            return contact
        return None

    @staticmethod
    def _component_version_from_build_id(build_id: str) -> str | None:
        match = re.search(r"@(?P<version>[0-9]+\.[0-9]+\.[0-9]+)(?:[/#]|$)", build_id)
        return match.group("version") if match else None

    @staticmethod
    def _command_version(command: str, pattern: str) -> str | None:
        try:
            completed = subprocess.run(
                [command, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        match = re.search(pattern, f"{completed.stdout}\n{completed.stderr}")
        return match.group(1) if match else None

    def _component_inventory(self, status: dict[str, Any], config: Any) -> dict[str, Any]:
        matrix_path = self._compatibility_matrix_path()
        if matrix_path is None:
            return {
                "schema_version": "1.0.0",
                "matrix_version": None,
                "release_family": None,
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "components": [],
                "summary": {"unknown": 0},
                "error": "compatibility_matrix_missing",
            }
        try:
            matrix = load_compatibility_matrix(matrix_path)
        except InventoryContractError as exc:
            return {
                "schema_version": "1.0.0",
                "matrix_version": None,
                "release_family": None,
                "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "components": [],
                "summary": {"unknown": 0},
                "error": str(exc),
            }

        selection = self._read_installer_selection()
        build_id = selection.get("BuildIdentity", "BuildId", fallback="").strip()
        installer_revision = selection.get("BuildIdentity", "InstallerRevision", fallback="").strip()
        setup_sha256 = selection.get("BuildIdentity", "SetupExeSha256", fallback="").strip().casefold()
        installed_version = self._component_version_from_build_id(build_id)
        source = _observed_source("installer_selection", str(self.selection_path))
        app_path = selection.get("PLwC", "AppPath", fallback="").strip()
        gateway_path = selection.get("PLwC", "GatewayPath", fallback="").strip()
        bridge_path_value = selection.get("PLwC", "BridgePath", fallback="").strip()
        bridge_root = Path(bridge_path_value).resolve(strict=False) if bridge_path_value else None
        bridge_identity_path = bridge_root / "build-identity.json" if bridge_root is not None else None
        bridge_identity = (
            self._read_json_object(bridge_identity_path)
            if bridge_identity_path is not None and bridge_identity_path.is_file()
            else None
        )
        bridge_components = (
            bridge_identity.get("components")
            if isinstance(bridge_identity, dict) and isinstance(bridge_identity.get("components"), dict)
            else {}
        )
        launcher_result = self._last_launcher_result(selection)
        extension_contact = self._browser_extension_contact(selection)
        launcher_ready = bool(launcher_result and launcher_result.get("ok") is True)
        launcher_tool_count = launcher_result.get("toolCount") if isinstance(launcher_result, dict) else None
        canonical_tools = list(matrix["contracts"]["gateway_facade"]["canonical_tools"])
        actual_tools = [str(tool) for tool in status.get("public_tools", [])]
        ui_sha256 = _sha256_file(Path(__file__).resolve())
        ui_build_id = f"plwc-configuration-ui@1.0.0#sha256:{ui_sha256}" if ui_sha256 else None
        bridge_entry = bridge_root / "bridge" / "dist" / "src" / "index.js" if bridge_root is not None else None
        launcher_path = (
            bridge_root / "native" / "bin" / "plwc-chat-bridge-launcher.exe"
            if bridge_root is not None
            else None
        )

        node_path = selection.get("Diagnostics", "NodePath", fallback="").strip() or shutil.which("node")
        node_version = self._command_version(node_path, r"v?([0-9]+\.[0-9]+\.[0-9]+)") if node_path else None
        docker_path = resolve_docker_executable()
        docker_selected = selection.get("Diagnostics", "DockerDesktopInstalled", fallback="").strip().casefold()
        docker_observation, document_worker_observation = _docker_component_observations(
            docker_path,
            installer_selected=docker_selected == "true",
        )
        qdrant_observation = _python_distribution_observation(
            "qdrant-client",
            enabled=bool(config.qdrant_enabled),
        )
        observations: dict[str, dict[str, Any]] = {
            "product": {
                "present": True,
                "semantic_version": installed_version or __version__,
                "build_revision": installer_revision or None,
                "build_identity_schema": 1 if build_id else None,
                "build_id": build_id or None,
                "sha256": setup_sha256 or None,
                "source": source if build_id else _observed_source("gateway_runtime"),
            },
            "windows_installer": {
                "present": bool(build_id and setup_sha256),
                "semantic_version": installed_version,
                "build_revision": installer_revision or None,
                "build_identity_schema": 1 if build_id else None,
                "build_id": build_id or None,
                "sha256": setup_sha256 or None,
                "source": source,
            },
            "gateway": {
                "present": True,
                "semantic_version": str(status.get("version") or __version__),
                "protocol_version": str(matrix["contracts"]["gateway_facade"]["version"]),
                "tool_count": status.get("registered_public_tool_count"),
                "canonical_tools_valid": actual_tools == canonical_tools,
                "postflight_verified": status.get("registered_public_tool_count") == len(canonical_tools)
                and actual_tools == canonical_tools,
                "active_paths": [path for path in (gateway_path, str(self.gateway_root or "")) if path],
                "source": _observed_source("gateway_runtime"),
            },
            "node_bridge": {
                "present": bool(bridge_entry and bridge_entry.is_file() and bridge_identity),
                "semantic_version": bridge_components.get("nodeBridge"),
                "protocol_version": "1.0.0" if launcher_ready else None,
                "build_identity_schema": bridge_identity.get("schemaVersion") if bridge_identity else None,
                "build_id": bridge_identity.get("buildId") if bridge_identity else None,
                "sha256": _sha256_file(bridge_entry) if bridge_entry and bridge_entry.is_file() else None,
                "tool_count": launcher_tool_count,
                "canonical_tools_valid": True if launcher_ready and launcher_tool_count == 8 else None,
                "postflight_verified": launcher_ready and launcher_tool_count == 8,
                "active_paths": [bridge_path_value] if bridge_path_value else [],
                "source": _observed_source("installed_bridge", str(bridge_identity_path)) if bridge_identity_path else None,
            },
            "native_launcher": {
                "present": bool(launcher_path and launcher_path.is_file()),
                "semantic_version": bridge_components.get("nativeLauncher"),
                "protocol_version": "1.0.0" if launcher_path and launcher_path.is_file() else None,
                "build_identity_schema": bridge_identity.get("schemaVersion") if bridge_identity else None,
                "build_id": bridge_identity.get("buildId") if bridge_identity else None,
                "sha256": _sha256_file(launcher_path) if launcher_path and launcher_path.is_file() else None,
                "postflight_verified": launcher_ready,
                "source": _observed_source("installed_launcher", str(launcher_path)) if launcher_path else None,
            },
            "configuration_ui": {
                "present": True,
                "semantic_version": "1.0.0",
                "build_identity_schema": 1,
                "build_id": ui_build_id,
                "sha256": ui_sha256,
                "postflight_verified": True,
                "source": _observed_source("configuration_ui", str(Path(__file__).resolve())),
            },
            "browser_extension": (
                {
                    "present": True,
                    "semantic_version": extension_contact.get("packageVersion"),
                    "protocol_version": extension_contact.get("protocolVersion"),
                    "build_identity_schema": (
                        (extension_contact.get("buildIdentity") or {}).get("schemaVersion")
                        if isinstance(extension_contact.get("buildIdentity"), dict)
                        else None
                    ),
                    "build_id": (
                        (extension_contact.get("buildIdentity") or {}).get("buildId")
                        if isinstance(extension_contact.get("buildIdentity"), dict)
                        else None
                    ),
                    "tool_count": extension_contact.get("toolCount"),
                    "canonical_tools_valid": extension_contact.get("toolCount") == 8,
                    "postflight_verified": extension_contact.get("toolCount") == 8
                    and extension_contact.get("stale") is False,
                    "source": _observed_source("native_messaging_contact", str(extension_contact.get("state_file"))),
                }
                if extension_contact is not None
                else {
                    "present": None,
                    "source": {"kind": "browser_handshake", "trust": "unavailable", "observed_at": None},
                }
            ),
            "python_runtime": {
                "present": True,
                "semantic_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "postflight_verified": True,
                "source": _observed_source("running_process", sys.executable),
            },
            "node_runtime": {
                "present": bool(node_path and node_version),
                "semantic_version": node_version,
                "source": _observed_source("runtime_probe", node_path) if node_path else None,
            },
            "docker": docker_observation,
            "qdrant": qdrant_observation,
            "document_worker": document_worker_observation,
        }
        inventory = build_component_inventory(matrix, observations)
        inventory["matrix_path"] = str(matrix_path)
        inventory["installation_paths"] = {
            "app": app_path or None,
            "gateway": gateway_path or str(self.gateway_root) if self.gateway_root else gateway_path or None,
            "bridge": bridge_path_value or None,
        }
        return inventory

    @staticmethod
    def _profile_inventory(status: dict[str, Any], active: str) -> list[dict[str, Any]]:
        profiles: list[dict[str, Any]] = []
        raw_profiles = status.get("available_profiles")
        for raw in raw_profiles if isinstance(raw_profiles, list) else []:
            if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
                continue
            name = str(raw["name"]).strip()
            profile_path = str(raw.get("profile_directory") or "")
            valid = raw.get("valid") is True
            missing = [str(item) for item in raw.get("missing_files", []) if str(item).strip()]
            reason = str(raw.get("validation_reason") or ("valid" if valid else "invalid_profile"))
            profiles.append(
                {
                    "name": name,
                    "path": profile_path,
                    "exists": bool(profile_path and Path(profile_path).is_dir()),
                    "valid": valid,
                    "status": "valid" if valid else reason,
                    "reason": reason,
                    "missing_files": missing,
                    "active": raw.get("active") is True or name.casefold() == active.casefold(),
                    "activatable": valid and name.casefold() != active.casefold(),
                    "schema_errors": list(
                        (raw.get("profile_schema_validation") or {}).get("errors", [])
                        if isinstance(raw.get("profile_schema_validation"), dict)
                        else []
                    ),
                }
            )
        profiles.sort(key=lambda profile: str(profile["name"]).casefold())
        return profiles

    def _config(self, *, read_only: bool = False):
        return load_gateway_config(
            project_root=self.project_root,
            create_directories=not read_only,
        )

    def _read_shared_settings(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            return {}
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"Shared PLwC settings could not be read safely: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ConfigurationError("Shared PLwC settings use an unsupported schema version.")
        settings = payload.get("settings")
        if not isinstance(settings, dict):
            raise ConfigurationError("Shared PLwC settings do not contain a settings object.")
        return dict(settings)

    def snapshot(self) -> dict[str, Any]:
        config = self._config()
        status = runtime_status_diagnose(config=config)
        if not isinstance(status, dict) or status.get("ok") is not True:
            raise ConfigurationError("PLwC runtime status is unavailable.")
        governance = config.governance
        active = str(status.get("active_profile_name") or config.active_profile_name)
        profiles = self._profile_inventory(status, active)
        return {
            "ok": True,
            "language": self.language,
            "gateway_version": __version__,
            "runtime": {
                "active_profile_name": active,
                "active_profile_source": status.get("active_profile_source"),
                "active_profile_status": status.get("active_profile_status"),
                "profile_valid": bool(status.get("profile_valid")),
                "available_profiles": profiles,
                "profiles_path": str(config.profile_root),
                "workspace_path": str(config.allowed_roots[0]) if config.allowed_roots else None,
            },
            "settings": {
                "workspace_path": str(config.allowed_roots[0]) if config.allowed_roots else None,
                "memory_write_threshold": governance.memory_write_threshold,
                "memory_write_threshold_source": governance.memory_write_threshold_source,
                "persona_write_threshold": governance.persona_write_threshold,
                "persona_write_threshold_source": governance.persona_write_threshold_source,
                "temperament_write_threshold": governance.temperament_write_threshold,
                "temperament_write_threshold_source": governance.temperament_write_threshold_source,
                "qdrant_enabled": bool(config.qdrant_enabled),
                "qdrant_enabled_source": config.qdrant_enabled_source,
                "persona_layer_enabled": bool(config.persona_layer_enabled),
                "persona_layer_enabled_source": config.persona_layer_enabled_source,
            },
            "files": {
                "shared_settings": str(self.settings_path),
                "active_profile_state": str(config.active_profile_state_file),
            },
            "setup_warnings": list(config.setup_warnings),
            "component_inventory": self._component_inventory(status, config),
            "launcher_last_result": self._last_launcher_result(),
            "browser_extension_last_contact": self._browser_extension_contact(),
            "update_center": self.update_center.snapshot(),
        }

    def check_updates(self) -> dict[str, Any]:
        return self.update_center.check(force=True)

    def plan_update_download(self, artifact_id: Any) -> dict[str, Any]:
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            raise ConfigurationError("Choose a release artifact before requesting a download plan.")
        return self.update_center.plan_download(artifact_id.strip())

    def download_update(self, plan_id: Any, confirmed: Any) -> dict[str, Any]:
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ConfigurationError("Choose a valid update download plan.")
        return self.update_center.download(plan_id.strip(), confirmed=confirmed is True)

    def install_update(self, plan_id: Any, confirmed: Any) -> dict[str, Any]:
        if not isinstance(plan_id, str) or not plan_id.strip():
            raise ConfigurationError("Choose a verified update before installation.")
        return self.update_center.install(plan_id.strip(), confirmed=confirmed is True)

    def _installation_doctor(self, config: Any) -> InstallationDoctor:
        workspace = Path(config.allowed_roots[0]) if config.allowed_roots else None
        return InstallationDoctor(
            self.project_root,
            workspace_root=workspace,
            profile_root=Path(config.profile_root),
            enable_system_probes=self.doctor_system_probes,
        )

    def run_doctor_diagnosis(self) -> dict[str, Any]:
        config = self._config(read_only=True)
        status = runtime_status_diagnose(config=config)
        if not isinstance(status, dict) or status.get("ok") is not True:
            raise ConfigurationError("PLwC runtime status is unavailable for Doctor diagnosis.")
        inventory = self._component_inventory(status, config)
        try:
            clu = clu_doctor_diagnose(doctor_scope="general", config=config)
            report = self._installation_doctor(config).diagnose(
                component_inventory=inventory,
                clu_diagnostic=clu,
            )
        except (DoctorContractError, ValueError) as exc:
            raise ConfigurationError(str(exc)) from exc
        self._doctor_diagnoses = {str(report["snapshot_id"]): report}
        return report

    def plan_doctor_repair(self, snapshot_id: Any) -> dict[str, Any]:
        if not isinstance(snapshot_id, str) or len(snapshot_id) != 64:
            raise ConfigurationError("Doctor repair planning requires a valid diagnosis snapshot ID.")
        diagnosis = self._doctor_diagnoses.get(snapshot_id)
        if diagnosis is None:
            raise ConfigurationError("Doctor diagnosis is no longer available. Run diagnosis again.")
        try:
            plan = InstallationDoctor.build_repair_plan(diagnosis)
        except DoctorContractError as exc:
            raise ConfigurationError(str(exc)) from exc
        self._doctor_plans = {str(plan["plan_id"]): plan}
        return plan

    def apply_doctor_repair(self, plan_id: Any, confirmed: Any) -> dict[str, Any]:
        if confirmed is not True:
            raise ConfigurationError("Doctor repair requires explicit confirmation.")
        if not isinstance(plan_id, str) or len(plan_id) != 64:
            raise ConfigurationError("Doctor repair plan ID is invalid.")
        plan = self._doctor_plans.get(plan_id)
        if plan is None:
            raise ConfigurationError("Doctor repair plan is no longer available. Review a new plan.")
        current = self.run_doctor_diagnosis()
        config = self._config()
        doctor = self._installation_doctor(config)
        try:
            result = doctor.apply_repair_plan(
                plan,
                confirmed_plan_id=plan_id,
                current_diagnosis=current,
                postflight=self.run_doctor_diagnosis,
            )
        except DoctorContractError as exc:
            raise ConfigurationError(str(exc)) from exc
        self._doctor_plans.clear()
        return result

    def update_settings(self, value: Any) -> dict[str, Any]:
        normalized = _normalize_settings(value)
        with self._write_lock:
            current = self._read_shared_settings()
            current.update(
                {
                    "memory_write_threshold": normalized["memory_write_threshold"],
                    "persona_write_threshold": normalized["persona_write_threshold"],
                    "temperament_write_threshold": normalized["temperament_write_threshold"],
                    "qdrant_enabled": normalized["qdrant_enabled"],
                    "persona_layer_disabled": not normalized["persona_layer_enabled"],
                }
            )
            unsupported = set(current) - SHARED_SETTING_KEYS
            if unsupported:
                names = ", ".join(sorted(unsupported))
                raise ConfigurationError(f"Shared settings contain unsupported keys: {names}.")
            _atomic_write_json(
                self.settings_path,
                {
                    "schema_version": 1,
                    "settings": current,
                    "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "updated_by": "plwc-local-configuration",
                },
                root=self.project_root / "config",
            )
            workspace_value = current.get("workspace_path")
            if isinstance(workspace_value, str) and workspace_value.strip():
                self._synchronize_workspace_references(Path(workspace_value), settings=current)
        return self.snapshot()

    def plan_workspace_change(self, workspace_path: Any) -> dict[str, Any]:
        workspace = _normalize_workspace_path(workspace_path)
        config = self._config()
        current_workspace = str(config.allowed_roots[0]) if config.allowed_roots else None
        nearest_parent = workspace
        while not nearest_parent.exists() and nearest_parent != nearest_parent.parent:
            nearest_parent = nearest_parent.parent
        path_exists = workspace.exists()
        path_is_directory = not path_exists or workspace.is_dir()
        parent_exists = nearest_parent.exists() and nearest_parent.is_dir()
        writable = parent_exists and os.access(nearest_parent, os.W_OK)
        unchanged = current_workspace is not None and workspace == Path(current_workspace).resolve(strict=False)
        valid = bool(path_is_directory and writable and not unchanged)
        if unchanged:
            reason = "workspace_unchanged"
        elif path_exists and not path_is_directory:
            reason = "workspace_path_is_not_a_directory"
        elif not parent_exists:
            reason = "workspace_parent_unavailable"
        elif not writable:
            reason = "workspace_parent_not_writable"
        else:
            reason = "workspace_change_ready"
        planned_writes = [
            {"path": str(workspace / name) if name else str(workspace), "purpose": purpose}
            for name, purpose in (
                ("", "workspace_root"),
                ("Tagebuch", "standard_directory"),
                ("Temp", "standard_directory"),
                ("Trashcan", "standard_directory"),
            )
        ]
        planned_writes.extend(
            (
                {"path": str(self.settings_path), "purpose": "shared_settings_reference"},
                {"path": str(self.selection_path), "purpose": "installer_selection_reference"},
            )
        )
        selection = self._read_installer_selection()
        reference_candidates = (
            self.installer_config_root / "clients" / "codex" / "plwc-gateway.generated.toml",
            self.installer_config_root / "clients" / "odysseus" / "plwc-gateway.generated.json",
        )
        for path in reference_candidates:
            if path.is_file():
                planned_writes.append({"path": str(path), "purpose": "client_workspace_reference"})
        app_path = selection.get("PLwC", "AppPath", fallback="").strip()
        bridge_path = selection.get("PLwC", "BridgePath", fallback="").strip()
        if app_path and bridge_path:
            app_root = Path(app_path).resolve(strict=False)
            bridge_root = Path(bridge_path).resolve(strict=False)
            if _is_inside(bridge_root, app_root):
                for filename in ("plwc.example.json", "plwc.json"):
                    path = bridge_root / "config" / filename
                    if path.is_file():
                        planned_writes.append({"path": str(path), "purpose": "bridge_workspace_reference"})
        if os.name == "nt":
            planned_writes.append(
                {
                    "path": r"HKCU\Software\PLwC\Installer\WorkspacePath",
                    "purpose": "installer_registry_reference",
                }
            )
        plan: dict[str, Any] = {
            "ok": valid,
            "plan_type": "workspace_change",
            "current_workspace_path": current_workspace,
            "requested_workspace_path": str(workspace),
            "path_exists": path_exists,
            "nearest_existing_parent": str(nearest_parent),
            "writable": writable,
            "valid": valid,
            "reason": reason,
            "planned_writes": planned_writes,
            "data_migration": False,
            "data_migration_note": "Existing workspace data is not moved, copied, or deleted.",
            "confirmation_required": True,
        }
        plan["plan_digest"] = _workspace_plan_digest(plan)
        return plan

    def apply_workspace_change(
        self,
        workspace_path: Any,
        plan_digest: Any,
        confirmed: Any,
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise ConfigurationError("Workspace change requires explicit confirmation.")
        if not isinstance(plan_digest, str) or len(plan_digest) != 64:
            raise ConfigurationError("Workspace change plan digest is invalid.")
        with self._write_lock:
            current_plan = self.plan_workspace_change(workspace_path)
            if current_plan["valid"] is not True:
                raise ConfigurationError(str(current_plan.get("reason") or "Workspace change is not valid."))
            if not hmac.compare_digest(current_plan["plan_digest"], plan_digest):
                raise ConfigurationError("Workspace change plan changed. Review the new plan before applying it.")
            workspace = Path(str(current_plan["requested_workspace_path"]))
            current = self._read_shared_settings()
            current["workspace_path"] = str(workspace)
            unsupported = set(current) - SHARED_SETTING_KEYS
            if unsupported:
                names = ", ".join(sorted(unsupported))
                raise ConfigurationError(f"Shared settings contain unsupported keys: {names}.")
            self._ensure_workspace_structure(workspace)
            _atomic_write_json(
                self.settings_path,
                {
                    "schema_version": 1,
                    "settings": current,
                    "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "updated_by": "plwc-local-configuration",
                },
                root=self.project_root / "config",
            )
            self._synchronize_workspace_references(workspace, settings=current)
        return {"ok": True, "applied_plan_digest": plan_digest, "state": self.snapshot()}

    @staticmethod
    def _ensure_workspace_structure(workspace: Path) -> None:
        for path in (workspace, workspace / "Tagebuch", workspace / "Temp", workspace / "Trashcan"):
            path.mkdir(parents=True, exist_ok=True)

    def _read_installer_selection(self) -> configparser.ConfigParser:
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        if self.selection_path.is_file():
            parser.read(self.selection_path, encoding="utf-8-sig")
        if not parser.has_section("PLwC"):
            parser.add_section("PLwC")
        return parser

    def _write_installer_selection(self, parser: configparser.ConfigParser) -> None:
        from io import StringIO

        output = StringIO()
        parser.write(output, space_around_delimiters=False)
        _atomic_write_text(
            self.selection_path,
            output.getvalue(),
            root=self.installer_config_root,
        )

    @staticmethod
    def _replace_workspace_in_toml(content: str, workspace: Path) -> str:
        escaped = json.dumps(str(workspace), ensure_ascii=False)[1:-1]
        pattern = re.compile(r'("PLWC_WORKSPACE_ROOT"\s*=\s*")[^"]*(")')
        return pattern.sub(lambda match: f"{match.group(1)}{escaped}{match.group(2)}", content, count=1)

    @staticmethod
    def _update_json_workspace(path: Path, keys: tuple[str, ...], workspace: Path) -> None:
        if not path.is_file():
            return
        payload = json.loads(_read_generated_text(path))
        target: Any = payload
        for key in keys[:-1]:
            if not isinstance(target, dict) or not isinstance(target.get(key), dict):
                return
            target = target[key]
        if not isinstance(target, dict):
            return
        target[keys[-1]] = str(workspace)
        _atomic_write_json(path, payload, root=path.parent)

    @staticmethod
    def _store_workspace_registry(workspace: Path) -> None:
        if os.name != "nt":
            return
        import winreg

        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\PLwC\Installer", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "WorkspacePath", 0, winreg.REG_SZ, str(workspace))

    def _synchronize_workspace_references(
        self,
        workspace: Path,
        *,
        settings: dict[str, Any] | None = None,
    ) -> None:
        selection = self._read_installer_selection()
        selection.set("PLwC", "WorkspacePath", str(workspace))
        if settings is not None:
            selection_values = {
                "ProfilesPath": settings.get("profiles_path"),
                "ActiveProfile": settings.get("active_profile_name"),
                "SecurityConfig": settings.get("security_config") or "",
                "MemoryWriteThreshold": settings.get("memory_write_threshold"),
                "PersonaWriteThreshold": settings.get("persona_write_threshold"),
                "TemperamentWriteThreshold": settings.get("temperament_write_threshold"),
                "QdrantEnabled": settings.get("qdrant_enabled"),
                "PersonaLayerDisabled": settings.get("persona_layer_disabled"),
            }
            for key, value in selection_values.items():
                if value is None and key != "SecurityConfig":
                    continue
                if isinstance(value, bool):
                    stored_value = str(value).lower()
                else:
                    stored_value = str(value)
                selection.set("PLwC", key, stored_value)
        app_path = selection.get("PLwC", "AppPath", fallback="").strip()
        bridge_path = selection.get("PLwC", "BridgePath", fallback="").strip()
        self._write_installer_selection(selection)
        self._store_workspace_registry(workspace)

        codex = self.installer_config_root / "clients" / "codex" / "plwc-gateway.generated.toml"
        if codex.is_file():
            updated = self._replace_workspace_in_toml(_read_generated_text(codex), workspace)
            _atomic_write_text(codex, updated, root=self.installer_config_root)
        self._update_json_workspace(
            self.installer_config_root / "clients" / "odysseus" / "plwc-gateway.generated.json",
            ("mcpServers", "plwc-gateway", "env", "PLWC_WORKSPACE_ROOT"),
            workspace,
        )
        if app_path and bridge_path:
            app_root = Path(app_path).resolve(strict=False)
            bridge_root = Path(bridge_path).resolve(strict=False)
            if _is_inside(bridge_root, app_root):
                for filename in ("plwc.example.json", "plwc.json"):
                    self._update_json_workspace(
                        bridge_root / "config" / filename,
                        ("gateway", "env", "PLWC_WORKSPACE_ROOT"),
                        workspace,
                    )

    def sync_installation(self, value: Any) -> None:
        if not isinstance(value, dict):
            raise ConfigurationError("Installation settings must be a JSON object.")
        normalized = _normalize_installation_settings({key: value.get(key) for key in INSTALLATION_SETTING_KEYS})
        workspace = Path(str(normalized["workspace_path"]))
        profiles = _normalize_workspace_path(value.get("profiles_path"))
        with self._write_lock:
            current = self._read_shared_settings()
            if not current:
                current = {
                    "active_profile_name": value.get("active_profile_name") or "default",
                    "security_config": value.get("security_config") or None,
                    "memory_write_threshold": normalized["memory_write_threshold"],
                    "persona_write_threshold": normalized["persona_write_threshold"],
                    "temperament_write_threshold": normalized["temperament_write_threshold"],
                    "qdrant_enabled": normalized["qdrant_enabled"],
                    "persona_layer_disabled": not normalized["persona_layer_enabled"],
                }
            current["workspace_path"] = str(workspace)
            current["profiles_path"] = str(profiles)
            unsupported = set(current) - SHARED_SETTING_KEYS
            if unsupported:
                names = ", ".join(sorted(unsupported))
                raise ConfigurationError(f"Shared settings contain unsupported keys: {names}.")
            self._ensure_workspace_structure(workspace)
            _atomic_write_json(
                self.settings_path,
                {
                    "schema_version": 1,
                    "settings": current,
                    "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "updated_by": "plwc-windows-setup",
                },
                root=self.project_root / "config",
            )
            self._synchronize_workspace_references(workspace, settings=current)

    def plan_profile_activation(self, profile_name: Any) -> dict[str, Any]:
        if not isinstance(profile_name, str) or not profile_name.strip():
            raise ConfigurationError("Choose a profile before requesting an activation plan.")
        requested = profile_name.strip()
        config = self._config()
        result = plwc_governor(
            operation="plan",
            plan_type="profile_activation",
            profile=requested,
            config=config,
        )
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            raise ConfigurationError("PLwC did not return a structured profile activation plan.")
        validation = data.get("validation") if isinstance(data.get("validation"), dict) else {}
        return {
            "ok": result.get("ok") is True,
            "current_active_profile": data.get("current_active_profile"),
            "requested_active_profile": data.get("requested_active_profile"),
            "target_profile_directory": data.get("target_profile_directory"),
            "missing_files": list(data.get("missing_files") or []),
            "planned_writes": list(data.get("planned_writes") or []),
            "valid": validation.get("valid") is True,
            "reason": validation.get("reason") or result.get("error"),
            "confirmation_required": True,
            "plan_digest": _profile_plan_digest(data),
        }

    def apply_profile_activation(self, profile_name: Any, plan_digest: Any, confirmed: Any) -> dict[str, Any]:
        if confirmed is not True:
            raise ConfigurationError("Profile activation requires explicit confirmation.")
        if not isinstance(plan_digest, str) or len(plan_digest) != 64:
            raise ConfigurationError("Profile activation plan digest is invalid.")
        with self._write_lock:
            current_plan = self.plan_profile_activation(profile_name)
            if current_plan["valid"] is not True:
                raise ConfigurationError(str(current_plan.get("reason") or "Profile activation plan is not valid."))
            if not hmac.compare_digest(current_plan["plan_digest"], plan_digest):
                raise ConfigurationError("Profile activation plan changed. Review the new plan before applying it.")
            requested = str(current_plan["requested_active_profile"])
            result = plwc_governor(
                operation="apply",
                plan_type="profile_activation",
                profile=requested,
                confirmed=True,
                config=self._config(),
            )
            if not isinstance(result, dict) or result.get("ok") is not True:
                message = result.get("error") if isinstance(result, dict) else None
                raise ConfigurationError(str(message or "PLwC rejected the profile activation."))
        return {"ok": True, "result": result, "state": self.snapshot()}

    def plan_profile_creation(self, value: Any) -> dict[str, Any]:
        answers = _normalize_onboarding_answers(value)
        profile_name = answers["profile_name"]
        result = plwc_governor(
            operation="plan",
            plan_type="profile_creation",
            profile=profile_name,
            onboarding_answers=answers,
            config=self._config(),
        )
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, dict):
            raise ConfigurationError("PLwC did not return a structured profile creation plan.")
        normalized_answers = data.get("normalized_onboarding_answers")
        if not isinstance(normalized_answers, dict):
            normalized_answers = answers
        activation = data.get("activation_after_apply") if isinstance(data.get("activation_after_apply"), dict) else {}
        return {
            "ok": result.get("ok") is True,
            "profile_name": data.get("target_profile") or profile_name,
            "profile_directory": data.get("profile_directory"),
            "decision": data.get("decision"),
            "approved_for_apply": data.get("approved_for_apply") is True,
            "missing_required_fields": list(data.get("missing_required_fields") or []),
            "validation_error": data.get("validation_error") or result.get("error"),
            "target_files": list(data.get("target_files") or []),
            "planned_writes": list(data.get("planned_writes") or []),
            "persona_layer_enabled": bool(self._config().persona_layer_enabled),
            "activation": {
                "will_be_active": activation.get("activation_effective_after_apply") is True,
                "state_write_planned": activation.get("active_state_write_planned") is True,
                "blocked_reason": activation.get("activation_blocked_reason"),
                "source_after": activation.get("active_profile_source_after"),
            },
            "onboarding_answers": {key: str(normalized_answers.get(key, "")) for key in ONBOARDING_FIELD_KEYS},
            "confirmation_required": True,
            "plan_digest": _profile_creation_plan_digest(data),
        }

    def apply_profile_creation(self, value: Any, plan_digest: Any, confirmed: Any) -> dict[str, Any]:
        if confirmed is not True:
            raise ConfigurationError("Profile creation requires explicit confirmation.")
        if not isinstance(plan_digest, str) or len(plan_digest) != 64:
            raise ConfigurationError("Profile creation plan digest is invalid.")
        answers = _normalize_onboarding_answers(value)
        with self._write_lock:
            current_plan = self.plan_profile_creation(answers)
            if current_plan["approved_for_apply"] is not True:
                raise ConfigurationError(
                    str(current_plan.get("validation_error") or "Profile creation plan is not ready for apply.")
                )
            if not hmac.compare_digest(current_plan["plan_digest"], plan_digest):
                raise ConfigurationError("Profile creation plan changed. Review the new plan before applying it.")
            normalized_answers = current_plan["onboarding_answers"]
            profile_name = str(current_plan["profile_name"])
            result = plwc_governor(
                operation="apply",
                plan_type="profile_creation",
                profile=profile_name,
                onboarding_answers=normalized_answers,
                confirmed=True,
                config=self._config(),
            )
            if not isinstance(result, dict) or result.get("ok") is not True:
                message = result.get("error") if isinstance(result, dict) else None
                raise ConfigurationError(str(message or "PLwC rejected the profile creation."))
        return {"ok": True, "result": result, "state": self.snapshot()}


class ConfigurationHttpServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        service: PlwcConfigurationService,
        static_root: Path,
        session_token: str,
    ) -> None:
        super().__init__(address, handler_class)
        self.service = service
        self.static_root = static_root.resolve(strict=True)
        self.session_token = session_token
        self.last_activity = time.monotonic()

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.server_port}"

    def touch(self) -> None:
        self.last_activity = time.monotonic()


class ConfigurationRequestHandler(BaseHTTPRequestHandler):
    server: ConfigurationHttpServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _security_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def _valid_host(self) -> bool:
        return self.headers.get("Host", "") == f"127.0.0.1:{self.server.server_port}"

    def _authenticated(self) -> bool:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except Exception:
            return False
        morsel = cookie.get(SESSION_COOKIE)
        return morsel is not None and hmac.compare_digest(morsel.value, self.server.session_token)

    def _send_bytes(self, status: HTTPStatus, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self._security_headers(content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, content, "application/json; charset=utf-8")

    def _reject(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"ok": False, "error": message})

    def _bootstrap_session(self, query: str, location: str) -> bool:
        supplied = parse_qs(query, keep_blank_values=True).get("token", [])
        if len(supplied) != 1 or not hmac.compare_digest(supplied[0], self.server.session_token):
            return False
        self.send_response(HTTPStatus.SEE_OTHER)
        self._security_headers("text/plain; charset=utf-8")
        self.send_header("Set-Cookie", f"{SESSION_COOKIE}={self.server.session_token}; HttpOnly; SameSite=Strict; Path=/")
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_GET(self) -> None:
        self.server.touch()
        if not self._valid_host():
            self._reject(HTTPStatus.BAD_REQUEST, "Invalid local host header.")
            return
        parsed = urlsplit(self.path)
        if parsed.path in ("/", "/getting-started") and parsed.query and self._bootstrap_session(parsed.query, parsed.path):
            return
        if not self._authenticated():
            self._reject(HTTPStatus.FORBIDDEN, "This local PLwC configuration session is not authorized.")
            return
        if parsed.path == "/api/state":
            try:
                self._send_json(HTTPStatus.OK, self.server.service.snapshot())
            except ConfigurationError as exc:
                self._reject(HTTPStatus.CONFLICT, str(exc))
            return
        configuration_files = {
            "/": "plwc-config-de.html" if self.server.service.language == "de" else "plwc-config-en.html",
            "/plwc-config.css": "plwc-config.css",
            "/plwc-config.js": "plwc-config.js",
        }
        guide_files = {
            "/getting-started": (
                "getting-started-de.html" if self.server.service.language == "de" else "getting-started-en.html"
            ),
            "/getting-started.css": "getting-started.css",
        }
        name = configuration_files.get(parsed.path)
        asset_root = self.server.static_root
        if name is None:
            name = guide_files.get(parsed.path)
            asset_root = self.server.service.project_root / "app" / "docs"
        if name is None:
            self._reject(HTTPStatus.NOT_FOUND, "Not found.")
            return
        asset_root = asset_root.resolve(strict=False)
        path = (asset_root / name).resolve(strict=False)
        if not _is_inside(path, asset_root) or not path.is_file():
            self._reject(HTTPStatus.NOT_FOUND, "Configuration asset is missing.")
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }[path.suffix]
        self._send_bytes(HTTPStatus.OK, path.read_bytes(), content_type)

    def do_POST(self) -> None:
        self.server.touch()
        if not self._valid_host() or not self._authenticated():
            self._reject(HTTPStatus.FORBIDDEN, "This local PLwC configuration session is not authorized.")
            return
        if self.headers.get("Origin") != self.server.origin or self.headers.get("X-PLwC-Config") != "1":
            self._reject(HTTPStatus.FORBIDDEN, "The configuration request did not originate from this local session.")
            return
        if self.headers.get_content_type() != "application/json":
            self._reject(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Configuration requests must use JSON.")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_JSON_BYTES:
            self._reject(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Configuration request size is invalid.")
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ConfigurationError("Configuration request must be a JSON object.")
            if self.path == "/api/settings":
                result = self.server.service.update_settings(payload.get("settings"))
            elif self.path == "/api/workspace/plan":
                result = self.server.service.plan_workspace_change(payload.get("workspace_path"))
            elif self.path == "/api/workspace/apply":
                result = self.server.service.apply_workspace_change(
                    payload.get("workspace_path"),
                    payload.get("plan_digest"),
                    payload.get("confirmed"),
                )
            elif self.path == "/api/profile/plan":
                result = self.server.service.plan_profile_activation(payload.get("profile_name"))
            elif self.path == "/api/profile/apply":
                result = self.server.service.apply_profile_activation(
                    payload.get("profile_name"),
                    payload.get("plan_digest"),
                    payload.get("confirmed"),
                )
            elif self.path == "/api/profile/create/plan":
                result = self.server.service.plan_profile_creation(payload.get("onboarding_answers"))
            elif self.path == "/api/profile/create/apply":
                result = self.server.service.apply_profile_creation(
                    payload.get("onboarding_answers"),
                    payload.get("plan_digest"),
                    payload.get("confirmed"),
                )
            elif self.path == "/api/doctor/diagnose":
                result = self.server.service.run_doctor_diagnosis()
            elif self.path == "/api/doctor/plan":
                result = self.server.service.plan_doctor_repair(payload.get("snapshot_id"))
            elif self.path == "/api/doctor/apply":
                result = self.server.service.apply_doctor_repair(
                    payload.get("plan_id"),
                    payload.get("confirmed"),
                )
            elif self.path == "/api/update/check":
                result = self.server.service.check_updates()
            elif self.path == "/api/update/download/plan":
                result = self.server.service.plan_update_download(payload.get("artifact_id"))
            elif self.path == "/api/update/download":
                result = self.server.service.download_update(
                    payload.get("plan_id"),
                    payload.get("confirmed"),
                )
            elif self.path == "/api/update/install":
                result = self.server.service.install_update(
                    payload.get("plan_id"),
                    payload.get("confirmed"),
                )
            else:
                self._reject(HTTPStatus.NOT_FOUND, "Not found.")
                return
        except (ConfigurationError, UpdateContractError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._reject(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except OSError:
            self._reject(HTTPStatus.INTERNAL_SERVER_ERROR, "PLwC could not update the local configuration safely.")
            return
        self._send_json(HTTPStatus.OK, result)


def create_http_server(
    service: PlwcConfigurationService,
    static_root: Path,
    *,
    session_token: str | None = None,
) -> ConfigurationHttpServer:
    token = session_token or secrets.token_urlsafe(32)
    server = ConfigurationHttpServer(
        ("127.0.0.1", 0),
        ConfigurationRequestHandler,
        service=service,
        static_root=static_root,
        session_token=token,
    )
    if service.update_center.trusted_keys:
        threading.Thread(target=service.update_center.check, daemon=True, name="plwc-update-check").start()
    return server


def _apply_launch_overrides(args: argparse.Namespace) -> None:
    values = {
        "PLWC_WORKSPACE_ROOT": args.workspace,
        "PLWC_PROFILE_ROOT": args.profiles,
        "PLWC_CONFIG_FILE": args.security_config,
        "PLWC_ACTIVE_PROFILE_NAME": args.active_profile,
        "PLWC_MEMORY_WRITE_THRESHOLD": args.memory_threshold,
        "PLWC_PERSONA_WRITE_THRESHOLD": args.persona_threshold,
        "PLWC_TEMPERAMENT_WRITE_THRESHOLD": args.temperament_threshold,
        "PLWC_QDRANT_ENABLED": args.qdrant_enabled,
        "PLWC_PERSONA_LAYER_DISABLED": args.persona_layer_disabled,
    }
    for key, value in values.items():
        if value is not None and str(value).strip():
            os.environ[key] = str(value).strip()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open the local PLwC configuration page.")
    parser.add_argument("--project-root", type=Path, default=default_app_root())
    parser.add_argument("--installer-config-root", type=Path)
    parser.add_argument("--gateway-root", type=Path)
    parser.add_argument("--workspace")
    parser.add_argument("--profiles")
    parser.add_argument("--security-config")
    parser.add_argument("--active-profile")
    parser.add_argument("--memory-threshold")
    parser.add_argument("--persona-threshold")
    parser.add_argument("--temperament-threshold")
    parser.add_argument("--qdrant-enabled", choices=("true", "false"))
    parser.add_argument("--persona-layer-disabled", choices=("true", "false"))
    parser.add_argument("--sync-installation", action="store_true")
    parser.add_argument("--language", choices=("de", "en"), default="en")
    parser.add_argument("--start-page", choices=("configuration", "getting-started"), default="configuration")
    parser.add_argument("--idle-timeout", type=int, default=900)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.idle_timeout < 30 or args.idle_timeout > 3600:
        raise SystemExit("--idle-timeout must be from 30 through 3600 seconds.")
    _apply_launch_overrides(args)
    static_root = Path(__file__).resolve().parent
    service = PlwcConfigurationService(
        args.project_root,
        installer_config_root=args.installer_config_root,
        gateway_root=args.gateway_root,
        language=args.language,
    )
    if args.sync_installation:
        service.sync_installation(
            {
                "workspace_path": args.workspace,
                "profiles_path": args.profiles,
                "active_profile_name": args.active_profile,
                "security_config": args.security_config,
                "memory_write_threshold": int(args.memory_threshold or "2"),
                "persona_write_threshold": int(args.persona_threshold or "3"),
                "temperament_write_threshold": int(args.temperament_threshold or "2"),
                "qdrant_enabled": args.qdrant_enabled == "true",
                "persona_layer_enabled": args.persona_layer_disabled != "true",
            }
        )
        return 0
    server = create_http_server(service, static_root)
    if not args.no_browser:
        start_path = "/getting-started" if args.start_page == "getting-started" else "/"
        webbrowser.open(f"{server.origin}{start_path}?token={server.session_token}", new=2)
    server.timeout = 1.0
    try:
        while time.monotonic() - server.last_activity < args.idle_timeout:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
