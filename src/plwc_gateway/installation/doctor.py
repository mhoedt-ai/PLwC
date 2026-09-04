from __future__ import annotations

import configparser
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


DOCTOR_SCHEMA_VERSION = "1.0.0"
REPAIR_PLAN_SCHEMA_VERSION = "1.0.0"
ALLOWED_REPAIR_ACTIONS = frozenset({"ensure_directory", "restore_file_from_payload"})
REQUIRED_PROFILE_FILES = (
    "CORE.md",
    "TEMPERAMENT.md",
    "PERSONA.md",
    "memory.md",
    "reflection.md",
    "governance/config.yaml",
)
STANDARD_WORKSPACE_DIRECTORIES = ("", "Tagebuch", "Temp", "Trashcan")
_AUDIT_LOCK = threading.Lock()
STABLE_CHAT_BRIDGE_EXTENSION_ID = "nlogfcafjdfdoknpkbehjgihpafpipdb"


class DoctorContractError(ValueError):
    """Raised when a diagnosis or repair request violates the Doctor contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str | None:
    try:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(block)
        return hasher.hexdigest()
    except OSError:
        return None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return dict(value) if isinstance(value, dict) else None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _path_fact(path: Path, *, include_hash: bool = False) -> dict[str, Any]:
    fact: dict[str, Any] = {
        "path": str(path.resolve(strict=False)),
        "exists": path.exists(),
        "kind": "directory" if path.is_dir() else "file" if path.is_file() else "missing",
    }
    if include_hash and path.is_file():
        fact["sha256"] = _file_sha256(path)
        try:
            fact["size"] = path.stat().st_size
        except OSError:
            fact["size"] = None
    return fact


def _check(
    check_id: str,
    *,
    status: str,
    evidence: list[str],
    risk: str,
    recommendation: str,
    repair_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "evidence": evidence,
        "risk": risk,
        "recommendation": recommendation,
        "repair_action": repair_action,
    }


def _merge_shortcut_details(
    path_facts: list[dict[str, Any]],
    shortcut_details: Any,
) -> list[dict[str, Any]]:
    if isinstance(shortcut_details, Mapping):
        details = [dict(shortcut_details)]
    elif isinstance(shortcut_details, list):
        details = [dict(item) for item in shortcut_details if isinstance(item, Mapping)]
    else:
        details = []
    details_by_path = {
        str(item.get("path", "")).casefold(): item
        for item in details
        if str(item.get("path", "")).strip()
    }
    merged = [
        details_by_path.get(str(item.get("path", "")).casefold(), item)
        for item in path_facts
    ]
    seen = {str(item.get("path", "")).casefold() for item in merged}
    merged.extend(
        item
        for item in details
        if str(item.get("path", "")).casefold() not in seen
    )
    return merged


def _run_powershell_json(script: str, *, timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        detail = (completed.stderr or completed.stdout).strip()
        raise ValueError(detail or f"PowerShell exited with code {completed.returncode}.")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("PowerShell probe did not return a JSON object.")
    return dict(payload)


def collect_windows_system_facts(*, timeout_seconds: int = 20) -> dict[str, Any]:
    """Collect bounded, read-only Windows evidence used by the installation Doctor."""

    if os.name != "nt":
        return {
            "available": False,
            "reason": "windows_only",
            "native_messaging": {},
            "processes": [],
            "port_3007": [],
            "scheduled_tasks": [],
            "shortcuts": [],
        }

    facts: dict[str, Any] = {
        "available": True,
        "native_messaging": {},
        "processes": [],
        "port_3007": [],
        "scheduled_tasks": [],
        "shortcuts": [],
        "probe_status": {},
        "errors": [],
    }
    try:
        import winreg

        registry_paths = {
            "chrome": r"Software\Google\Chrome\NativeMessagingHosts\plwc.chat_bridge.launcher",
            "edge": r"Software\Microsoft\Edge\NativeMessagingHosts\plwc.chat_bridge.launcher",
            "brave": r"Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\plwc.chat_bridge.launcher",
        }
        for browser, key_path in registry_paths.items():
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    value, _kind = winreg.QueryValueEx(key, None)
                facts["native_messaging"][browser] = {"registered": True, "manifest": str(value)}
            except FileNotFoundError:
                facts["native_messaging"][browser] = {"registered": False, "manifest": None}
            except OSError as exc:
                facts["native_messaging"][browser] = {"registered": None, "manifest": None, "error": str(exc)}
    except (ImportError, OSError) as exc:
        facts["errors"].append(f"registry: {exc}")

    app_data = Path(os.environ.get("APPDATA", ""))
    user_profile = Path(os.environ.get("USERPROFILE", ""))
    shortcut_candidates: list[Path] = []
    if str(app_data):
        programs = app_data / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        startup = programs / "Startup"
        shortcut_candidates.extend(
            (
                startup / "PLwC Chat Bridge.lnk",
                startup / "PLwC.lnk",
                programs / "PLwC" / "PLwC configuration.lnk",
                programs / "PLwC" / "PLwC-Konfiguration.lnk",
            )
        )
    if str(user_profile):
        desktop = user_profile / "Desktop"
        shortcut_candidates.extend(
            (
                desktop / "PLwC-Konfiguration.lnk",
                desktop / "PLwC Konfiguration.lnk",
                desktop / "PLwC configuration.lnk",
            )
        )
    for candidate in shortcut_candidates:
        facts["shortcuts"].append(_path_fact(candidate))

    shortcut_script = (
        "$ErrorActionPreference='Stop';"
        "$shell=New-Object -ComObject WScript.Shell;"
        "$programs=[Environment]::GetFolderPath('Programs');"
        "$startup=[Environment]::GetFolderPath('Startup');"
        "$desktop=[Environment]::GetFolderPath('Desktop');"
        "$shortcutPaths=@();"
        "$shortcutPaths += (Join-Path $startup 'PLwC Chat Bridge.lnk');"
        "$shortcutPaths += (Join-Path $startup 'PLwC.lnk');"
        "$shortcutPaths += (Join-Path $programs 'PLwC\\PLwC configuration.lnk');"
        "$shortcutPaths += (Join-Path $programs 'PLwC\\PLwC-Konfiguration.lnk');"
        "$shortcutPaths += (Join-Path $desktop 'PLwC-Konfiguration.lnk');"
        "$shortcutPaths += (Join-Path $desktop 'PLwC Konfiguration.lnk');"
        "$shortcutPaths += (Join-Path $desktop 'PLwC configuration.lnk');"
        "$links=@();"
        "foreach($linkPath in $shortcutPaths){"
        "if(Test-Path -LiteralPath $linkPath){$link=$shell.CreateShortcut($linkPath);"
        "$links += [pscustomobject]@{path=$linkPath;exists=$true;kind='file';target=$link.TargetPath;arguments=$link.Arguments;working_directory=$link.WorkingDirectory;icon_location=$link.IconLocation}}}"
        "ConvertTo-Json -InputObject ([pscustomobject]@{shortcuts=@($links)}) -Compress -Depth 5"
    )
    process_script = (
        "$ErrorActionPreference='Stop';"
        "$items=Get-CimInstance Win32_Process | Where-Object {"
        "$_.Name -match '^(node|pythonw?|plwc-chat-bridge-launcher)\\.exe$' -or $_.CommandLine -match 'PLwC'"
        "} | Select-Object ProcessId,Name,ExecutablePath,CommandLine;"
        "ConvertTo-Json -InputObject ([pscustomobject]@{processes=@($items)}) -Compress -Depth 5"
    )
    port_script = (
        "$ErrorActionPreference='Stop';"
        "$items=Get-NetTCPConnection -State Listen -LocalPort 3007 -ErrorAction SilentlyContinue | "
        "Select-Object LocalAddress,LocalPort,OwningProcess;"
        "ConvertTo-Json -InputObject ([pscustomobject]@{port_3007=@($items)}) -Compress -Depth 5"
    )
    task_script = (
        "$ErrorActionPreference='Stop';"
        "$items=Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {$_.TaskName -match 'PLwC'} | "
        "Select-Object TaskName,TaskPath,State;"
        "ConvertTo-Json -InputObject ([pscustomobject]@{scheduled_tasks=@($items)}) -Compress -Depth 5"
    )

    for probe_name, key, script in (
        ("shortcuts", "shortcuts", shortcut_script),
        ("processes", "processes", process_script),
        ("port_3007", "port_3007", port_script),
        ("scheduled_tasks", "scheduled_tasks", task_script),
    ):
        try:
            payload = _run_powershell_json(script, timeout_seconds=timeout_seconds)
            value = payload.get(key)
            if key == "shortcuts":
                facts["shortcuts"] = _merge_shortcut_details(
                    facts["shortcuts"],
                    value,
                )
            else:
                facts[key] = value if isinstance(value, list) else ([] if value is None else [value])
            facts["probe_status"][probe_name] = True
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError) as exc:
            facts["probe_status"][probe_name] = False
            facts["errors"].append(f"powershell.{probe_name}: {exc}")
    for key in ("processes", "port_3007", "scheduled_tasks", "shortcuts"):
        if isinstance(facts.get(key), list):
            facts[key] = sorted(facts[key], key=_canonical_json)
    return facts


class InstallationDoctor:
    """Read-only installation diagnosis plus a deterministic repair transaction."""

    def __init__(
        self,
        installation_root: Path,
        *,
        workspace_root: Path | None = None,
        profile_root: Path | None = None,
        payload_root: Path | None = None,
        enable_system_probes: bool = True,
    ) -> None:
        self.installation_root = installation_root.resolve(strict=False)
        self.app_root = self.installation_root / "app"
        self.workspace_root = workspace_root.resolve(strict=False) if workspace_root else None
        self.profile_root = (profile_root or self.installation_root / "profiles").resolve(strict=False)
        self.payload_root = payload_root.resolve(strict=False) if payload_root else None
        self.state_root = self.installation_root / "state" / "doctor"
        self.audit_path = self.installation_root / "logs" / "doctor" / "repair-audit.jsonl"
        self.enable_system_probes = enable_system_probes

    def _selection(self) -> tuple[configparser.ConfigParser, Path]:
        path = self.installation_root / "config" / "installer" / "selection.ini"
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        if path.is_file():
            try:
                parser.read(path, encoding="utf-8-sig")
            except (OSError, UnicodeError, configparser.Error):
                pass
        return parser, path

    @staticmethod
    def _selected_path(parser: configparser.ConfigParser, name: str, fallback: Path) -> Path:
        value = parser.get("PLwC", name, fallback="").strip() if parser.has_section("PLwC") else ""
        return Path(value).resolve(strict=False) if value else fallback.resolve(strict=False)

    def _runtime_facts(self) -> dict[str, Any]:
        selection, selection_path = self._selection()
        gateway_root = self._selected_path(selection, "GatewayPath", self.app_root / "gateway")
        bridge_root = self._selected_path(selection, "BridgePath", self.app_root / "bridge")
        expected_files = {
            "gateway_package": gateway_root / "src" / "plwc_gateway" / "__init__.py",
            "bridge_entry": bridge_root / "bridge" / "dist" / "src" / "index.js",
            "bridge_build_identity": bridge_root / "build-identity.json",
            "native_launcher": bridge_root / "native" / "bin" / "plwc-chat-bridge-launcher.exe",
            "configuration_service": self.app_root / "configuration" / "plwc-config.py",
        }
        legacy_candidates = [self.app_root / "chat-bridge"]
        legacy_candidates.extend(sorted(self.app_root.glob("chat-bridge-*")))
        legacy_candidates.extend(sorted(self.app_root.glob("bridge-*")))
        legacy = [_path_fact(path) for path in legacy_candidates if path.exists()]
        build_identity = _read_json(expected_files["bridge_build_identity"])
        return {
            "selection": _path_fact(selection_path, include_hash=True),
            "gateway_root": _path_fact(gateway_root),
            "bridge_root": _path_fact(bridge_root),
            "expected_files": {
                name: _path_fact(path, include_hash=True) for name, path in expected_files.items()
            },
            "bridge_build_identity": build_identity,
            "legacy_paths": legacy,
        }

    def _workspace_facts(self) -> dict[str, Any]:
        if self.workspace_root is None:
            return {"configured": False, "root": None, "directories": []}
        return {
            "configured": True,
            "root": str(self.workspace_root),
            "directories": [
                _path_fact(self.workspace_root / name if name else self.workspace_root)
                for name in STANDARD_WORKSPACE_DIRECTORIES
            ],
        }

    def _profile_facts(self) -> dict[str, Any]:
        profiles: list[dict[str, Any]] = []
        if self.profile_root.is_dir():
            try:
                directories = sorted((path for path in self.profile_root.iterdir() if path.is_dir()), key=lambda path: path.name.casefold())
            except OSError:
                directories = []
            for path in directories:
                missing = [name for name in REQUIRED_PROFILE_FILES if not (path / Path(name)).is_file()]
                profiles.append(
                    {
                        "name": path.name,
                        "path": str(path.resolve(strict=False)),
                        "valid": not missing,
                        "missing_required_files": missing,
                    }
                )
        return {"root": _path_fact(self.profile_root), "profiles": profiles}

    def _state_facts(self) -> dict[str, Any]:
        bridge_state = self.installation_root / "state" / "chat-bridge"
        logs = self.installation_root / "logs"
        return {
            "launcher_last_result": _read_json(bridge_state / "launcher-last-result.json"),
            "browser_extension_last_contact": _read_json(bridge_state / "browser-extension-last-contact.json"),
            "logs_root": _path_fact(logs),
            "known_logs": {
                "launcher": _path_fact(logs / "chat-bridge" / "native-launcher.log"),
                "installer": _path_fact(logs / "setup" / "installer-diagnostic.log"),
                "audit": _path_fact(self.installation_root / "logs" / "audit.jsonl"),
            },
        }

    @staticmethod
    def _component_summary(component_inventory: Mapping[str, Any] | None) -> list[dict[str, Any]]:
        components = component_inventory.get("components") if isinstance(component_inventory, Mapping) else None
        if not isinstance(components, list):
            return []
        summary: list[dict[str, Any]] = []
        for value in components:
            if not isinstance(value, Mapping):
                continue
            installed = value.get("installed") if isinstance(value.get("installed"), Mapping) else {}
            summary.append(
                {
                    "id": value.get("id"),
                    "required": value.get("required"),
                    "status": value.get("status"),
                    "compatible": value.get("compatible"),
                    "semantic_version": installed.get("semantic_version"),
                    "build_revision": installed.get("build_revision"),
                    "build_id": installed.get("build_id"),
                    "sha256": installed.get("sha256"),
                }
            )
        return summary

    def hard_postflight(
        self,
        *,
        system_facts: Mapping[str, Any] | None = None,
        expected_extension_id: str = STABLE_CHAT_BRIDGE_EXTENSION_ID,
    ) -> dict[str, Any] | None:
        """Reuse the installer's hash and exact 8/8 postflight for an installed r26 payload."""

        from .installer_state import InstallerStateEngine

        selection, selection_path = self._selection()
        app_root = self._selected_path(selection, "AppPath", self.app_root)
        payload_manifest = app_root / "installation" / "payload-manifest.json"
        if not payload_manifest.is_file():
            return None
        gateway_root = self._selected_path(selection, "GatewayPath", app_root / "gateway")
        bridge_root = self._selected_path(selection, "BridgePath", app_root / "bridge")
        workspace_root = self._selected_path(selection, "WorkspacePath", self.installation_root / "workspace")
        profile_root = self._selected_path(selection, "ProfilesPath", self.profile_root)
        config_root = self._selected_path(selection, "ConfigPath", self.installation_root / "config")
        state_root = self._selected_path(selection, "StatePath", self.installation_root / "state")
        logs_root = self._selected_path(selection, "LogsPath", self.installation_root / "logs")
        backups_root = self._selected_path(selection, "BackupsPath", self.installation_root / "profile_backups")
        engine = InstallerStateEngine(
            self.installation_root,
            app_root=app_root,
            gateway_root=gateway_root,
            bridge_root=bridge_root,
            workspace_root=workspace_root,
            profile_root=profile_root,
            config_root=config_root,
            state_root=state_root,
            logs_root=logs_root,
            backups_root=backups_root,
        )
        preflight = engine.preflight(selection_path=selection_path, system_facts=system_facts)
        return engine.postflight(
            preflight=preflight,
            payload_manifest_path=payload_manifest,
            selection_path=selection_path,
            system_facts=system_facts,
            expected_extension_id=expected_extension_id,
        )

    def diagnose(
        self,
        *,
        component_inventory: Mapping[str, Any] | None = None,
        clu_diagnostic: Mapping[str, Any] | None = None,
        system_facts: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a diagnosis without creating, changing, or deleting local state."""

        runtime = self._runtime_facts()
        workspace = self._workspace_facts()
        profiles = self._profile_facts()
        state = self._state_facts()
        systems = dict(system_facts) if isinstance(system_facts, Mapping) else (
            collect_windows_system_facts() if self.enable_system_probes else {"available": False, "reason": "disabled"}
        )
        components = self._component_summary(component_inventory)
        try:
            hard_postflight = self.hard_postflight(system_facts=systems)
        except (OSError, ValueError) as exc:
            hard_postflight = {"ok": False, "error": str(exc), "checks": []}
        facts = {
            "installation_root": str(self.installation_root),
            "runtime": runtime,
            "workspace": workspace,
            "profiles": profiles,
            "state": state,
            "components": components,
            "system": systems,
            "hard_postflight": hard_postflight,
        }
        checks: list[dict[str, Any]] = []

        if hard_postflight is not None:
            checks.append(
                _check(
                    "installation.hard_postflight",
                    status="PASS" if hard_postflight.get("ok") is True else "FAIL",
                    evidence=[
                        "shared_engine=true",
                        f"report_id={hard_postflight.get('report_id', 'unavailable')}",
                    ],
                    risk="A failed shared postflight means the installed payload or exact 8/8 runtime is not confirmed.",
                    recommendation="Review the shared Installer/Doctor postflight checks before repair.",
                )
            )

        bad_components = [
            item for item in components
            if item.get("status") in {"required_update", "missing", "mixed_installation"}
        ]
        unknown_components = [item for item in components if item.get("status") == "unknown"]
        checks.append(
            _check(
                "installation.compatibility",
                status="FAIL" if bad_components else "WARN" if unknown_components else "PASS",
                evidence=[
                    "blocking=" + (",".join(str(item.get("id")) for item in bad_components) or "none"),
                    "unknown=" + (",".join(str(item.get("id")) for item in unknown_components) or "none"),
                ],
                risk="Incompatible required components can make the runtime unsafe or unavailable.",
                recommendation="Use only trusted component identities and the shared compatibility matrix.",
            )
        )

        missing_runtime = [
            name for name, value in runtime["expected_files"].items() if value["kind"] != "file"
        ]
        checks.append(
            _check(
                "installation.runtime_files",
                status="FAIL" if missing_runtime else "PASS",
                evidence=["missing=" + (",".join(missing_runtime) or "none")],
                risk="Missing runtime files prevent a reliable bridge or configuration start.",
                recommendation=(
                    "Restore only from a hash-verified PLwC payload."
                    if missing_runtime
                    else "No runtime-file repair is required."
                ),
            )
        )

        legacy_paths = runtime["legacy_paths"]
        bridge_present = runtime["bridge_root"]["kind"] == "directory"
        checks.append(
            _check(
                "installation.runtime_paths",
                status="FAIL" if legacy_paths and bridge_present else "WARN" if legacy_paths else "PASS",
                evidence=[
                    f"active_bridge={runtime['bridge_root']['path']}",
                    "legacy=" + (",".join(str(item["path"]) for item in legacy_paths) or "none"),
                ],
                risk="Parallel legacy and current paths can start different binaries.",
                recommendation="Review a migration plan; never delete an unverified legacy path automatically.",
            )
        )

        invalid_profiles = [profile for profile in profiles["profiles"] if profile["valid"] is not True]
        checks.append(
            _check(
                "profiles.required_files",
                status="WARN" if invalid_profiles else "PASS",
                evidence=[
                    "invalid=" + (",".join(str(profile["name"]) for profile in invalid_profiles) or "none")
                ],
                risk="Incomplete profiles cannot be safely activated.",
                recommendation="Use governed onboarding or import; Doctor never invents profile content.",
            )
        )

        missing_workspace = [
            item for item in workspace["directories"] if item["kind"] != "directory"
        ]
        workspace_actions = [
            {
                "type": "ensure_directory",
                "path": item["path"],
                "explanation": "Create a missing standard PLwC workspace directory without moving existing data.",
                "risk": "low",
                "precondition": "The path is one of the configured standard workspace directories.",
            }
            for item in missing_workspace
        ]
        for index, action in enumerate(workspace_actions):
            checks.append(
                _check(
                    f"workspace.standard_directory.{index}",
                    status="FAIL",
                    evidence=[f"missing={action['path']}"],
                    risk="A missing standard directory can break generated output or recovery flows.",
                    recommendation="Create the directory idempotently after plan confirmation.",
                    repair_action=action,
                )
            )
        if not missing_workspace:
            checks.append(
                _check(
                    "workspace.standard_directories",
                    status="PASS" if workspace["configured"] else "UNKNOWN",
                    evidence=["missing=none" if workspace["configured"] else "workspace_not_configured"],
                    risk="No risk was detected." if workspace["configured"] else "Workspace checks are unavailable.",
                    recommendation="No workspace-directory repair is required." if workspace["configured"] else "Configure a workspace before repair.",
                )
            )

        launcher = state["launcher_last_result"]
        launcher_ok = isinstance(launcher, Mapping) and launcher.get("ok") is True and launcher.get("toolCount") == 8
        checks.append(
            _check(
                "bridge.last_launcher_result",
                status="PASS" if launcher_ok else "WARN",
                evidence=[
                    f"stored={str(isinstance(launcher, Mapping)).lower()}",
                    f"tool_count={launcher.get('toolCount') if isinstance(launcher, Mapping) else 'unknown'}",
                ],
                risk="A stale or failed launcher result requires a fresh postflight before readiness is claimed.",
                recommendation="Run a fresh launcher and exact 8/8 health check before declaring success.",
            )
        )

        systems_available = systems.get("available") is True
        checks.append(
            _check(
                "windows.installation_state",
                status="PASS_WITH_NOTES" if systems_available else "NOT_CHECKED",
                evidence=[
                    f"available={str(systems_available).lower()}",
                    f"process_count={len(systems.get('processes', [])) if isinstance(systems.get('processes'), list) else 0}",
                    f"port_3007_count={len(systems.get('port_3007', [])) if isinstance(systems.get('port_3007'), list) else 0}",
                    f"scheduled_task_count={len(systems.get('scheduled_tasks', [])) if isinstance(systems.get('scheduled_tasks'), list) else 0}",
                ],
                risk="Unknown process, port, shortcut, task, or Native Messaging state must not be repaired speculatively.",
                recommendation="Use the recorded paths and command lines to distinguish proven PLwC state from foreign state.",
            )
        )

        snapshot_payload = {
            "schema_version": DOCTOR_SCHEMA_VERSION,
            "facts": facts,
            "checks": checks,
            "clu_summary": {
                "ok": clu_diagnostic.get("ok") if isinstance(clu_diagnostic, Mapping) else None,
                "operation": clu_diagnostic.get("operation") if isinstance(clu_diagnostic, Mapping) else None,
                "doctor_mode": clu_diagnostic.get("doctor_mode") if isinstance(clu_diagnostic, Mapping) else None,
                "doctor_scope": clu_diagnostic.get("doctor_scope") if isinstance(clu_diagnostic, Mapping) else None,
            },
        }
        return {
            "ok": True,
            "schema_version": DOCTOR_SCHEMA_VERSION,
            "generated_at": _utc_now(),
            "read_only": True,
            "snapshot_id": _digest(snapshot_payload),
            "facts": facts,
            "checks": checks,
            "clu_diagnostic": dict(clu_diagnostic) if isinstance(clu_diagnostic, Mapping) else None,
            "summary": {
                "pass": sum(check["status"] == "PASS" for check in checks),
                "warnings": sum(check["status"] in {"WARN", "UNKNOWN", "NOT_CHECKED", "PASS_WITH_NOTES"} for check in checks),
                "failures": sum(check["status"] == "FAIL" for check in checks),
                "repairable": sum(isinstance(check.get("repair_action"), dict) for check in checks),
            },
        }

    @staticmethod
    def build_repair_plan(diagnosis: Mapping[str, Any]) -> dict[str, Any]:
        if diagnosis.get("read_only") is not True or not isinstance(diagnosis.get("snapshot_id"), str):
            raise DoctorContractError("Repair planning requires a valid immutable Doctor diagnosis.")
        actions: list[dict[str, Any]] = []
        seen: set[str] = set()
        checks = diagnosis.get("checks")
        if not isinstance(checks, list):
            raise DoctorContractError("Doctor diagnosis does not contain checks.")
        for check in checks:
            action = check.get("repair_action") if isinstance(check, Mapping) else None
            if not isinstance(action, Mapping):
                continue
            normalized = dict(action)
            action_type = normalized.get("type")
            if action_type not in ALLOWED_REPAIR_ACTIONS:
                raise DoctorContractError(f"Doctor proposed unsupported repair action: {action_type!r}.")
            action_key = _canonical_json(normalized)
            if action_key not in seen:
                seen.add(action_key)
                normalized["action_id"] = hashlib.sha256(action_key.encode("utf-8")).hexdigest()[:16]
                actions.append(normalized)
        plan_core = {
            "schema_version": REPAIR_PLAN_SCHEMA_VERSION,
            "snapshot_id": diagnosis["snapshot_id"],
            "actions": actions,
        }
        return {
            "ok": True,
            **plan_core,
            "plan_id": _digest(plan_core),
            "confirmation_required": True,
            "change_count": len(actions),
            "no_changes": len(actions) == 0,
        }

    @staticmethod
    def _verify_plan(plan: Mapping[str, Any]) -> None:
        actions = plan.get("actions")
        if plan.get("schema_version") != REPAIR_PLAN_SCHEMA_VERSION or not isinstance(actions, list):
            raise DoctorContractError("Unsupported Doctor repair-plan schema.")
        core = {
            "schema_version": plan["schema_version"],
            "snapshot_id": plan.get("snapshot_id"),
            "actions": actions,
        }
        if not isinstance(plan.get("plan_id"), str) or not hmac.compare_digest(plan["plan_id"], _digest(core)):
            raise DoctorContractError("Doctor repair plan was changed after review.")
        for action in actions:
            if not isinstance(action, Mapping) or action.get("type") not in ALLOWED_REPAIR_ACTIONS:
                raise DoctorContractError("Doctor repair plan contains an unsupported action.")

    def _allowed_directory_targets(self) -> set[Path]:
        if self.workspace_root is None:
            return set()
        return {
            (self.workspace_root / name if name else self.workspace_root).resolve(strict=False)
            for name in STANDARD_WORKSPACE_DIRECTORIES
        }

    def _audit(self, payload: Mapping[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        line = _canonical_json({"timestamp": _utc_now(), **dict(payload)}) + "\n"
        with _AUDIT_LOCK:
            with self.audit_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())

    def _apply_action(
        self,
        action: Mapping[str, Any],
        *,
        backup_root: Path,
    ) -> dict[str, Any]:
        action_type = action["type"]
        action_id = str(action.get("action_id") or "unknown")
        if action_type == "ensure_directory":
            target = Path(str(action.get("path") or "")).resolve(strict=False)
            if target not in self._allowed_directory_targets():
                raise DoctorContractError("Doctor directory action escaped the configured workspace allowlist.")
            if target.exists() and not target.is_dir():
                raise DoctorContractError(f"Doctor cannot replace a non-directory path: {target}.")
            created = not target.exists()
            target.mkdir(parents=True, exist_ok=True)
            return {"action_id": action_id, "type": action_type, "target": str(target), "created": created}

        source = Path(str(action.get("source") or "")).resolve(strict=False)
        target = Path(str(action.get("path") or "")).resolve(strict=False)
        expected_sha256 = str(action.get("sha256") or "").lower()
        if self.payload_root is None or not _inside(source, self.payload_root):
            raise DoctorContractError("Doctor payload source escaped the verified payload allowlist.")
        if not _inside(target, self.app_root):
            raise DoctorContractError("Doctor runtime target escaped the PLwC app allowlist.")
        if len(expected_sha256) != 64 or _file_sha256(source) != expected_sha256:
            raise DoctorContractError("Doctor rejected an unverified repair payload.")
        relative = target.relative_to(self.app_root)
        backup = backup_root / "app" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.is_file()
        if existed:
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.doctor.tmp")
        try:
            shutil.copy2(source, temporary)
            if _file_sha256(temporary) != expected_sha256:
                raise DoctorContractError("Doctor payload hash changed while staging the repair.")
            os.replace(temporary, target)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        return {
            "action_id": action_id,
            "type": action_type,
            "target": str(target),
            "created": not existed,
            "backup": str(backup) if existed else None,
        }

    @staticmethod
    def _rollback_action(result: Mapping[str, Any]) -> None:
        target = Path(str(result["target"]))
        if result["type"] == "ensure_directory":
            if result.get("created") is True:
                target.rmdir()
            return
        backup_value = result.get("backup")
        if isinstance(backup_value, str) and backup_value:
            backup = Path(backup_value)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
        elif result.get("created") is True:
            target.unlink(missing_ok=True)

    def apply_repair_plan(
        self,
        plan: Mapping[str, Any],
        *,
        confirmed_plan_id: str,
        current_diagnosis: Mapping[str, Any],
        postflight: Callable[[], Mapping[str, Any]],
    ) -> dict[str, Any]:
        self._verify_plan(plan)
        plan_id = str(plan["plan_id"])
        if not isinstance(confirmed_plan_id, str) or not hmac.compare_digest(plan_id, confirmed_plan_id):
            raise DoctorContractError("Repair requires confirmation of this exact Doctor plan ID.")
        if current_diagnosis.get("snapshot_id") != plan.get("snapshot_id"):
            raise DoctorContractError("Installation state changed after diagnosis. Review a new repair plan.")
        actions = plan["actions"]
        if not actions:
            return {
                "ok": True,
                "plan_id": plan_id,
                "result": "no_changes",
                "changed": False,
                "applied_actions": [],
                "rollback": {"attempted": False, "complete": True, "errors": []},
                "postflight": dict(current_diagnosis),
            }

        transaction_id = hashlib.sha256(f"{plan_id}:{_utc_now()}".encode("utf-8")).hexdigest()[:20]
        backup_root = self.state_root / "backups" / transaction_id
        completed: list[dict[str, Any]] = []
        self._audit({"event": "repair_started", "transaction_id": transaction_id, "plan_id": plan_id})
        try:
            for action in actions:
                result = self._apply_action(action, backup_root=backup_root)
                completed.append(result)
                self._audit(
                    {
                        "event": "repair_action_applied",
                        "transaction_id": transaction_id,
                        "plan_id": plan_id,
                        "action": result,
                    }
                )
            postflight_report = dict(postflight())
            if postflight_report.get("ok") is not True:
                raise DoctorContractError("Doctor postflight did not return a valid diagnosis.")
            remaining_plan = self.build_repair_plan(postflight_report)
            remaining_action_ids = {str(action.get("action_id")) for action in remaining_plan["actions"]}
            planned_action_ids = {str(action.get("action_id")) for action in actions}
            if planned_action_ids & remaining_action_ids:
                raise DoctorContractError("Doctor postflight still requires an applied repair action.")
            self._audit(
                {
                    "event": "repair_completed",
                    "transaction_id": transaction_id,
                    "plan_id": plan_id,
                    "result": "successful",
                }
            )
            return {
                "ok": True,
                "plan_id": plan_id,
                "transaction_id": transaction_id,
                "result": "successful",
                "changed": any(result.get("created") is True or result["type"] != "ensure_directory" for result in completed),
                "applied_actions": completed,
                "backup_root": str(backup_root),
                "audit_path": str(self.audit_path),
                "rollback": {"attempted": False, "complete": True, "errors": []},
                "postflight": postflight_report,
            }
        except Exception as exc:
            rollback_errors: list[str] = []
            for result in reversed(completed):
                try:
                    self._rollback_action(result)
                except OSError as rollback_error:
                    rollback_errors.append(f"{result.get('action_id')}: {rollback_error}")
            outcome = "rolled_back" if completed and not rollback_errors else "failed"
            self._audit(
                {
                    "event": "repair_failed",
                    "transaction_id": transaction_id,
                    "plan_id": plan_id,
                    "result": outcome,
                    "error": str(exc),
                    "rollback_errors": rollback_errors,
                }
            )
            return {
                "ok": False,
                "plan_id": plan_id,
                "transaction_id": transaction_id,
                "result": outcome,
                "changed": False if not rollback_errors else None,
                "error": str(exc),
                "applied_actions": completed,
                "backup_root": str(backup_root),
                "audit_path": str(self.audit_path),
                "rollback": {
                    "attempted": bool(completed),
                    "complete": not rollback_errors,
                    "errors": rollback_errors,
                },
            }
