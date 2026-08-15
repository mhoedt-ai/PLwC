from __future__ import annotations

import argparse
import configparser
import hashlib
import hmac
import json
import os
import re
import secrets
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
    candidates.extend(sorted(app_root.glob("gateway-*"), reverse=True))
    for root in candidates:
        source_root = root.expanduser().resolve(strict=False) / "src"
        if (source_root / "plwc_gateway" / "__init__.py").is_file():
            sys.path.insert(0, str(source_root))
            return


_bootstrap_gateway_import_path()

from plwc_gateway import __version__
from plwc_gateway.config.settings import SHARED_SETTINGS_FILE_NAME, default_app_root, load_gateway_config
from plwc_gateway.mcp.server import plwc_governor, plwc_status


EDITABLE_SETTING_KEYS = {
    "workspace_path",
    "memory_write_threshold",
    "persona_write_threshold",
    "temperament_write_threshold",
    "qdrant_enabled",
    "persona_layer_enabled",
}
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


def _normalize_settings(value: Any) -> dict[str, int | bool | str]:
    if not isinstance(value, dict) or set(value) != EDITABLE_SETTING_KEYS:
        raise ConfigurationError("Settings must contain exactly the supported PLwC controls.")
    normalized: dict[str, int | bool | str] = {
        "workspace_path": str(_normalize_workspace_path(value.get("workspace_path"))),
    }
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


def _canonical_digest(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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
        language: str = "en",
    ) -> None:
        self.project_root = project_root.resolve(strict=False)
        self.installer_config_root = (
            installer_config_root.resolve(strict=False)
            if installer_config_root is not None
            else self.project_root / "config"
        )
        self.language = "de" if language.casefold().startswith("de") else "en"
        self.settings_path = self.project_root / "config" / SHARED_SETTINGS_FILE_NAME
        self.selection_path = self.installer_config_root / "installer" / "selection.ini"
        self._write_lock = threading.Lock()

    def _config(self):
        return load_gateway_config(project_root=self.project_root)

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
        status = plwc_status(scope="runtime", config=config)
        if not isinstance(status, dict) or status.get("ok") is not True:
            raise ConfigurationError("PLwC runtime status is unavailable.")
        governance = config.governance
        profile_names = [str(name) for name in status.get("available_profile_names", []) if str(name).strip()]
        active = str(status.get("active_profile_name") or config.active_profile_name)
        if active and all(active.casefold() != name.casefold() for name in profile_names):
            profile_names.append(active)
        profile_names.sort(key=str.casefold)
        return {
            "ok": True,
            "language": self.language,
            "gateway_version": __version__,
            "runtime": {
                "active_profile_name": active,
                "active_profile_source": status.get("active_profile_source"),
                "active_profile_status": status.get("active_profile_status"),
                "profile_valid": bool(status.get("profile_valid")),
                "available_profiles": profile_names,
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
        }

    def update_settings(self, value: Any) -> dict[str, Any]:
        normalized = _normalize_settings(value)
        with self._write_lock:
            current = self._read_shared_settings()
            current.update(
                {
                    "workspace_path": normalized["workspace_path"],
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
            workspace = Path(str(normalized["workspace_path"]))
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
            self._synchronize_workspace_references(workspace)
        return self.snapshot()

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
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
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

    def _synchronize_workspace_references(self, workspace: Path) -> None:
        selection = self._read_installer_selection()
        selection.set("PLwC", "WorkspacePath", str(workspace))
        app_path = selection.get("PLwC", "AppPath", fallback="").strip()
        bridge_path = selection.get("PLwC", "BridgePath", fallback="").strip()
        self._write_installer_selection(selection)
        self._store_workspace_registry(workspace)

        codex = self.installer_config_root / "clients" / "codex" / "plwc-gateway.generated.toml"
        if codex.is_file():
            updated = self._replace_workspace_in_toml(codex.read_text(encoding="utf-8-sig"), workspace)
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
                self._update_json_workspace(
                    bridge_root / "config" / "plwc.json",
                    ("gateway", "env", "PLWC_WORKSPACE_ROOT"),
                    workspace,
                )

    def sync_installation(self, value: Any) -> None:
        if not isinstance(value, dict):
            raise ConfigurationError("Installation settings must be a JSON object.")
        normalized = _normalize_settings({key: value.get(key) for key in EDITABLE_SETTING_KEYS})
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
            self._synchronize_workspace_references(workspace)

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
            else:
                self._reject(HTTPStatus.NOT_FOUND, "Not found.")
                return
        except (ConfigurationError, json.JSONDecodeError, UnicodeDecodeError) as exc:
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
    return ConfigurationHttpServer(
        ("127.0.0.1", 0),
        ConfigurationRequestHandler,
        service=service,
        static_root=static_root,
        session_token=token,
    )


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
