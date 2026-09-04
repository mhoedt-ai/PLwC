from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from installer_state import InstallerStateEngine, InstallerStateError


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
    parser = argparse.ArgumentParser(description="PLwC r26 Windows installer migration transaction")
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
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.action == "preflight-prepare":
            return _prepare(args)
        if args.action == "postflight":
            if not args.payload_manifest or not args.extension_id:
                raise InstallerStateError("Postflight requires the payload manifest and extension ID.")
            return _postflight(args)
        return _rollback(args)
    except (InstallerStateError, OSError, ValueError, json.JSONDecodeError) as exc:
        try:
            _atomic_write_json(
                Path(args.report_path),
                {
                    "ok": False,
                    "phase": args.action,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "transaction": str(Path(args.transaction_path).resolve(strict=False)),
                },
            )
        except OSError:
            pass
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InstallerStateError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PLwC installer maintenance failed: {exc}", file=sys.stderr)
        raise SystemExit(40) from exc
