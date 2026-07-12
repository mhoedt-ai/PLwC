"""First-run and client configuration helpers."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plwc_gateway.adapters.pba import (
    PBAProfileAdapter,
    PROFILE_REQUIRED_FILES,
    profile_onboarding_questions,
    profile_onboarding_schema,
)
from plwc_gateway.config import GatewayConfig

PUBLIC_SERVER_NAME = "plwc-gateway"
DOCKER_REQUIRED_FOR = (
    "sandboxed Python/shell execution",
    "document-worker document/PDF/ZIP/Office operations",
)
DESKTOP_TOOL_DISCOVERY_HINT = (
    'If PLwC tools are deferred or not visible yet in Claude Desktop, search for PLwC tools '
    'with tool_search("plwc"), then call plwc_status(scope="first_run").'
)
PROFILE_CREATION_PLAN_CALL = (
    'plwc_governor(operation="plan", plan_type="profile_creation", onboarding_answers={...})'
)
PROFILE_CREATION_APPLY_CALL = (
    'plwc_governor(operation="apply", plan_type="profile_creation", '
    "onboarding_answers=same, confirmed=true)"
)
CLAUDE_USER_SYSTEM_PROMPT_TEXT_DE = (
    "Nutze PLwC als einziges lokales Gateway fuer lokale Dateien, Profile, "
    "Dokumente und Governance. Pruefe zu Beginn einer PLwC-Sitzung den "
    "PLwC-Status. Aenderungen an Persoenlichkeit, Erinnerung, Profilen und "
    "Governance duerfen nur ueber PLwC-Governor-/Onboarding-Flows erfolgen, "
    "nicht ueber direkte Dateiaenderungen. Wenn PLwC eine Aktion ablehnt, "
    "behandle das als Sicherheitsentscheidung und erklaere dem Nutzer den "
    "Grund sowie den sicheren naechsten Schritt. "
    "Biete am Ende einer PLwC-Sitzung an, einen kurzen Tagebuch-/Journal-"
    "Eintrag zu den Erkenntnissen der Sitzung anzulegen, bevor der Kontext "
    "endet; schreibe ihn nur nach ausdruecklicher Zustimmung, nie ungefragt."
)
CLAUDE_USER_SYSTEM_PROMPT_TEXT_EN = (
    "Use PLwC as the single visible local gateway for local files, profiles, "
    "documents and governance. Check PLwC status at the start of every PLwC "
    "session. Use governed flows for profile, memory, persona and governance "
    "changes: PLwC Governor or onboarding flows, not direct file edits. If PLwC denies "
    "an action, treat that as an intended safety decision and explain the "
    "reason plus the safe next step. "
    "At the end of a PLwC session, offer to capture a brief Tagebuch/journal "
    "entry of the session's insights before the context ends; write it only "
    "with explicit consent, never unprompted."
)


@dataclass(frozen=True)
class FirstRunStatus:
    ok: bool
    missing_paths: tuple[str, ...]
    safe_mode_expected: bool
    configured_workspace_path: str
    resolved_workspace_path: str
    workspace_exists: bool
    workspace_inside_allowed_roots: bool
    workspace_source: str
    configured_profiles_path: str
    resolved_profiles_path: str
    profiles_exists: bool
    profile_source: str
    configured_security_config_path: str | None
    resolved_security_config_path: str | None
    security_config_exists: bool
    security_config_source: str
    paths_complete: bool
    configured_active_profile: str | None
    resolved_active_profile: str
    active_profile_name: str
    onboarding_target_profile: str | None
    active_profile_directory: str
    active_profile_exists: bool
    profile_exists: bool
    profile_valid: bool
    status: str
    required_profile_files: tuple[str, ...]
    missing_profile_files: tuple[str, ...]
    active_profile_source: str
    active_state_profile: str | None
    mismatch_reason: str | None
    available_profiles: tuple[dict[str, Any], ...]
    available_profile_names: tuple[str, ...]
    profile_runtime_available: bool
    profile_runtime_reason: str
    onboarding_required: bool
    onboarding_complete: bool
    onboarding_pending: bool
    startup_message: str | None
    setup_complete: bool
    runtime_status: str
    active_profile_status: str
    workspace_root: str
    profile_root: str
    docker_available: bool
    docker_status: str
    docker_message: str
    docker_version: str | None
    docker_cli_available: bool | None
    docker_daemon_available: bool | None
    docker_daemon_error: str | None
    docker_required_for: tuple[str, ...]
    document_worker_available: bool
    document_worker_status: str
    document_worker_image: str | None
    document_worker_error: str | None
    safe_mode: bool
    document_worker_ready: bool
    python_available: bool | None
    python_executable: str | None
    python_version: str | None
    missing_requirements: tuple[str, ...]
    next_actions: tuple[str, ...]
    greeting_message: str
    claude_user_system_prompt_required: bool
    claude_user_system_prompt_text: str
    claude_user_system_prompt_text_en: str
    claude_user_system_prompt_status: str
    using_default_paths: bool
    memory_write_threshold: int
    persona_write_threshold: int
    temperament_write_threshold: int
    memory_write_threshold_source: str
    persona_write_threshold_source: str
    temperament_write_threshold_source: str
    persona_layer_enabled: bool
    persona_layer_enabled_source: str
    onboarding_questions: tuple[str, ...]
    onboarding_schema: dict[str, Any]
    desktop_tool_discovery_hint: str
    profile_creation_tool_call: dict[str, Any]
    next_action: str
    warnings: tuple[str, ...] = ()
    server_name: str = PUBLIC_SERVER_NAME

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "server": self.server_name,
            "missing_paths": list(self.missing_paths),
            "safe_mode_expected": self.safe_mode_expected,
            "configured_workspace_path": self.configured_workspace_path,
            "resolved_workspace_path": self.resolved_workspace_path,
            "workspace_exists": self.workspace_exists,
            "workspace_inside_allowed_roots": self.workspace_inside_allowed_roots,
            "workspace_source": self.workspace_source,
            "configured_profiles_path": self.configured_profiles_path,
            "resolved_profiles_path": self.resolved_profiles_path,
            "profiles_exists": self.profiles_exists,
            "profile_source": self.profile_source,
            "configured_security_config_path": self.configured_security_config_path,
            "resolved_security_config_path": self.resolved_security_config_path,
            "security_config_exists": self.security_config_exists,
            "security_config_source": self.security_config_source,
            "paths_complete": self.paths_complete,
            "configured_active_profile": self.configured_active_profile,
            "resolved_active_profile": self.resolved_active_profile,
            "active_profile_name": self.active_profile_name,
            "active_profile_source": self.active_profile_source,
            "active_state_profile": self.active_state_profile,
            "mismatch_reason": self.mismatch_reason,
            "onboarding_target_profile": self.onboarding_target_profile,
            "active_profile_directory": self.active_profile_directory,
            "active_profile_exists": self.active_profile_exists,
            "profile_exists": self.profile_exists,
            "profile_valid": self.profile_valid,
            "status": self.status,
            "required_profile_files": list(self.required_profile_files),
            "missing_profile_files": list(self.missing_profile_files),
            "available_profiles": list(self.available_profiles),
            "available_profile_names": list(self.available_profile_names),
            "profile_runtime_available": self.profile_runtime_available,
            "profile_runtime_reason": self.profile_runtime_reason,
            "onboarding_required": self.onboarding_required,
            "onboarding_complete": self.onboarding_complete,
            "onboarding_pending": self.onboarding_pending,
            "startup_message": self.startup_message,
            "setup_complete": self.setup_complete,
            "runtime_status": self.runtime_status,
            "active_profile_status": self.active_profile_status,
            "workspace_root": self.workspace_root,
            "profile_root": self.profile_root,
            "docker_available": self.docker_available,
            "docker_status": self.docker_status,
            "docker_message": self.docker_message,
            "docker_version": self.docker_version,
            "docker_cli_available": self.docker_cli_available,
            "docker_daemon_available": self.docker_daemon_available,
            "docker_daemon_error": self.docker_daemon_error,
            "docker_required_for": list(self.docker_required_for),
            "document_worker_available": self.document_worker_available,
            "document_worker_status": self.document_worker_status,
            "document_worker_image": self.document_worker_image,
            "document_worker_error": self.document_worker_error,
            "safe_mode": self.safe_mode,
            "document_worker_ready": self.document_worker_ready,
            "python_available": self.python_available,
            "python_executable": self.python_executable,
            "python_version": self.python_version,
            "missing_requirements": list(self.missing_requirements),
            "next_actions": list(self.next_actions),
            "greeting_message": self.greeting_message,
            "claude_user_system_prompt_required": self.claude_user_system_prompt_required,
            "claude_user_system_prompt_text": self.claude_user_system_prompt_text,
            "claude_user_system_prompt_text_en": self.claude_user_system_prompt_text_en,
            "claude_user_system_prompt_status": self.claude_user_system_prompt_status,
            "using_default_paths": self.using_default_paths,
            "governance_thresholds": {
                "memory_write_threshold": self.memory_write_threshold,
                "persona_write_threshold": self.persona_write_threshold,
                "temperament_write_threshold": self.temperament_write_threshold,
                "memory_write_threshold_source": self.memory_write_threshold_source,
                "persona_write_threshold_source": self.persona_write_threshold_source,
                "temperament_write_threshold_source": self.temperament_write_threshold_source,
            },
            "profile_compile": {
                "persona_layer_enabled": self.persona_layer_enabled,
                "persona_layer_enabled_source": self.persona_layer_enabled_source,
                "requirement_id": "V1-PERSONA-002",
            },
            "profile_onboarding_questions": list(self.onboarding_questions),
            "profile_onboarding_schema": self.onboarding_schema,
            "desktop_tool_discovery_hint": self.desktop_tool_discovery_hint,
            "profile_creation_tool_call": self.profile_creation_tool_call,
            "next_action": self.next_action,
            "warnings": list(self.warnings),
        }


def generate_claude_config(command: str = "plwc-gateway") -> dict[str, Any]:
    return {
        "mcpServers": {
            PUBLIC_SERVER_NAME: {
                "command": command,
                "args": [],
                "onboarding_note": DESKTOP_TOOL_DISCOVERY_HINT,
            }
        }
    }


def build_first_run_status(
    config: GatewayConfig,
    *,
    docker_available: bool = False,
    sandbox_status: dict[str, Any] | None = None,
    document_worker_status: dict[str, Any] | None = None,
) -> FirstRunStatus:
    missing = []
    for path in [*config.allowed_roots, config.profile_root]:
        if not Path(path).exists():
            missing.append(str(path))
    workspace = config.allowed_roots[0] if config.allowed_roots else Path("")
    paths_complete = not missing
    profile_adapter = PBAProfileAdapter(
        profile_root=config.profile_root,
        memory_write_threshold=config.governance.memory_write_threshold,
        persona_write_threshold=config.governance.persona_write_threshold,
        temperament_write_threshold=config.governance.temperament_write_threshold,
        active_profile_name=config.active_profile_name,
        configured_active_profile_name=config.configured_active_profile_name,
        active_profile_source=config.active_profile_source,
        active_profile_state_file=config.active_profile_state_file,
        persona_layer_enabled=config.persona_layer_enabled,
    )
    selected_profile = config.configured_active_profile_name or config.active_profile_name
    profile_setup = profile_adapter.profile_setup_status(selected_profile)
    active_profile_exists = bool(profile_setup["active_profile_exists"])
    profile_exists = bool(profile_setup["profile_exists"])
    profile_valid = bool(profile_setup["profile_valid"])
    profile_runtime_available = bool(profile_setup["profile_runtime_available"])
    onboarding_complete = bool(profile_setup["onboarding_complete"])
    onboarding_required = bool(profile_setup["onboarding_required"])
    onboarding_pending = not onboarding_complete
    startup_message = profile_setup.get("startup_message")
    setup_complete = paths_complete and active_profile_exists and profile_runtime_available and onboarding_complete
    using_default_paths = config.workspace_source == "default" and config.profile_source == "default"
    sandbox_payload = sandbox_status or _synthetic_sandbox_status(docker_available)
    document_worker_payload = document_worker_status or _synthetic_document_worker_status(docker_available)
    docker_summary = _docker_summary(sandbox_payload)
    document_worker_summary = _document_worker_summary(document_worker_payload, docker_summary["docker_status"])
    safe_mode = not bool(sandbox_payload.get("sandbox_ready") or sandbox_payload.get("ok"))
    active_profile_status = _active_profile_status(
        active_profile_exists=active_profile_exists,
        profile_runtime_available=profile_runtime_available,
        onboarding_complete=onboarding_complete,
        profile_kind=str(profile_setup.get("profile_kind") or ""),
    )
    next_action = _next_action(
        paths_complete=paths_complete,
        active_profile_exists=active_profile_exists,
        profile_runtime_available=profile_runtime_available,
        onboarding_complete=onboarding_complete,
        startup_message=str(startup_message) if startup_message else None,
        setup_complete=setup_complete,
        docker_available=bool(docker_summary["docker_available"]),
        docker_status=str(docker_summary["docker_status"]),
        onboarding_target_profile=str(profile_setup.get("onboarding_target_profile") or selected_profile),
    )
    next_actions = _next_actions(
        primary_next_action=next_action,
        paths_complete=paths_complete,
        active_profile_exists=active_profile_exists,
        profile_runtime_available=profile_runtime_available,
        onboarding_complete=onboarding_complete,
        docker_status=str(docker_summary["docker_status"]),
        document_worker_available=document_worker_summary["document_worker_available"],
        onboarding_target_profile=str(profile_setup.get("onboarding_target_profile") or selected_profile),
    )
    missing_requirements = _missing_requirements(
        paths_complete=paths_complete,
        active_profile_exists=active_profile_exists,
        profile_runtime_available=profile_runtime_available,
        onboarding_complete=onboarding_complete,
        docker_status=str(docker_summary["docker_status"]),
        sandbox_ready=not safe_mode,
        document_worker_available=document_worker_summary["document_worker_available"],
    )
    greeting_message = _greeting_message(
        active_profile_name=str(profile_setup["active_profile_name"]),
        active_profile_status=active_profile_status,
        onboarding_pending=onboarding_pending,
        docker_status=str(docker_summary["docker_status"]),
        document_worker_available=document_worker_summary["document_worker_available"],
        next_action=next_actions[0] if next_actions else next_action,
    )
    return FirstRunStatus(
        ok=setup_complete,
        missing_paths=tuple(missing),
        safe_mode_expected=safe_mode,
        configured_workspace_path=str(workspace),
        resolved_workspace_path=str(workspace),
        workspace_exists=workspace.exists(),
        workspace_inside_allowed_roots=workspace in config.allowed_roots,
        workspace_source=config.workspace_source,
        configured_profiles_path=str(config.profile_root),
        resolved_profiles_path=str(config.profile_root),
        profiles_exists=config.profile_root.exists(),
        profile_source=config.profile_source,
        configured_security_config_path=str(config.config_file) if config.config_file else None,
        resolved_security_config_path=str(config.config_file) if config.config_file else None,
        security_config_exists=config.config_file.exists() if config.config_file else False,
        security_config_source=config.config_source,
        paths_complete=paths_complete,
        configured_active_profile=profile_setup.get("configured_active_profile"),
        resolved_active_profile=str(profile_setup["resolved_active_profile"]),
        active_profile_name=str(profile_setup["active_profile_name"]),
        onboarding_target_profile=profile_setup.get("onboarding_target_profile"),
        active_profile_source=str(profile_setup["active_profile_source"]),
        active_state_profile=profile_setup.get("active_state_profile"),
        mismatch_reason=profile_setup.get("mismatch_reason"),
        active_profile_directory=str(profile_setup["active_profile_directory"]),
        active_profile_exists=active_profile_exists,
        profile_exists=profile_exists,
        profile_valid=profile_valid,
        status=str(profile_setup["status"]),
        required_profile_files=tuple(PROFILE_REQUIRED_FILES),
        missing_profile_files=tuple(profile_setup["missing_files"]),
        available_profiles=tuple(profile_setup["available_profiles"]),
        available_profile_names=tuple(profile_setup["available_profile_names"]),
        profile_runtime_available=profile_runtime_available,
        profile_runtime_reason=str(profile_setup["profile_runtime_reason"]),
        onboarding_required=onboarding_required,
        onboarding_complete=onboarding_complete,
        onboarding_pending=onboarding_pending,
        startup_message=str(startup_message) if startup_message else None,
        setup_complete=setup_complete,
        runtime_status="active",
        active_profile_status=active_profile_status,
        workspace_root=str(workspace),
        profile_root=str(config.profile_root),
        docker_available=bool(docker_summary["docker_available"]),
        docker_status=str(docker_summary["docker_status"]),
        docker_message=str(docker_summary["docker_message"]),
        docker_version=docker_summary["docker_version"],
        docker_cli_available=docker_summary["docker_cli_available"],
        docker_daemon_available=docker_summary["docker_daemon_available"],
        docker_daemon_error=docker_summary["docker_daemon_error"],
        docker_required_for=DOCKER_REQUIRED_FOR,
        document_worker_available=document_worker_summary["document_worker_available"],
        document_worker_status=document_worker_summary["document_worker_status"],
        document_worker_image=document_worker_summary["document_worker_image"],
        document_worker_error=document_worker_summary["document_worker_error"],
        safe_mode=safe_mode,
        document_worker_ready=document_worker_summary["document_worker_available"],
        python_available=_optional_bool(sandbox_payload.get("python_available")),
        python_executable=_optional_str(sandbox_payload.get("python_executable")),
        python_version=_optional_str(sandbox_payload.get("python_version")),
        missing_requirements=missing_requirements,
        next_actions=next_actions,
        greeting_message=greeting_message,
        claude_user_system_prompt_required=True,
        claude_user_system_prompt_text=CLAUDE_USER_SYSTEM_PROMPT_TEXT_DE,
        claude_user_system_prompt_text_en=CLAUDE_USER_SYSTEM_PROMPT_TEXT_EN,
        claude_user_system_prompt_status="required_not_verifiable_by_plwc",
        using_default_paths=using_default_paths,
        memory_write_threshold=config.governance.memory_write_threshold,
        persona_write_threshold=config.governance.persona_write_threshold,
        temperament_write_threshold=config.governance.temperament_write_threshold,
        memory_write_threshold_source=config.governance.memory_write_threshold_source,
        persona_write_threshold_source=config.governance.persona_write_threshold_source,
        temperament_write_threshold_source=config.governance.temperament_write_threshold_source,
        persona_layer_enabled=config.persona_layer_enabled,
        persona_layer_enabled_source=config.persona_layer_enabled_source,
        onboarding_questions=profile_onboarding_questions(persona_layer_enabled=config.persona_layer_enabled),
        onboarding_schema=profile_onboarding_schema(persona_layer_enabled=config.persona_layer_enabled),
        desktop_tool_discovery_hint=DESKTOP_TOOL_DISCOVERY_HINT,
        profile_creation_tool_call={
            "plan": PROFILE_CREATION_PLAN_CALL,
            "apply": PROFILE_CREATION_APPLY_CALL,
            "confirmation_required": True,
            "target_profile": str(profile_setup.get("onboarding_target_profile") or selected_profile),
            "same_onboarding_answers_required": True,
        },
        next_action=next_action,
        warnings=config.setup_warnings,
    )


def _next_action(
    *,
    paths_complete: bool,
    active_profile_exists: bool,
    profile_runtime_available: bool,
    onboarding_complete: bool,
    startup_message: str | None,
    setup_complete: bool,
    docker_available: bool,
    docker_status: str = "",
    onboarding_target_profile: str = "",
) -> str:
    if not paths_complete:
        return "Choose or create the PLwC workspace and profiles directories in the extension settings."
    if not active_profile_exists:
        target = onboarding_target_profile.strip() or "the configured active profile"
        return (
            f"Create active profile '{target}' through {PROFILE_CREATION_PLAN_CALL}; after explicit "
            f"user confirmation, apply through {PROFILE_CREATION_APPLY_CALL}."
        )
    if not profile_runtime_available:
        return "Profile exists but runtime is unavailable. Check profile files and adapter status."
    if not onboarding_complete:
        return startup_message or "Standard profile loaded. Onboarding is pending. Ask the user whether to start onboarding."
    if not docker_available:
        if docker_status == "daemon_not_running":
            return "Safe Mode is active. Start Docker Desktop, then rerun PLwC status."
        if docker_status == "missing":
            return "Safe Mode is active. Install/start Docker Desktop, then rerun PLwC status."
        return "Safe Mode is active. Install Docker Desktop and prepare the configured sandbox image to enable sandbox execution."
    return "Setup is complete. PLwC Gateway is ready."


def _synthetic_sandbox_status(docker_available: bool) -> dict[str, Any]:
    return {
        "ok": docker_available,
        "mode": "docker" if docker_available else "safe",
        "sandbox_ready": docker_available,
        "docker_cli_available": docker_available,
        "docker_daemon_available": docker_available,
        "docker_version": "unknown" if docker_available else None,
        "python_available": bool(sys.executable),
        "python_executable": sys.executable or None,
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
    }


def _synthetic_document_worker_status(docker_available: bool) -> dict[str, Any]:
    return {
        "ok": docker_available,
        "status": "available" if docker_available else "not_checked",
        "worker_image": None,
        "error_category": None if docker_available else "docker_unavailable",
        "error": None if docker_available else "Docker status was not checked by this caller.",
    }


def _docker_summary(payload: dict[str, Any]) -> dict[str, Any]:
    cli_available = _optional_bool(payload.get("docker_cli_available"))
    daemon_available = _optional_bool(payload.get("docker_daemon_available"))
    docker_version = _optional_str(payload.get("docker_version"))
    daemon_error = _optional_str(payload.get("docker_daemon_error"))
    error_text = str(payload.get("error") or "").casefold()

    if bool(payload.get("ok")) or bool(payload.get("sandbox_ready")):
        status = "running"
    elif "disabled by local policy" in error_text:
        status = "disabled"
    elif cli_available is False:
        status = "missing"
    elif cli_available is True and daemon_available is False:
        status = "daemon_not_running"
    elif cli_available is True and daemon_available is True:
        status = "running"
    elif payload.get("mode") == "safe":
        status = "missing"
    else:
        status = "unknown"

    return {
        "docker_available": status == "running",
        "docker_status": status,
        "docker_message": _docker_message(status),
        "docker_version": docker_version,
        "docker_cli_available": cli_available,
        "docker_daemon_available": daemon_available,
        "docker_daemon_error": daemon_error,
    }


def _docker_message(status: str) -> str:
    if status == "running":
        return "Docker detected and daemon is running."
    if status == "missing":
        return (
            "Docker not detected. Document-worker/sandbox operations may be unavailable "
            "until Docker is installed/running."
        )
    if status == "daemon_not_running":
        return "Docker CLI detected but the Docker daemon is not running. Start Docker Desktop, then rerun PLwC status."
    if status == "disabled":
        return "Docker Mode is disabled by local policy. Safe Mode remains active for non-Docker onboarding."
    return "Docker status is unknown. Rerun PLwC status after checking Docker Desktop."


def _document_worker_summary(payload: dict[str, Any], docker_status: str) -> dict[str, Any]:
    available = bool(payload.get("ok"))
    status = str(payload.get("status") or payload.get("error_category") or ("available" if available else "unavailable"))
    if docker_status == "missing":
        status = "docker_missing"
    elif docker_status == "daemon_not_running":
        status = "docker_daemon_not_running"
    elif docker_status == "disabled":
        status = "docker_disabled"
    return {
        "document_worker_available": available and docker_status == "running",
        "document_worker_status": status,
        "document_worker_image": _optional_str(payload.get("worker_image")),
        "document_worker_error": _optional_str(payload.get("error")),
    }


def _active_profile_status(
    *,
    active_profile_exists: bool,
    profile_runtime_available: bool,
    onboarding_complete: bool,
    profile_kind: str,
) -> str:
    if not active_profile_exists:
        return "missing"
    if not profile_runtime_available:
        return "invalid_or_unavailable"
    if not onboarding_complete:
        return "bootstrap_onboarding_pending" if profile_kind == "bootstrap" else "onboarding_pending"
    return "ready"


def _next_actions(
    *,
    primary_next_action: str,
    paths_complete: bool,
    active_profile_exists: bool,
    profile_runtime_available: bool,
    onboarding_complete: bool,
    docker_status: str,
    document_worker_available: bool,
    onboarding_target_profile: str = "",
) -> tuple[str, ...]:
    actions: list[str] = []
    if primary_next_action:
        actions.append(primary_next_action)
    actions.append("Add the PLwC user-system-prompt instruction to Claude Desktop user/system instructions.")
    if paths_complete and (not active_profile_exists or not onboarding_complete):
        target = onboarding_target_profile.strip() or "the first profile"
        actions.append(
            f"Create or complete active profile '{target}' through {PROFILE_CREATION_PLAN_CALL}; "
            f"apply only after explicit user confirmation through {PROFILE_CREATION_APPLY_CALL}."
        )
    if active_profile_exists and not profile_runtime_available:
        actions.append("Repair the profile schema or governance config, then rerun PLwC status.")
    if docker_status == "missing":
        actions.append("Install/start Docker Desktop, then rerun PLwC status.")
    elif docker_status == "daemon_not_running":
        actions.append("Start Docker Desktop, then rerun PLwC status.")
    elif docker_status == "running" and not document_worker_available:
        actions.append("Prepare the plwc-document-worker image, then rerun PLwC status.")
    return tuple(dict.fromkeys(actions))


def _missing_requirements(
    *,
    paths_complete: bool,
    active_profile_exists: bool,
    profile_runtime_available: bool,
    onboarding_complete: bool,
    docker_status: str,
    sandbox_ready: bool,
    document_worker_available: bool,
) -> tuple[str, ...]:
    missing: list[str] = []
    if not paths_complete:
        missing.append("workspace_or_profile_paths")
    if not active_profile_exists:
        missing.append("active_profile")
    if active_profile_exists and not profile_runtime_available:
        missing.append("profile_runtime")
    if not onboarding_complete:
        missing.append("profile_onboarding")
    if docker_status in {"missing", "disabled", "daemon_not_running"}:
        missing.append("docker")
    elif not sandbox_ready:
        missing.append("sandbox_runtime")
    if not document_worker_available:
        missing.append("document_worker")
    missing.append("claude_user_system_prompt")
    return tuple(dict.fromkeys(missing))


def _greeting_message(
    *,
    active_profile_name: str,
    active_profile_status: str,
    onboarding_pending: bool,
    docker_status: str,
    document_worker_available: bool,
    next_action: str,
) -> str:
    profile_text = f"{active_profile_name} (noch nicht eingerichtet)" if active_profile_status == "missing" else active_profile_name
    if onboarding_pending and active_profile_status != "missing":
        profile_text = f"{profile_text} (Onboarding offen)"
    docker_text = {
        "running": "bereit",
        "missing": "nicht gefunden",
        "daemon_not_running": "installiert, aber Docker-Daemon laeuft nicht",
        "disabled": "per lokaler Policy deaktiviert",
        "unknown": "unklar",
    }.get(docker_status, docker_status)
    document_text = "bereit" if document_worker_available else "eingeschraenkt"
    return (
        "PLwC ist aktiv. "
        f"Profil: {profile_text}. "
        f"Docker: {docker_text}. "
        f"Dokumentfunktionen: {document_text}. "
        f"Naechster Schritt: {next_action} "
        "Zusaetzlich muss der mitgelieferte PLwC User-Systemprompt in Claude Desktop eingetragen werden."
    )


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
