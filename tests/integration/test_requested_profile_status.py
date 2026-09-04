from __future__ import annotations

from pathlib import Path

from plwc_gateway.config.settings import load_gateway_config
from plwc_gateway.mcp.server import build_mcp_server, plwc_status


def test_status_inspects_missing_onboarding_target_without_changing_active_profile(
    tmp_path: Path,
) -> None:
    config = load_gateway_config(project_root=tmp_path)

    result = plwc_status("runtime", "ZASA", config=config)

    assert result["active_profile_name"] == "default"
    assert result["requested_profile_name"] == "ZASA"
    assert result["requested_profile_is_active"] is False
    assert result["requested_profile_workflow"] == "profile_creation"
    assert result["profile_name_parameter_effect"] == "inspection_only"
    assert result["active_profile_changed"] is False
    assert result["requested_profile_status"]["selected_profile_exists"] is False
    assert "creates and activates the profile automatically" in result["requested_profile_instruction"]
    assert "Extension settings" not in result["requested_profile_instruction"]


def test_status_rejects_invalid_requested_profile_without_suggesting_governed_writes(
    tmp_path: Path,
) -> None:
    config = load_gateway_config(project_root=tmp_path)

    result = plwc_status("first_run", "../ZASA", config=config, docker_available=False)

    assert result["requested_profile_workflow"] == "invalid_profile_name"
    assert result["requested_profile_status"]["active_profile_directory"] is None
    assert "valid profile name" in result["requested_profile_instruction"]
    assert "plwc_governor" not in result["requested_profile_instruction"]


def test_first_run_accepts_optional_profile_name_as_inspection_only(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    result = plwc_status("first_run", "ZASA", config=config, docker_available=False)

    assert result["scope"] == "first_run"
    assert result["requested_profile_name"] == "ZASA"
    assert result["profile_name_parameter_effect"] == "inspection_only"
    assert result["active_profile_changed"] is False
    assert result["requested_profile_workflow"] == "profile_creation"


def test_status_without_requested_profile_keeps_the_existing_contract(
    tmp_path: Path,
) -> None:
    config = load_gateway_config(project_root=tmp_path)

    result = plwc_status("runtime", config=config)

    assert "requested_profile_name" not in result
    assert "requested_profile_status" not in result


def test_public_mcp_status_schema_advertises_requested_profile_inspection() -> None:
    server = build_mcp_server()
    status_tool = next(tool for tool in server._tool_manager.list_tools() if tool.name == "plwc_status")

    assert set(status_tool.parameters["properties"]) == {"profile_name", "scope"}
    assert "profile_name" not in status_tool.parameters.get("required", [])
