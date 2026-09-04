from __future__ import annotations

import configparser
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from src.plwc_gateway.installation.doctor import InstallationDoctor
from src.plwc_gateway.installation.installer_state import (
    INSTALLER_MANAGED_CONFIG_PATHS,
    InstallerStateEngine,
    InstallerStateError,
)


EXTENSION_ID = "nlogfcafjdfdoknpkbehjgihpafpipdb"


def _write(path: Path, content: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _engine(tmp_path: Path) -> tuple[InstallerStateEngine, dict[str, Path]]:
    root = tmp_path / "PLwC"
    paths = {
        "root": root,
        "app": root / "app",
        "gateway": root / "app" / "gateway",
        "bridge": root / "app" / "bridge",
        "workspace": root / "workspace",
        "profiles": root / "profiles",
        "config": root / "config",
        "state": root / "state",
        "logs": root / "logs",
        "backups": root / "profile_backups",
        "selection": root / "config" / "installer" / "selection.ini",
    }
    engine = InstallerStateEngine(
        root,
        app_root=paths["app"],
        gateway_root=paths["gateway"],
        bridge_root=paths["bridge"],
        workspace_root=paths["workspace"],
        profile_root=paths["profiles"],
        config_root=paths["config"],
        state_root=paths["state"],
        logs_root=paths["logs"],
        backups_root=paths["backups"],
    )
    return engine, paths


def _system_facts(paths: dict[str, Path], *, foreign: bool = False) -> dict[str, object]:
    launcher = paths["bridge"] / "native" / "bin" / "plwc-chat-bridge-launcher.exe"
    manifest = paths["config"] / "native-messaging" / "plwc.chat_bridge.launcher.json"
    facts: dict[str, object] = {
        "available": True,
        "native_messaging": {
            browser: {"registered": True, "manifest": str(manifest)}
            for browser in ("chrome", "edge", "brave")
        },
        "processes": [],
        "port_3007": [],
        "scheduled_tasks": [],
        "shortcuts": [
            {
                "path": str(paths["root"] / "Startup" / "PLwC Chat Bridge.lnk"),
                "exists": True,
                "target": str(launcher),
                "arguments": "--start --delay-seconds 20 --lang de",
            },
            {
                "path": str(paths["root"] / "Desktop" / "PLwC-Konfiguration.lnk"),
                "exists": True,
                "target": str(paths["root"] / "Python" / "pythonw.exe"),
                "arguments": f'"{paths["app"] / "configuration" / "plwc-config.py"}" --no-browser',
            },
        ],
    }
    if foreign:
        facts["processes"] = [
            {
                "ProcessId": 8123,
                "Name": "foreign.exe",
                "ExecutablePath": str(paths["root"].parent / "Foreign" / "foreign.exe"),
                "CommandLine": "foreign.exe --listen 3007",
            }
        ]
        facts["port_3007"] = [{"LocalPort": 3007, "OwningProcess": 8123}]
    return facts


def test_postflight_fails_closed_when_windows_fact_probe_is_incomplete(tmp_path: Path) -> None:
    engine, paths = _engine(tmp_path)
    manifest = _install_payload(paths)
    preflight = engine.preflight(
        selection_path=paths["selection"],
        system_facts=_system_facts(paths),
    )
    facts = _system_facts(paths)
    facts["probe_status"] = {
        "shortcuts": True,
        "processes": False,
        "port_3007": True,
        "scheduled_tasks": True,
    }
    facts["errors"] = ["powershell.processes: timed out"]

    report = engine.postflight(
        preflight=preflight,
        payload_manifest_path=manifest,
        selection_path=paths["selection"],
        system_facts=facts,
        expected_extension_id=EXTENSION_ID,
    )
    checks = {check["id"]: check for check in report["checks"]}

    assert report["ok"] is False
    assert checks["port.3007_owner"]["ok"] is False
    assert checks["legacy.processes"]["ok"] is False
    assert checks["scheduled_tasks.legacy"]["ok"] is True
    assert checks["port.3007_owner"]["evidence"] == ["powershell.processes: timed out"]


def _write_selection(paths: dict[str, Path], *, stored_bridge: Path | None = None) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser["PLwC"] = {
        "AppPath": str(paths["app"]),
        "GatewayPath": str(paths["gateway"]),
        "BridgePath": str(stored_bridge or paths["bridge"]),
        "WorkspacePath": str(paths["workspace"]),
        "ProfilesPath": str(paths["profiles"]),
        "ConfigPath": str(paths["config"]),
        "StatePath": str(paths["state"]),
        "LogsPath": str(paths["logs"]),
        "BackupsPath": str(paths["backups"]),
    }
    parser["Components"] = {
        "ClaudeMCPB": "false",
        "CodexSTDIO": "false",
        "OdysseusSTDIO": "false",
        "ChatBridge": "true",
    }
    parser["BuildIdentity"] = {
        "InstallerRevision": "installer-r26",
        "SetupExeSha256": "a" * 64,
    }
    paths["selection"].parent.mkdir(parents=True, exist_ok=True)
    with paths["selection"].open("w", encoding="utf-8", newline="\n") as handle:
        parser.write(handle)


def _install_payload(paths: dict[str, Path]) -> Path:
    payload_files = {
        "common/configuration/plwc-config.py": b"print('config')\n",
        "common/configuration/plwc.ico": b"icon",
        "gateway/server.py": b"# gateway\n",
        "gateway/manifest.json": b'{"version":"1.0.0"}\n',
        "chat-bridge/build-identity.json": b'{"buildId":"plwc-chat-bridge@1.0.0"}\n',
        "chat-bridge/native/bin/plwc-chat-bridge-launcher.exe": b"launcher",
        "chat-bridge/bridge/dist/src/index.js": b"bridge",
        "chat-bridge/config/plwc.example.json": b'{"generated":false}\n',
    }
    mappings = {
        "common": paths["app"],
        "gateway": paths["gateway"],
        "chat-bridge": paths["bridge"],
    }
    manifest_files: list[dict[str, object]] = []
    for relative, content in payload_files.items():
        prefix, suffix = relative.split("/", 1)
        target = mappings[prefix] / suffix
        _write(target, content)
        manifest_files.append({"path": relative, "sha256": _sha256(target), "size": target.stat().st_size})
    # Setup intentionally creates this file after payload extraction.
    _write(paths["bridge"] / "config" / "plwc.example.json", '{"generated":true}\n')
    launcher = paths["bridge"] / "native" / "bin" / "plwc-chat-bridge-launcher.exe"
    native_manifest = paths["config"] / "native-messaging" / "plwc.chat_bridge.launcher.json"
    _write(
        native_manifest,
        json.dumps(
            {
                "name": "plwc.chat_bridge.launcher",
                "path": str(launcher),
                "type": "stdio",
                "allowed_origins": [f"chrome-extension://{EXTENSION_ID}/"],
            }
        ),
    )
    _write(
        paths["state"] / "chat-bridge" / "launcher-last-result.json",
        json.dumps({"ok": True, "toolCount": 8, "buildId": "plwc-chat-bridge@1.0.0"}),
    )
    manifest = paths["app"] / "installation" / "payload-manifest.json"
    _write(
        manifest,
        json.dumps(
            {
                "schemaVersion": 1,
                "installer": {"revision": "installer-r26"},
                "files": manifest_files,
            }
        ),
    )
    _write_selection(paths)
    return manifest


def _preexisting_user_data(paths: dict[str, Path]) -> None:
    _write(paths["profiles"] / "FAUN" / "PERSONA.md", "kept profile\n")
    _write(paths["config"] / "user-policy.yaml", "keep: true\n")
    _write(
        paths["config"] / "native-messaging" / "plwc.chat_bridge.launcher.json",
        '{"path":"legacy-bridge-launcher.exe"}\n',
    )
    _write(
        paths["root"] / "config" / "gateway-settings.json",
        json.dumps(
            {
                "schema_version": 1,
                "settings": {"active_profile_name": "FAUN", "workspace_path": str(paths["workspace"])},
                "updated_at": "old",
                "updated_by": "user",
            }
        ),
    )


@pytest.mark.parametrize("scenario", ["clean", "r25_update", "dirty_migration"])
def test_clean_update_and_dirty_migration_share_the_hard_postflight(tmp_path: Path, scenario: str) -> None:
    engine, paths = _engine(tmp_path)
    _preexisting_user_data(paths)
    legacy = paths["app"] / "chat-bridge"
    if scenario == "r25_update":
        _write(paths["bridge"] / "old-runtime.txt", "r25")
        _write_selection(paths)
    elif scenario == "dirty_migration":
        _write(legacy / "old-runtime.txt", "legacy")
        _write_selection(paths, stored_bridge=legacy)

    facts = _system_facts(paths)
    preflight = engine.preflight(selection_path=paths["selection"], system_facts=facts)
    plan = engine.plan(preflight)
    assert plan["ok"] is True
    prepared = engine.prepare(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_preflight=preflight,
        current_system_facts=facts,
    )
    manifest = _install_payload(paths)
    report = engine.postflight(
        preflight=preflight,
        payload_manifest_path=manifest,
        selection_path=paths["selection"],
        system_facts=_system_facts(paths),
        expected_extension_id=EXTENSION_ID,
    )

    assert report["ok"] is True, report["checks"]
    assert all(check["ok"] is True for check in report["checks"])
    doctor_report = InstallationDoctor(
        paths["root"],
        workspace_root=paths["workspace"],
        profile_root=paths["profiles"],
        enable_system_probes=False,
    ).hard_postflight(system_facts=_system_facts(paths))
    assert doctor_report is not None and doctor_report["ok"] is True
    archived = engine.archive_legacy_after_success(plan, report)
    if scenario == "dirty_migration":
        assert not legacy.exists()
        assert len(archived) == 1
    else:
        assert archived == []
    if scenario == "clean":
        assert prepared["target_backup"] is None
    else:
        assert Path(str(prepared["target_backup"])).is_dir()


def test_foreign_port_owner_blocks_without_stopping_any_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine, paths = _engine(tmp_path)
    facts = _system_facts(paths, foreign=True)
    preflight = engine.preflight(selection_path=paths["selection"], system_facts=facts)
    plan = engine.plan(preflight)
    stopped: list[int] = []
    monkeypatch.setattr("src.plwc_gateway.installation.installer_state.os.kill", lambda pid, _signal: stopped.append(pid))

    assert plan["blocked"] is True
    assert plan["block_reason"] == "foreign_port_3007_owner"
    assert preflight["facts"]["attribution"]["processes"][0]["classification"] == "unknown"
    with pytest.raises(InstallerStateError, match="unverified process"):
        engine.prepare(
            plan,
            confirmed_plan_id=plan["plan_id"],
            current_preflight=preflight,
            current_system_facts=facts,
        )
    assert stopped == []


def test_only_a_proven_legacy_process_is_stopped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine, paths = _engine(tmp_path)
    legacy = paths["app"] / "chat-bridge"
    _write(legacy / "bridge" / "dist" / "src" / "index.js", "legacy")
    _write_selection(paths, stored_bridge=legacy)
    process = {
        "ProcessId": 8451,
        "Name": "node.exe",
        "ExecutablePath": str(legacy / "node.exe"),
        "CommandLine": f'node.exe "{legacy / "bridge" / "dist" / "src" / "index.js"}"',
    }
    facts = _system_facts(paths)
    facts["processes"] = [process]
    facts["port_3007"] = [{"LocalPort": 3007, "OwningProcess": 8451}]
    stopped: list[int] = []
    monkeypatch.setattr("src.plwc_gateway.installation.installer_state.os.kill", lambda pid, _signal: stopped.append(pid))

    preflight = engine.preflight(selection_path=paths["selection"], system_facts=facts)
    plan = engine.plan(preflight)
    assert preflight["facts"]["attribution"]["processes"][0]["classification"] == "proven"
    assert plan["blocked"] is False
    engine.prepare(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_preflight=preflight,
        current_system_facts=facts,
    )
    assert stopped == ([8451] if os.name == "nt" else [])


def test_postflight_detects_hash_and_profile_mutation_and_never_allows_archive(tmp_path: Path) -> None:
    engine, paths = _engine(tmp_path)
    _preexisting_user_data(paths)
    preflight = engine.preflight(selection_path=paths["selection"], system_facts=_system_facts(paths))
    plan = engine.plan(preflight)
    engine.prepare(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_preflight=preflight,
        current_system_facts=_system_facts(paths),
    )
    manifest = _install_payload(paths)
    _write(paths["gateway"] / "server.py", "tampered\n")
    _write(paths["profiles"] / "FAUN" / "PERSONA.md", "lost\n")
    report = engine.postflight(
        preflight=preflight,
        payload_manifest_path=manifest,
        selection_path=paths["selection"],
        system_facts=_system_facts(paths),
        expected_extension_id=EXTENSION_ID,
    )

    failures = {check["id"] for check in report["checks"] if check["ok"] is not True}
    assert report["ok"] is False
    assert {"payload.hashes", "user_data.profiles"} <= failures
    with pytest.raises(InstallerStateError, match="only after a successful postflight"):
        engine.archive_legacy_after_success(plan, report)


def test_failed_update_rolls_back_the_complete_application_tree(tmp_path: Path) -> None:
    engine, paths = _engine(tmp_path)
    _write(paths["app"] / "configuration" / "old.txt", "r25")
    _write(paths["bridge"] / "old-runtime.txt", "r25 bridge")
    _preexisting_user_data(paths)
    _write_selection(paths, stored_bridge=paths["app"] / "chat-bridge")
    for relative in (
        "installer/installation-summary.txt",
        "clients/codex/plwc-gateway.generated.toml",
        "clients/odysseus/plwc-gateway.generated.json",
    ):
        _write(paths["config"] / relative, f"r25:{relative}\n")
    original_config = {
        relative: (paths["config"] / relative).read_bytes()
        for relative in INSTALLER_MANAGED_CONFIG_PATHS
    }
    preflight = engine.preflight(selection_path=paths["selection"], system_facts=_system_facts(paths))
    plan = engine.plan(preflight)
    prepared = engine.prepare(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_preflight=preflight,
        current_system_facts=_system_facts(paths),
    )
    _install_payload(paths)
    for relative in INSTALLER_MANAGED_CONFIG_PATHS:
        _write(paths["config"] / relative, f"failed-r26:{relative}\n")
    result = engine.rollback(prepared)

    assert result["result"] == "restored"
    assert (paths["app"] / "configuration" / "old.txt").read_text(encoding="utf-8") == "r25"
    assert (paths["bridge"] / "old-runtime.txt").read_text(encoding="utf-8") == "r25 bridge"
    assert not (paths["app"] / "installation" / "payload-manifest.json").exists()
    assert result["quarantine"] is not None
    assert {
        relative: (paths["config"] / relative).read_bytes()
        for relative in INSTALLER_MANAGED_CONFIG_PATHS
    } == original_config


@pytest.mark.skipif(os.name != "nt", reason="Windows process-tree rollback contract")
def test_rollback_stops_only_the_proven_target_bridge_before_atomic_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, paths = _engine(tmp_path)
    _write(paths["app"] / "configuration" / "old.txt", "r25")
    preflight = engine.preflight(selection_path=paths["selection"], system_facts=_system_facts(paths))
    plan = engine.plan(preflight)
    prepared = engine.prepare(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_preflight=preflight,
        current_system_facts=_system_facts(paths),
    )
    _install_payload(paths)
    target_pid = 8452
    foreign_pid = 8453
    facts = _system_facts(paths)
    facts["processes"] = [
        {
            "ProcessId": target_pid,
            "Name": "node.exe",
            "ExecutablePath": r"C:\Program Files\nodejs\node.exe",
            "CommandLine": f'node.exe "{paths["bridge"] / "bridge" / "dist" / "src" / "index.js"}"',
        },
        {
            "ProcessId": foreign_pid,
            "Name": "foreign.exe",
            "ExecutablePath": str(paths["root"].parent / "Foreign" / "foreign.exe"),
            "CommandLine": "foreign.exe --listen 3008",
        },
    ]
    facts["port_3007"] = [{"LocalPort": 3007, "OwningProcess": target_pid}]
    calls: list[list[str]] = []

    def fake_run(arguments: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, "SUCCESS", "")

    monkeypatch.setattr("src.plwc_gateway.installation.installer_state.subprocess.run", fake_run)
    result = engine.rollback(prepared, system_facts=facts)

    assert calls == [["taskkill.exe", "/PID", str(target_pid), "/T", "/F"]]
    assert result["stopped_processes"] == [target_pid]
    assert result["result"] == "restored"
    assert (paths["app"] / "configuration" / "old.txt").read_text(encoding="utf-8") == "r25"


def test_plan_id_and_preflight_snapshot_are_immutable(tmp_path: Path) -> None:
    engine, paths = _engine(tmp_path)
    preflight = engine.preflight(selection_path=paths["selection"], system_facts=_system_facts(paths))
    plan = engine.plan(preflight)
    plan["actions"].append({"type": "delete_unknown_directory", "path": str(paths["root"] / "unknown")})

    with pytest.raises(InstallerStateError, match="changed after preflight"):
        engine.prepare(
            plan,
            confirmed_plan_id=plan["plan_id"],
            current_preflight=preflight,
            current_system_facts=_system_facts(paths),
        )


def test_unsafe_overlapping_runtime_and_data_roots_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "PLwC"
    with pytest.raises(InstallerStateError, match="data root must not overlap"):
        InstallerStateEngine(
            root,
            app_root=root / "app",
            gateway_root=root / "app" / "gateway",
            bridge_root=root / "app" / "bridge",
            workspace_root=root / "app" / "workspace",
            profile_root=root / "profiles",
            config_root=root / "config",
            state_root=root / "state",
            logs_root=root / "logs",
            backups_root=root / "profile_backups",
        )
