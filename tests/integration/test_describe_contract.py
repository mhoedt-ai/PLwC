from __future__ import annotations

import asyncio
import json
from pathlib import Path

from plwc_gateway.config import WORKSPACE_STANDARD_DIRECTORIES, load_gateway_config
from plwc_gateway.mcp.server import build_mcp_server, plwc_describe


def test_describe_document_operation_filter_returns_only_create_pdf_contract(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_describe(
        scope="document_operation",
        operation="create_pdf",
        config=config,
    )

    assert payload["ok"] is True
    assert payload["operation_filter"] == "create_pdf"
    data = payload["data"]
    assert data["supported_operations"] == ["create_pdf"]
    assert set(data["required_fields"]) == {"create_pdf"}
    assert set(data["optional_fields"]) == {"create_pdf"}
    assert data["required_fields"]["create_pdf"]["top_level"] == ["operation", "output_path"]
    assert "pdf_creation_v2_limits" in data
    assert "docx_creation_v2_limits" not in data
    assert "create_docx" not in json.dumps(data, sort_keys=True)
    assert data["example_call"].startswith('plwc_document_operation(operation="create_pdf"')


def test_describe_unknown_operation_returns_precise_next_step(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_describe(
        scope="document_operation",
        operation="make_pdf",
        config=config,
    )

    assert payload["ok"] is False
    assert payload["error_category"] == "INVALID_REQUEST"
    assert payload["error_detail_category"] == "unknown_operation"
    assert payload["unsupported_operation_filter"] == "make_pdf"
    assert payload["next_tool"] == "plwc_describe"
    assert payload["next_operation"] == "describe"
    assert payload["next_plan_type"] is None
    assert payload["required_fields"] == ["scope", "operation"]
    assert payload["example_call"] == 'plwc_describe(scope="document_operation", operation="create_pdf")'
    assert "create_pdf" in payload["supported_operations"]


def test_describe_unknown_scope_returns_precise_next_step(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_describe(scope="document_operations", config=config)

    assert payload["ok"] is False
    assert payload["error_category"] == "INVALID_REQUEST"
    assert payload["error_detail_category"] == "unknown_scope"
    assert payload["next_tool"] == "plwc_describe"
    assert payload["next_operation"] == "describe"
    assert payload["next_plan_type"] is None
    assert payload["required_fields"] == ["scope"]
    assert payload["example_call"] == 'plwc_describe(scope="tools")'


def test_describe_workspace_contract_names_temp_and_trashcan_rules(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    payload = plwc_describe(scope="workspace_operation", config=config)

    assert payload["ok"] is True
    data = payload["data"]
    assert data["workspace_standard_directories"] == list(WORKSPACE_STANDARD_DIRECTORIES)
    assert "Temp/<task>/" in data["temp_policy"]
    assert "never cleans Temp automatically" in data["temp_policy"]
    assert "Trashcan/" in data["trashcan_policy"]
    assert "no delete operation" in data["trashcan_policy"]


def test_describe_mcp_schema_exposes_operation_filter() -> None:
    tools = asyncio.run(build_mcp_server().list_tools())
    describe = next(tool for tool in tools if tool.name == "plwc_describe")

    assert "operation" in describe.inputSchema["properties"]
