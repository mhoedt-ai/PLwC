from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from plwc_gateway.installation import DoctorContractError, InstallationDoctor
from plwc_gateway.installation.doctor import _merge_shortcut_details, _run_powershell_json
from plwc_gateway.audit import InMemoryAuditLogger
from plwc_gateway.config.settings import load_gateway_config
from plwc_gateway.mcp.server import PUBLIC_TOOLS, plwc_profile


def _write(path: Path, content: bytes = b"fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _tree(root: Path) -> list[tuple[str, str, str | None]]:
    if not root.exists():
        return []
    result: list[tuple[str, str, str | None]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            result.append((relative, "directory", None))
        elif path.is_file():
            result.append((relative, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
    return result


def _ready_installation(root: Path, *, incomplete_workspace: bool = False) -> InstallationDoctor:
    bridge = root / "app" / "bridge"
    gateway = root / "app" / "gateway"
    workspace = root / "workspace"
    profile = root / "profiles" / "default"
    _write(gateway / "src" / "plwc_gateway" / "__init__.py")
    _write(bridge / "bridge" / "dist" / "src" / "index.js")
    _write(
        bridge / "build-identity.json",
        b'{"schemaVersion":1,"buildId":"plwc-chat-bridge@1.0.0","releaseVersion":"1.0.0"}',
    )
    _write(bridge / "native" / "bin" / "plwc-chat-bridge-launcher.exe")
    _write(root / "app" / "configuration" / "plwc-config.py")
    selection = (
        "[PLwC]\n"
        f"GatewayPath={gateway}\n"
        f"BridgePath={bridge}\n"
        f"WorkspacePath={workspace}\n"
    )
    _write(root / "config" / "installer" / "selection.ini", selection.encode("utf-8"))
    for name in ("", "Tagebuch", "Temp", "Trashcan"):
        if incomplete_workspace and name in {"Temp", "Trashcan"}:
            continue
        (workspace / name if name else workspace).mkdir(parents=True, exist_ok=True)
    for name in ("CORE.md", "TEMPERAMENT.md", "PERSONA.md", "memory.md", "reflection.md"):
        _write(profile / name)
    _write(profile / "governance" / "config.yaml")
    return InstallationDoctor(
        root,
        workspace_root=workspace,
        profile_root=root / "profiles",
        enable_system_probes=False,
    )


def test_windows_shortcut_details_replace_path_facts_and_keep_redirected_folders() -> None:
    startup = r"C:\Users\Test\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\PLwC Chat Bridge.lnk"
    redirected_desktop = r"F:\Eigene Dokumente\Desktop\PLwC-Konfiguration.lnk"
    facts = [{"path": startup, "exists": True, "kind": "file"}]
    details = [
        {
            "path": startup,
            "exists": True,
            "kind": "file",
            "target": r"C:\Users\Test\AppData\Roaming\PLwC\app\bridge\native\bin\plwc-chat-bridge-launcher.exe",
            "arguments": "--start --delay-seconds 20 --lang de",
        },
        {
            "path": redirected_desktop,
            "exists": True,
            "kind": "file",
            "target": r"C:\Python\pythonw.exe",
            "arguments": '"C:\\PLwC\\app\\configuration\\plwc-config.py"',
        },
    ]

    merged = _merge_shortcut_details(facts, details)

    assert merged[0]["target"].endswith("plwc-chat-bridge-launcher.exe")
    assert merged[0]["arguments"] == "--start --delay-seconds 20 --lang de"
    assert merged[1]["path"] == redirected_desktop


def test_windows_shortcut_details_accept_one_powershell_object() -> None:
    path = r"C:\Users\Test\Desktop\PLwC-Konfiguration.lnk"
    merged = _merge_shortcut_details(
        [{"path": path, "exists": True, "kind": "file"}],
        {"path": path, "exists": True, "kind": "file", "target": r"C:\Python\pythonw.exe"},
    )

    assert merged == [{"path": path, "exists": True, "kind": "file", "target": r"C:\Python\pythonw.exe"}]


def test_windows_powershell_probe_requires_one_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    class Completed:
        returncode = 0
        stdout = '{"shortcuts":[]}'
        stderr = ""

    monkeypatch.setattr("plwc_gateway.installation.doctor.subprocess.run", lambda *args, **kwargs: Completed())

    assert _run_powershell_json("fixture", timeout_seconds=1) == {"shortcuts": []}


def test_doctor_diagnosis_is_read_only_and_keeps_public_mcp_boundary(tmp_path: Path) -> None:
    doctor = _ready_installation(tmp_path, incomplete_workspace=True)
    before = _tree(tmp_path)

    report = doctor.diagnose(
        component_inventory={"components": []},
        clu_diagnostic={"ok": True, "operation": "doctor", "doctor_mode": "clu", "doctor_scope": "general"},
    )

    assert report["ok"] is True
    assert report["read_only"] is True
    assert len(report["snapshot_id"]) == 64
    assert report["summary"]["repairable"] == 2
    assert report["facts"]["runtime"]["expected_files"]["bridge_entry"]["exists"] is True
    assert next(check for check in report["checks"] if check["id"] == "installation.runtime_files")["status"] == "PASS"
    assert _tree(tmp_path) == before
    assert len(PUBLIC_TOOLS) == 8
    assert "plwc_doctor" not in PUBLIC_TOOLS


def test_public_clu_doctor_keeps_diagnosis_read_only_with_metadata_audit(tmp_path: Path) -> None:
    _ready_installation(tmp_path)
    config = load_gateway_config(project_root=tmp_path)
    before = _tree(tmp_path)
    audit = InMemoryAuditLogger()

    result = plwc_profile(
        operation="doctor",
        doctor_mode="clu",
        doctor_scope="general",
        config=config,
        audit_logger=audit,
    )

    assert result["ok"] is True
    assert result["operation"] == "doctor"
    assert result["doctor_mode"] == "clu"
    assert _tree(tmp_path) == before
    assert audit.events


def test_repair_requires_the_exact_plan_and_second_run_is_change_free(tmp_path: Path) -> None:
    doctor = _ready_installation(tmp_path, incomplete_workspace=True)
    diagnosis = doctor.diagnose(component_inventory={"components": []})
    plan = doctor.build_repair_plan(diagnosis)

    assert plan["change_count"] == 2
    assert all(action["type"] == "ensure_directory" for action in plan["actions"])
    assert all(action["explanation"] and action["risk"] for action in plan["actions"])
    with pytest.raises(DoctorContractError, match="exact Doctor plan ID"):
        doctor.apply_repair_plan(
            plan,
            confirmed_plan_id="0" * 64,
            current_diagnosis=diagnosis,
            postflight=lambda: doctor.diagnose(component_inventory={"components": []}),
        )

    result = doctor.apply_repair_plan(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_diagnosis=diagnosis,
        postflight=lambda: doctor.diagnose(component_inventory={"components": []}),
    )
    assert result["ok"] is True
    assert result["result"] == "successful"
    assert (tmp_path / "workspace" / "Temp").is_dir()
    assert (tmp_path / "workspace" / "Trashcan").is_dir()
    assert result["audit_path"] == str(doctor.audit_path)

    second_diagnosis = doctor.diagnose(component_inventory={"components": []})
    second_plan = doctor.build_repair_plan(second_diagnosis)
    before_second_apply = _tree(tmp_path)
    second_result = doctor.apply_repair_plan(
        second_plan,
        confirmed_plan_id=second_plan["plan_id"],
        current_diagnosis=second_diagnosis,
        postflight=lambda: doctor.diagnose(component_inventory={"components": []}),
    )
    assert second_plan["no_changes"] is True
    assert second_result["result"] == "no_changes"
    assert second_result["changed"] is False
    assert _tree(tmp_path) == before_second_apply


def test_repair_rejects_a_changed_or_stale_plan(tmp_path: Path) -> None:
    doctor = _ready_installation(tmp_path, incomplete_workspace=True)
    diagnosis = doctor.diagnose(component_inventory={"components": []})
    plan = doctor.build_repair_plan(diagnosis)
    plan["actions"][0]["path"] = str(tmp_path / "outside")

    with pytest.raises(DoctorContractError, match="changed after review"):
        doctor.apply_repair_plan(
            plan,
            confirmed_plan_id=plan["plan_id"],
            current_diagnosis=diagnosis,
            postflight=lambda: diagnosis,
        )

    fresh_plan = doctor.build_repair_plan(diagnosis)
    stale = dict(diagnosis)
    stale["snapshot_id"] = "f" * 64
    with pytest.raises(DoctorContractError, match="state changed"):
        doctor.apply_repair_plan(
            fresh_plan,
            confirmed_plan_id=fresh_plan["plan_id"],
            current_diagnosis=stale,
            postflight=lambda: stale,
        )


def test_repair_failure_rolls_back_completed_reversible_actions(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    payload = tmp_path / "payload"
    doctor = InstallationDoctor(
        tmp_path,
        workspace_root=workspace,
        payload_root=payload,
        enable_system_probes=False,
    )
    diagnosis = {
        "ok": True,
        "read_only": True,
        "snapshot_id": "a" * 64,
        "checks": [
            {
                "repair_action": {
                    "type": "ensure_directory",
                    "path": str(workspace),
                    "explanation": "Create workspace.",
                    "risk": "low",
                    "precondition": "Configured workspace.",
                }
            },
            {
                "repair_action": {
                    "type": "restore_file_from_payload",
                    "source": str(payload / "missing.bin"),
                    "path": str(tmp_path / "app" / "missing.bin"),
                    "sha256": "0" * 64,
                    "explanation": "Restore verified runtime file.",
                    "risk": "medium",
                    "precondition": "Payload hash matches.",
                }
            },
        ],
    }
    plan = doctor.build_repair_plan(diagnosis)

    result = doctor.apply_repair_plan(
        plan,
        confirmed_plan_id=plan["plan_id"],
        current_diagnosis=diagnosis,
        postflight=lambda: diagnosis,
    )

    assert result["ok"] is False
    assert result["result"] == "rolled_back"
    assert result["rollback"] == {"attempted": True, "complete": True, "errors": []}
    assert not workspace.exists()
    assert doctor.audit_path.is_file()
