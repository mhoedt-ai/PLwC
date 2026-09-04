from __future__ import annotations

import configparser
import hashlib
import hmac
import json
import os
import shutil
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:
    from .doctor import collect_windows_system_facts
except ImportError:  # Standalone copy extracted by Windows Setup.
    from doctor import collect_windows_system_facts  # type: ignore[no-redef]


INSTALLER_STATE_SCHEMA_VERSION = "1.0.0"
INSTALLER_MIGRATION_PLAN_VERSION = "1.0.0"
INSTALLER_MANAGED_CONFIG_PATHS = (
    "gateway-settings.json",
    "installer/installation-summary.txt",
    "installer/selection.ini",
    "clients/codex/plwc-gateway.generated.toml",
    "clients/odysseus/plwc-gateway.generated.json",
    "native-messaging/plwc.chat_bridge.launcher.json",
)


class InstallerStateError(ValueError):
    """Raised when installer state is unsafe, stale, or outside its allowlist."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str | None:
    try:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _tree_hashes(root: Path) -> dict[str, dict[str, Any]]:
    if not root.is_dir():
        return {}
    result: dict[str, dict[str, Any]] = {}
    try:
        files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.as_posix().casefold())
    except OSError:
        return {}
    for path in files:
        digest = _sha256(path)
        try:
            size = path.stat().st_size
        except OSError:
            size = None
        result[path.relative_to(root).as_posix()] = {"sha256": digest, "size": size}
    return result


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return dict(value) if isinstance(value, dict) else None


def _logical_gateway_settings(path: Path) -> dict[str, Any] | None:
    value = _read_json(path)
    if value is None:
        return None
    return {
        "schema_version": value.get("schema_version"),
        "settings": value.get("settings"),
    }


def _read_selection(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if path.is_file():
        try:
            parser.read(path, encoding="utf-8-sig")
        except (OSError, UnicodeError, configparser.Error):
            pass
    return parser


def _process_value(process: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in process:
            return process[name]
    lowered = {str(key).casefold(): value for key, value in process.items()}
    for name in names:
        if name.casefold() in lowered:
            return lowered[name.casefold()]
    return None


def _path_in_roots(value: Any, roots: list[Path]) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        path = Path(value.strip().strip('"')).resolve(strict=False)
    except OSError:
        return False
    return any(_inside(path, root) for root in roots)


def _proven_plwc_process(process: Mapping[str, Any], roots: list[Path]) -> bool:
    executable = _process_value(process, "ExecutablePath", "executable_path")
    if _path_in_roots(executable, roots):
        return True
    command_line = _process_value(process, "CommandLine", "command_line")
    if not isinstance(command_line, str):
        return False
    folded = command_line.casefold()
    runtime_marker = any(marker in folded for marker in ("bridge\\dist", "bridge/dist", "plwc-chat-bridge-launcher"))
    return runtime_marker and any(str(root).casefold() in folded for root in roots)


def _pid(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _known_shortcut_path(path: Path) -> bool:
    allowed_names = {
        "plwc chat bridge.lnk",
        "plwc.lnk",
        "plwc-konfiguration.lnk",
        "plwc konfiguration.lnk",
        "plwc configuration.lnk",
    }
    if path.name.casefold() not in allowed_names:
        return False
    roots = [
        Path(value).resolve(strict=False)
        for value in (os.environ.get("APPDATA"), os.environ.get("USERPROFILE"))
        if value
    ]
    return bool(roots) and any(_inside(path, root) for root in roots)


class InstallerStateEngine:
    """Shared r26 preflight, migration, rollback, and hard-postflight engine."""

    def __init__(
        self,
        installation_root: Path,
        *,
        app_root: Path,
        gateway_root: Path,
        bridge_root: Path,
        workspace_root: Path,
        profile_root: Path,
        config_root: Path,
        state_root: Path,
        logs_root: Path,
        backups_root: Path,
    ) -> None:
        self.installation_root = installation_root.resolve(strict=False)
        self.app_root = app_root.resolve(strict=False)
        self.gateway_root = gateway_root.resolve(strict=False)
        self.bridge_root = bridge_root.resolve(strict=False)
        self.workspace_root = workspace_root.resolve(strict=False)
        self.profile_root = profile_root.resolve(strict=False)
        self.config_root = config_root.resolve(strict=False)
        self.state_root = state_root.resolve(strict=False)
        self.logs_root = logs_root.resolve(strict=False)
        self.backups_root = backups_root.resolve(strict=False)
        if not _inside(self.gateway_root, self.app_root) or not _inside(self.bridge_root, self.app_root):
            raise InstallerStateError("Gateway and Bridge targets must stay below the PLwC app root.")
        if self.bridge_root.name.casefold() != "bridge":
            raise InstallerStateError("r26 requires the versionless app\\bridge runtime target.")
        if _inside(self.gateway_root, self.bridge_root) or _inside(self.bridge_root, self.gateway_root):
            raise InstallerStateError("Gateway and Bridge runtime targets must not overlap.")
        data_roots = {
            "workspace": self.workspace_root,
            "profiles": self.profile_root,
            "config": self.config_root,
            "state": self.state_root,
            "logs": self.logs_root,
            "backups": self.backups_root,
        }
        for name, path in data_roots.items():
            if _inside(path, self.app_root) or _inside(self.app_root, path):
                raise InstallerStateError(f"The {name} data root must not overlap the PLwC app root.")
        items = list(data_roots.items())
        for index, (first_name, first_path) in enumerate(items):
            for second_name, second_path in items[index + 1 :]:
                if _inside(first_path, second_path) or _inside(second_path, first_path):
                    raise InstallerStateError(
                        f"The {first_name} and {second_name} data roots must not overlap."
                    )

    @property
    def gateway_settings_path(self) -> Path:
        return self.installation_root / "config" / "gateway-settings.json"

    def _legacy_paths(self, stored_bridge_path: str | None) -> list[Path]:
        candidates = [self.app_root / "chat-bridge"]
        candidates.extend(sorted(self.app_root.glob("chat-bridge-*")))
        candidates.extend(sorted(self.app_root.glob("bridge-*")))
        if stored_bridge_path:
            candidates.append(Path(stored_bridge_path))
        unique: dict[str, Path] = {}
        for candidate in candidates:
            resolved = candidate.resolve(strict=False)
            if resolved == self.bridge_root or not resolved.exists() or not _inside(resolved, self.app_root):
                continue
            unique[str(resolved).casefold()] = resolved
        return sorted(unique.values(), key=lambda path: str(path).casefold())

    def preflight(
        self,
        *,
        selection_path: Path,
        system_facts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Collect evidence only. This method does not create or change state."""

        selection = _read_selection(selection_path)
        stored_bridge = selection.get("PLwC", "BridgePath", fallback="").strip() if selection.has_section("PLwC") else ""
        legacy = self._legacy_paths(stored_bridge)
        systems = dict(system_facts) if isinstance(system_facts, Mapping) else collect_windows_system_facts()
        approved_roots = [self.bridge_root, *legacy]
        processes = systems.get("processes") if isinstance(systems.get("processes"), list) else []
        process_attribution: list[dict[str, Any]] = []
        for process in processes:
            if not isinstance(process, Mapping):
                continue
            command_line = str(_process_value(process, "CommandLine", "command_line") or "")
            if _proven_plwc_process(process, approved_roots):
                classification = "proven"
            elif "plwc" in command_line.casefold():
                classification = "suspected"
            else:
                classification = "unknown"
            process_attribution.append(
                {
                    "pid": _pid(_process_value(process, "ProcessId", "process_id")),
                    "classification": classification,
                    "executable": _process_value(process, "ExecutablePath", "executable_path"),
                    "command_line": command_line or None,
                }
            )
        facts = {
            "paths": {
                "installation_root": str(self.installation_root),
                "app": str(self.app_root),
                "gateway": str(self.gateway_root),
                "bridge": str(self.bridge_root),
                "workspace": str(self.workspace_root),
                "profiles": str(self.profile_root),
                "config": str(self.config_root),
                "state": str(self.state_root),
                "logs": str(self.logs_root),
                "backups": str(self.backups_root),
                "selection": str(selection_path.resolve(strict=False)),
            },
            "existing": {
                "app": self.app_root.is_dir(),
                "gateway": self.gateway_root.is_dir(),
                "bridge": self.bridge_root.is_dir(),
                "workspace": self.workspace_root.is_dir(),
                "profiles": self.profile_root.is_dir(),
                "config": self.config_root.is_dir(),
            },
            "stored_bridge_path": stored_bridge or None,
            "legacy_paths": [str(path) for path in legacy],
            "attribution": {
                "states": ["proven", "suspected", "unknown"],
                "processes": process_attribution,
                "foreign_port_owners": self._foreign_port_owners(systems, approved_roots),
            },
            "preserved": {
                "profiles": _tree_hashes(self.profile_root),
                "config": _tree_hashes(self.config_root),
                "gateway_settings": _logical_gateway_settings(self.gateway_settings_path),
            },
            "runtime_identities": {
                "bridge": _read_json(self.bridge_root / "build-identity.json"),
                "gateway": _read_json(self.gateway_root / "manifest.json"),
                "installer_selection": (
                    dict(selection.items("BuildIdentity")) if selection.has_section("BuildIdentity") else None
                ),
                "launcher_result": _read_json(self.state_root / "chat-bridge" / "launcher-last-result.json"),
            },
            "integration": {
                "native_messaging": systems.get("native_messaging"),
                "shortcuts": systems.get("shortcuts"),
                "scheduled_tasks": systems.get("scheduled_tasks"),
            },
            "system": systems,
        }
        snapshot_core = {"schema_version": INSTALLER_STATE_SCHEMA_VERSION, "facts": facts}
        return {
            "ok": True,
            "schema_version": INSTALLER_STATE_SCHEMA_VERSION,
            "generated_at": _now(),
            "read_only": True,
            "snapshot_id": _digest(snapshot_core),
            "facts": facts,
        }

    @staticmethod
    def _foreign_port_owners(system: Mapping[str, Any], approved_roots: list[Path]) -> list[dict[str, Any]]:
        processes = system.get("processes") if isinstance(system.get("processes"), list) else []
        process_by_pid = {
            _pid(_process_value(process, "ProcessId", "process_id")): process
            for process in processes
            if isinstance(process, Mapping)
        }
        owners: list[dict[str, Any]] = []
        ports = system.get("port_3007") if isinstance(system.get("port_3007"), list) else []
        for port in ports:
            if not isinstance(port, Mapping):
                continue
            owner_pid = _pid(_process_value(port, "OwningProcess", "owning_process"))
            process = process_by_pid.get(owner_pid)
            if process is None or not _proven_plwc_process(process, approved_roots):
                owners.append({"pid": owner_pid, "process": dict(process) if isinstance(process, Mapping) else None})
        return owners

    def plan(self, preflight: Mapping[str, Any]) -> dict[str, Any]:
        if preflight.get("read_only") is not True or not isinstance(preflight.get("snapshot_id"), str):
            raise InstallerStateError("Migration planning requires a valid read-only preflight snapshot.")
        facts = preflight.get("facts")
        if not isinstance(facts, Mapping):
            raise InstallerStateError("Preflight facts are missing.")
        legacy = [Path(str(path)).resolve(strict=False) for path in facts.get("legacy_paths", [])]
        approved_roots = [self.bridge_root, *legacy]
        system = facts.get("system") if isinstance(facts.get("system"), Mapping) else {}
        foreign = self._foreign_port_owners(system, approved_roots)
        processes = system.get("processes") if isinstance(system.get("processes"), list) else []
        proven = [
            dict(process) for process in processes
            if isinstance(process, Mapping) and _proven_plwc_process(process, approved_roots)
        ]
        actions: list[dict[str, Any]] = []
        if self.app_root.exists():
            actions.append(
                {
                    "type": "backup_application_tree",
                    "path": str(self.app_root),
                    "explanation": "Back up the complete existing PLwC application tree before r26 replaces runtime files.",
                }
            )
        for process in proven:
            actions.append(
                {
                    "type": "stop_proven_plwc_process",
                    "pid": _pid(_process_value(process, "ProcessId", "process_id")),
                    "executable": _process_value(process, "ExecutablePath", "executable_path"),
                    "explanation": "Stop only a process whose executable path or PLwC Bridge command is inside an inventoried PLwC runtime.",
                }
            )
        for path in legacy:
            actions.append(
                {
                    "type": "archive_legacy_after_postflight",
                    "path": str(path),
                    "explanation": "Keep the legacy runtime as recovery evidence until the r26 8/8 postflight succeeds.",
                }
            )
        core = {
            "schema_version": INSTALLER_MIGRATION_PLAN_VERSION,
            "snapshot_id": preflight["snapshot_id"],
            "target_bridge": str(self.bridge_root),
            "actions": actions,
            "foreign_port_owners": foreign,
        }
        return {
            "ok": not foreign,
            **core,
            "plan_id": _digest(core),
            "blocked": bool(foreign),
            "block_reason": "foreign_port_3007_owner" if foreign else None,
            "confirmation_source": "confirmed_windows_setup_run",
        }

    @staticmethod
    def _verify_plan(plan: Mapping[str, Any]) -> None:
        actions = plan.get("actions")
        if plan.get("schema_version") != INSTALLER_MIGRATION_PLAN_VERSION or not isinstance(actions, list):
            raise InstallerStateError("Unsupported installer migration plan.")
        core = {
            "schema_version": plan["schema_version"],
            "snapshot_id": plan.get("snapshot_id"),
            "target_bridge": plan.get("target_bridge"),
            "actions": actions,
            "foreign_port_owners": plan.get("foreign_port_owners"),
        }
        if not isinstance(plan.get("plan_id"), str) or not hmac.compare_digest(plan["plan_id"], _digest(core)):
            raise InstallerStateError("Installer migration plan was changed after preflight.")

    def prepare(
        self,
        plan: Mapping[str, Any],
        *,
        confirmed_plan_id: str,
        current_preflight: Mapping[str, Any],
        current_system_facts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._verify_plan(plan)
        if not hmac.compare_digest(str(plan["plan_id"]), confirmed_plan_id):
            raise InstallerStateError("Installer migration requires the exact confirmed plan ID.")
        if plan.get("blocked") is True or plan.get("foreign_port_owners"):
            raise InstallerStateError("Port 3007 is owned by an unverified process; no process was stopped.")
        if current_preflight.get("snapshot_id") != plan.get("snapshot_id"):
            raise InstallerStateError("Installer state changed after preflight; review a new migration plan.")
        backup_root = self.backups_root / "installer-r26" / str(plan["snapshot_id"])
        target_backup = backup_root / "app-before-r26"
        applied: list[dict[str, Any]] = []
        current_system = dict(current_system_facts) if isinstance(current_system_facts, Mapping) else collect_windows_system_facts()
        current_processes = current_system.get("processes") if isinstance(current_system.get("processes"), list) else []
        legacy = [Path(str(path)).resolve(strict=False) for path in current_preflight.get("facts", {}).get("legacy_paths", [])]
        approved_roots = [self.bridge_root, *legacy]
        current_foreign = self._foreign_port_owners(current_system, approved_roots)
        if current_foreign:
            raise InstallerStateError("Port 3007 is now owned by an unverified process; no process was stopped.")
        integration_backup_root = backup_root / "windows-integration-before-r26"
        config_file_backups: list[dict[str, Any]] = []
        for index, relative in enumerate(INSTALLER_MANAGED_CONFIG_PATHS):
            source = (self.config_root / relative).resolve(strict=False)
            if not _inside(source, self.config_root):
                raise InstallerStateError("Installer-managed config backup escaped the PLwC config root.")
            entry: dict[str, Any] = {
                "path": str(source),
                "relative": relative,
                "existed": source.is_file(),
                "backup": None,
            }
            if source.is_file():
                backup = integration_backup_root / "config-files" / f"{index:02d}-{source.name}"
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)
                entry["backup"] = str(backup)
            config_file_backups.append(entry)
        shortcut_backups: list[dict[str, Any]] = []
        shortcuts = current_preflight.get("facts", {}).get("integration", {}).get("shortcuts", [])
        if isinstance(shortcuts, list):
            for index, item in enumerate(shortcuts):
                if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                    continue
                source = Path(str(item["path"])).resolve(strict=False)
                if not _known_shortcut_path(source):
                    continue
                entry: dict[str, Any] = {"path": str(source), "existed": source.is_file(), "backup": None}
                if source.is_file():
                    backup = integration_backup_root / "shortcuts" / f"{index:02d}-{source.name}"
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, backup)
                    entry["backup"] = str(backup)
                shortcut_backups.append(entry)
        task_backups: list[dict[str, Any]] = []
        scheduled_tasks = current_preflight.get("facts", {}).get("integration", {}).get("scheduled_tasks", [])
        if os.name == "nt" and isinstance(scheduled_tasks, list):
            for index, task in enumerate(scheduled_tasks):
                if not isinstance(task, Mapping):
                    continue
                task_name = str(_process_value(task, "TaskName", "task_name") or "")
                task_path = str(_process_value(task, "TaskPath", "task_path") or "\\")
                if task_name.casefold() not in {"plwc chat bridge", "plwc bridge"}:
                    continue
                qualified = task_path.rstrip("\\") + "\\" + task_name
                completed = subprocess.run(
                    ["schtasks.exe", "/Query", "/TN", qualified, "/XML"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if completed.returncode == 0 and completed.stdout.strip():
                    backup = integration_backup_root / "scheduled-tasks" / f"{index:02d}.xml"
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_text(completed.stdout, encoding="utf-8")
                    task_backups.append({"task_name": qualified, "backup": str(backup)})
        for action in plan["actions"]:
            if action.get("type") == "backup_application_tree":
                source = Path(str(action.get("path"))).resolve(strict=False)
                if source != self.app_root:
                    raise InstallerStateError("Application backup escaped the configured PLwC app root.")
                if source.is_dir() and not target_backup.exists():
                    target_backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(source, target_backup, copy_function=shutil.copy2)
                applied.append({"type": action["type"], "source": str(source), "backup": str(target_backup)})
            elif action.get("type") == "stop_proven_plwc_process":
                process_id = _pid(action.get("pid"))
                if process_id is None:
                    raise InstallerStateError("A proven PLwC process action has no valid PID.")
                matching = [
                    process for process in current_processes
                    if isinstance(process, Mapping)
                    and _pid(_process_value(process, "ProcessId", "process_id")) == process_id
                ]
                if matching and not all(_proven_plwc_process(process, approved_roots) for process in matching):
                    raise InstallerStateError("A planned PLwC PID now belongs to an unverified process; it was not stopped.")
                if os.name == "nt":
                    try:
                        os.kill(process_id, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                applied.append({"type": action["type"], "pid": process_id})
            elif action.get("type") == "archive_legacy_after_postflight":
                continue
            else:
                raise InstallerStateError(f"Unsupported installer migration action: {action.get('type')!r}.")
        record = {
            "ok": True,
            "schema_version": INSTALLER_STATE_SCHEMA_VERSION,
            "prepared_at": _now(),
            "plan_id": plan["plan_id"],
            "snapshot_id": plan["snapshot_id"],
            "backup_root": str(backup_root),
            "target_backup": str(target_backup) if target_backup.exists() else None,
            "target_existed": self.app_root.exists(),
            "applied": applied,
            "config_file_backups": config_file_backups,
            "shortcut_backups": shortcut_backups,
            "scheduled_task_backups": task_backups,
        }
        backup_root.mkdir(parents=True, exist_ok=True)
        (backup_root / "prepare-result.json").write_text(_canonical(record) + "\n", encoding="utf-8")
        return record

    @staticmethod
    def _restore_native_messaging(preflight: Mapping[str, Any]) -> list[str]:
        if os.name != "nt":
            return []
        native = preflight.get("facts", {}).get("integration", {}).get("native_messaging", {})
        if not isinstance(native, Mapping):
            return []
        import winreg

        registry_paths = {
            "chrome": r"Software\Google\Chrome\NativeMessagingHosts\plwc.chat_bridge.launcher",
            "edge": r"Software\Microsoft\Edge\NativeMessagingHosts\plwc.chat_bridge.launcher",
            "brave": r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\plwc.chat_bridge.launcher",
        }
        errors: list[str] = []
        for browser, key_path in registry_paths.items():
            entry = native.get(browser)
            if not isinstance(entry, Mapping) or entry.get("registered") is None:
                continue
            try:
                if entry.get("registered") is True and isinstance(entry.get("manifest"), str):
                    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, str(entry["manifest"]))
                else:
                    try:
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
                    except FileNotFoundError:
                        pass
            except OSError as exc:
                errors.append(f"native_messaging:{browser}:{exc}")
        return errors

    def rollback(
        self,
        prepare_result: Mapping[str, Any],
        *,
        preflight: Mapping[str, Any] | None = None,
        system_facts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        errors: list[str] = []
        runtime_result = "no_target_backup"
        stopped_processes = self._stop_target_bridge_for_rollback(system_facts=system_facts)
        app_backup_value = prepare_result.get("target_backup")
        snapshot_id = str(prepare_result.get("snapshot_id") or "unknown")
        suffix = snapshot_id[:12] if snapshot_id else "unknown"
        failed_runtime = self.app_root.with_name(f"{self.app_root.name}-r26-failed-{suffix}")
        restore_staging = self.app_root.with_name(f"{self.app_root.name}-r26-restore-{suffix}")
        if failed_runtime.exists() or restore_staging.exists():
            raise InstallerStateError("Installer rollback quarantine or restore staging already exists.")
        if not isinstance(app_backup_value, str) or not app_backup_value:
            if prepare_result.get("target_existed") is False and self.app_root.exists():
                self.app_root.rename(failed_runtime)
                runtime_result = "quarantined_new_application"
        else:
            backup = Path(app_backup_value).resolve(strict=False)
            allowed_backup_root = (self.backups_root / "installer-r26").resolve(strict=False)
            if not _inside(backup, allowed_backup_root) or not backup.is_dir():
                raise InstallerStateError("Installer rollback backup is outside the r26 backup root.")
            self.app_root.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(backup, restore_staging, copy_function=shutil.copy2)
            if _tree_hashes(backup) != _tree_hashes(restore_staging):
                raise InstallerStateError("Installer rollback staging does not match the application backup.")
            if self.app_root.exists():
                self.app_root.rename(failed_runtime)
            try:
                restore_staging.rename(self.app_root)
            except OSError:
                if failed_runtime.exists() and not self.app_root.exists():
                    failed_runtime.rename(self.app_root)
                raise
            runtime_result = "restored"

        allowed_config_paths = {
            (self.config_root / relative).resolve(strict=False)
            for relative in INSTALLER_MANAGED_CONFIG_PATHS
        }
        for item in prepare_result.get("config_file_backups", []):
            if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                continue
            target = Path(str(item["path"])).resolve(strict=False)
            if target not in allowed_config_paths:
                errors.append(f"config_file:unsafe:{target}")
                continue
            try:
                if target.exists() and not target.is_file():
                    raise InstallerStateError("Installer-managed config target is not a file.")
                target.unlink(missing_ok=True)
                backup_value = item.get("backup")
                if item.get("existed") is True and isinstance(backup_value, str):
                    backup = Path(backup_value).resolve(strict=False)
                    if not _inside(backup, (self.backups_root / "installer-r26").resolve(strict=False)):
                        raise InstallerStateError("Config rollback backup escaped the r26 backup root.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, target)
            except (OSError, InstallerStateError) as exc:
                errors.append(f"config_file:{target}:{exc}")

        for item in prepare_result.get("shortcut_backups", []):
            if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                continue
            target = Path(str(item["path"])).resolve(strict=False)
            if not _known_shortcut_path(target):
                errors.append(f"shortcut:unsafe:{target}")
                continue
            try:
                target.unlink(missing_ok=True)
                backup_value = item.get("backup")
                if item.get("existed") is True and isinstance(backup_value, str):
                    backup = Path(backup_value).resolve(strict=False)
                    if not _inside(backup, (self.backups_root / "installer-r26").resolve(strict=False)):
                        raise InstallerStateError("Shortcut rollback backup escaped the r26 backup root.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, target)
            except (OSError, InstallerStateError) as exc:
                errors.append(f"shortcut:{target}:{exc}")

        if os.name == "nt":
            for item in prepare_result.get("scheduled_task_backups", []):
                if not isinstance(item, Mapping):
                    continue
                task_name = str(item.get("task_name") or "")
                backup = Path(str(item.get("backup") or "")).resolve(strict=False)
                if not task_name or not _inside(backup, (self.backups_root / "installer-r26").resolve(strict=False)):
                    errors.append(f"scheduled_task:unsafe:{task_name}")
                    continue
                completed = subprocess.run(
                    ["schtasks.exe", "/Create", "/TN", task_name, "/XML", str(backup), "/F"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if completed.returncode != 0:
                    errors.append(f"scheduled_task:{task_name}:{(completed.stderr or completed.stdout).strip()}")
        if isinstance(preflight, Mapping):
            errors.extend(self._restore_native_messaging(preflight))
        return {
            "ok": not errors,
            "result": runtime_result if not errors else "partially_restored",
            "target": str(self.app_root),
            "backup": app_backup_value if isinstance(app_backup_value, str) else None,
            "quarantine": str(failed_runtime) if failed_runtime.exists() else None,
            "stopped_processes": stopped_processes,
            "errors": errors,
        }

    def _stop_target_bridge_for_rollback(
        self,
        *,
        system_facts: Mapping[str, Any] | None = None,
    ) -> list[int]:
        if os.name != "nt":
            return []
        supplied_facts = isinstance(system_facts, Mapping)
        systems = dict(system_facts) if supplied_facts else collect_windows_system_facts()
        processes = systems.get("processes") if isinstance(systems.get("processes"), list) else []
        listeners = systems.get("port_3007") if isinstance(systems.get("port_3007"), list) else []
        stopped: list[int] = []
        for listener in listeners:
            if not isinstance(listener, Mapping):
                continue
            process_id = _pid(_process_value(listener, "OwningProcess", "owning_process"))
            if process_id is None:
                continue
            matching = [
                process for process in processes
                if isinstance(process, Mapping)
                and _pid(_process_value(process, "ProcessId", "process_id")) == process_id
            ]
            if not matching or not all(_proven_plwc_process(process, [self.bridge_root]) for process in matching):
                continue
            if not supplied_facts:
                fresh = collect_windows_system_facts()
                fresh_processes = fresh.get("processes") if isinstance(fresh.get("processes"), list) else []
                matching = [
                    process for process in fresh_processes
                    if isinstance(process, Mapping)
                    and _pid(_process_value(process, "ProcessId", "process_id")) == process_id
                ]
                if not matching:
                    continue
                if not all(_proven_plwc_process(process, [self.bridge_root]) for process in matching):
                    raise InstallerStateError(
                        "The rollback Bridge PID changed identity; the process was not stopped."
                    )
            completed = subprocess.run(
                ["taskkill.exe", "/PID", str(process_id), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                raise InstallerStateError(
                    f"The verified r26 Bridge process could not be stopped before rollback: {detail}"
                )
            stopped.append(process_id)
        return stopped

    @staticmethod
    def _selected_components(selection: configparser.ConfigParser) -> set[str]:
        selected = {"common", "gateway"}
        if not selection.has_section("Components"):
            return selected
        mapping = {
            "ClaudeMCPB": "claude",
            "CodexSTDIO": "codex",
            "OdysseusSTDIO": "odysseus",
            "ChatBridge": "chat-bridge",
        }
        for key, prefix in mapping.items():
            if selection.get("Components", key, fallback="false").strip().casefold() == "true":
                selected.add(prefix)
        return selected

    def _installed_payload_path(self, relative: str) -> Path | None:
        mappings = {
            "common/": self.app_root,
            "gateway/": self.gateway_root,
            "chat-bridge/": self.bridge_root,
            "codex/": self.app_root / "clients" / "codex",
            "odysseus/": self.app_root / "clients" / "odysseus",
            "claude/": self.app_root / "packages",
        }
        normalized = relative.replace("\\", "/")
        for prefix, root in mappings.items():
            if normalized.startswith(prefix):
                target = (root / normalized[len(prefix):]).resolve(strict=False)
                return target if _inside(target, root) else None
        return None

    def postflight(
        self,
        *,
        preflight: Mapping[str, Any],
        payload_manifest_path: Path,
        selection_path: Path,
        system_facts: Mapping[str, Any] | None = None,
        expected_extension_id: str | None = None,
    ) -> dict[str, Any]:
        manifest = _read_json(payload_manifest_path)
        if manifest is None or manifest.get("schemaVersion") != 1:
            raise InstallerStateError("Installed payload manifest is missing or invalid.")
        selection = _read_selection(selection_path)
        selected = self._selected_components(selection)
        checks: list[dict[str, Any]] = []
        mismatches: list[str] = []
        files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
        for item in files:
            if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                continue
            prefix = item["path"].replace("\\", "/").split("/", 1)[0]
            if prefix not in selected:
                continue
            target = self._installed_payload_path(item["path"])
            expected = str(item.get("sha256") or "").casefold()
            mutable_generated = item["path"].replace("\\", "/").casefold() == "chat-bridge/config/plwc.example.json"
            if not mutable_generated and (target is None or not target.is_file() or _sha256(target) != expected):
                mismatches.append(item["path"])
        checks.append({"id": "payload.hashes", "ok": not mismatches, "evidence": mismatches[:50]})

        launcher = _read_json(self.state_root / "chat-bridge" / "launcher-last-result.json")
        bridge_selected = "chat-bridge" in selected
        launcher_ok = not bridge_selected or bool(
            launcher and launcher.get("ok") is True and launcher.get("toolCount") == 8
        )
        checks.append({"id": "bridge.launcher_build_tools", "ok": launcher_ok, "evidence": launcher})
        checks.append({"id": "gateway.responds", "ok": launcher_ok, "evidence": launcher})

        systems = dict(system_facts) if isinstance(system_facts, Mapping) else collect_windows_system_facts()
        probe_status = systems.get("probe_status") if isinstance(systems.get("probe_status"), Mapping) else {}

        def probe_ok(*names: str) -> bool:
            return not probe_status or all(probe_status.get(name) is True for name in names)

        probe_errors = systems.get("errors") if isinstance(systems.get("errors"), list) else []
        legacy = [Path(str(path)).resolve(strict=False) for path in preflight.get("facts", {}).get("legacy_paths", [])]
        approved = [self.bridge_root, *legacy]
        foreign = self._foreign_port_owners(systems, approved)
        port_probe_ok = probe_ok("processes", "port_3007")
        checks.append({"id": "port.3007_owner", "ok": port_probe_ok and not foreign, "evidence": foreign or ([] if port_probe_ok else probe_errors)})
        processes = systems.get("processes") if isinstance(systems.get("processes"), list) else []
        old_processes = [
            dict(process) for process in processes
            if isinstance(process, Mapping) and _proven_plwc_process(process, legacy)
        ]
        process_probe_ok = probe_ok("processes")
        checks.append({"id": "legacy.processes", "ok": process_probe_ok and not old_processes, "evidence": old_processes or ([] if process_probe_ok else probe_errors)})

        native = systems.get("native_messaging") if isinstance(systems.get("native_messaging"), Mapping) else {}
        native_errors: list[str] = []
        if bridge_selected:
            expected_origin = f"chrome-extension://{expected_extension_id}/" if expected_extension_id else None
            for browser in ("chrome", "edge", "brave"):
                entry = native.get(browser)
                if not isinstance(entry, Mapping) or entry.get("registered") is not True:
                    native_errors.append(f"{browser}:not_registered")
                    continue
                manifest_value = entry.get("manifest")
                manifest_path = Path(str(manifest_value)).resolve(strict=False) if manifest_value else None
                manifest_data = _read_json(manifest_path) if manifest_path else None
                command = Path(str(manifest_data.get("path", ""))).resolve(strict=False) if manifest_data else None
                origins = manifest_data.get("allowed_origins") if manifest_data else None
                if manifest_path is None or not _inside(manifest_path, self.config_root):
                    native_errors.append(f"{browser}:manifest_outside_config")
                elif command != (self.bridge_root / "native" / "bin" / "plwc-chat-bridge-launcher.exe").resolve(strict=False):
                    native_errors.append(f"{browser}:wrong_launcher")
                elif expected_origin and (not isinstance(origins, list) or expected_origin not in origins):
                    native_errors.append(f"{browser}:wrong_extension_origin")
        checks.append({"id": "native_messaging.registration", "ok": not native_errors, "evidence": native_errors})
        shortcuts = systems.get("shortcuts") if isinstance(systems.get("shortcuts"), list) else []
        startup = [item for item in shortcuts if isinstance(item, Mapping) and str(item.get("path", "")).casefold().endswith("plwc chat bridge.lnk") and item.get("exists") is True]
        expected_launcher = (self.bridge_root / "native" / "bin" / "plwc-chat-bridge-launcher.exe").resolve(strict=False)
        shortcut_probe_ok = probe_ok("shortcuts")
        shortcuts_ok = not bridge_selected or (shortcut_probe_ok and
            len(startup) == 1
            and Path(str(startup[0].get("target", ""))).resolve(strict=False) == expected_launcher
            and str(startup[0].get("arguments", "")).strip().startswith("--start --delay-seconds 20 --lang ")
        )
        checks.append({"id": "shortcuts.autostart", "ok": shortcuts_ok, "evidence": startup or ([] if shortcut_probe_ok else probe_errors)})

        old_tasks = [
            dict(item) for item in systems.get("scheduled_tasks", [])
            if isinstance(item, Mapping) and str(item.get("TaskName", item.get("task_name", ""))).casefold() in {
                "plwc chat bridge", "plwc bridge"
            }
        ] if isinstance(systems.get("scheduled_tasks"), list) else []
        task_probe_ok = probe_ok("scheduled_tasks")
        checks.append({"id": "scheduled_tasks.legacy", "ok": task_probe_ok and not old_tasks, "evidence": old_tasks or ([] if task_probe_ok else probe_errors)})

        config_script = self.app_root / "configuration" / "plwc-config.py"
        config_ui_ok = all(
            path.is_file()
            for path in (
                config_script,
                self.app_root / "configuration" / "plwc.ico",
            )
        )
        config_links = [
            dict(item) for item in shortcuts
            if isinstance(item, Mapping)
            and item.get("exists") is True
            and "plwc-konfiguration.lnk" in str(item.get("path", "")).casefold()
        ]
        config_link_ok = any(
            Path(str(item.get("target", ""))).name.casefold() in {"python.exe", "pythonw.exe"}
            and str(config_script).casefold() in str(item.get("arguments", "")).casefold()
            for item in config_links
        )
        checks.append({"id": "configuration.ui_icon", "ok": shortcut_probe_ok and config_ui_ok and config_link_ok, "evidence": config_links or ([] if shortcut_probe_ok else probe_errors)})

        preserved = preflight.get("facts", {}).get("preserved", {})
        before_profiles = preserved.get("profiles") if isinstance(preserved, Mapping) else {}
        before_config = preserved.get("config") if isinstance(preserved, Mapping) else {}
        after_profiles = _tree_hashes(self.profile_root)
        after_config = _tree_hashes(self.config_root)
        profile_changes = [key for key, value in before_profiles.items() if after_profiles.get(key) != value] if isinstance(before_profiles, Mapping) else []
        installer_managed_config = {
            "native-messaging/plwc.chat_bridge.launcher.json",
        }
        protected_config_changes = [
            key for key, value in before_config.items()
            if not key.startswith("installer/")
            and key != "gateway-settings.json"
            and not key.startswith("clients/")
            and key not in installer_managed_config
            and after_config.get(key) != value
        ] if isinstance(before_config, Mapping) else []
        gateway_settings_preserved = (
            preserved.get("gateway_settings") == _logical_gateway_settings(self.gateway_settings_path)
            if isinstance(preserved, Mapping) and preserved.get("gateway_settings") is not None
            else True
        )
        checks.append({"id": "user_data.profiles", "ok": not profile_changes, "evidence": profile_changes})
        checks.append({"id": "user_data.config", "ok": not protected_config_changes and gateway_settings_preserved, "evidence": protected_config_changes})

        manifest_installer = manifest.get("installer") if isinstance(manifest.get("installer"), Mapping) else {}
        bridge_identity = _read_json(self.bridge_root / "build-identity.json")
        identity_ok = (
            selection.get("BuildIdentity", "InstallerRevision", fallback="") == "installer-r26"
            and len(selection.get("BuildIdentity", "SetupExeSha256", fallback="")) == 64
            and manifest_installer.get("revision") == "installer-r26"
            and isinstance(bridge_identity, Mapping)
            and bridge_identity.get("buildId") == "plwc-chat-bridge@1.0.0"
        )
        checks.append({"id": "installation.identity", "ok": identity_ok, "evidence": []})

        report_core = {
            "schema_version": INSTALLER_STATE_SCHEMA_VERSION,
            "preflight_snapshot_id": preflight.get("snapshot_id"),
            "payload_manifest": str(payload_manifest_path.resolve(strict=False)),
            "checks": checks,
        }
        return {
            "ok": all(check["ok"] is True for check in checks),
            **report_core,
            "generated_at": _now(),
            "report_id": _digest(report_core),
        }

    def archive_legacy_after_success(
        self,
        plan: Mapping[str, Any],
        postflight: Mapping[str, Any],
    ) -> list[dict[str, str]]:
        self._verify_plan(plan)
        if postflight.get("ok") is not True:
            raise InstallerStateError("Legacy paths may be archived only after a successful postflight.")
        recovery_root = self.backups_root / "installer-r26" / str(plan["snapshot_id"]) / "legacy-recovery"
        archived: list[dict[str, str]] = []
        for action in plan["actions"]:
            if action.get("type") != "archive_legacy_after_postflight":
                continue
            source = Path(str(action.get("path"))).resolve(strict=False)
            if not _inside(source, self.app_root) or source == self.bridge_root:
                raise InstallerStateError("Legacy archive action escaped the PLwC app root.")
            if not source.exists():
                continue
            recovery_root.mkdir(parents=True, exist_ok=True)
            target = recovery_root / source.name
            if target.exists():
                raise InstallerStateError(f"Legacy recovery target already exists: {target}.")
            shutil.move(str(source), str(target))
            archived.append({"source": str(source), "recovery": str(target)})
        return archived
