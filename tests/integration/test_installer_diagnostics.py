from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "installer" / "windows" / "assets"
INSTALLATION_SOURCE = ROOT / "src" / "plwc_gateway" / "installation"


def _load_maintenance():
    sys.path.insert(0, str(INSTALLATION_SOURCE))
    spec = importlib.util.spec_from_file_location("plwc_installer_maintenance_diagnostic_tests", ASSETS / "installer-maintenance.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


maintenance = _load_maintenance()


def _arguments(tmp_path: Path, action: str = "preflight-prepare") -> list[str]:
    names = (
        "installation-root",
        "app-root",
        "gateway-root",
        "bridge-root",
        "workspace-root",
        "profile-root",
        "config-root",
        "state-root",
        "logs-root",
        "backups-root",
        "selection-path",
        "transaction-path",
        "report-path",
    )
    values = {name: tmp_path / name for name in names}
    values["logs-root"] = tmp_path / "logs"
    values["report-path"] = tmp_path / "logs" / "setup" / f"r27-installer-{action}.json"
    arguments = ["installer-maintenance.py", action]
    for name in names:
        arguments.extend((f"--{name}", str(values[name])))
    if action == "postflight":
        arguments.extend(("--payload-manifest", str(tmp_path / "payload.json"), "--extension-id", "a" * 32))
    return arguments


def test_unexpected_exception_writes_complete_existing_report(tmp_path: Path, monkeypatch) -> None:
    def explode(_args):
        raise RuntimeError("synthetic unexpected maintenance failure")

    monkeypatch.setattr(maintenance, "_prepare", explode)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 40
    report_path = tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    for key in (
        "phase",
        "category",
        "command_id",
        "started",
        "started_at",
        "finished_at",
        "duration_ms",
        "exit_code",
        "stdout",
        "stderr",
        "exception_type",
        "report_path",
        "report_id",
        "ok",
    ):
        assert key in report
    assert report["phase"] == "preflight-prepare"
    assert report["exit_code"] == 40
    assert report["exception_type"] == "RuntimeError"
    assert Path(report["report_path"]).is_file()


def test_success_also_persists_process_envelope(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(maintenance, "_prepare", lambda _args: 0)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 0
    report_path = tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["exit_code"] == 0
    assert report["started"] is True
    assert report["stdout"] == report["stderr"] == ""


def test_inno_never_displays_an_unchecked_report_path() -> None:
    source = (ROOT / "installer" / "windows" / "PLwCSetup.iss").read_text(encoding="utf-8")
    assert "function GetExistingMaintenanceReportReference" in source
    assert "if FileExists(ReportPath) then" in source
    assert "GetExistingMaintenanceReportReference('preflight-prepare')" in source
    assert "GetExistingMaintenanceReportReference('postflight')" in source
