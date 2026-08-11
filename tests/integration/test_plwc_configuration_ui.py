from __future__ import annotations

import http.client
import importlib.util
import json
import threading
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
def configuration_module() -> ModuleType:
    return _load_configuration_module()


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
    after = service.update_settings(
        {
            "memory_write_threshold": 4,
            "persona_write_threshold": 5,
            "temperament_write_threshold": 6,
            "qdrant_enabled": True,
            "persona_layer_enabled": False,
        }
    )

    assert before["runtime"]["active_profile_name"] == "default"
    assert before["runtime"]["available_profiles"] == ["default", "Writer"]
    assert after["settings"]["memory_write_threshold"] == 4
    assert after["settings"]["qdrant_enabled"] is True
    assert after["settings"]["persona_layer_enabled"] is False
    payload = json.loads((configured_root / "config" / "gateway-settings.json").read_text(encoding="utf-8"))
    assert payload["updated_by"] == "plwc-local-configuration"
    assert payload["settings"]["workspace_path"] == str(configured_root / "workspace")
    assert payload["settings"]["active_profile_name"] == "default"
    assert payload["settings"]["persona_layer_disabled"] is True
    assert not list((configured_root / "config").glob("*.tmp"))


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
    service = configuration_module.PlwcConfigurationService(configured_root)

    with pytest.raises(configuration_module.ConfigurationError):
        service.update_settings(settings)


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
    service = configuration_module.PlwcConfigurationService(configured_root)
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

        status, payload, headers = _request(server, "GET", "/getting-started", cookie=cookie)
        assert status == 200
        assert payload is None
        assert headers["content-type"] == "text/html; charset=utf-8"

        settings = {
            "settings": {
                "memory_write_threshold": 3,
                "persona_write_threshold": 4,
                "temperament_write_threshold": 5,
                "qdrant_enabled": True,
                "persona_layer_enabled": True,
            }
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
    assert english.count("formnovalidate") == 5
    assert german.count("formnovalidate") == 5
    assert "[hidden]" in styles
    assert 'typeof write === "object"' in javascript
    assert "http://" not in combined
    assert "https://" not in combined
    for endpoint in (
        "/api/state",
        "/api/settings",
        "/api/profile/plan",
        "/api/profile/apply",
        "/api/profile/create/plan",
        "/api/profile/create/apply",
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
