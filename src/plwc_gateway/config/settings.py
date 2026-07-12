"""Deterministic local configuration for PLwC Gateway."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from plwc_gateway.policy.paths import PROTECTED_GOVERNANCE_FILENAMES

CONFIG_ENV_VAR = "PLWC_CONFIG_FILE"
LEGACY_CONFIG_ENV_VAR = "PLWC_SECURITY_CONFIG"
WORKSPACE_ENV_VAR = "PLWC_WORKSPACE_ROOT"
PROFILE_ENV_VAR = "PLWC_PROFILE_ROOT"
ACTIVE_PROFILE_ENV_VAR = "PLWC_ACTIVE_PROFILE_NAME"
ACTIVE_PROFILE_STATE_FILE_NAME = "active_profile.json"
MEMORY_THRESHOLD_ENV_VAR = "PLWC_MEMORY_WRITE_THRESHOLD"
PERSONA_THRESHOLD_ENV_VAR = "PLWC_PERSONA_WRITE_THRESHOLD"
TEMPERAMENT_THRESHOLD_ENV_VAR = "PLWC_TEMPERAMENT_WRITE_THRESHOLD"
PERSONA_LAYER_ENABLED_ENV_VAR = "PLWC_PERSONA_LAYER_ENABLED"
PERSONA_LAYER_DISABLED_ENV_VAR = "PLWC_PERSONA_LAYER_DISABLED"
PBA_MEMORY_THRESHOLD_ENV_VAR = "PBA_MEMORY_MIN_SESSIONS"
PBA_PERSONA_THRESHOLD_ENV_VAR = "PBA_PERSONA_MIN_SESSIONS"
PBA_TEMPERAMENT_THRESHOLD_ENV_VAR = "PBA_TEMPERAMENT_MIN_SESSIONS"
DEFAULT_MEMORY_WRITE_THRESHOLD = 2
DEFAULT_PERSONA_WRITE_THRESHOLD = 3
DEFAULT_TEMPERAMENT_WRITE_THRESHOLD = 2
DEFAULT_PERSONA_LAYER_ENABLED = True
WORKSPACE_BINARY_MAX_BYTES_ENV_VAR = "PLWC_WORKSPACE_BINARY_MAX_BYTES"
DEFAULT_WORKSPACE_BINARY_MAX_BYTES = 100 * 1024 * 1024  # 100 MiB

# RC12-FS-003 — search scope guards (override via extension config / env).
WORKSPACE_SEARCH_MAX_FILE_BYTES_ENV_VAR = "PLWC_WORKSPACE_SEARCH_MAX_FILE_BYTES"
DEFAULT_WORKSPACE_SEARCH_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB
WORKSPACE_SEARCH_MAX_FILES_SCANNED_ENV_VAR = "PLWC_WORKSPACE_SEARCH_MAX_FILES_SCANNED"
DEFAULT_WORKSPACE_SEARCH_MAX_FILES_SCANNED = 50_000
MEMORY_LIMIT_RE = re.compile(r"^[1-9][0-9]*[kmgKMG]?$")
CPU_LIMIT_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
DOCKER_IMAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]*$")
DEFAULT_MEMORY_WRITE_THRESHOLD = 2
DEFAULT_PERSONA_WRITE_THRESHOLD = 3
DEFAULT_PROTECTED_PATH_PATTERNS = (
    "./profiles/*/CORE.md",
    "./profiles/*/PERSONA.md",
    "./profiles/*/TEMPERAMENT.md",
    "./profiles/*/CONSCIENCE.md",
    "./profiles/*/memory.md",
    "./profiles/*/reflection.md",
    "./profiles/*/journal.md",
    "./profiles/*/compiled_prompt.txt",
    "./security.yaml",
    "./config/*.yaml",
)


class ConfigValidationError(ValueError):
    """Raised when security configuration cannot be accepted safely."""


@dataclass(frozen=True)
class DockerConfig:
    enabled: bool = True
    image: str = "python:3.12-slim"
    network: str = "none"
    memory: str = "512m"
    cpus: str = "1"
    pids_limit: int = 64
    timeout_seconds: int = 20
    read_only_root: bool = True
    allow_privileged: bool = False
    allow_docker_socket_mount: bool = False
    allow_host_network: bool = False
    allow_dynamic_image: bool = False
    allow_dynamic_mounts: bool = False
    node_image: str = "plwc-node-runner:0.1.0"
    node_memory: str = "768m"


@dataclass(frozen=True)
class GovernanceConfig:
    memory_write_threshold: int = DEFAULT_MEMORY_WRITE_THRESHOLD
    persona_write_threshold: int = DEFAULT_PERSONA_WRITE_THRESHOLD
    temperament_write_threshold: int = DEFAULT_TEMPERAMENT_WRITE_THRESHOLD
    memory_write_threshold_source: str = "default"
    persona_write_threshold_source: str = "default"
    temperament_write_threshold_source: str = "default"

    def as_dict(self) -> dict[str, int | str]:
        return {
            "memory_write_threshold": self.memory_write_threshold,
            "persona_write_threshold": self.persona_write_threshold,
            "temperament_write_threshold": self.temperament_write_threshold,
            "memory_write_threshold_source": self.memory_write_threshold_source,
            "persona_write_threshold_source": self.persona_write_threshold_source,
            "temperament_write_threshold_source": self.temperament_write_threshold_source,
        }


@dataclass(frozen=True)
class GatewayConfig:
    project_root: Path
    allowed_roots: tuple[Path, ...]
    profile_root: Path
    audit_log_file: Path
    active_profile_name: str = "default"
    configured_active_profile_name: str | None = None
    docker: DockerConfig = DockerConfig()
    protected_path_patterns: tuple[str, ...] = DEFAULT_PROTECTED_PATH_PATTERNS
    governance: GovernanceConfig = GovernanceConfig()
    config_file: Path | None = None
    active_profile_state_file: Path | None = None
    state_root: Path | None = None
    config_source: str = "defaults"
    workspace_source: str = "default"
    profile_source: str = "default"
    active_profile_source: str = "default"
    workspace_binary_max_bytes: int = DEFAULT_WORKSPACE_BINARY_MAX_BYTES
    workspace_binary_max_bytes_source: str = "default"
    workspace_search_max_file_bytes: int = DEFAULT_WORKSPACE_SEARCH_MAX_FILE_BYTES
    workspace_search_max_file_bytes_source: str = "default"
    workspace_search_max_files_scanned: int = DEFAULT_WORKSPACE_SEARCH_MAX_FILES_SCANNED
    workspace_search_max_files_scanned_source: str = "default"
    persona_layer_enabled: bool = DEFAULT_PERSONA_LAYER_ENABLED
    persona_layer_enabled_source: str = "default"
    setup_warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def resolved_state_root(self) -> Path:
        """Governed runtime state directory.

        Defaults to ``project_root/state``. The directory lives outside
        ``allowed_roots`` and ``profile_root``: workspace and document tools
        cannot reach it, so it is suitable for pending-plan snapshots and
        other governed runtime state. The installed MCPB runtime resolves
        ``project_root`` under ``%APPDATA%/PLwC`` (or the platform-equivalent
        user app-state root), so this lands at
        ``%APPDATA%/PLwC/state`` by default.
        """
        if self.state_root is not None:
            return self.state_root
        return self.project_root / "state"

    @property
    def pending_plan_root(self) -> Path:
        """Pending-plan snapshot store under the governed state root."""
        return self.resolved_state_root / "pending_plans"


def load_gateway_config(
    config_path: str | os.PathLike[str] | None = None,
    *,
    project_root: str | os.PathLike[str] | None = None,
) -> GatewayConfig:
    root = Path(project_root).resolve(strict=False) if project_root else default_app_root()
    selected_config = _find_config_path(config_path, root)
    parsed = _parse_simple_yaml(selected_config.read_text(encoding="utf-8")) if selected_config else {}
    base_dir = selected_config.parent if selected_config else root

    paths = _section(parsed, "paths")
    audit = _section(parsed, "audit")
    docker_values = _section(parsed, "docker")
    execution = _section(parsed, "execution")
    governance_values = _section(parsed, "governance")
    memory_governance_values = _section(parsed, "memory_governance")

    protected_path_patterns = tuple(
        _validated_string_list(
            paths.get("protected_paths"),
            list(DEFAULT_PROTECTED_PATH_PATTERNS),
            key="paths.protected_paths",
        )
    )
    allow_project_root = _bool_value(paths.get("allow_project_root"), False)
    workspace_override = _configured_env_value(WORKSPACE_ENV_VAR)
    profile_override = _configured_env_value(PROFILE_ENV_VAR)
    active_profile_override = _configured_env_value(ACTIVE_PROFILE_ENV_VAR)
    setup_warnings: list[str] = []

    if workspace_override:
        allowed_root_values = [workspace_override]
        workspace_source = "extension_config"
        allowed_root_base = root
        require_workspace_inside_project = False
    else:
        allowed_root_values = _validated_string_list(
            paths.get("allowed_roots"),
            [str(root / "workspace")],
            key="paths.allowed_roots",
        )
        workspace_source = "security_config" if paths.get("allowed_roots") is not None else "default"
        allowed_root_base = base_dir
        require_workspace_inside_project = paths.get("allowed_roots") is not None

    if profile_override:
        profile_root_value = profile_override
        profile_source = "extension_config"
        profile_base = root
        require_profile_inside_project = False
    else:
        profile_root_value = _string_value(paths.get("profile_root"), str(root / "profiles"))
        profile_source = "security_config" if paths.get("profile_root") is not None else "default"
        profile_base = base_dir
        require_profile_inside_project = paths.get("profile_root") is not None

    if active_profile_override:
        active_profile_name = _validate_profile_name(active_profile_override)
        active_profile_source = "extension_config"
        configured_active_profile_name: str | None = active_profile_name
    else:
        configured_active_profile_name = None
        if paths.get("active_profile_name") is not None:
            active_profile_name = _validate_profile_name(_string_value(paths.get("active_profile_name"), "default"))
            active_profile_source = "security_config"
            configured_active_profile_name = active_profile_name
        else:
            active_profile_name = _validate_profile_name("default")
            active_profile_source = "default"

    allowed_roots = _validate_root_list(
        allowed_root_values,
        base_dir=allowed_root_base,
        project_root=root,
        protected_patterns=protected_path_patterns,
        role="allowed root",
        allow_project_root=allow_project_root,
        require_inside_project_root=require_workspace_inside_project,
        scan_protected_targets=True,
    )
    profile_root = _validate_root(
        profile_root_value,
        base_dir=profile_base,
        project_root=root,
        protected_patterns=protected_path_patterns,
        role="profile root",
        allow_project_root=False,
        require_inside_project_root=require_profile_inside_project,
        scan_protected_targets=False,
    )
    audit_log_file = _resolve_path(_string_value(audit.get("log_file"), str(root / "logs" / "audit.jsonl")), base_dir)
    active_profile_state_file = (root / "config" / ACTIVE_PROFILE_STATE_FILE_NAME).resolve(strict=False)
    state_profile = _active_profile_from_state(active_profile_state_file, setup_warnings)
    if state_profile and configured_active_profile_name is None:
        active_profile_name = state_profile
        active_profile_source = "plwc_state"
    elif state_profile and not _same_profile_name(state_profile, configured_active_profile_name):
        setup_warnings.append(
            "Active profile state was ignored because configured active_profile_name takes precedence."
        )
    governance = _load_governance_config(governance_values, memory_governance_values, setup_warnings)

    docker = _validate_docker_config(
        DockerConfig(
            enabled=_bool_value(execution.get("docker_enabled"), True),
            image=_string_value(docker_values.get("image"), "python:3.12-slim"),
            network=_string_value(docker_values.get("network"), "none"),
            memory=_string_value(docker_values.get("memory"), "512m"),
            cpus=_string_value(docker_values.get("cpus"), "1"),
            pids_limit=_int_value(docker_values.get("pids_limit"), 64),
            timeout_seconds=_int_value(docker_values.get("timeout_seconds"), 20),
            read_only_root=_bool_value(docker_values.get("read_only_root"), True),
            allow_privileged=_bool_value(docker_values.get("allow_privileged"), False),
            allow_docker_socket_mount=_bool_value(docker_values.get("allow_docker_socket_mount"), False),
            allow_host_network=_bool_value(docker_values.get("allow_host_network"), False),
            allow_dynamic_image=_bool_value(docker_values.get("allow_dynamic_image"), False),
            allow_dynamic_mounts=_bool_value(docker_values.get("allow_dynamic_mounts"), False),
        )
    )
    state_root = (root / "state").resolve(strict=False)
    pending_plan_root = state_root / "pending_plans"
    _validate_private_state_root(
        state_root=state_root,
        pending_plan_root=pending_plan_root,
        allowed_roots=allowed_roots,
        profile_root=profile_root,
    )
    _ensure_runtime_directories(
        *allowed_roots,
        profile_root,
        audit_log_file.parent,
        active_profile_state_file.parent,
        state_root,
        pending_plan_root,
    )

    binary_max_bytes, binary_max_bytes_source = _workspace_binary_max_bytes(setup_warnings)
    search_max_file_bytes, search_max_file_bytes_source = _positive_int_setting(
        WORKSPACE_SEARCH_MAX_FILE_BYTES_ENV_VAR,
        DEFAULT_WORKSPACE_SEARCH_MAX_FILE_BYTES,
        setup_warnings,
    )
    search_max_files_scanned, search_max_files_scanned_source = _positive_int_setting(
        WORKSPACE_SEARCH_MAX_FILES_SCANNED_ENV_VAR,
        DEFAULT_WORKSPACE_SEARCH_MAX_FILES_SCANNED,
        setup_warnings,
    )
    persona_layer_enabled, persona_layer_enabled_source = _persona_layer_enabled_setting(setup_warnings)

    return GatewayConfig(
        project_root=root,
        allowed_roots=allowed_roots,
        profile_root=profile_root,
        audit_log_file=audit_log_file,
        active_profile_name=active_profile_name,
        configured_active_profile_name=configured_active_profile_name,
        docker=docker,
        protected_path_patterns=protected_path_patterns,
        governance=governance,
        config_file=selected_config,
        active_profile_state_file=active_profile_state_file,
        state_root=state_root,
        config_source=_config_source(selected_config, config_path),
        workspace_source=workspace_source,
        profile_source=profile_source,
        active_profile_source=active_profile_source,
        workspace_binary_max_bytes=binary_max_bytes,
        workspace_binary_max_bytes_source=binary_max_bytes_source,
        workspace_search_max_file_bytes=search_max_file_bytes,
        workspace_search_max_file_bytes_source=search_max_file_bytes_source,
        workspace_search_max_files_scanned=search_max_files_scanned,
        workspace_search_max_files_scanned_source=search_max_files_scanned_source,
        persona_layer_enabled=persona_layer_enabled,
        persona_layer_enabled_source=persona_layer_enabled_source,
        setup_warnings=tuple(setup_warnings),
    )


def _workspace_binary_max_bytes(setup_warnings: list[str]) -> tuple[int, str]:
    raw = _configured_env_value(WORKSPACE_BINARY_MAX_BYTES_ENV_VAR)
    if raw is None:
        return DEFAULT_WORKSPACE_BINARY_MAX_BYTES, "default"
    try:
        parsed = int(raw)
    except ValueError:
        setup_warnings.append(
            f"{WORKSPACE_BINARY_MAX_BYTES_ENV_VAR} must be a positive integer; using default {DEFAULT_WORKSPACE_BINARY_MAX_BYTES}."
        )
        return DEFAULT_WORKSPACE_BINARY_MAX_BYTES, "default"
    if parsed < 1:
        setup_warnings.append(
            f"{WORKSPACE_BINARY_MAX_BYTES_ENV_VAR} must be at least 1; using default {DEFAULT_WORKSPACE_BINARY_MAX_BYTES}."
        )
        return DEFAULT_WORKSPACE_BINARY_MAX_BYTES, "default"
    return parsed, "extension_config"


def _positive_int_setting(env_var: str, default: int, setup_warnings: list[str]) -> tuple[int, str]:
    """Read a positive-integer setting from the extension config / environment."""
    raw = _configured_env_value(env_var)
    if raw is None:
        return default, "default"
    try:
        parsed = int(raw)
    except ValueError:
        setup_warnings.append(f"{env_var} must be a positive integer; using default {default}.")
        return default, "default"
    if parsed < 1:
        setup_warnings.append(f"{env_var} must be at least 1; using default {default}.")
        return default, "default"
    return parsed, "extension_config"


def _bool_env_setting(env_var: str, default: bool, setup_warnings: list[str]) -> tuple[bool, str]:
    raw = _configured_env_value(env_var)
    if raw is None:
        return default, "default"
    parsed = _parse_bool_text(raw)
    if parsed is not None:
        return parsed, "extension_config"
    setup_warnings.append(f"{env_var} must be a boolean; using default {str(default).lower()}.")
    return default, "default"


def _persona_layer_enabled_setting(setup_warnings: list[str]) -> tuple[bool, str]:
    disabled_raw = _configured_env_value(PERSONA_LAYER_DISABLED_ENV_VAR)
    enabled_raw = _configured_env_value(PERSONA_LAYER_ENABLED_ENV_VAR)

    if disabled_raw is not None:
        disabled = _parse_bool_text(disabled_raw)
        if disabled is True:
            return False, "extension_config"
        if disabled is False and enabled_raw is None:
            return True, "extension_config"
        if disabled is None:
            setup_warnings.append(f"{PERSONA_LAYER_DISABLED_ENV_VAR} must be a boolean; ignoring it.")

    if enabled_raw is not None:
        enabled = _parse_bool_text(enabled_raw)
        if enabled is not None:
            return enabled, "extension_config"
        setup_warnings.append(
            f"{PERSONA_LAYER_ENABLED_ENV_VAR} must be a boolean; using default {str(DEFAULT_PERSONA_LAYER_ENABLED).lower()}."
        )

    return DEFAULT_PERSONA_LAYER_ENABLED, "default"


def _parse_bool_text(value: str) -> bool | None:
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on", "enabled", "enable"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled", "disable"}:
        return False
    return None


def _find_config_path(config_path: str | os.PathLike[str] | None, project_root: Path) -> Path | None:
    candidates = []
    explicit_config = _clean_config_value(config_path)
    if explicit_config:
        candidates.append(Path(explicit_config))
    for env_name in (CONFIG_ENV_VAR, LEGACY_CONFIG_ENV_VAR):
        env_path = _configured_env_value(env_name)
        if env_path:
            candidates.append(Path(env_path))
    candidates.extend([project_root / "security.yaml", project_root / "config" / "security.yaml"])

    for candidate in candidates:
        resolved = candidate.expanduser()
        if not resolved.is_absolute():
            resolved = project_root / resolved
        if resolved.exists():
            return resolved.resolve(strict=False)
    return None


def _active_profile_from_state(state_file: Path, setup_warnings: list[str]) -> str | None:
    if not state_file.exists():
        return None
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        setup_warnings.append(f"Active profile state could not be read; using configured active profile. Reason: {exc}")
        return None
    if not isinstance(payload, dict):
        setup_warnings.append("Active profile state must be a JSON object; using configured active profile.")
        return None
    raw_name = payload.get("active_profile_name")
    if raw_name is None:
        setup_warnings.append("Active profile state has no active_profile_name; using configured active profile.")
        return None
    try:
        return _validate_profile_name(str(raw_name))
    except ConfigValidationError as exc:
        setup_warnings.append(f"Active profile state is invalid; using configured active profile. Reason: {exc}")
        return None


def _same_profile_name(left: str | None, right: str | None) -> bool:
    return bool(left and right) and left.casefold() == right.casefold()


def default_app_root() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if base:
            return (Path(base) / "PLwC").resolve(strict=False)
        return (Path.home() / "AppData" / "Roaming" / "PLwC").resolve(strict=False)
    return (Path.home() / ".plwc").resolve(strict=False)


def _parse_simple_yaml(content: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None
    current_list_key: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":"):
            section_name = stripped[:-1]
            current_section = {}
            root[section_name] = current_section
            current_list_key = None
            continue

        if current_section is None:
            continue

        if stripped.startswith("- ") and current_list_key:
            current_section.setdefault(current_list_key, []).append(_parse_scalar(stripped[2:].strip()))
            continue

        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            current_section[key] = []
            current_list_key = key
        else:
            current_section[key] = _parse_scalar(value)
            current_list_key = None

    return root


def _parse_scalar(value: str) -> Any:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.casefold() == "true":
        return True
    if value.casefold() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _section(values: dict[str, Any], key: str) -> dict[str, Any]:
    value = values.get(key)
    return value if isinstance(value, dict) else {}


def _validated_string_list(value: Any, default: list[str], *, key: str) -> list[str]:
    if value is None:
        return default
    if not isinstance(value, list):
        raise ConfigValidationError(f"{key} must be a YAML list.")
    values = [str(item) for item in value]
    if not values:
        raise ConfigValidationError(f"{key} must contain at least one value.")
    if any(not item.strip() for item in values):
        raise ConfigValidationError(f"{key} must not contain empty values.")
    return values


def _string_value(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(value)


def _bool_value(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _int_value(value: Any, default: int) -> int:
    return value if isinstance(value, int) else default


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve(strict=False)


def _load_governance_config(
    governance_values: dict[str, Any],
    memory_governance_values: dict[str, Any],
    setup_warnings: list[str],
) -> GovernanceConfig:
    memory_raw, memory_source = _first_configured_value(
        (
            (_configured_env_value(MEMORY_THRESHOLD_ENV_VAR), "extension_config"),
            (_configured_env_value(PBA_MEMORY_THRESHOLD_ENV_VAR), "extension_config"),
            (governance_values.get("memory_write_threshold"), "governed_config"),
            (governance_values.get("memory_write_modifier"), "governed_config"),
            (memory_governance_values.get("write_threshold"), "governed_config"),
        )
    )
    persona_raw, persona_source = _first_configured_value(
        (
            (_configured_env_value(PERSONA_THRESHOLD_ENV_VAR), "extension_config"),
            (_configured_env_value(PBA_PERSONA_THRESHOLD_ENV_VAR), "extension_config"),
            (governance_values.get("persona_write_threshold"), "governed_config"),
            (governance_values.get("persona_write_modifier"), "governed_config"),
        )
    )
    temperament_raw, temperament_source = _first_configured_value(
        (
            (_configured_env_value(TEMPERAMENT_THRESHOLD_ENV_VAR), "extension_config"),
            (_configured_env_value(PBA_TEMPERAMENT_THRESHOLD_ENV_VAR), "extension_config"),
            (governance_values.get("temperament_write_threshold"), "governed_config"),
            (governance_values.get("temperament_write_modifier"), "governed_config"),
        )
    )
    memory, memory_source = _threshold_value(
        memory_raw,
        default=DEFAULT_MEMORY_WRITE_THRESHOLD,
        source=memory_source,
        key="governance.memory_write_threshold",
        setup_warnings=setup_warnings,
    )
    persona, persona_source = _threshold_value(
        persona_raw,
        default=DEFAULT_PERSONA_WRITE_THRESHOLD,
        source=persona_source,
        key="governance.persona_write_threshold",
        setup_warnings=setup_warnings,
    )
    temperament, temperament_source = _threshold_value(
        temperament_raw,
        default=DEFAULT_TEMPERAMENT_WRITE_THRESHOLD,
        source=temperament_source,
        key="governance.temperament_write_threshold",
        setup_warnings=setup_warnings,
    )
    return GovernanceConfig(
        memory_write_threshold=memory,
        persona_write_threshold=persona,
        temperament_write_threshold=temperament,
        memory_write_threshold_source=memory_source,
        persona_write_threshold_source=persona_source,
        temperament_write_threshold_source=temperament_source,
    )


def _first_configured_value(values: tuple[tuple[Any, str], ...]) -> tuple[Any, str]:
    for value, source in values:
        if value is not None:
            return value, source
    return None, "default"


def _threshold_value(
    value: Any,
    *,
    default: int,
    source: str,
    key: str,
    setup_warnings: list[str],
) -> tuple[int, str]:
    if value is None:
        return default, "default"
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        setup_warnings.append(f"{key} is invalid; using safe default {default}.")
        return default, "default"
    if parsed < 1:
        setup_warnings.append(f"{key} must be at least 1; using safe default {default}.")
        return default, "default"
    return parsed, source


def _validate_profile_name(value: str) -> str:
    cleaned = value.strip() or "default"
    if Path(cleaned).name != cleaned or cleaned.casefold() == "template":
        raise ConfigValidationError("active_profile_name must be a non-template name without path separators.")
    if any(char in cleaned for char in (":", "*", "?", '"', "<", ">", "|")):
        raise ConfigValidationError("active_profile_name contains unsupported path characters.")
    return cleaned


def _ensure_runtime_directories(*paths: Path) -> None:
    for path in paths:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigValidationError(f"Unable to create required PLwC directory {path}: {exc}") from exc


def _configured_env_value(env_name: str) -> str | None:
    return _clean_config_value(os.environ.get(env_name))


def _clean_config_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.startswith("${user_config."):
        return None
    return text


def _config_source(selected_config: Path | None, explicit_config: str | os.PathLike[str] | None) -> str:
    if selected_config is None:
        return "defaults"
    if _clean_config_value(explicit_config):
        return "explicit_argument"
    if _configured_env_value(CONFIG_ENV_VAR) or _configured_env_value(LEGACY_CONFIG_ENV_VAR):
        return "extension_config"
    return "default_security_config"


def _validate_docker_config(docker: DockerConfig) -> DockerConfig:
    if docker.network != "none":
        raise ConfigValidationError("docker.network must be none.")
    if not docker.read_only_root:
        raise ConfigValidationError("docker.read_only_root must remain true.")
    if docker.allow_privileged:
        raise ConfigValidationError("docker.allow_privileged must remain false.")
    if docker.allow_docker_socket_mount:
        raise ConfigValidationError("docker.allow_docker_socket_mount must remain false.")
    if docker.allow_host_network:
        raise ConfigValidationError("docker.allow_host_network must remain false.")
    if docker.allow_dynamic_image:
        raise ConfigValidationError("docker.allow_dynamic_image must remain false.")
    if docker.allow_dynamic_mounts:
        raise ConfigValidationError("docker.allow_dynamic_mounts must remain false.")
    if not DOCKER_IMAGE_RE.fullmatch(docker.image) or docker.image.startswith("-"):
        raise ConfigValidationError("docker.image must be a static image reference without flags or whitespace.")
    if not MEMORY_LIMIT_RE.fullmatch(docker.memory):
        raise ConfigValidationError("docker.memory must be a static memory limit.")
    if not DOCKER_IMAGE_RE.fullmatch(docker.node_image) or docker.node_image.startswith("-"):
        raise ConfigValidationError("docker.node_image must be a static image reference without flags or whitespace.")
    if not MEMORY_LIMIT_RE.fullmatch(docker.node_memory):
        raise ConfigValidationError("docker.node_memory must be a static memory limit.")
    if not CPU_LIMIT_RE.fullmatch(docker.cpus) or float(docker.cpus) <= 0:
        raise ConfigValidationError("docker.cpus must be a positive static CPU limit.")
    if docker.pids_limit <= 0:
        raise ConfigValidationError("docker.pids_limit must be positive.")
    if docker.timeout_seconds <= 0:
        raise ConfigValidationError("docker.timeout_seconds must be positive.")
    return docker


def _validate_root_list(
    values: list[str],
    *,
    base_dir: Path,
    project_root: Path,
    protected_patterns: tuple[str, ...],
    role: str,
    allow_project_root: bool,
    require_inside_project_root: bool,
    scan_protected_targets: bool,
) -> tuple[Path, ...]:
    return tuple(
        _validate_root(
            value,
            base_dir=base_dir,
            project_root=project_root,
            protected_patterns=protected_patterns,
            role=role,
            allow_project_root=allow_project_root,
            require_inside_project_root=require_inside_project_root,
            scan_protected_targets=scan_protected_targets,
        )
        for value in values
    )


def _validate_root(
    value: str,
    *,
    base_dir: Path,
    project_root: Path,
    protected_patterns: tuple[str, ...],
    role: str,
    allow_project_root: bool,
    require_inside_project_root: bool,
    scan_protected_targets: bool,
) -> Path:
    if _has_parent_traversal(value):
        raise ConfigValidationError(f"{role} must not use parent traversal: {value}")

    resolved = _resolve_path(value, base_dir)
    if _is_filesystem_root(resolved):
        raise ConfigValidationError(f"{role} must not be a filesystem root: {resolved}")
    if _is_home_root(resolved):
        raise ConfigValidationError(f"{role} must not be the user home directory: {resolved}")
    if _is_system_path(resolved):
        raise ConfigValidationError(f"{role} must not be a system directory: {resolved}")

    source_overlap = _source_overlap(resolved, project_root)
    if source_overlap:
        raise ConfigValidationError(f"{role} must not overlap {source_overlap}: {resolved}")

    if require_inside_project_root and not _is_inside_or_same(resolved, project_root):
        raise ConfigValidationError(f"{role} must stay inside the project root: {resolved}")
    if not allow_project_root and _same_path(resolved, project_root):
        raise ConfigValidationError(f"{role} must not be the repository root unless explicitly allowed.")
    if resolved.exists() and not resolved.is_dir():
        raise ConfigValidationError(f"{role} must be a directory when it already exists: {resolved}")
    if scan_protected_targets and _contains_protected_target(resolved, protected_patterns, project_root):
        raise ConfigValidationError(f"{role} contains protected governance targets: {resolved}")
    return resolved


def _validate_private_state_root(
    *,
    state_root: Path,
    pending_plan_root: Path,
    allowed_roots: tuple[Path, ...],
    profile_root: Path,
) -> None:
    protected_state_roots = (state_root, pending_plan_root)
    for protected_root in protected_state_roots:
        if _is_inside_or_same(protected_root, profile_root) or _is_inside_or_same(profile_root, protected_root):
            raise ConfigValidationError("runtime state root must not overlap profile root.")
        for allowed_root in allowed_roots:
            if _is_inside_or_same(protected_root, allowed_root) or _is_inside_or_same(allowed_root, protected_root):
                raise ConfigValidationError("runtime state root must not overlap workspace allowed_roots.")


def _source_overlap(candidate: Path, project_root: Path) -> str | None:
    parts = {part.casefold() for part in candidate.parts}
    if "pba2" in parts:
        return "Source A ../PBA2"
    if "mcp_hardened_commander" in parts:
        return "Source B ../MCP_Hardened_Commander"
    source_roots = (
        ("Source A ../PBA2", (project_root.parent / "PBA2").resolve(strict=False)),
        ("Source B ../MCP_Hardened_Commander", (project_root.parent / "MCP_Hardened_Commander").resolve(strict=False)),
    )
    for label, source_root in source_roots:
        if _is_inside_or_same(candidate, source_root) or _is_inside_or_same(source_root, candidate):
            return label
    return None


def _contains_protected_target(root: Path, protected_patterns: tuple[str, ...], project_root: Path) -> bool:
    if not root.exists():
        return False
    try:
        candidates = root.rglob("*")
        for candidate in candidates:
            if not candidate.is_file():
                continue
            resolved = candidate.resolve(strict=False)
            if resolved.name.casefold() in _protected_filenames_casefold():
                return True
            if _matches_protected_pattern(resolved, protected_patterns, project_root):
                return True
    except OSError as exc:
        raise ConfigValidationError(f"Unable to inspect {root} for protected targets: {exc}") from exc
    return False


def _matches_protected_pattern(candidate: Path, protected_patterns: tuple[str, ...], project_root: Path) -> bool:
    candidate_text = _normalize(candidate)
    for raw_pattern in protected_patterns:
        pattern_path = Path(raw_pattern).expanduser()
        if not pattern_path.is_absolute():
            pattern_path = project_root / pattern_path
        if fnmatch.fnmatch(candidate_text, _normalize(pattern_path)):
            return True
    return False


def _has_parent_traversal(path_value: str) -> bool:
    return ".." in path_value.replace("\\", "/").split("/")


def _is_inside_or_same(candidate: Path, root: Path) -> bool:
    try:
        common_path = os.path.commonpath([_normalize(candidate), _normalize(root)])
    except ValueError:
        return False
    return common_path == _normalize(root)


def _same_path(left: Path, right: Path) -> bool:
    return _normalize(left) == _normalize(right)


def _is_filesystem_root(path_value: Path) -> bool:
    anchor = Path(path_value.anchor) if path_value.anchor else None
    return anchor is not None and _same_path(path_value, anchor)


def _is_home_root(path_value: Path) -> bool:
    return _same_path(path_value, Path.home().resolve(strict=False))


def _is_system_path(path_value: Path) -> bool:
    if sys.platform != "win32":
        return False
    system_root = os.environ.get("SystemRoot") or r"C:\Windows"
    windows_root = Path(system_root).resolve(strict=False)
    return _is_inside_or_same(path_value, windows_root)


def _protected_filenames_casefold() -> frozenset[str]:
    return frozenset(name.casefold() for name in PROTECTED_GOVERNANCE_FILENAMES)


def _normalize(path_value: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path_value)))
