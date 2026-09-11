from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


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


def _assert_report_id(report: dict) -> None:
    assert report["report_id"] == maintenance._report_id(report)


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
    arguments.extend(("--build-id", "fixture-installer-r27"))
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
        "build_id",
        "plan_id",
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
    assert report["phase"] == "preflight"
    assert report["build_id"] == "fixture-installer-r27"
    assert report["exit_code"] == 40
    assert report["exception_type"] == "RuntimeError"
    assert report["stderr"] == "synthetic unexpected maintenance failure"
    assert Path(report["report_path"]).is_file()
    _assert_report_id(report)


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
    assert report["state"] == "completed"
    _assert_report_id(report)


@pytest.mark.parametrize(
    ("action", "helper_name", "exit_code", "phase"),
    [
        ("preflight-prepare", "_prepare", 1, "preflight"),
        ("preflight-prepare", "_prepare", 20, "preflight"),
        ("postflight", "_postflight", 30, "postflight"),
        ("rollback", "_rollback", 50, "rollback"),
    ],
)
def test_expected_maintenance_exit_codes_are_preserved(
    tmp_path: Path,
    monkeypatch,
    action: str,
    helper_name: str,
    exit_code: int,
    phase: str,
) -> None:
    monkeypatch.setattr(maintenance, helper_name, lambda _args: exit_code)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path, action))
    assert maintenance.main() == exit_code
    report_path = tmp_path / "logs" / "setup" / f"r27-installer-{action}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["exit_code"] == exit_code
    assert report["phase"] == phase
    assert report["ok"] is False
    _assert_report_id(report)


def test_running_envelope_exists_before_maintenance_action(tmp_path: Path, monkeypatch) -> None:
    observed: dict = {}

    def inspect_running(args) -> int:
        observed.update(json.loads(Path(args.report_path).read_text(encoding="utf-8")))
        return 0

    monkeypatch.setattr(maintenance, "_prepare", inspect_running)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 0
    assert observed["state"] == "running"
    assert observed["started"] is True
    assert observed["finished_at"] is None
    assert observed["exit_code"] == 40
    _assert_report_id(observed)


def test_transaction_plan_id_replaces_attempt_id_in_final_report(tmp_path: Path, monkeypatch) -> None:
    expected_plan_id = "a" * 64

    def persist_transaction(args) -> int:
        Path(args.transaction_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.transaction_path).write_text(
            json.dumps({"plan": {"plan_id": expected_plan_id}}),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(maintenance, "_prepare", persist_transaction)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 0
    report_path = tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["plan_id"] == expected_plan_id
    _assert_report_id(report)


def test_keyboard_interrupt_is_a_categorized_cancellation(tmp_path: Path, monkeypatch) -> None:
    def interrupt(_args):
        raise KeyboardInterrupt()

    monkeypatch.setattr(maintenance, "_prepare", interrupt)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 25
    report_path = tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["cancelled"] is True
    assert report["timed_out"] is False
    assert report["error_category"] == "cancelled"
    assert report["exception_type"] == "KeyboardInterrupt"
    _assert_report_id(report)


def test_exception_text_is_normalized_redacted_and_bounded(tmp_path: Path, monkeypatch, capsys) -> None:
    secret = "gh" + "p_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"

    def explode(_args):
        raise RuntimeError(f"authorization=Bearer {secret} \x01" + "x" * 70000)

    monkeypatch.setattr(maintenance, "_prepare", explode)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 40
    capsys.readouterr()
    report_path = tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert secret not in report["stderr"]
    assert "[REDACTED]" in report["stderr"]
    assert "\x01" not in report["stderr"]
    assert len(report["stderr"].encode("utf-8")) <= maintenance.MAX_CAPTURE_BYTES
    assert report["stderr_truncated"] is True
    _assert_report_id(report)


def test_primary_write_failure_uses_complete_existing_fallback(tmp_path: Path, monkeypatch) -> None:
    primary = tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json"
    real_atomic_write = maintenance._atomic_write_json

    def fail_primary(path: Path, value: dict) -> None:
        if Path(path) == primary:
            raise OSError("synthetic primary write failure")
        real_atomic_write(Path(path), value)

    monkeypatch.setattr(maintenance, "_atomic_write_json", fail_primary)
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 40
    fallback = tmp_path / "logs" / "setup" / "r27-installer-maintenance-preflight-prepare-fallback.json"
    assert not primary.exists()
    report = json.loads(fallback.read_text(encoding="utf-8"))
    assert Path(report["report_path"]) == fallback.resolve()
    assert report["exception_type"] == "OSError"
    assert report["ok"] is False
    _assert_report_id(report)


def test_primary_and_fallback_write_failure_creates_no_false_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        maintenance,
        "_atomic_write_json",
        lambda _path, _value: (_ for _ in ()).throw(OSError("synthetic total write failure")),
    )
    monkeypatch.setattr(sys, "argv", _arguments(tmp_path))
    assert maintenance.main() == 40
    assert not (tmp_path / "logs" / "setup" / "r27-installer-preflight-prepare.json").exists()
    assert not (
        tmp_path / "logs" / "setup" / "r27-installer-maintenance-preflight-prepare-fallback.json"
    ).exists()


def test_inno_never_displays_an_unchecked_report_path() -> None:
    source = (ROOT / "installer" / "windows" / "PLwCSetup.iss").read_text(encoding="utf-8")
    assert "function GetExistingMaintenanceReportReference" in source
    assert "if IsValidDiagnosticReportFile(ReportPath) then" in source
    assert "else if IsValidDiagnosticReportFile(FallbackPath) then" in source
    assert "GetExistingMaintenanceReportReference('preflight-prepare')" in source
    assert "GetExistingMaintenanceReportReference('postflight')" in source


def test_inno_fallbacks_use_complete_hash_identified_envelopes() -> None:
    source = (ROOT / "installer" / "windows" / "PLwCSetup.iss").read_text(encoding="utf-8")
    assert "function BuildInnoFallbackDiagnosticReport" in source
    assert "GetSHA256OfString(Utf8Encode(Canonical))" in source
    assert "function GetUtcDiagnosticTimestamp" in source
    assert "GetSystemTime(SystemTime)" in source
    assert "WriteInstallerMaintenanceFallbackReport" in source
    assert "WriteRuntimeImageFallbackReport" in source
    for field in (
        "build_id",
        "cancelled",
        "category",
        "command_id",
        "duration_ms",
        "error_category",
        "exception_type",
        "exit_code",
        "finished_at",
        "ok",
        "phase",
        "plan_id",
        "report_id",
        "report_path",
        "schema_version",
        "started",
        "started_at",
        "stderr",
        "stderr_truncated",
        "stdout",
        "stdout_truncated",
        "timed_out",
    ):
        assert f'"{field}"' in source


def test_inno_uses_one_primary_failure_dialog_and_rejects_stale_reports() -> None:
    source = (ROOT / "installer" / "windows" / "PLwCSetup.iss").read_text(encoding="utf-8")
    prepare_block = source[source.index("procedure PrepareInstallerMigration") : source.index("function RollbackInstallerMigration")]
    postflight_block = source[
        source.index("procedure RunHardInstallerPostflight") : source.index("procedure SetPrerequisitePhase")
    ]
    assert prepare_block.count("RaiseException(") == 1
    assert postflight_block.count("RaiseException(") == 1
    assert "DeleteFile(GetInstallerMaintenanceReportPath(ActionName))" in source
    assert "DeleteFile(GetInstallerMaintenanceFallbackPath(ActionName))" in source
    assert "PrimaryReportValid := IsValidDiagnosticReportFile" in source
    assert "DeleteFile(RuntimeImagesReportPath)" in source
    assert "The runtime image manager did not create a valid report." in source
    assert "GetExistingRuntimeImageReportReference" in source
    assert "FailureReportPath := GetExistingMaintenanceReportPath('preflight-prepare')" in source
