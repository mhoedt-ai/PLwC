from __future__ import annotations

import json
from pathlib import Path

from plwc_gateway.adapters.pba import PBAProfileAdapter
from plwc_gateway.config.settings import load_gateway_config


def _write_shared_settings(root: Path, *, active_profile: str) -> None:
    settings_file = root / "config" / "gateway-settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "settings": {
                    "workspace_path": str(root / "workspace"),
                    "profiles_path": str(root / "profiles"),
                    "active_profile_name": active_profile,
                    "security_config": None,
                    "memory_write_threshold": 2,
                    "persona_write_threshold": 3,
                    "temperament_write_threshold": 2,
                    "qdrant_enabled": True,
                    "persona_layer_disabled": False,
                },
            }
        ),
        encoding="utf-8",
    )


def test_shared_settings_and_governed_profile_state_override_stale_host_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_shared_settings(tmp_path, active_profile="WasIstDas")
    state_file = tmp_path / "config" / "active_profile.json"
    state_file.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "active_profile_name": "Sororitas",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PLWC_WORKSPACE_ROOT", str(tmp_path / "stale-workspace"))
    monkeypatch.setenv("PLWC_PROFILE_ROOT", str(tmp_path / "stale-profiles"))
    monkeypatch.setenv("PLWC_ACTIVE_PROFILE_NAME", "WasIstDas")
    monkeypatch.setenv("PLWC_MEMORY_WRITE_THRESHOLD", "99")
    monkeypatch.setenv("PLWC_PERSONA_WRITE_THRESHOLD", "99")
    monkeypatch.setenv("PLWC_TEMPERAMENT_WRITE_THRESHOLD", "99")
    monkeypatch.setenv("PLWC_QDRANT_ENABLED", "false")
    monkeypatch.setenv("PLWC_PERSONA_LAYER_DISABLED", "true")

    config = load_gateway_config(project_root=tmp_path)

    assert config.allowed_roots == ((tmp_path / "workspace").resolve(),)
    assert config.profile_root == (tmp_path / "profiles").resolve()
    assert config.workspace_source == "shared_config"
    assert config.profile_source == "shared_config"
    assert config.configured_active_profile_name == "Sororitas"
    assert config.active_profile_name == "Sororitas"
    assert config.active_profile_source == "plwc_state"
    assert config.governance.memory_write_threshold == 2
    assert config.governance.persona_write_threshold == 3
    assert config.governance.temperament_write_threshold == 2
    assert config.governance.memory_write_threshold_source == "shared_config"
    assert config.governance.persona_write_threshold_source == "shared_config"
    assert config.governance.temperament_write_threshold_source == "shared_config"
    assert config.qdrant_enabled is True
    assert config.qdrant_enabled_source == "shared_config"
    assert config.persona_layer_enabled is True
    assert config.persona_layer_enabled_source == "shared_config"


def test_shared_null_values_select_plwc_defaults_instead_of_stale_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_shared_settings(tmp_path, active_profile="Sororitas")
    settings_file = tmp_path / "config" / "gateway-settings.json"
    payload = json.loads(settings_file.read_text(encoding="utf-8"))
    payload["settings"]["profiles_path"] = None
    payload["settings"]["active_profile_name"] = None
    payload["settings"]["qdrant_enabled"] = None
    settings_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("PLWC_PROFILE_ROOT", str(tmp_path / "stale-profiles"))
    monkeypatch.setenv("PLWC_ACTIVE_PROFILE_NAME", "WasIstDas")
    monkeypatch.setenv("PLWC_QDRANT_ENABLED", "true")

    config = load_gateway_config(project_root=tmp_path)

    assert config.profile_root == (tmp_path / "profiles").resolve()
    assert config.active_profile_name == "default"
    assert config.configured_active_profile_name is None
    assert config.qdrant_enabled is None


def test_new_profile_activation_is_not_blocked_by_a_stale_host_selection(
    tmp_path: Path,
) -> None:
    adapter = PBAProfileAdapter(
        profile_root=tmp_path / "profiles",
        active_profile_name="WasIstDas",
        configured_active_profile_name="WasIstDas",
        active_profile_source="extension_config",
        active_profile_state_file=tmp_path / "config" / "active_profile.json",
    )

    activation = adapter._profile_creation_activation_plan("Sororitas")

    assert activation["activation_blocked_reason"] is None
    assert activation["active_state_write_planned"] is True
    assert activation["activation_effective_after_apply"] is True
    assert activation["active_profile_source_after"] == "plwc_state"
