"""Cross-check the PLwC Chat Bridge boundary against the live gateway registry."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from plwc_gateway.mcp.server import build_mcp_server


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_CONFIG = ROOT / "integrations" / "plwc-chat-bridge" / "config" / "plwc.example.json"
EXTENSION_ROOT = ROOT / "integrations" / "plwc-chat-bridge" / "extension"
EXTENSION_MANIFEST = EXTENSION_ROOT / "src" / "manifest.json"
EXTENSION_ICON = EXTENSION_ROOT / "public" / "icons" / "plwc-icon-512.png"
PLWC_ICON = ROOT / "plwc-icon-512.png"
WINDOWS_LAUNCHER = ROOT / "integrations" / "plwc-chat-bridge" / "scripts" / "start-windows.ps1"

EXPECTED_PUBLIC_TOOLS = (
    "plwc_status",
    "plwc_describe",
    "plwc_profile",
    "plwc_reflection",
    "plwc_governor",
    "plwc_sandbox_run",
    "plwc_workspace_operation",
    "plwc_document_operation",
)
EXPECTED_ICON_SHA256 = "952f2b7ebb6f2ab1bf2093f320a716dc3769c0ad9431aabb89b027d9b6f9a6fa"


def test_bridge_contract_matches_live_public_tool_registry() -> None:
    tools = asyncio.run(build_mcp_server().list_tools())

    assert tuple(tool.name for tool in tools) == EXPECTED_PUBLIC_TOOLS
    assert all(tool.inputSchema.get("type") == "object" for tool in tools)
    assert all(tool.description for tool in tools)


def test_bridge_example_config_is_loopback_only_and_requires_eight_tools() -> None:
    config = json.loads(BRIDGE_CONFIG.read_text(encoding="utf-8"))

    assert config["bridge"]["host"] == "127.0.0.1"
    assert config["bridge"]["path"] == "/message"
    assert config["tools"] == {
        "publicFacadeOnly": True,
        "expectedPublicToolCount": len(EXPECTED_PUBLIC_TOOLS),
    }


def test_bridge_uses_the_canonical_plwc_gateway_icon_source() -> None:
    digest = hashlib.sha256(PLWC_ICON.read_bytes()).hexdigest()
    extension_digest = hashlib.sha256(EXTENSION_ICON.read_bytes()).hexdigest()

    assert digest == EXPECTED_ICON_SHA256
    assert extension_digest == digest


def test_extension_manifest_is_plwc_only_and_uses_narrow_permissions() -> None:
    manifest = json.loads(EXTENSION_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["name"] == "PLwC Chat Bridge"
    assert manifest["host_permissions"] == ["ws://127.0.0.1:3007/*"]
    assert manifest["content_scripts"] == [
        {
            "matches": ["https://chatgpt.com/*", "https://chat.openai.com/*"],
            "js": ["content.js"],
            "run_at": "document_idle",
        }
    ]
    assert set(manifest["icons"].values()) == {"icons/plwc-icon-512.png"}
    assert manifest["web_accessible_resources"] == [
        {
            "resources": ["icons/plwc-icon-512.png"],
            "matches": ["https://chatgpt.com/*", "https://chat.openai.com/*"],
        }
    ]


@pytest.mark.skipif(os.name != "nt", reason="The PLwC MCPB settings importer is a Windows launcher feature.")
def test_windows_launcher_imports_every_visible_plwc_mcpb_setting(tmp_path: Path) -> None:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell is unavailable.")

    workspace = tmp_path / "workspace"
    profiles = tmp_path / "profiles"
    security_config = tmp_path / "security.yaml"
    workspace.mkdir()
    profiles.mkdir()
    security_config.write_text("execution:\n  fail_closed: true\n", encoding="utf-8")

    appdata = tmp_path / "AppData" / "Roaming"
    settings_path = (
        appdata
        / "Claude"
        / "Claude Extensions Settings"
        / "local.mcpb.plwc.plwc-gateway.json"
    )
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "isEnabled": True,
                "userConfig": {
                    "workspace_path": str(workspace),
                    "profiles_path": str(profiles),
                    "active_profile_name": "BridgeTestProfile",
                    "security_config": str(security_config),
                    "memory_write_threshold": 4,
                    "persona_write_threshold": 5,
                    "temperament_write_threshold": 6,
                    "qdrant_enabled": True,
                    "persona_layer_disabled": True,
                },
            }
        ),
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment["APPDATA"] = str(appdata)
    for name in (
        "PLWC_WORKSPACE_ROOT",
        "PLWC_PROFILE_ROOT",
        "PLWC_ACTIVE_PROFILE_NAME",
        "PLWC_CONFIG_FILE",
        "PLWC_MEMORY_WRITE_THRESHOLD",
        "PLWC_PERSONA_WRITE_THRESHOLD",
        "PLWC_TEMPERAMENT_WRITE_THRESHOLD",
        "PLWC_QDRANT_ENABLED",
        "PLWC_PERSONA_LAYER_DISABLED",
    ):
        environment.pop(name, None)

    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WINDOWS_LAUNCHER),
            "-DryRun",
        ],
        cwd=WINDOWS_LAUNCHER.parent.parent,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    expected_lines = (
        f"Workspace root (PLwC MCPB settings): {workspace}",
        f"Profile root (PLwC MCPB settings): {profiles}",
        "Active profile (PLwC MCPB settings): BridgeTestProfile",
        f"Security config (PLwC MCPB settings): {security_config}",
        "Memory write threshold (PLwC MCPB settings): 4",
        "Persona write threshold (PLwC MCPB settings): 5",
        "Temperament write threshold (PLwC MCPB settings): 6",
        "Qdrant enabled (PLwC MCPB settings): true",
        "Persona layer disabled (PLwC MCPB settings): true",
    )
    assert all(line in completed.stdout for line in expected_lines)
    assert "Unsupported PLwC MCPB settings" not in completed.stdout


@pytest.mark.skipif(os.name != "nt", reason="The PLwC MCPB settings importer is a Windows launcher feature.")
def test_windows_launcher_uses_plwc_defaults_without_mcpb_settings(tmp_path: Path) -> None:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell is unavailable.")

    environment = os.environ.copy()
    environment["APPDATA"] = str(tmp_path / "empty-appdata")
    for name in (
        "PLWC_WORKSPACE_ROOT",
        "PLWC_PROFILE_ROOT",
        "PLWC_ACTIVE_PROFILE_NAME",
        "PLWC_CONFIG_FILE",
        "PLWC_MEMORY_WRITE_THRESHOLD",
        "PLWC_PERSONA_WRITE_THRESHOLD",
        "PLWC_TEMPERAMENT_WRITE_THRESHOLD",
        "PLWC_QDRANT_ENABLED",
        "PLWC_PERSONA_LAYER_DISABLED",
    ):
        environment.pop(name, None)

    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WINDOWS_LAUNCHER),
            "-DryRun",
        ],
        cwd=WINDOWS_LAUNCHER.parent.parent,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "Workspace root: PLwC configured/default root" in completed.stdout
    assert "Memory write threshold: PLwC configured/default value" in completed.stdout
    assert "Dry run complete. No bridge or gateway process started." in completed.stdout
