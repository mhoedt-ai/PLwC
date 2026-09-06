from __future__ import annotations

import json
from pathlib import Path

import pytest

from plwc_gateway.installation import (
    InventoryContractError,
    build_component_inventory,
    load_compatibility_matrix,
    version_in_policy,
)


ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "config" / "compatibility-matrix.json"
SCHEMA_PATH = ROOT / "config" / "compatibility-matrix.schema.json"
NOW = "2026-09-02T18:00:00+00:00"


def _verified_source(kind: str = "local_build_identity") -> dict[str, str]:
    return {"kind": kind, "trust": "verified_local", "observed_at": NOW}


def _extension_observation(version: str) -> dict[str, object]:
    return {
        "present": True,
        "semantic_version": version,
        "protocol_version": "1.0.0",
        "build_identity_schema": 1,
        "build_id": f"plwc-chat-bridge-extension@{version}#test",
        "tool_count": 8,
        "canonical_tools_valid": True,
        "postflight_verified": True,
        "source": _verified_source("native_messaging_contact"),
    }


def _component(inventory: dict[str, object], component_id: str) -> dict[str, object]:
    components = inventory["components"]
    assert isinstance(components, list)
    return next(component for component in components if component["id"] == component_id)


def test_compatibility_matrix_and_schema_are_machine_readable() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert matrix["matrix_version"] == "1.0.0"
    assert matrix["product"]["installer_revision"] == "installer-r26"
    assert matrix["contracts"]["gateway_facade"]["required_tool_count"] == 8
    assert len(matrix["contracts"]["gateway_facade"]["canonical_tools"]) == 8
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_semantic_version_policy_supports_runtime_ranges() -> None:
    policy = {"minimum": "22.12.0", "maximum_exclusive": "25.0.0"}

    assert version_in_policy("22.12.0", policy) is True
    assert version_in_policy("24.18.0", policy) is True
    assert version_in_policy("25.0.0", policy) is False
    assert version_in_policy("22.12.0-rc.1", policy) is False


def test_inventory_classifies_compatible_extension_101_separately_from_protocol_100() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    inventory = build_component_inventory(
        matrix,
        {"browser_extension": _extension_observation("1.0.1")},
        generated_at=NOW,
    )

    extension = _component(inventory, "browser_extension")
    assert extension["status"] == "ready"
    assert extension["compatible"] is True
    assert extension["installed"]["semantic_version"] == "1.0.1"
    assert extension["installed"]["protocol_version"] == "1.0.0"
    assert extension["installed"]["build_id"].endswith("#test")
    assert extension["installed"]["sha256"] is None


def test_inventory_keeps_semantic_protocol_revision_build_and_hash_identity_separate() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    inventory = build_component_inventory(
        matrix,
        {
            "product": {
                "present": True,
                "semantic_version": "1.0.0",
                "protocol_version": None,
                "build_revision": "installer-r25",
                "build_identity_schema": 1,
                "build_id": "plwc-windows-setup@1.0.0/installer-r25#sha256:test",
                "sha256": "e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c",
                "postflight_verified": True,
                "source": _verified_source(),
            }
        },
        generated_at=NOW,
    )

    installed = _component(inventory, "product")["installed"]
    assert installed == {
        "semantic_version": "1.0.0",
        "protocol_version": None,
        "build_revision": "installer-r25",
        "build_identity_schema": 1,
        "build_id": "plwc-windows-setup@1.0.0/installer-r25#sha256:test",
        "sha256": "e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c",
        "source": _verified_source(),
    }


def test_inventory_classifies_compatible_100_as_recommended_update_without_breaking_it() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    inventory = build_component_inventory(
        matrix,
        {"browser_extension": _extension_observation("1.0.0")},
        available_releases={
            "browser_extension": {
                "semantic_version": "1.0.1",
                "update_kind": "recommended",
                "source": {
                    "kind": "signed_release_manifest",
                    "trust": "trusted_release",
                    "observed_at": NOW,
                },
            }
        },
        generated_at=NOW,
    )

    extension = _component(inventory, "browser_extension")
    assert extension["status"] == "recommended_update"
    assert extension["compatible"] is True
    assert extension["reasons"] == ["trusted_recommended_update_available"]


@pytest.mark.parametrize(
    ("extension_version", "installer_revision"),
    [
        ("1.0.0", "installer-r25"),
        ("1.0.0", "installer-r26"),
        ("1.0.1", "installer-r25"),
        ("1.0.1", "installer-r26"),
    ],
)
def test_extension_packages_100_and_101_remain_compatible_with_r25_and_r26_runtime_contracts(
    extension_version: str,
    installer_revision: str,
) -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    inventory = build_component_inventory(
        matrix,
        {
            "browser_extension": _extension_observation(extension_version),
            "windows_installer": {
                "present": True,
                "semantic_version": "1.0.0",
                "build_revision": installer_revision,
                "build_identity_schema": 1,
                "build_id": f"plwc-windows-setup@1.0.0/{installer_revision}#sha256:test",
                "sha256": "a" * 64,
                "postflight_verified": True,
                "source": _verified_source(),
            },
        },
        generated_at=NOW,
    )

    extension = _component(inventory, "browser_extension")
    installer = _component(inventory, "windows_installer")
    assert extension["compatible"] is True
    assert extension["status"] == "ready"
    assert extension["installed"]["protocol_version"] == "1.0.0"
    assert installer["compatible"] is True
    assert installer["installed"]["build_revision"] == installer_revision


def test_inventory_requires_update_for_incompatible_protocol_or_tool_contract() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    observation = _extension_observation("1.0.0")
    observation["protocol_version"] = "2.0.0"
    observation["tool_count"] = 7

    inventory = build_component_inventory(
        matrix,
        {"browser_extension": observation},
        generated_at=NOW,
    )

    extension = _component(inventory, "browser_extension")
    assert extension["status"] == "required_update"
    assert extension["compatible"] is False
    assert extension["reasons"] == ["protocol_version_not_supported", "tool_count_mismatch"]


def test_inventory_distinguishes_unknown_optional_and_mixed_installations() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    inventory = build_component_inventory(
        matrix,
        {
            "browser_extension": {"present": None},
            "docker": {"present": False, "source": {"kind": "path_probe", "trust": "observed_local"}},
            "node_bridge": {
                "present": True,
                "active_paths": [
                    "C:/Users/Test/AppData/Roaming/PLwC/app/bridge",
                    "C:/Users/Test/AppData/Roaming/PLwC/app/chat-bridge",
                ],
                "source": {"kind": "preflight_inventory", "trust": "observed_local"},
            },
        },
        generated_at=NOW,
    )

    assert _component(inventory, "browser_extension")["status"] == "unknown"
    assert _component(inventory, "docker")["status"] == "optional"
    assert _component(inventory, "node_bridge")["status"] == "mixed_installation"


def test_untrusted_online_version_never_creates_an_update_classification() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    inventory = build_component_inventory(
        matrix,
        {"browser_extension": _extension_observation("1.0.0")},
        available_releases={
            "browser_extension": {
                "semantic_version": "1.0.1",
                "source": {"kind": "network_response", "trust": "unverified"},
            }
        },
        generated_at=NOW,
    )

    extension = _component(inventory, "browser_extension")
    assert extension["status"] == "ready"
    assert extension["reasons"] == ["all_required_contracts_match", "available_release_untrusted"]


def test_inventory_rejects_unknown_components_and_invalid_matrix_versions() -> None:
    matrix = load_compatibility_matrix(MATRIX_PATH)
    with pytest.raises(InventoryContractError, match="unknown components"):
        build_component_inventory(matrix, {"invented": {"present": True}})

    invalid = dict(matrix)
    invalid["schema_version"] = "2.0.0"
    with pytest.raises(InventoryContractError, match="Unsupported"):
        build_component_inventory(invalid, {})


def test_installer_stages_the_shared_compatibility_contract() -> None:
    build_source = (ROOT / "installer" / "windows" / "build.ps1").read_text(encoding="utf-8")

    assert "compatibility-matrix.json" in build_source
    assert "compatibility-matrix.schema.json" in build_source
