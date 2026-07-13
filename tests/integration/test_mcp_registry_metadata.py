"""Registry metadata checks for the public MCPB package."""

from __future__ import annotations

import json
import re
from pathlib import Path

from plwc_gateway.mcp.server_constants import (
    FORBIDDEN_PUBLIC_SERVER_NAMES,
    PUBLIC_SERVER_NAME,
)


ROOT = Path(__file__).resolve().parents[2]
SERVER_JSON = ROOT / "server.json"
EXPECTED_RELEASE_URL = (
    "https://github.com/mhoedt-ai/PLwC/releases/download/"
    "v0.2.0-rc18.dev9/plwc-gateway-0.2.0-rc18.dev9.mcpb"
)
EXPECTED_SHA256 = (
    "2f71ac903bf85cc70023805ec0f901e84c4294982c1b59940350db3591a2d345"
)


def _load_server_metadata() -> dict:
    return json.loads(SERVER_JSON.read_text(encoding="utf-8"))


def test_registry_server_json_points_to_dev9_mcpb_release_asset() -> None:
    metadata = _load_server_metadata()

    assert metadata["name"] == f"io.github.mhoedt-ai/{PUBLIC_SERVER_NAME}"
    assert metadata["version"] == "0.2.0-rc18.dev9"
    assert metadata["repository"] == {
        "url": "https://github.com/mhoedt-ai/PLwC",
        "source": "github",
    }

    assert len(metadata["packages"]) == 1
    package = metadata["packages"][0]
    assert package["registryType"] == "mcpb"
    assert package["identifier"] == EXPECTED_RELEASE_URL
    assert package["identifier"].endswith(".mcpb")
    assert package["fileSha256"] == EXPECTED_SHA256
    assert re.fullmatch(r"[0-9a-f]{64}", package["fileSha256"])
    assert package["transport"] == {"type": "stdio"}


def test_registry_server_json_does_not_expose_bypass_server_names() -> None:
    metadata_text = SERVER_JSON.read_text(encoding="utf-8")

    assert PUBLIC_SERVER_NAME in metadata_text
    for forbidden_name in FORBIDDEN_PUBLIC_SERVER_NAMES:
        assert forbidden_name not in metadata_text

    metadata = _load_server_metadata()
    assert "remotes" not in metadata
    assert metadata["packages"][0]["registryType"] == "mcpb"
