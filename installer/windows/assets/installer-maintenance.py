from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from installer_state import InstallerStateEngine, InstallerStateError


REPORT_SCHEMA_VERSION = "1.0.0"
MAX_CAPTURE_BYTES = 64 * 1024


_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"),
    re.compile(r"(?i)((?:token|password|passwd|secret|cookie)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\b(?:ghp|github_pat|glpat)-?[A-Za-z0-9_\-]{16,}\b"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _report_id(value: dict[str, Any]) -> str:
    import hashlib

    payload = dict(value)
    payload.pop("report_id", None)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _redact_text(value: str) -> str:
    normalized = "".join(character if character in "\n\r\t" or ord(character) >= 32 else "?" for character in value)
    for pattern in _SECRET_PATTERNS:
        normalized = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]" if match.lastindex else "[REDACTED]", normalized)
    return normalized


def _bounded_text(value: str) -> tuple[str, bool]:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_CAPTURE_BYTES:
        return value, False
    return encoded[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace"), True


def _transaction_plan_id(args: argparse.Namespace) -> str:
    transaction = _read_report_if_present(Path(args.transaction_path))
    plan = transaction.get("plan")
    if isinstance(plan, dict) and isinstance(plan.get("plan_id"), str):
        return str(plan["plan_id"])
    return str(args.plan_id)


def _final_report(
    args: argparse.Namespace,
    payload: dict[str, Any],
    *,
    started_at: str,
    started_monotonic: float,
    exit_code: int,
    exception: BaseException | None = None,
    cancelled: bool = False,
) -> dict[str, Any]:
    report = dict(payload)
    if report.get("state") == "running":
        report["state"] = "completed"
        report["ok"] = exit_code == 0
    stderr, stderr_truncated = _bounded_text(_redact_text(str(exception)) if exception is not None else "")
    report.update(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "build_id": args.build_id,
            "plan_id": _transaction_plan_id(args),
            "phase": "preflight" if args.action == "preflight-prepare" else args.action,
            "category": "maintenance",
            "command_id": f"installer-maintenance-{args.action}",
            "started": True,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "duration_ms": max(0, int((time.monotonic() - started_monotonic) * 1000)),
            "exit_code": exit_code,
            "stdout": "",
            "stderr": stderr,
            "stdout_truncated": False,
            "stderr_truncated": stderr_truncated,
            "timed_out": False,
            "cancelled": cancelled,
            "exception_type": type(exception).__name__ if exception is not None else None,
            "report_path": str(Path(args.report_path).resolve(strict=False)),
            "ok": exit_code == 0 and report.get("ok", True) is not False,
        }
    )
    if exception is not None:
        report["error"] = stderr
        report["error_category"] = "cancelled" if cancelled else "unexpected_maintenance_error"
    else:
        report.setdefault("error_category", None)
    report["report_id"] = _report_id(report)
    return report


def _running_report(args: argparse.Namespace, *, started_at: str, started_monotonic: float) -> dict[str, Any]:
    report = _final_report(
        args,
        {},
        started_at=started_at,
        started_monotonic=started_monotonic,
        exit_code=40,
    )
    report.update({"state": "running", "finished_at": None, "duration_ms": 0})
    report["report_id"] = _report_id(report)
    return report


def _read_report_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise InstallerStateError(f"Expected a JSON object: {path}")
    return dict(value)


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _engine(args: argparse.Namespace) -> InstallerStateEngine:
    return InstallerStateEngine(
        Path(args.installation_root),
        app_root=Path(args.app_root),
        gateway_root=Path(args.gateway_root),
        bridge_root=Path(args.bridge_root),
        workspace_root=Path(args.workspace_root),
        profile_root=Path(args.profile_root),
        config_root=Path(args.config_root),
        state_root=Path(args.state_root),
        logs_root=Path(args.logs_root),
        backups_root=Path(args.backups_root),
    )


def _prepare(args: argparse.Namespace) -> int:
    engine = _engine(args)
    preflight = engine.preflight(selection_path=Path(args.selection_path))
    plan = engine.plan(preflight)
    transaction = {
        "schema_version": "1.0.0",
        "status": "blocked" if plan["blocked"] else "planned",
        "preflight": preflight,
        "plan": plan,
    }
    _atomic_write_json(Path(args.transaction_path), transaction)
    if plan["blocked"]:
        _atomic_write_json(
            Path(args.report_path),
            {
                "ok": False,
                "phase": "preflight",
                "error": "Port 3007 is owned by an unverified process. No process was stopped.",
                "foreign_port_owners": plan["foreign_port_owners"],
                "transaction": str(Path(args.transaction_path).resolve(strict=False)),
            },
        )
        return 20
    prepared = engine.prepare(
        plan,
        confirmed_plan_id=str(plan["plan_id"]),
        current_preflight=preflight,
    )
    transaction["status"] = "prepared"
    transaction["prepare"] = prepared
    _atomic_write_json(Path(args.transaction_path), transaction)
    return 0


def _postflight(args: argparse.Namespace) -> int:
    engine = _engine(args)
    transaction_path = Path(args.transaction_path)
    transaction = _read_json(transaction_path)
    if transaction.get("status") != "prepared":
        raise InstallerStateError("Installer transaction is not in the prepared state.")
    preflight = transaction.get("preflight")
    plan = transaction.get("plan")
    if not isinstance(preflight, dict) or not isinstance(plan, dict):
        raise InstallerStateError("Installer transaction is incomplete.")
    report = engine.postflight(
        preflight=preflight,
        payload_manifest_path=Path(args.payload_manifest),
        selection_path=Path(args.selection_path),
        expected_extension_id=args.extension_id,
    )
    report["phase"] = "postflight"
    report["transaction"] = str(transaction_path.resolve(strict=False))
    _atomic_write_json(Path(args.report_path), report)
    persisted = _read_json(Path(args.report_path))
    if report.get("ok") is not True or persisted.get("report_id") != report.get("report_id"):
        return 30
    archived = engine.archive_legacy_after_success(plan, report)
    report["legacy_archive"] = archived
    report["diagnostic_report_written"] = True
    _atomic_write_json(Path(args.report_path), report)
    transaction["status"] = "postflight_succeeded"
    transaction["postflight_report"] = str(Path(args.report_path).resolve(strict=False))
    transaction["legacy_archive"] = archived
    _atomic_write_json(transaction_path, transaction)
    return 0


def _rollback(args: argparse.Namespace) -> int:
    engine = _engine(args)
    transaction_path = Path(args.transaction_path)
    if not transaction_path.is_file():
        _atomic_write_json(
            Path(args.report_path),
            {"ok": True, "phase": "rollback", "result": "not_required", "transaction": str(transaction_path.resolve(strict=False))},
        )
        return 0
    transaction = _read_json(transaction_path)
    prepared = transaction.get("prepare")
    if not isinstance(prepared, dict):
        _atomic_write_json(
            Path(args.report_path),
            {"ok": True, "phase": "rollback", "result": "not_prepared", "transaction": str(transaction_path.resolve(strict=False))},
        )
        return 0
    preflight = transaction.get("preflight")
    result = engine.rollback(prepared, preflight=preflight if isinstance(preflight, dict) else None)
    transaction["status"] = "rolled_back"
    transaction["rollback"] = result
    _atomic_write_json(transaction_path, transaction)
    _atomic_write_json(
        Path(args.report_path),
        {"phase": "rollback", "transaction": str(transaction_path.resolve(strict=False)), **result},
    )
    return 0 if result.get("ok") is True else 50


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PLwC r27 Windows installer migration transaction")
    parser.add_argument("action", choices=("preflight-prepare", "postflight", "rollback"))
    for name in (
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
    ):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--payload-manifest")
    parser.add_argument("--extension-id")
    parser.add_argument("--build-id", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    started_at = _utc_now()
    started_monotonic = time.monotonic()
    args.plan_id = uuid.uuid4().hex
    report_path = Path(args.report_path)
    try:
        _atomic_write_json(
            report_path,
            _running_report(args, started_at=started_at, started_monotonic=started_monotonic),
        )
        if args.action == "preflight-prepare":
            exit_code = _prepare(args)
        elif args.action == "postflight":
            if not args.payload_manifest or not args.extension_id:
                raise InstallerStateError("Postflight requires the payload manifest and extension ID.")
            exit_code = _postflight(args)
        else:
            exit_code = _rollback(args)
        report = _final_report(
            args,
            _read_report_if_present(report_path),
            started_at=started_at,
            started_monotonic=started_monotonic,
            exit_code=exit_code,
        )
        _atomic_write_json(report_path, report)
        return exit_code
    except KeyboardInterrupt as exc:
        report = _final_report(
            args,
            _read_report_if_present(report_path),
            started_at=started_at,
            started_monotonic=started_monotonic,
            exit_code=25,
            exception=exc,
            cancelled=True,
        )
        try:
            _atomic_write_json(report_path, report)
        except OSError:
            fallback = (
                Path(args.logs_root)
                / "setup"
                / f"r27-installer-maintenance-{args.action}-fallback.json"
            )
            try:
                report["report_path"] = str(fallback.resolve(strict=False))
                report["report_id"] = _report_id(report)
                _atomic_write_json(fallback, report)
            except OSError:
                pass
        return 25
    except Exception as exc:
        report = _final_report(
            args,
            _read_report_if_present(report_path),
            started_at=started_at,
            started_monotonic=started_monotonic,
            exit_code=40,
            exception=exc,
        )
        try:
            _atomic_write_json(report_path, report)
        except OSError:
            fallback = (
                Path(args.logs_root)
                / "setup"
                / f"r27-installer-maintenance-{args.action}-fallback.json"
            )
            try:
                report["report_path"] = str(fallback.resolve(strict=False))
                report["report_id"] = _report_id(report)
                _atomic_write_json(fallback, report)
            except OSError:
                pass
        print(f"PLwC installer maintenance failed: {_redact_text(str(exc))}", file=sys.stderr)
        return 40


if __name__ == "__main__":
    raise SystemExit(main())
