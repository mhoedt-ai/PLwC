from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from plwc_gateway.config import load_gateway_config
from plwc_gateway.mcp.server import plwc_describe, plwc_governor, plwc_status, plwc_workspace_operation


class _UnavailableSandbox:
    def status(self) -> dict[str, Any]:
        return {
            "ok": False,
            "mode": "safe",
            "policy_decision": "DENY",
            "error": "Docker was not found. PLwC is running in Safe Mode.",
            "error_category": "sandbox_unavailable",
            "requirement_ids": ["SR-002", "OR-002"],
        }


class _GovernorAdapter:
    def governor_plan(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "operation": "plan",
            "policy_decision": "ALLOW",
            "data": {"plan_type": "profile_activation"},
            "requirement_ids": ["SR-010"],
        }

    def governor_apply(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "operation": "apply",
            "policy_decision": "ALLOW",
            "data": {"plan_type": "profile_activation"},
            "requirement_ids": ["SR-010"],
        }


def test_public_error_category_contract_maps_core_failures(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)
    note = config.allowed_roots[0] / "Temp" / "note.txt"
    note.write_text("hello", encoding="utf-8")

    invalid = plwc_describe(scope="unknown_scope", config=config)
    not_found = plwc_workspace_operation("read", path="Temp/missing.txt", config=config)
    unavailable = plwc_status("sandbox", config=config, sandbox_adapter=_UnavailableSandbox())
    conflict = plwc_workspace_operation(
        "exact_replace",
        path="Temp/note.txt",
        old_text="absent",
        new_text="new",
        expected_replacements=1,
        config=config,
    )
    policy_deny = plwc_workspace_operation("read", path="governance/config.yaml", config=config)

    assert invalid["error_category"] == "INVALID_REQUEST"
    assert invalid["error_detail_category"] == "unknown_scope"
    assert not_found["error_category"] == "NOT_FOUND"
    assert not_found["error_detail_category"] == "not_found"
    assert unavailable["error_category"] == "UNAVAILABLE"
    assert unavailable["error_detail_category"] == "sandbox_unavailable"
    assert conflict["error_category"] == "CONFLICT"
    assert conflict["error_detail_category"] == "unexpected_replacement_count"
    assert policy_deny["error_category"] == "POLICY_DENY"
    assert policy_deny["error_detail_category"] == "policy_denied"
    assert policy_deny["policy_decision"] == "DENY"


def test_effective_governance_policy_is_shared_by_status_plan_and_apply(tmp_path: Path) -> None:
    settings_file = tmp_path / "config" / "gateway-settings.json"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "settings": {
                    "workspace_path": str(tmp_path / "workspace"),
                    "profiles_path": str(tmp_path / "profiles"),
                    "active_profile_name": "Sororitas",
                    "memory_write_threshold": 2,
                    "persona_write_threshold": 3,
                    "temperament_write_threshold": 4,
                },
            }
        ),
        encoding="utf-8",
    )
    config = load_gateway_config(project_root=tmp_path)
    adapter = _GovernorAdapter()

    status = plwc_status("runtime", config=config)
    plan = plwc_governor(
        operation="plan",
        plan_type="profile_activation",
        profile="Sororitas",
        config=config,
        adapter=adapter,
    )
    apply = plwc_governor(
        operation="apply",
        plan_type="profile_activation",
        profile="Sororitas",
        confirmed=True,
        config=config,
        adapter=adapter,
    )

    assert status["effective_governance_policy"] == plan["effective_governance_policy"]
    assert status["effective_governance_policy"] == apply["effective_governance_policy"]
    rule = status["effective_governance_policy"]["rules"]["memory_write_threshold"]
    assert rule["user_preference_recorded"] is True
    assert rule["user_preference"] == 2
    assert rule["user_preference_source"] == "shared_config"
    assert rule["effective_policy"] == 2
    assert rule["effective_policy_source"] == "shared_config"
    assert rule["effective_policy_overridden_by_global_minimum"] is False


def test_describe_exposes_public_error_and_governance_contract(tmp_path: Path) -> None:
    config = load_gateway_config(project_root=tmp_path)

    tools = plwc_describe(scope="tools", config=config)["data"]
    status = plwc_describe(scope="status", config=config)["data"]
    governor = plwc_describe(scope="governor", config=config)["data"]

    assert tools["public_error_categories"] == [
        "INVALID_REQUEST",
        "NOT_FOUND",
        "UNAVAILABLE",
        "CONFLICT",
        "POLICY_DENY",
    ]
    assert status["effective_governance_policy_contract"]["schema_version"] == "1.0"
    assert governor["effective_governance_policy_contract"]["shared_with_status"] is True
