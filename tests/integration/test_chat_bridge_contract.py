"""Cross-check the PLwC Chat Bridge boundary against the live gateway registry."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from plwc_gateway.mcp.server import build_mcp_server


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_CONFIG = ROOT / "integrations" / "plwc-chat-bridge" / "config" / "plwc.example.json"
EXTENSION_ROOT = ROOT / "integrations" / "plwc-chat-bridge" / "extension"
EXTENSION_MANIFEST = EXTENSION_ROOT / "src" / "manifest.json"
EXTENSION_ICON = EXTENSION_ROOT / "public" / "icons" / "plwc-icon-512.png"
PLWC_ICON = ROOT / "plwc-icon-512.png"

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
