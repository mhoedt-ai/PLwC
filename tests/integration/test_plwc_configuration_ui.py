from __future__ import annotations

import http.client
import importlib.util
import json
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGURATION_ROOT = REPO_ROOT / "installer" / "windows" / "assets" / "configuration"
CONFIGURATION_SCRIPT = CONFIGURATION_ROOT / "plwc-config.py"
GETTING_STARTED_ROOT = REPO_ROOT / "installer" / "windows" / "assets" / "getting-started"
PROFILE_FILES = (
    "CORE.md",
    "TEMPERAMENT.md",
    "PERSONA.md",
    "memory.md",
    "reflection.md",
)


def _load_configuration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("plwc_local_configuration", CONFIGURATION_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def configuration_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = _load_configuration_module()
    monkeypatch.setattr(
        module.PlwcConfigurationService,
        "_store_workspace_registry",
        staticmethod(lambda workspace: None),
    )
    return module


def _write_profile(root: Path, name: str) -> None:
    profile = root / "profiles" / name
    profile.mkdir(parents=True)
    for filename in PROFILE_FILES:
        (profile / filename).write_text(f"# {filename}\n", encoding="utf-8")
    governance = profile / "governance" / "config.yaml"
    governance.parent.mkdir()
    governance.write_text(
        "\n".join(
            (
                "profile_kind: standard",
                "onboarding_complete: true",
                "memory_write_threshold: 2",
                "persona_write_threshold: 3",
                "temperament_write_threshold: 2",
                "workspace_tools_may_modify_profile_files: false",
                "governed_tools_required: true",
                "",
            )
        ),
        encoding="utf-8",
    )


def _write_shared_settings(root: Path) -> Path:
    settings_path = root / "config" / "gateway-settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "settings": {
                    "workspace_path": str(root / "workspace"),
                    "profiles_path": str(root / "profiles"),
                    "active_profile_name": "default",
                    "security_config": None,
                    "memory_write_threshold": 2,
                    "persona_write_threshold": 3,
                    "temperament_write_threshold": 2,
                    "qdrant_enabled": False,
                    "persona_layer_disabled": False,
                },
            }
        ),
        encoding="utf-8",
    )
    return settings_path


def _onboarding_answers(profile_name: str = "Researcher") -> dict[str, str]:
    return {
        "profile_name": profile_name,
        "role_use_case": "Research and technical writing assistant",
        "preferred_name": "Alex",
        "form_of_address": "Use Alex",
        "tone": "Clear, calm and direct",
        "working_style": "Structured, critical and evidence-oriented",
        "strictness": "Mark uncertainty and verify important assumptions",
        "memory_scope": "Only confirmed information useful across future sessions",
        "confirmation_boundaries": "Never change profile, memory or policy without confirmation",
        "project_context": "Long-running research and documentation projects",
        "language_preference": "German conversation and English public documents",
        "special_instructions": "Keep summaries concise",
    }


def _editable_settings(**overrides: object) -> dict[str, object]:
    settings: dict[str, object] = {
        "memory_write_threshold": 2,
        "persona_write_threshold": 3,
        "temperament_write_threshold": 2,
        "qdrant_enabled": False,
        "persona_layer_enabled": True,
    }
    settings.update(overrides)
    return settings


def _apply_workspace(service, workspace: Path) -> dict[str, object]:
    plan = service.plan_workspace_change(str(workspace))
    assert plan["valid"] is True
    return service.apply_workspace_change(str(workspace), plan["plan_digest"], True)


@pytest.fixture()
def configured_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "PLWC_WORKSPACE_ROOT",
        "PLWC_PROFILE_ROOT",
        "PLWC_ACTIVE_PROFILE_NAME",
        "PLWC_MEMORY_WRITE_THRESHOLD",
        "PLWC_PERSONA_WRITE_THRESHOLD",
        "PLWC_TEMPERAMENT_WRITE_THRESHOLD",
        "PLWC_QDRANT_ENABLED",
        "PLWC_PERSONA_LAYER_DISABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / "workspace").mkdir()
    _write_profile(tmp_path, "default")
    _write_profile(tmp_path, "Writer")
    _write_shared_settings(tmp_path)
    return tmp_path


def test_snapshot_and_atomic_settings_update_are_shared_across_clients(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    service = configuration_module.PlwcConfigurationService(configured_root, language="en")

    before = service.snapshot()
    service.update_settings(
        _editable_settings(
            memory_write_threshold=4,
            persona_write_threshold=5,
            temperament_write_threshold=6,
            qdrant_enabled=True,
            persona_layer_enabled=False,
        )
    )
    plan = service.plan_workspace_change(str(configured_root / "workspace-new"))

    assert plan["valid"] is True
    assert plan["data_migration"] is False
    assert not (configured_root / "workspace-new").exists()
    with pytest.raises(configuration_module.ConfigurationError, match="explicit confirmation"):
        service.apply_workspace_change(str(configured_root / "workspace-new"), plan["plan_digest"], False)
    after = service.apply_workspace_change(
        str(configured_root / "workspace-new"),
        plan["plan_digest"],
        True,
    )["state"]

    assert before["runtime"]["active_profile_name"] == "default"
    assert [profile["name"] for profile in before["runtime"]["available_profiles"]] == ["default", "Writer"]
    assert after["settings"]["memory_write_threshold"] == 4
    assert after["settings"]["qdrant_enabled"] is True
    assert after["settings"]["persona_layer_enabled"] is False
    payload = json.loads((configured_root / "config" / "gateway-settings.json").read_text(encoding="utf-8"))
    assert payload["updated_by"] == "plwc-local-configuration"
    assert payload["settings"]["workspace_path"] == str(configured_root / "workspace-new")
    assert payload["settings"]["active_profile_name"] == "default"
    assert payload["settings"]["persona_layer_disabled"] is True
    selection = (configured_root / "config" / "installer" / "selection.ini").read_text(encoding="utf-8")
    assert "ActiveProfile=default" in selection
    assert "MemoryWriteThreshold=4" in selection
    assert "QdrantEnabled=true" in selection
    assert "PersonaLayerDisabled=true" in selection
    assert not list((configured_root / "config").glob("*.tmp"))
    assert all(
        (configured_root / "workspace-new" / name).is_dir()
        for name in ("Tagebuch", "Temp", "Trashcan")
    )


@pytest.mark.parametrize(
    "settings",
    (
        {},
        {
            "memory_write_threshold": 0,
            "persona_write_threshold": 3,
            "temperament_write_threshold": 2,
            "qdrant_enabled": False,
            "persona_layer_enabled": True,
        },
        {
            "memory_write_threshold": 2,
            "persona_write_threshold": 3,
            "temperament_write_threshold": 2,
            "qdrant_enabled": "true",
            "persona_layer_enabled": True,
        },
    ),
)
def test_settings_update_rejects_incomplete_or_ineffective_values(
    configuration_module: ModuleType,
    configured_root: Path,
    settings: dict[str, object],
) -> None:
    service = configuration_module.PlwcConfigurationService(configured_root, doctor_system_probes=False)

    with pytest.raises(configuration_module.ConfigurationError):
        service.update_settings(settings)


def test_workspace_update_synchronizes_installer_and_generated_client_files(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    selection = configured_root / "config" / "installer" / "selection.ini"
    bridge_root = configured_root / "app" / "bridge"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        "[PLwC]\n"
        f"AppPath={configured_root / 'app'}\n"
        f"BridgePath={bridge_root}\n"
        f"WorkspacePath={configured_root / 'workspace'}\n",
        encoding="utf-8",
    )
    codex = configured_root / "config" / "clients" / "codex" / "plwc-gateway.generated.toml"
    codex.parent.mkdir(parents=True)
    codex.write_text(
        '# Vom Setup geändert\n'
        'env = { "PLWC_WORKSPACE_ROOT" = "old", "PLWC_PROFILE_ROOT" = "profiles" }\n',
        encoding="cp1252",
    )
    odysseus = configured_root / "config" / "clients" / "odysseus" / "plwc-gateway.generated.json"
    odysseus.parent.mkdir(parents=True)
    odysseus.write_text(
        json.dumps(
            {
                "_comment": "Vom Setup geändert",
                "mcpServers": {"plwc-gateway": {"env": {"PLWC_WORKSPACE_ROOT": "old"}}},
            },
            ensure_ascii=False,
        ),
        encoding="cp1252",
    )
    bridge = bridge_root / "config" / "plwc.example.json"
    bridge.parent.mkdir(parents=True)
    bridge.write_text(
        json.dumps({"gateway": {"env": {"PLWC_WORKSPACE_ROOT": "old"}}}),
        encoding="utf-8",
    )
    service = configuration_module.PlwcConfigurationService(configured_root)
    new_workspace = configured_root / "relocated-workspace"

    _apply_workspace(service, new_workspace)

    assert f"WorkspacePath={new_workspace}" in selection.read_text(encoding="utf-8")
    assert "ActiveProfile=default" in selection.read_text(encoding="utf-8")
    assert "MemoryWriteThreshold=2" in selection.read_text(encoding="utf-8")
    assert str(new_workspace).replace("\\", "\\\\") in codex.read_text(encoding="utf-8")
    assert json.loads(odysseus.read_text(encoding="utf-8"))["mcpServers"]["plwc-gateway"]["env"][
        "PLWC_WORKSPACE_ROOT"
    ] == str(new_workspace)
    assert json.loads(bridge.read_text(encoding="utf-8"))["gateway"]["env"]["PLWC_WORKSPACE_ROOT"] == str(
        new_workspace
    )


def test_installer_sync_updates_paths_without_replacing_existing_runtime_choices(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    settings_path = configured_root / "config" / "gateway-settings.json"
    existing = json.loads(settings_path.read_text(encoding="utf-8"))
    existing["settings"]["active_profile_name"] = "Writer"
    existing["settings"]["memory_write_threshold"] = 9
    existing["settings"]["qdrant_enabled"] = True
    settings_path.write_text(json.dumps(existing), encoding="utf-8")
    service = configuration_module.PlwcConfigurationService(configured_root)
    new_workspace = configured_root / "setup-workspace"

    service.sync_installation(
        {
            "workspace_path": str(new_workspace),
            "profiles_path": str(configured_root / "profiles"),
            "active_profile_name": "default",
            "security_config": None,
            "memory_write_threshold": 2,
            "persona_write_threshold": 3,
            "temperament_write_threshold": 2,
            "qdrant_enabled": False,
            "persona_layer_enabled": True,
        }
    )

    updated = json.loads(settings_path.read_text(encoding="utf-8"))
    assert updated["updated_by"] == "plwc-windows-setup"
    assert updated["settings"]["workspace_path"] == str(new_workspace)
    assert updated["settings"]["active_profile_name"] == "Writer"
    assert updated["settings"]["memory_write_threshold"] == 9
    assert updated["settings"]["qdrant_enabled"] is True
    selection = (configured_root / "config" / "installer" / "selection.ini").read_text(encoding="utf-8")
    assert f"WorkspacePath={new_workspace}" in selection
    assert f"ProfilesPath={configured_root / 'profiles'}" in selection
    assert "ActiveProfile=Writer" in selection
    assert "MemoryWriteThreshold=9" in selection
    assert "PersonaWriteThreshold=3" in selection
    assert "QdrantEnabled=true" in selection
    assert "PersonaLayerDisabled=false" in selection


def test_workspace_update_uses_a_custom_installer_configuration_root(
    configuration_module: ModuleType,
    configured_root: Path,
    tmp_path: Path,
) -> None:
    custom_config = tmp_path / "custom-installer-config"
    selection = custom_config / "installer" / "selection.ini"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        "[PLwC]\n"
        f"AppPath={configured_root / 'app'}\n"
        f"BridgePath={configured_root / 'app' / 'bridge'}\n"
        f"WorkspacePath={configured_root / 'workspace'}\n",
        encoding="utf-8",
    )
    codex = custom_config / "clients" / "codex" / "plwc-gateway.generated.toml"
    codex.parent.mkdir(parents=True)
    codex.write_text(
        'env = { "PLWC_WORKSPACE_ROOT" = "old", "PLWC_PROFILE_ROOT" = "profiles" }\n',
        encoding="utf-8",
    )
    service = configuration_module.PlwcConfigurationService(
        configured_root,
        installer_config_root=custom_config,
    )
    new_workspace = configured_root / "custom-config-workspace"

    _apply_workspace(service, new_workspace)

    assert f"WorkspacePath={new_workspace}" in selection.read_text(encoding="utf-8")
    assert str(new_workspace).replace("\\", "\\\\") in codex.read_text(encoding="utf-8")


def test_profile_activation_uses_governor_plan_and_explicit_confirmation(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    service = configuration_module.PlwcConfigurationService(configured_root)

    plan = service.plan_profile_activation("Writer")

    assert plan["ok"] is True
    assert plan["valid"] is True
    assert plan["current_active_profile"] == "default"
    assert plan["requested_active_profile"] == "Writer"
    assert len(plan["plan_digest"]) == 64
    with pytest.raises(configuration_module.ConfigurationError, match="explicit confirmation"):
        service.apply_profile_activation("Writer", plan["plan_digest"], False)
    with pytest.raises(configuration_module.ConfigurationError, match="plan changed"):
        service.apply_profile_activation("Writer", "0" * 64, True)

    result = service.apply_profile_activation("Writer", plan["plan_digest"], True)

    assert result["state"]["runtime"]["active_profile_name"] == "Writer"
    state = json.loads((configured_root / "config" / "active_profile.json").read_text(encoding="utf-8"))
    assert state["active_profile_name"] == "Writer"


def test_empty_profile_is_visible_as_invalid_and_activation_stays_blocked(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    (configured_root / "profiles" / "FAUN").mkdir()
    service = configuration_module.PlwcConfigurationService(configured_root, language="de")

    snapshot = service.snapshot()
    plan = service.plan_profile_activation("FAUN")

    faun = next(profile for profile in snapshot["runtime"]["available_profiles"] if profile["name"] == "FAUN")
    assert faun["exists"] is True
    assert faun["valid"] is False
    assert faun["activatable"] is False
    assert faun["status"] == "missing_required_files"
    assert plan["ok"] is False
    assert plan["valid"] is False
    assert plan["reason"] == "Requested profile is missing required files."
    assert plan["missing_files"] == [
        "CORE.md",
        "TEMPERAMENT.md",
        "PERSONA.md",
        "memory.md",
        "reflection.md",
        "governance/config.yaml",
    ]


def test_business_rejection_preserves_structured_reason_instead_of_http_200_fallback() -> None:
    javascript = (CONFIGURATION_ROOT / "plwc-config.js").read_text(encoding="utf-8")

    assert "payload?.reason" in javascript
    assert "payload?.message" in javascript
    assert "payload?.validation_error" in javascript
    assert "payload?.missing_files" in javascript
    assert "allowBusinessRejection: true" in javascript
    assert 'throw new Error(payload.error || `HTTP ${response.status}`);' not in javascript


def test_profile_creation_uses_governor_onboarding_plan_and_activates_new_profile(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    service = configuration_module.PlwcConfigurationService(configured_root)
    answers = _onboarding_answers()

    plan = service.plan_profile_creation(answers)

    assert plan["ok"] is True
    assert plan["approved_for_apply"] is True
    assert plan["profile_name"] == "Researcher"
    assert plan["missing_required_fields"] == []
    assert plan["activation"]["will_be_active"] is True
    assert "PERSONA.md" in plan["target_files"]
    assert not (configured_root / "profiles" / "Researcher").exists()
    with pytest.raises(configuration_module.ConfigurationError, match="explicit confirmation"):
        service.apply_profile_creation(answers, plan["plan_digest"], False)
    changed_answers = {**answers, "tone": "Different after review"}
    with pytest.raises(configuration_module.ConfigurationError, match="plan changed"):
        service.apply_profile_creation(changed_answers, plan["plan_digest"], True)

    result = service.apply_profile_creation(answers, plan["plan_digest"], True)

    profile = configured_root / "profiles" / "Researcher"
    assert result["state"]["runtime"]["active_profile_name"] == "Researcher"
    assert all((profile / filename).is_file() for filename in (*PROFILE_FILES, "journal.md"))
    assert (profile / "governance" / "config.yaml").is_file()
    assert "Research and technical writing assistant" in (profile / "PERSONA.md").read_text(encoding="utf-8")


def test_profile_creation_rejects_unknown_fields_and_incomplete_onboarding(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    service = configuration_module.PlwcConfigurationService(configured_root)

    with pytest.raises(configuration_module.ConfigurationError, match="unsupported fields"):
        service.plan_profile_creation({**_onboarding_answers(), "unexpected": "value"})

    incomplete = _onboarding_answers()
    incomplete["memory_scope"] = ""
    plan = service.plan_profile_creation(incomplete)
    assert plan["ok"] is False
    assert plan["approved_for_apply"] is False
    assert plan["missing_required_fields"] == ["memory_scope"]
    assert not (configured_root / "profiles" / "Researcher").exists()


def test_optional_component_probes_report_docker_and_document_worker_versions(
    configuration_module: ModuleType,
) -> None:
    image_id = "sha256:" + "c" * 64

    def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "Docker version 29.3.1, build fixture\n", "")
        if args[1:] == ["version", "--format", "{{.Server.Version}}"]:
            return subprocess.CompletedProcess(args, 0, "29.3.1\n", "")
        if args[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(args, 0, image_id + "\n", "")
        raise AssertionError(f"Unexpected probe: {args!r}")

    docker, worker = configuration_module._docker_component_observations(
        "C:/Docker/docker.exe",
        installer_selected=True,
        runner=runner,
    )

    assert docker["present"] is True
    assert docker["semantic_version"] == "29.3.1"
    assert docker["postflight_verified"] is True
    assert docker["source"]["trust"] == "observed_local"
    assert worker["present"] is True
    assert worker["semantic_version"] == "0.1.0"
    assert worker["build_id"] == image_id
    assert worker["postflight_verified"] is True
    assert worker["source"]["trust"] == "observed_local"


def test_document_worker_probe_distinguishes_missing_image_from_unavailable_daemon(
    configuration_module: ModuleType,
) -> None:
    def missing_image_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "Docker version 29.3.1, build fixture\n", "")
        if args[1:] == ["version", "--format", "{{.Server.Version}}"]:
            return subprocess.CompletedProcess(args, 0, "29.3.1\n", "")
        return subprocess.CompletedProcess(args, 1, "", "No such image")

    _, missing_worker = configuration_module._docker_component_observations(
        "C:/Docker/docker.exe",
        installer_selected=True,
        runner=missing_image_runner,
    )

    def unavailable_daemon_runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        if args[1:] == ["--version"]:
            return subprocess.CompletedProcess(args, 0, "Docker version 29.3.1, build fixture\n", "")
        return subprocess.CompletedProcess(args, 1, "", "daemon unavailable")

    _, unknown_worker = configuration_module._docker_component_observations(
        "C:/Docker/docker.exe",
        installer_selected=True,
        runner=unavailable_daemon_runner,
    )

    assert missing_worker["present"] is False
    assert missing_worker["source"]["trust"] == "observed_local"
    assert unknown_worker["present"] is None
    assert unknown_worker["source"]["trust"] == "unavailable"


def test_qdrant_probe_reports_distribution_version_independent_of_feature_flag(
    configuration_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(configuration_module.importlib_metadata, "version", lambda name: "1.18.0")

    observation = configuration_module._python_distribution_observation("qdrant-client", enabled=False)

    assert observation["present"] is True
    assert observation["semantic_version"] == "1.18.0"
    assert observation["source"]["trust"] == "observed_local"
    assert "enabled=false" in observation["source"]["detail"]


def test_snapshot_exposes_actual_component_values_and_persisted_launcher_result(
    configuration_module: ModuleType,
    configured_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        configuration_module,
        "_docker_component_observations",
        lambda *_args, **_kwargs: (
            {
                "present": True,
                "semantic_version": "29.3.1",
                "postflight_verified": True,
                "source": configuration_module._observed_source("docker_cli", "fixture"),
            },
            {
                "present": True,
                "semantic_version": "0.1.0",
                "build_id": "sha256:" + "c" * 64,
                "postflight_verified": True,
                "source": configuration_module._observed_source("docker_image_inspect", "fixture"),
            },
        ),
    )
    monkeypatch.setattr(
        configuration_module,
        "_python_distribution_observation",
        lambda *_args, **_kwargs: {
            "present": True,
            "semantic_version": "1.18.0",
            "source": configuration_module._observed_source("python_distribution", "fixture"),
        },
    )
    app_root = configured_root / "app"
    gateway_root = app_root / "gateway"
    bridge_root = app_root / "bridge"
    bridge_entry = bridge_root / "bridge" / "dist" / "src" / "index.js"
    launcher = bridge_root / "native" / "bin" / "plwc-chat-bridge-launcher.exe"
    bridge_entry.parent.mkdir(parents=True)
    launcher.parent.mkdir(parents=True)
    bridge_entry.write_text("console.log('bridge');\n", encoding="utf-8")
    launcher.write_bytes(b"launcher-fixture")
    build_identity = {
        "schemaVersion": 1,
        "product": "PLwC Chat Bridge",
        "releaseVersion": "1.0.0",
        "buildId": "plwc-chat-bridge@1.0.0",
        "components": {
            "nodeBridge": "1.0.0",
            "browserExtension": "1.0.0",
            "nativeLauncher": "1.0.0",
        },
    }
    (bridge_root / "build-identity.json").write_text(json.dumps(build_identity), encoding="utf-8")
    selection = configured_root / "config" / "installer" / "selection.ini"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        "[PLwC]\n"
        f"AppPath={app_root}\n"
        f"GatewayPath={gateway_root}\n"
        f"BridgePath={bridge_root}\n"
        f"StatePath={configured_root / 'state'}\n"
        "[BuildIdentity]\n"
        "BuildId=plwc-windows-setup@1.0.0/installer-r26#sha256:" + "a" * 64 + "\n"
        "InstallerRevision=installer-r26\n"
        "SetupExeSha256=" + "a" * 64 + "\n",
        encoding="utf-8",
    )
    launcher_state = configured_root / "state" / "chat-bridge" / "launcher-last-result.json"
    launcher_state.parent.mkdir(parents=True)
    launcher_state.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "timestamp": "2026-09-02T12:00:00+00:00",
                "action": "command_line_start",
                "ok": True,
                "state": "started",
                "statusCode": "ready",
                "operationExitCode": 0,
                "bridgePath": str(bridge_root),
                "toolCount": 8,
                "logPath": str(configured_root / "logs" / "native-launcher.log"),
                "buildIdentity": build_identity,
            }
        ),
        encoding="utf-8",
    )
    extension_contact = configured_root / "state" / "chat-bridge" / "browser-extension-last-contact.json"
    extension_contact.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "packageVersion": "1.0.1",
                "extensionId": "feceodobnhefdbfgmbinkndhogpfkicb",
                "browserFamily": "chrome",
                "protocolVersion": "1.0.0",
                "reportedAt": datetime.now(timezone.utc).isoformat(),
                "receivedAt": datetime.now(timezone.utc).isoformat(),
                "toolCount": 8,
                "buildIdentity": build_identity,
            }
        ),
        encoding="utf-8",
    )
    service = configuration_module.PlwcConfigurationService(configured_root, gateway_root=gateway_root)

    snapshot = service.snapshot()
    components = {component["id"]: component for component in snapshot["component_inventory"]["components"]}

    assert components["windows_installer"]["installed"]["semantic_version"] == "1.0.0"
    assert components["windows_installer"]["installed"]["build_revision"] == "installer-r26"
    assert components["windows_installer"]["installed"]["sha256"] == "a" * 64
    assert components["gateway"]["status"] == "ready"
    assert components["gateway"]["installed"]["semantic_version"] == "1.0.0"
    assert components["node_bridge"]["installed"]["build_id"] == "plwc-chat-bridge@1.0.0"
    assert components["node_bridge"]["status"] == "ready"
    assert components["native_launcher"]["installed"]["sha256"]
    assert components["browser_extension"]["status"] == "ready"
    assert components["browser_extension"]["installed"]["semantic_version"] == "1.0.1"
    assert components["browser_extension"]["installed"]["protocol_version"] == "1.0.0"
    assert components["docker"]["status"] == "ready"
    assert components["docker"]["installed"]["semantic_version"] == "29.3.1"
    assert components["qdrant"]["status"] == "compatible"
    assert components["qdrant"]["installed"]["semantic_version"] == "1.18.0"
    assert components["document_worker"]["status"] == "ready"
    assert components["document_worker"]["installed"]["semantic_version"] == "0.1.0"
    assert components["document_worker"]["installed"]["build_id"] == "sha256:" + "c" * 64
    assert snapshot["launcher_last_result"]["statusCode"] == "ready"
    assert snapshot["launcher_last_result"]["state_file"] == str(launcher_state)
    assert snapshot["browser_extension_last_contact"]["extensionId"] == "feceodobnhefdbfgmbinkndhogpfkicb"
    assert snapshot["browser_extension_last_contact"]["stale"] is False


def test_configuration_doctor_diagnosis_plan_apply_and_idempotence(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    service = configuration_module.PlwcConfigurationService(
        configured_root,
        doctor_system_probes=False,
    )
    before = {
        path.relative_to(configured_root).as_posix(): (
            "directory" if path.is_dir() else path.read_bytes()
        )
        for path in configured_root.rglob("*")
    }

    diagnosis = service.run_doctor_diagnosis()

    assert diagnosis["read_only"] is True
    assert diagnosis["clu_diagnostic"]["doctor_mode"] == "clu"
    assert diagnosis["clu_diagnostic"]["doctor_scope"] == "general"
    assert not (configured_root / "logs" / "audit.jsonl").exists()
    assert before == {
        path.relative_to(configured_root).as_posix(): (
            "directory" if path.is_dir() else path.read_bytes()
        )
        for path in configured_root.rglob("*")
    }

    plan = service.plan_doctor_repair(diagnosis["snapshot_id"])
    assert plan["change_count"] == 3
    assert all(action["type"] == "ensure_directory" for action in plan["actions"])
    with pytest.raises(configuration_module.ConfigurationError, match="explicit confirmation"):
        service.apply_doctor_repair(plan["plan_id"], False)

    result = service.apply_doctor_repair(plan["plan_id"], True)
    assert result["ok"] is True
    assert result["result"] == "successful"
    assert all((configured_root / "workspace" / name).is_dir() for name in ("Tagebuch", "Temp", "Trashcan"))

    second_diagnosis = service.run_doctor_diagnosis()
    second_plan = service.plan_doctor_repair(second_diagnosis["snapshot_id"])
    assert second_plan["no_changes"] is True
    second_result = service.apply_doctor_repair(second_plan["plan_id"], True)
    assert second_result["result"] == "no_changes"
    assert second_result["changed"] is False


def test_native_launcher_persists_structured_last_result_atomically() -> None:
    source = (
        REPO_ROOT
        / "integrations"
        / "plwc-chat-bridge"
        / "native"
        / "launcher-host"
        / "Plwc.ChatBridge.NativeLauncher.cs"
    ).read_text(encoding="utf-8-sig")

    assert '"launcher-last-result.json"' in source
    for field in (
        "timestamp",
        "action",
        "statusCode",
        "operationExitCode",
        "bridgePath",
        "toolCount",
        "logPath",
        "buildIdentity",
    ):
        assert f'\\\"{field}\\\"' in source
    assert "File.Replace(temporary, LastResultPath, null)" in source
    assert '"browser-extension-last-contact.json"' in source
    assert "PersistBrowserContact" in source
    assert 'String.Equals(command, "record_contact"' in source
    assert 'String.Equals(command, "start"' in source
    assert "PersistBrowserContact(request, buildIdentity, out ignoredContactError)" in source
    assert "return StartWithMutex(german, buildIdentity);" in source


def _request(
    server,
    method: str,
    path: str,
    *,
    cookie: str | None = None,
    origin: str | None = None,
    body: dict[str, object] | None = None,
) -> tuple[int, dict[str, object] | None, dict[str, str]]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    headers = {"Host": f"127.0.0.1:{server.server_port}"}
    if cookie:
        headers["Cookie"] = cookie
    if origin:
        headers["Origin"] = origin
        headers["X-PLwC-Config"] = "1"
    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    connection.request(method, path, body=encoded, headers=headers)
    response = connection.getresponse()
    raw = response.read()
    response_headers = {key.lower(): value for key, value in response.getheaders()}
    payload = json.loads(raw) if raw and response_headers.get("content-type", "").startswith("application/json") else None
    connection.close()
    return response.status, payload, response_headers


def test_loopback_http_session_requires_bootstrap_cookie_and_same_origin_posts(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    docs = configured_root / "app" / "docs"
    docs.mkdir(parents=True)
    (docs / "getting-started-en.html").write_text("<!doctype html><title>Getting Started</title>", encoding="utf-8")
    (docs / "getting-started.css").write_text("body { color: black; }", encoding="utf-8")
    (configured_root / "profiles" / "FAUN").mkdir()
    service = configuration_module.PlwcConfigurationService(configured_root, doctor_system_probes=False)
    server = configuration_module.create_http_server(
        service,
        CONFIGURATION_ROOT,
        session_token="test-session-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload, _ = _request(server, "GET", "/api/state")
        assert status == 403
        assert payload == {"ok": False, "error": "This local PLwC configuration session is not authorized."}

        status, _, headers = _request(server, "GET", "/?token=test-session-token")
        assert status == 303
        assert headers["location"] == "/"
        assert "HttpOnly" in headers["set-cookie"]
        assert "SameSite=Strict" in headers["set-cookie"]
        cookie = headers["set-cookie"].split(";", 1)[0]

        status, payload, _ = _request(server, "GET", "/api/state", cookie=cookie)
        assert status == 200
        assert payload is not None and payload["ok"] is True

        status, diagnosis, _ = _request(
            server,
            "POST",
            "/api/doctor/diagnose",
            cookie=cookie,
            origin=server.origin,
            body={},
        )
        assert status == 200
        assert diagnosis is not None and diagnosis["read_only"] is True
        status, doctor_plan, _ = _request(
            server,
            "POST",
            "/api/doctor/plan",
            cookie=cookie,
            origin=server.origin,
            body={"snapshot_id": diagnosis["snapshot_id"]},
        )
        assert status == 200
        assert doctor_plan is not None and doctor_plan["confirmation_required"] is True

        status, rejected_plan, _ = _request(
            server,
            "POST",
            "/api/profile/plan",
            cookie=cookie,
            origin=server.origin,
            body={"profile_name": "FAUN"},
        )
        assert status == 200
        assert rejected_plan is not None and rejected_plan["ok"] is False
        assert rejected_plan["reason"] == "Requested profile is missing required files."
        assert rejected_plan["missing_files"] == [
            "CORE.md",
            "TEMPERAMENT.md",
            "PERSONA.md",
            "memory.md",
            "reflection.md",
            "governance/config.yaml",
        ]

        status, payload, headers = _request(server, "GET", "/getting-started", cookie=cookie)
        assert status == 200
        assert payload is None
        assert headers["content-type"] == "text/html; charset=utf-8"

        settings = {
            "settings": _editable_settings(
                memory_write_threshold=3,
                persona_write_threshold=4,
                temperament_write_threshold=5,
                qdrant_enabled=True,
            )
        }
        status, payload, _ = _request(
            server,
            "POST",
            "/api/settings",
            cookie=cookie,
            origin="http://example.invalid",
            body=settings,
        )
        assert status == 403
        assert payload is not None and payload["ok"] is False

        status, payload, _ = _request(
            server,
            "POST",
            "/api/settings",
            cookie=cookie,
            origin=server.origin,
            body=settings,
        )
        assert status == 200
        assert payload is not None and payload["settings"]["memory_write_threshold"] == 3

        workspace_path = str(configured_root / "workspace-http")
        status, plan, _ = _request(
            server,
            "POST",
            "/api/workspace/plan",
            cookie=cookie,
            origin=server.origin,
            body={"workspace_path": workspace_path},
        )
        assert status == 200
        assert plan is not None and plan["valid"] is True
        assert not Path(workspace_path).exists()
        status, applied, _ = _request(
            server,
            "POST",
            "/api/workspace/apply",
            cookie=cookie,
            origin=server.origin,
            body={"workspace_path": workspace_path, "plan_digest": plan["plan_digest"], "confirmed": True},
        )
        assert status == 200
        assert applied is not None and applied["state"]["runtime"]["workspace_path"] == workspace_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_loopback_update_endpoints_preserve_separate_confirmations(
    configuration_module: ModuleType,
    configured_root: Path,
) -> None:
    class FakeUpdateCenter:
        trusted_keys = {}

        def __init__(self) -> None:
            self.download_confirmations: list[bool] = []
            self.install_confirmations: list[bool] = []

        @staticmethod
        def snapshot() -> dict[str, object]:
            return {"state": "update_available", "integrity_verified": True}

        @staticmethod
        def check(*, force: bool = False) -> dict[str, object]:
            assert force is True
            return {"state": "update_available", "integrity_verified": True}

        @staticmethod
        def plan_download(artifact_id: str) -> dict[str, object]:
            assert artifact_id == "windows_installer"
            return {"plan_id": "plan-1", "confirmation_required": True}

        def download(self, plan_id: str, *, confirmed: bool) -> dict[str, object]:
            assert plan_id == "plan-1"
            self.download_confirmations.append(confirmed)
            if not confirmed:
                raise configuration_module.UpdateContractError("download confirmation required")
            return {"ok": True, "state": "download_verified", "integrity_verified": True}

        def install(self, plan_id: str, *, confirmed: bool) -> dict[str, object]:
            assert plan_id == "plan-1"
            self.install_confirmations.append(confirmed)
            if not confirmed:
                raise configuration_module.UpdateContractError("install confirmation required")
            return {"ok": True, "state": "installer_completed"}

    update_center = FakeUpdateCenter()
    service = configuration_module.PlwcConfigurationService(
        configured_root,
        doctor_system_probes=False,
        update_center=update_center,
    )
    server = configuration_module.create_http_server(
        service,
        CONFIGURATION_ROOT,
        session_token="update-session-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _, headers = _request(server, "GET", "/?token=update-session-token")
        assert status == 303
        cookie = headers["set-cookie"].split(";", 1)[0]

        for path, body in (
            ("/api/update/check", {}),
            ("/api/update/download/plan", {"artifact_id": "windows_installer"}),
        ):
            status, payload, _ = _request(
                server,
                "POST",
                path,
                cookie=cookie,
                origin=server.origin,
                body=body,
            )
            assert status == 200
            assert payload is not None

        for path in ("/api/update/download", "/api/update/install"):
            status, payload, _ = _request(
                server,
                "POST",
                path,
                cookie=cookie,
                origin=server.origin,
                body={"plan_id": "plan-1", "confirmed": False},
            )
            assert status == 400
            assert payload is not None and payload["ok"] is False

        status, downloaded, _ = _request(
            server,
            "POST",
            "/api/update/download",
            cookie=cookie,
            origin=server.origin,
            body={"plan_id": "plan-1", "confirmed": True},
        )
        assert status == 200
        assert downloaded is not None and downloaded["state"] == "download_verified"

        status, installed, _ = _request(
            server,
            "POST",
            "/api/update/install",
            cookie=cookie,
            origin=server.origin,
            body={"plan_id": "plan-1", "confirmed": True},
        )
        assert status == 200
        assert installed is not None and installed["state"] == "installer_completed"
        assert update_center.download_confirmations == [False, True]
        assert update_center.install_confirmations == [False, True]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_static_configuration_ui_is_bilingual_local_and_feature_complete() -> None:
    english = (CONFIGURATION_ROOT / "plwc-config-en.html").read_text(encoding="utf-8")
    german = (CONFIGURATION_ROOT / "plwc-config-de.html").read_text(encoding="utf-8")
    javascript = (CONFIGURATION_ROOT / "plwc-config.js").read_text(encoding="utf-8")
    styles = (CONFIGURATION_ROOT / "plwc-config.css").read_text(encoding="utf-8")
    guide_english = (GETTING_STARTED_ROOT / "getting-started-en.html").read_text(encoding="utf-8")
    guide_german = (GETTING_STARTED_ROOT / "getting-started-de.html").read_text(encoding="utf-8")
    combined = "\n".join((english, german, javascript, styles, guide_english, guide_german))

    for control in (
        'id="profile-select"',
        'id="workspace-input"',
        'id="memory-threshold"',
        'id="persona-threshold"',
        'id="temperament-threshold"',
        'id="persona-toggle"',
        'id="qdrant-toggle"',
        'id="new-profile-button"',
        'id="create-profile-dialog"',
        'id="new-profile-name"',
        'id="review-create-profile-button"',
        'id="create-profile-button"',
        'id="profile-details"',
        'id="review-workspace-button"',
        'id="workspace-dialog"',
        'id="component-table-body"',
        'id="launcher-result"',
        'id="browser-extension-contact"',
        'id="doctor-diagnose-button"',
        'id="doctor-plan-button"',
        'id="doctor-export-button"',
        'id="doctor-dialog"',
        'id="doctor-confirmation"',
        'id="doctor-apply-button"',
        'id="update-check-button"',
        'id="update-review-button"',
        'id="update-dialog"',
        'id="update-download-confirmation"',
        'id="update-download-button"',
        'id="update-install-confirmation"',
        'id="update-install-button"',
    ):
        assert control in english
        assert control in german
    assert "PLwC Configuration" in english
    assert "PLwC-Konfiguration" in german
    assert "Governor" in english and "Governor" in german
    assert 'href="/getting-started"' in english and 'href="/getting-started"' in german
    assert 'class="header-link" href="/"' in guide_english
    assert 'class="header-link" href="/"' in guide_german
    assert 'class="app-link"' not in guide_english and 'class="app-link"' not in guide_german
    assert "Create a new profile" in guide_english
    assert "Neues Profil anlegen" in guide_german
    assert english.count("formnovalidate") == 10
    assert german.count("formnovalidate") == 10
    assert "[hidden]" in styles
    assert 'typeof write === "object"' in javascript
    assert "http://" not in combined
    assert "https://" not in combined
    for endpoint in (
        "/api/state",
        "/api/settings",
        "/api/workspace/plan",
        "/api/workspace/apply",
        "/api/profile/plan",
        "/api/profile/apply",
        "/api/profile/create/plan",
        "/api/profile/create/apply",
        "/api/doctor/diagnose",
        "/api/doctor/plan",
        "/api/doctor/apply",
        "/api/update/check",
        "/api/update/download/plan",
        "/api/update/download",
        "/api/update/install",
    ):
        assert endpoint in javascript

    source = CONFIGURATION_SCRIPT.read_text(encoding="utf-8")
    assert '"/getting-started"' in source
    assert 'parser.add_argument("--start-page"' in source


def test_installed_script_bootstraps_the_selected_gateway_source_tree() -> None:
    source = CONFIGURATION_SCRIPT.read_text(encoding="utf-8")

    assert '"--gateway-root"' in source
    assert 'root.expanduser().resolve(strict=False) / "src"' in source
    assert 'source_root / "plwc_gateway" / "__init__.py"' in source
