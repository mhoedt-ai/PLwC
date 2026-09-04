from __future__ import annotations

import base64
from pathlib import Path

import pytest

from plwc_gateway.audit import InMemoryAuditLogger
from plwc_gateway.config import ConfigValidationError, WORKSPACE_STANDARD_DIRECTORIES, load_gateway_config
from plwc_gateway.mcp.server import plwc_status, plwc_workspace_operation


def test_workspace_standard_directories_are_created_idempotently(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    existing_file = workspace / "Temp" / "keep.txt"
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("keep", encoding="utf-8")

    config = load_gateway_config(project_root=tmp_path)
    load_gateway_config(project_root=tmp_path)

    assert config.workspace_standard_directories == WORKSPACE_STANDARD_DIRECTORIES
    assert {path.name for path in workspace.iterdir()} == set(WORKSPACE_STANDARD_DIRECTORIES)
    assert all((workspace / directory).is_dir() for directory in WORKSPACE_STANDARD_DIRECTORIES)
    assert not (workspace / "Inbox").exists()
    assert existing_file.read_text(encoding="utf-8") == "keep"


def test_workspace_standard_directory_name_conflict_fails_closed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "Temp").write_text("not a directory", encoding="utf-8")

    with pytest.raises(ConfigValidationError):
        load_gateway_config(project_root=tmp_path)


def test_runtime_status_reports_workspace_standard_directory_contract(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    status = plwc_status("runtime", config=config)

    assert status["workspace_standard_directories"] == list(WORKSPACE_STANDARD_DIRECTORIES)
    assert status["workspace_standard_directories_complete"] is True
    assert {
        item["name"]: item["is_directory"]
        for item in status["workspace_standard_directory_status"]
    } == {directory: True for directory in WORKSPACE_STANDARD_DIRECTORIES}


def test_write_binary_reports_workspace_binary_provenance_and_audit(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)
    audit_logger = InMemoryAuditLogger()
    raw = b"%PDF-workspace-binary-write"

    payload = plwc_workspace_operation(
        "write_binary",
        path="Temp/generated.pdf",
        content_base64=base64.b64encode(raw).decode("ascii"),
        config=config,
        audit_logger=audit_logger,
    )

    assert payload["ok"] is True
    assert payload["artifact_origin"] == "workspace_binary_write"
    assert payload["validation_status"] == "unvalidated"
    assert (config.allowed_roots[0] / "Temp" / "generated.pdf").read_bytes() == raw
    completion = [
        event for event in audit_logger.events
        if event["event"] == "tool_call_completed"
    ][-1]
    assert completion["artifact_origin"] == "workspace_binary_write"
    assert completion["validation_status"] == "unvalidated"


def test_existing_binary_files_report_unknown_unvalidated_provenance(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)
    target = config.allowed_roots[0] / "Temp" / "existing.bin"
    target.write_bytes(b"existing")

    read_payload = plwc_workspace_operation(
        "read_binary",
        path="Temp/existing.bin",
        config=config,
    )
    info_payload = plwc_workspace_operation(
        "file_info",
        path="Temp/existing.bin",
        config=config,
    )

    assert read_payload["ok"] is True
    assert read_payload["artifact_origin"] == "unknown"
    assert read_payload["validation_status"] == "unvalidated"
    assert info_payload["ok"] is True
    assert info_payload["artifact_origin"] == "unknown"
    assert info_payload["validation_status"] == "unvalidated"
