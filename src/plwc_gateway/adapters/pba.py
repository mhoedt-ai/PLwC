"""Governed PLfC / PBA profile adapter."""

from __future__ import annotations

import contextvars
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import unicodedata
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from plwc_gateway.policy import (
    IntentAction,
    PolicyDecision,
    PolicyIntent,
    execute_with_policy,
)

RuntimeCallable = Callable[..., dict[str, Any]]
DEFAULT_MEMORY_WRITE_THRESHOLD = 2
DEFAULT_PERSONA_WRITE_THRESHOLD = 3
DEFAULT_TEMPERAMENT_WRITE_THRESHOLD = 2
# RC8-FEAT-001: age heuristic for the list_retirable history_only flag.
DEFAULT_RETIREMENT_AGE_THRESHOLD_DAYS = 90
# RC12-RETIRE-002: Jaccard threshold for the list_retirable near_duplicate flag
# (catches near-dupes the exact-normalized `duplicate` check misses). Configurable
# via governance/config.yaml ``near_duplicate_similarity_threshold``.
DEFAULT_NEAR_DUPLICATE_SIMILARITY_THRESHOLD = 0.85
RC14_RETIREMENT_REQUIREMENT_ID = "RC14-RETIRE-001"
# RC12-INNER-001: similarity threshold above which a scan_tagebuch cluster is
# flagged as possibly redundant with an existing ACTIVE entry (memory.md /
# TEMPERAMENT.md). Configurable via governance/config.yaml ``inner_redundancy_threshold``.
DEFAULT_INNER_REDUNDANCY_THRESHOLD = 0.85
PBA_MEMORY_THRESHOLD_ENV_VAR = "PBA_MEMORY_MIN_SESSIONS"
PBA_PERSONA_THRESHOLD_ENV_VAR = "PBA_PERSONA_MIN_SESSIONS"
PBA_TEMPERAMENT_THRESHOLD_ENV_VAR = "PBA_TEMPERAMENT_MIN_SESSIONS"
PBA_MEMORY_THRESHOLD_SOURCE_ENV_VAR = "PLWC_MEMORY_WRITE_THRESHOLD_SOURCE"
PBA_PERSONA_THRESHOLD_SOURCE_ENV_VAR = "PLWC_PERSONA_WRITE_THRESHOLD_SOURCE"
PBA_TEMPERAMENT_THRESHOLD_SOURCE_ENV_VAR = "PLWC_TEMPERAMENT_WRITE_THRESHOLD_SOURCE"

PROFILE_REQUIRED_FILES = (
    "CORE.md",
    "TEMPERAMENT.md",
    "PERSONA.md",
    "memory.md",
    "reflection.md",
    "governance/config.yaml",
)
PROFILE_TEMPLATE_FILES = (
    *PROFILE_REQUIRED_FILES,
    "journal.md",
)
PBA2_PERSONALITY_LAYER_FILES = ("CORE.md", "TEMPERAMENT.md", "PERSONA.md", "memory.md")
PBA2_NON_COMPILED_PROFILE_FILES = ("reflection.md", "journal.md", "governance/config.yaml")
# RC8-FEAT-001: files whose entries may be retired. CORE.md is deliberately
# absent — it stays non_target and can never be retired.
RETIREMENT_TARGET_FILES = ("memory.md", "PERSONA.md", "TEMPERAMENT.md", "reflection.md")
MEMORY_RETIREMENT_PLAN_TYPE = "memory_retirement"
PBA2_STATE_FILE = "STATE.md"
PROFILE_OPTIONAL_FILES = ("journal.md", PBA2_STATE_FILE, "CONSCIENCE.md")
PBA2_ALLOWED_CONDENSATION_TARGETS = frozenset({"memory.md", "PERSONA.md"})
PBA2_IMPORT_REQUIRED_FILES = (
    "CORE.md",
    "TEMPERAMENT.md",
    "PERSONA.md",
    "memory.md",
    "reflection.md",
)
PBA2_IMPORT_OPTIONAL_FILES = (
    "journal.md",
    "STATE.md",
)
PBA2_IMPORT_ALLOWED_FILES = (
    *PBA2_IMPORT_REQUIRED_FILES,
    *PBA2_IMPORT_OPTIONAL_FILES,
)
MAX_PROFILE_IMPORT_FILE_BYTES = 1_000_000
# RC12-INNER-002: marker for the persona's inner-perspective ("soft truth") entries that
# live in PERSONA.md, capped at MAX_ACTIVE_INNER_TRUTHS active at once.
INNER_PERSPECTIVE_MARKER = "Innenperspektive"
MAX_ACTIVE_INNER_TRUTHS = 3
PBA2_REFLECTION_MARKERS = ("Beobachtung", "Hypothese", "Wunsch", "Sorge", "Muster", INNER_PERSPECTIVE_MARKER)
REFLECTION_MARKER_RECOMMENDED_VALUES = {
    "observation": "Beobachtung",
    "hypothesis": "Hypothese",
    "wish": "Wunsch",
    "concern": "Sorge",
    "pattern": "Muster",
    "inner_perspective": INNER_PERSPECTIVE_MARKER,
}
# English aliases for the canonical German markers. Input may use either; the
# stored marker is always the canonical German value so journal.md / memory.md
# stay consistent. (RC3-UX-005, RC18-ALIAS-001)
REFLECTION_MARKER_SYNONYMS = {
    **REFLECTION_MARKER_RECOMMENDED_VALUES,
    "note": "Beobachtung",
    "assumption": "Hypothese",
    "desire": "Wunsch",
    "request": "Wunsch",
    "risk": "Sorge",
    "worry": "Sorge",
    "recurring_pattern": "Muster",
    "recurring pattern": "Muster",
    "behavior_pattern": "Muster",
    "behavior pattern": "Muster",
    "inner perspective": INNER_PERSPECTIVE_MARKER,
    "inner-perspective": INNER_PERSPECTIVE_MARKER,
    "inner_truth": INNER_PERSPECTIVE_MARKER,
    "inner truth": INNER_PERSPECTIVE_MARKER,
    "inner-truth": INNER_PERSPECTIVE_MARKER,
}
PBA2_REFLECTION_TRUST_LEVELS = ("niedrig", "mittel", "hoch")
REFLECTION_TRUST_RECOMMENDED_VALUES = {
    "low": "niedrig",
    "medium": "mittel",
    "high": "hoch",
}
CONFIDENCE_TO_PBA2_TRUST = {
    **REFLECTION_TRUST_RECOMMENDED_VALUES,
    "weak": "niedrig",
    "moderate": "mittel",
    "strong": "hoch",
}
PBA2_PROMOTION_PLAN_TYPES = frozenset({"memory_promotion", "persona_promotion", "temperament_promotion"})
PBA2_JOURNAL_SCHEMA_VERSION = "1.0"
NON_BEHAVIORAL_MEMORY_MARKERS = frozenset({"wunsch", "sorge"})
EXPLICIT_MEMORY_CLASSIFICATIONS = frozenset(
    {
        "explicit_user_decision",
        "scope_boundary",
        "security_requirement",
        "direct_user_instruction",
    }
)
EXPLICIT_PERSONA_CLASSIFICATIONS = frozenset(
    {
        "explicit_persona_instruction",
        "style_preference",
        "interaction_preference",
        "project_working_style",
        "safety_behavior_preference",
    }
)
EXPLICIT_TEMPERAMENT_CLASSIFICATIONS = frozenset(
    {
        "temperament_trait",
        "collaboration_tendency",
        "tone_shift",
        "working_style",
    }
)
EVIDENCE_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
PBA2_GOVERNOR_PROMOTION_REQUIREMENTS = (
    "FR-005",
    "FR-PBA2-GOV-001",
    "FR-PBA2-GOV-002",
    "FR-PBA2-GOV-003",
    "FR-PBA2-GOV-004",
    "FR-PBA2-GOV-005",
    "FR-PBA2-GOV-006",
    "FR-PBA2-GOV-007",
    "FR-PBA2-GOV-008",
    "SR-010",
)
PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS = (
    "FR-005",
    "FR-PBA2-REL-001",
    "FR-PBA2-REL-002",
    "FR-PBA2-REL-003",
    "FR-PBA2-REL-004",
    "FR-PBA2-REL-005",
    "FR-PBA2-REL-006",
    "FR-PBA2-REL-007",
    "FR-PBA2-REL-008",
    "FR-PBA2-REL-009",
    "FR-PBA2-REL-010",
    "FR-PBA2-GATE-003",
    "FR-PBA2-GATE-004",
    "FR-PBA2-GATE-005",
    "FR-PBA2-FINAL-001",
    "FR-PBA2-FINAL-002",
    "FR-PBA2-FINAL-003",
    "SR-010",
)
GOVERNOR_LIFECYCLE_STATES = (
    "candidate",
    "planned",
    "applied",
    "rejected",
    "no_op",
    "review_required",
    "stale",
    "failed",
    "rolled_back",
)
REFLECTION_CONDENSATION_PLAN_TYPE = "reflection_condensation"
GOVERNOR_JOURNAL_EVENT_TYPE = "governor_apply"
# RC8-JOURNAL-001: compiled_layer_chars tracking event per plwc_profile compile.
COMPILE_JOURNAL_EVENT_TYPE = "profile_compile"
PENDING_PLAN_SCHEMA_VERSION = "1.0"
PENDING_PLAN_ID_RE = re.compile(r"^[0-9a-f]{16,64}$")
PROFILE_CREATION_PLAN_TYPE = "profile_creation"
PROFILE_CREATION_PLAN_TYPES = frozenset(
    {
        PROFILE_CREATION_PLAN_TYPE,
        "create_profile",
        "onboarding_profile_creation",
    }
)
REFLECTION_MEMORY_PROMOTION_PLAN_TYPE = "reflection_memory_promotion"
AUTOMATIC_REFLECTION_MEMORY_MODE = "automatic_reflection_memory"
REFLECTION_MEMORY_PROMOTION_PLAN_TYPES = frozenset(
    {REFLECTION_MEMORY_PROMOTION_PLAN_TYPE, AUTOMATIC_REFLECTION_MEMORY_MODE}
)
PROFILE_ONBOARDING_QUESTIONS = (
    "Profile name",
    "Intended role/use case of the profile",
    "Preferred name",
    "Preferred form of address",
    "Preferred tone",
    "Preferred working style",
    "How strict the assistant should be",
    "What may be stored in memory",
    "What must never be changed without confirmation",
    "Main project/work context if any",
    "Language preference",
)
PROFILE_ONBOARDING_FIELDS = (
    ("profile_name", "Profile name"),
    ("role_use_case", "Intended role/use case of the profile"),
    ("preferred_name", "Preferred name"),
    ("form_of_address", "Preferred form of address"),
    ("tone", "Preferred tone"),
    ("working_style", "Preferred working style"),
    ("strictness", "How strict the assistant should be"),
    ("memory_scope", "What may be stored in memory"),
    ("confirmation_boundaries", "What must never be changed without confirmation"),
    ("project_context", "Main project/work context if any"),
    ("language_preference", "Language preference"),
)
PROFILE_ONBOARDING_OPTIONAL_FIELDS = (
    ("special_instructions", "Special instructions"),
)
PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES = tuple(field for field, _question in PROFILE_ONBOARDING_FIELDS)
PROFILE_ONBOARDING_OPTIONAL_FIELD_NAMES = tuple(field for field, _question in PROFILE_ONBOARDING_OPTIONAL_FIELDS)
PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES = (
    *PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES,
    *PROFILE_ONBOARDING_OPTIONAL_FIELD_NAMES,
)
PROFILE_ONBOARDING_PERSONA_LAYER_FIELD_NAMES = frozenset(
    {
        "role_use_case",
        "preferred_name",
        "form_of_address",
        "project_context",
    }
)
PROFILE_ONBOARDING_FIELD_DESCRIPTIONS = {
    "profile_name": "Profile directory name to create and activate.",
    "role_use_case": "The intended role or use case for this profile.",
    "preferred_name": "The user's preferred name or stable display name for this profile.",
    "form_of_address": "How the assistant should address the user.",
    "tone": "The preferred tone for assistant responses.",
    "working_style": "The preferred collaboration and work style.",
    "strictness": "How strict the assistant should be around safety, evidence and uncertainty.",
    "memory_scope": "What may be stored as memory through governed flows.",
    "confirmation_boundaries": "What must never be changed without explicit confirmation.",
    "project_context": "Main project or work context for the profile.",
    "language_preference": "Language preference for status, chat and public artifacts.",
    "special_instructions": "Optional additional profile instructions. Use only explicit user-provided instructions.",
}
PROFILE_ONBOARDING_ALIAS_MAP = {
    "assistant_name": "preferred_name",
    "main_project": "project_context",
    "language": "language_preference",
    "confirmation_policy": "confirmation_boundaries",
    "memory_policy": "memory_scope",
}
PROFILE_ONBOARDING_SUGGESTED_MAPPINGS = {
    **PROFILE_ONBOARDING_ALIAS_MAP,
    "assistant": "preferred_name",
    "project": "project_context",
    "main_work": "project_context",
    "confirmation": "confirmation_boundaries",
    "memory": "memory_scope",
}
PROFILE_CREATION_FILE_MAP = {
    "CORE.md": ("profile_name",),
    "PERSONA.md": (
        "role_use_case",
        "project_context",
        "preferred_name",
        "form_of_address",
        "memory_scope",
        "confirmation_boundaries",
        "language_preference",
        "special_instructions",
    ),
    "TEMPERAMENT.md": ("tone", "working_style", "strictness", "language_preference", "special_instructions"),
    "memory.md": ("memory_scope",),
    "reflection.md": (),
    "governance/config.yaml": ("confirmation_boundaries",),
    "journal.md": ("profile_name",),
}
PROFILE_ONBOARDING_SCHEMA_VERSION = "1.0"
BOOTSTRAP_STARTUP_MESSAGE = (
    "Standard profile loaded. Onboarding is pending. Ask the user whether to start onboarding."
)

# Shown as startup_message when onboarding_complete is False.
# Deliberately more informative than BOOTSTRAP_STARTUP_MESSAGE so Claude can give
# a meaningful first-session introduction without the user having to ask. (RC2-UX-003)
BOOTSTRAP_ONBOARDING_INTRO = (
    "PLwC ist geladen. Das Profil ist noch nicht personalisiert (onboarding_complete: false "
    "in governance/config.yaml). Hier eine kurze Einführung:\n\n"
    "PLwC ist ein governed MCP Gateway fuer Claude Desktop. Es kontrolliert alle Workspace-, "
    "Dokument- und Profiloperationen unter Governance und fuehrt ein Audit-Log.\n\n"
    "Die acht Tools:\n"
    "  plwc_status          — Systemstatus, Sandbox, Profil-Konfiguration\n"
    "  plwc_describe        — Was kann PLwC? Alle Tools und Operationen beschreiben\n"
    "  plwc_profile         — Profil laden, anzeigen, aktivieren\n"
    "  plwc_reflection      — Reflexionseintrag schreiben (governed)\n"
    "  plwc_governor        — Gedaechtnis/Persona promoten, Plan/Apply\n"
    "  plwc_sandbox_run     — Python oder Shell in Docker ausfuehren\n"
    "  plwc_workspace_operation — Dateien lesen, schreiben, suchen, kopieren\n"
    "  plwc_document_operation  — DOCX/XLSX/PPTX/PDF erstellen und verarbeiten\n\n"
    "Was Claude NICHT autonom tut:\n"
    "  - Keine Schreibvorgaenge auf PERSONA.md oder memory.md ohne explizite Bestaetigung\n"
    "  - Keine Reflexions-Eintraege ohne deine Aufforderung\n"
    "  - Kein Governor-Apply ohne confirmed=true\n\n"
    "Naechster Schritt: Profil aktivieren mit plwc_profile(operation=compile) oder "
    "neues Profil anlegen mit plwc_governor(operation=plan, plan_type=profile_creation)."
)

_PROFILE_WRITE_LOCKS: dict[str, threading.Lock] = {}
_PROFILE_WRITE_LOCKS_GUARD = threading.Lock()


def profile_onboarding_questions(*, persona_layer_enabled: bool = True) -> tuple[str, ...]:
    active_fields = _profile_onboarding_active_field_names(persona_layer_enabled=persona_layer_enabled)
    question_by_field = dict(PROFILE_ONBOARDING_FIELDS)
    return tuple(question_by_field[field] for field in active_fields if field in question_by_field)


def profile_onboarding_schema(*, persona_layer_enabled: bool = True) -> dict[str, Any]:
    field_questions = {
        field: question
        for field, question in (*PROFILE_ONBOARDING_FIELDS, *PROFILE_ONBOARDING_OPTIONAL_FIELDS)
    }
    required_fields = _profile_onboarding_required_field_names(persona_layer_enabled=persona_layer_enabled)
    optional_fields = _profile_onboarding_optional_field_names(persona_layer_enabled=persona_layer_enabled)
    active_fields = _profile_onboarding_active_field_names(persona_layer_enabled=persona_layer_enabled)
    inactive_fields = _profile_onboarding_inactive_field_names(persona_layer_enabled=persona_layer_enabled)
    return {
        "schema_version": PROFILE_ONBOARDING_SCHEMA_VERSION,
        "contract": "plwc_profile_onboarding_payload",
        "persona_layer_enabled": bool(persona_layer_enabled),
        "accepted_fields": list(PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES),
        "active_fields": list(active_fields),
        "inactive_fields": list(inactive_fields),
        "required_fields": list(required_fields),
        "optional_fields": list(optional_fields),
        "governor_plan_type": PROFILE_CREATION_PLAN_TYPE,
        "governor_plan_type_aliases": sorted(PROFILE_CREATION_PLAN_TYPES - {PROFILE_CREATION_PLAN_TYPE}),
        "aliases": dict(PROFILE_ONBOARDING_ALIAS_MAP),
        "suggested_mappings": dict(PROFILE_ONBOARDING_SUGGESTED_MAPPINGS),
        "field_details": [
            {
                "key": field,
                "active": field in active_fields,
                "required": field in required_fields,
                "question": field_questions[field],
                "type": "string",
                "description": PROFILE_ONBOARDING_FIELD_DESCRIPTIONS[field],
            }
            for field in PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES
        ],
        "example_payload": {
            "profile_name": "Lumen",
            "preferred_name": "Alex",
            "form_of_address": "Use Alex",
            "role_use_case": "Technical work assistant and development companion",
            "project_context": "PLwC release hardening and MCPB validation",
            "tone": "Factual, direct, occasionally humorous",
            "working_style": "Structured, reviewing, no false promises",
            "strictness": "Security before convenience and traceability before speed",
            "memory_scope": "Only long-term useful information explicitly confirmed by the user",
            "confirmation_boundaries": "Never change persona, memory, policy or release decisions without confirmation",
            "language_preference": "German for status reports, English for code and public docs",
            "special_instructions": "Optional explicit user-provided profile instructions",
        },
        "validation": {
            "unknown_fields": "Rejected unless an explicit alias maps them to a canonical field.",
            "missing_required_fields": "Block approved apply until every required field has a non-empty value.",
            "alias_reporting": "Every applied alias is returned in alias_mappings_applied.",
            "apply_rule": (
                'plwc_governor(operation="apply") mutates files only when decision is '
                "approved_for_apply and confirmed=true."
            ),
            "persona_layer_disabled": (
                "When persona_layer_enabled is false, persona-only onboarding fields remain accepted "
                "for explicit callers but are inactive, not asked and not required."
            ),
        },
    }


def _profile_onboarding_required_field_names(*, persona_layer_enabled: bool) -> tuple[str, ...]:
    if persona_layer_enabled:
        return PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES
    return tuple(
        field
        for field in PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES
        if field not in PROFILE_ONBOARDING_PERSONA_LAYER_FIELD_NAMES
    )


def _profile_onboarding_optional_field_names(*, persona_layer_enabled: bool) -> tuple[str, ...]:
    required = set(_profile_onboarding_required_field_names(persona_layer_enabled=persona_layer_enabled))
    return tuple(field for field in PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES if field not in required)


def _profile_onboarding_active_field_names(*, persona_layer_enabled: bool) -> tuple[str, ...]:
    if persona_layer_enabled:
        return PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES
    return tuple(
        field
        for field in PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES
        if field not in PROFILE_ONBOARDING_PERSONA_LAYER_FIELD_NAMES
    )


def _profile_onboarding_inactive_field_names(*, persona_layer_enabled: bool) -> tuple[str, ...]:
    if persona_layer_enabled:
        return ()
    return tuple(
        field
        for field in PROFILE_ONBOARDING_REQUIRED_FIELD_NAMES
        if field in PROFILE_ONBOARDING_PERSONA_LAYER_FIELD_NAMES
    )


@dataclass(frozen=True)
class ProfileResult:
    ok: bool
    operation: str
    policy_decision: PolicyDecision
    profile_path: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None
    error_category: str | None = None
    requirement_ids: tuple[str, ...] = ()


class PBAProfileAdapter:
    source_contract = "pba_adapters.api.run_runtime_json"
    internal_runtime_contract = "plwc_gateway.adapters.pba.run_plwc_profile_runtime"

    def __init__(
        self,
        *,
        profile_root: str | Path,
        source_root: str | Path | None = None,
        runtime_callable: RuntimeCallable | None = None,
        policy_engine: Any | None = None,
        memory_write_threshold: int = DEFAULT_MEMORY_WRITE_THRESHOLD,
        persona_write_threshold: int = DEFAULT_PERSONA_WRITE_THRESHOLD,
        temperament_write_threshold: int = DEFAULT_TEMPERAMENT_WRITE_THRESHOLD,
        memory_write_threshold_source: str = "adapter_config",
        persona_write_threshold_source: str = "adapter_config",
        temperament_write_threshold_source: str = "adapter_config",
        active_profile_name: str = "default",
        configured_active_profile_name: str | None = None,
        active_profile_source: str = "default",
        active_profile_state_file: str | Path | None = None,
        pending_plan_root: str | Path | None = None,
        persona_layer_enabled: bool = True,
    ) -> None:
        self.profile_root = Path(profile_root).resolve(strict=False)
        self._source_root_explicit = source_root is not None
        self.source_root = Path(source_root).resolve(strict=False) if source_root else _default_pba_source_root()
        self._runtime_callable = runtime_callable
        self.policy_engine = policy_engine
        self.memory_write_threshold = memory_write_threshold
        self.persona_write_threshold = persona_write_threshold
        self.temperament_write_threshold = temperament_write_threshold
        self.memory_write_threshold_source = memory_write_threshold_source
        self.persona_write_threshold_source = persona_write_threshold_source
        self.temperament_write_threshold_source = temperament_write_threshold_source
        self.persona_layer_enabled = bool(persona_layer_enabled)
        self.active_profile_source = active_profile_source
        resolved_active_profile_name = _validate_profile_name(active_profile_name)
        if configured_active_profile_name is not None and str(configured_active_profile_name).strip():
            self.configured_active_profile_name = _validate_profile_name(str(configured_active_profile_name))
        elif active_profile_source in {"extension_config", "security_config"}:
            self.configured_active_profile_name = resolved_active_profile_name
        else:
            self.configured_active_profile_name = None
        self.active_profile_name = self.configured_active_profile_name or resolved_active_profile_name
        self.active_profile_state_file = (
            Path(active_profile_state_file).resolve(strict=False)
            if active_profile_state_file is not None
            else None
        )
        # Governed pending-plan store. Lives outside ``profile_root`` and outside
        # workspace ``allowed_roots`` so that workspace/document tools cannot
        # read or mutate stored plan snapshots. For installed MCPB runtime this
        # resolves under ``%APPDATA%/PLwC/state/pending_plans``.
        self.pending_plan_root = (
            Path(pending_plan_root).resolve(strict=False)
            if pending_plan_root is not None
            else None
        )

    @property
    def profile_runtime_source(self) -> str:
        """Non-leaking descriptor of where the profile runtime comes from.

        Returns "bundled_internal" for the normal shipped runtime and
        "external_source" only when an explicit source_root was configured.
        Used in place of exposing the raw source_root path, which otherwise
        leaked an internal legacy 'PBA2' source-tree path that does not exist
        in real installs. (RC2-LEGACY-001)"""
        return "external_source" if self._source_root_explicit else "bundled_internal"

    def runtime_status(self, profile: str = "default") -> ProfileResult:
        setup = self.profile_setup_status(profile)
        if not setup["active_profile_exists"]:
            return ProfileResult(
                ok=False,
                operation="profile_status",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=setup["active_profile_directory"],
                data=setup,
                error="Active profile setup is required.",
                requirement_ids=("OR-001", "FR-002", "NFR-002"),
            )
        return self._runtime_call("profile_status", profile, task_context="")

    def profile_setup_status(self, profile: str = "default") -> dict[str, Any]:
        active_state_profile = self._active_state_profile_name()
        mismatch_reason = self._active_profile_mismatch_reason(active_state_profile)
        try:
            profile_path = self._resolve_profile(profile)
        except ValueError as exc:
            return {
                "profiles_path": str(self.profile_root),
                "configured_active_profile": self.configured_active_profile_name,
                "resolved_active_profile": profile,
                "active_profile_name": profile,
                "active_profile_source": self.active_profile_source,
                "active_state_profile": active_state_profile,
                "mismatch_reason": mismatch_reason,
                "active_profile_state_file": str(self.active_profile_state_file) if self.active_profile_state_file else None,
                "onboarding_target_profile": profile,
                "active_profile_directory": None,
                "active_profile_exists": False,
                "profile_exists": False,
                "profile_valid": False,
                "selected_profile_exists": False,
                "selected_profile_valid": False,
                "status": "setup_required",
                "required_files": list(PROFILE_REQUIRED_FILES),
                "missing_files": list(PROFILE_REQUIRED_FILES),
                "available_profiles": self.available_profiles(),
                "available_profile_names": self.available_profile_names(),
                "profile_runtime_available": False,
                "profile_runtime_reason": str(exc),
                "profile_activation_supported": self.active_profile_state_file is not None,
                "onboarding_required": True,
                "onboarding_complete": False,
                "profile_kind": "invalid",
                "bootstrap_profile_created": False,
                "startup_message": None,
                "profile_creation_mode": "guided_onboarding",
                "onboarding_questions": list(
                    profile_onboarding_questions(persona_layer_enabled=self.persona_layer_enabled)
                ),
                "next_action": "Choose one of the available profiles or create a new profile.",
                "next_actions": [
                    "Choose one of the available profiles or create a new profile through governed PLwC onboarding.",
                ],
            }
        bootstrap_created = (
            self._ensure_bootstrap_profile_if_needed(profile_path)
            if _same_profile_name(profile_path.name, self.active_profile_name)
            and not self._is_configured_active_profile(profile_path.name)
            else False
        )
        missing_files = _missing_profile_files(profile_path)
        schema_validation = _profile_schema_validation(profile_path)
        active_profile_exists = profile_path.exists() and not missing_files
        selected_profile_exists = profile_path.exists() and profile_path.is_dir()
        selected_profile_valid = selected_profile_exists and not missing_files and bool(schema_validation["valid"])
        runtime_available = active_profile_exists and bool(schema_validation["valid"]) and self._runtime_available()
        onboarding_complete = active_profile_exists and _profile_onboarding_complete(profile_path)
        profile_kind = _profile_kind(profile_path) if active_profile_exists else "missing"
        startup_message = BOOTSTRAP_ONBOARDING_INTRO if active_profile_exists and not onboarding_complete else None
        profile_status = self._profile_setup_state(
            profile_path=profile_path,
            selected_profile_exists=selected_profile_exists,
            missing_files=missing_files,
            schema_validation=schema_validation,
            runtime_available=runtime_available,
            onboarding_complete=onboarding_complete,
        )
        if not profile_path.exists():
            next_action = f"Create active profile '{profile_path.name}' through governed PLwC onboarding."
        elif missing_files:
            next_action = "Complete the active profile through governed PLwC onboarding."
        elif not schema_validation["valid"]:
            next_action = "Repair the active profile schema or governance config before use."
        elif not runtime_available:
            next_action = "Profile exists but runtime is unavailable. Check profile files and adapter status."
        elif not onboarding_complete:
            next_action = BOOTSTRAP_STARTUP_MESSAGE
        else:
            next_action = "Profile runtime is available."
        return {
            "profiles_path": str(self.profile_root),
            "configured_active_profile": self.configured_active_profile_name,
            "resolved_active_profile": profile,
            "active_profile_name": profile,
            "active_profile_source": self.active_profile_source,
            "active_state_profile": active_state_profile,
            "mismatch_reason": mismatch_reason,
            "active_profile_state_file": str(self.active_profile_state_file) if self.active_profile_state_file else None,
            "onboarding_target_profile": profile,
            "active_profile_directory": str(profile_path),
            "active_profile_exists": active_profile_exists,
            "profile_exists": selected_profile_exists,
            "profile_valid": selected_profile_valid,
            "selected_profile_exists": selected_profile_exists,
            "selected_profile_valid": selected_profile_valid,
            "status": profile_status,
            "required_files": list(PROFILE_REQUIRED_FILES),
            "missing_files": missing_files,
            "available_profiles": self.available_profiles(),
            "available_profile_names": self.available_profile_names(),
            "profile_runtime_available": runtime_available,
            "profile_runtime_reason": _profile_runtime_reason(
                source_root=self.source_root,
                source_root_explicit=self._source_root_explicit,
                active_profile_exists=active_profile_exists,
                runtime_callable=self._runtime_callable,
            ),
            "profile_activation_supported": self.active_profile_state_file is not None,
            "onboarding_required": not active_profile_exists or not runtime_available or not onboarding_complete,
            "onboarding_complete": onboarding_complete,
            "profile_kind": profile_kind,
            "profile_schema_validation": schema_validation,
            "bootstrap_profile_created": bootstrap_created,
            "startup_message": startup_message,
            "profile_creation_mode": "guided_onboarding",
            "onboarding_questions": list(
                profile_onboarding_questions(persona_layer_enabled=self.persona_layer_enabled)
            ),
            "import_direction": "Import existing external profiles into the PLwC-owned profiles path before use.",
            "next_action": next_action,
            "next_actions": self._profile_next_actions(
                status=profile_status,
                target_profile=profile_path.name,
                next_action=next_action,
            ),
        }

    def _is_configured_active_profile(self, profile_name: str) -> bool:
        return _same_profile_name(profile_name, self.configured_active_profile_name or "")

    def _active_state_profile_name(self) -> str | None:
        if self.active_profile_state_file is None or not self.active_profile_state_file.exists():
            return None
        try:
            payload = json.loads(self.active_profile_state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        value = payload.get("active_profile_name") if isinstance(payload, dict) else None
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            return _validate_profile_name(value)
        except ValueError:
            return None

    def _active_profile_mismatch_reason(self, active_state_profile: str | None) -> str | None:
        if (
            self.configured_active_profile_name
            and active_state_profile
            and not _same_profile_name(active_state_profile, self.configured_active_profile_name)
        ):
            return "configured_active_profile_takes_precedence_over_active_state"
        return None

    def _profile_setup_state(
        self,
        *,
        profile_path: Path,
        selected_profile_exists: bool,
        missing_files: list[str],
        schema_validation: dict[str, Any],
        runtime_available: bool,
        onboarding_complete: bool,
    ) -> str:
        if not selected_profile_exists:
            return "onboarding_required" if self.profile_root.exists() else "setup_required"
        if missing_files or not schema_validation["valid"]:
            return (
                "invalid_configured_profile"
                if self._is_configured_active_profile(profile_path.name)
                else "setup_required"
            )
        if not runtime_available:
            return "setup_required"
        if not onboarding_complete:
            return "onboarding_required"
        return "ok"

    def _profile_next_actions(self, *, status: str, target_profile: str, next_action: str) -> list[str]:
        actions = [next_action]
        if status == "onboarding_required":
            actions.append(
                f'Run plwc_governor(operation="plan", plan_type="profile_creation") for target profile '
                f"'{target_profile}', review the file_previews, then apply through "
                'plwc_governor(operation="apply", plan_type="profile_creation", confirmed=true).'
            )
        elif status == "invalid_configured_profile":
            actions.append(
                f"Repair or recreate configured active profile '{target_profile}' through governed PLwC onboarding."
            )
        elif status == "setup_required":
            actions.append("Review profile setup status, repair missing files or configuration, then rerun PLwC status.")
        return list(dict.fromkeys(actions))

    def available_profiles(self) -> list[dict[str, Any]]:
        return self._available_profile_descriptors(active_profile_name=self.active_profile_name)

    def available_profile_names(self) -> list[str]:
        if not self.profile_root.exists():
            return []
        profiles: list[str] = []
        for candidate in self.profile_root.iterdir():
            if candidate.is_dir() and candidate.name.casefold() != "template":
                profiles.append(candidate.name)
        return sorted(profiles)

    def _available_profile_descriptors(self, *, active_profile_name: str) -> list[dict[str, Any]]:
        profiles: list[dict[str, Any]] = []
        if not self.profile_root.exists():
            return profiles
        for name in self.available_profile_names():
            try:
                profile_path = self._resolve_profile(name)
                missing_files = _missing_profile_files(profile_path)
                schema_validation = _profile_schema_validation(profile_path)
                valid = profile_path.exists() and profile_path.is_dir() and not missing_files and bool(schema_validation["valid"])
                if valid:
                    reason = "valid"
                elif missing_files:
                    reason = "missing_required_files"
                elif schema_validation["errors"]:
                    reason = "invalid_profile_schema"
                else:
                    reason = "invalid_profile"
            except ValueError as exc:
                profile_path = self.profile_root / name
                missing_files = list(PROFILE_REQUIRED_FILES)
                valid = False
                reason = str(exc)
                schema_validation = {"valid": False, "errors": [str(exc)], "warnings": []}
            profiles.append(
                {
                    "name": name,
                    "active": _same_profile_name(name, active_profile_name),
                    "valid": valid,
                    "required_profile_files_present": valid,
                    "missing_files": missing_files,
                    "profile_directory": str(profile_path),
                    "validation_reason": reason,
                    "profile_schema_validation": schema_validation,
                }
            )
        return profiles

    def _runtime_available(self) -> bool:
        return True

    def snapshot(self, profile: str = "default") -> ProfileResult:
        result = self._runtime_call("profile_snapshot", profile, task_context="")
        if not result.ok or result.data is None:
            return result
        return _with_data(
            result,
            {
                **_profile_runtime_metadata(result.data),
                "snapshot": result.data.get("snapshot", {}),
            },
        )

    def compile_profile(
        self,
        profile: str = "default",
        *,
        task_context: str = "",
        record_journal_event: bool = True,
    ) -> ProfileResult:
        result = self._runtime_call("compile_profile", profile, task_context=task_context)
        if not result.ok or result.data is None:
            return result
        compiled_layer_chars = len(result.data.get("compiled_layer", ""))
        journal_event_written = (
            self._journal_compile_event(profile, compiled_layer_chars) if record_journal_event else False
        )
        return _with_data(
            result,
            {
                **_profile_runtime_metadata(result.data),
                "compiled_layer": result.data.get("compiled_layer", ""),
                "compiled_layer_chars": compiled_layer_chars,
                "compile_journal_event_written": journal_event_written,
                "source_contract": self.source_contract,
                "runtime_contract": result.data.get("runtime_contract", self.source_contract),
            },
        )

    def _journal_compile_event(self, profile: str, compiled_layer_chars: int) -> bool:
        """RC8-JOURNAL-001 — persist compiled_layer_chars per compile in journal.md.

        Additive tracking event (``event_type=profile_compile``) so the growth
        curve no longer has to be reconstructed manually. Best-effort: a journal
        write failure must never break the compile read path.
        """
        try:
            profile_path = self._resolve_profile(profile.strip() or self.active_profile_name)
            if not profile_path.exists():
                return False
            payload = {
                "schema_version": PBA2_JOURNAL_SCHEMA_VERSION,
                "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "event_type": COMPILE_JOURNAL_EVENT_TYPE,
                "profile_name": profile_path.name,
                "compiled_layer_chars": compiled_layer_chars,
                "actor": "plwc-gateway",
                "tool": "plwc_profile",
            }
            journal = profile_path / "journal.md"
            current = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
            block = "\n".join(
                (
                    f"## COMPILE EVENT {payload['timestamp']}",
                    "```json",
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                    "```",
                )
            )
            _atomic_write_text(journal, _append_profile_block(current, block))
            return True
        except Exception:
            return False

    def write_reflection(
        self,
        profile: str,
        *,
        summary: str,
        evidence: str,
        confidence: str,
        marker: str = "observation",
        trust: str = "",
        candidate_for: str = "",
        target: str = "",
        entry_date: str = "",
        source: str = "plwc-gateway",
    ) -> ProfileResult:
        try:
            requested_profile = _validate_profile_name(profile.strip() or self.active_profile_name)
        except ValueError as exc:
            return _profile_error("write_reflection", str(exc), ("NFR-002",))
        active_profile = self.active_profile_name
        if not _same_profile_name(requested_profile, active_profile):
            reason = (
                "Cross-profile reflection writes are not allowed. "
                f"Active profile is {active_profile}, requested profile is {requested_profile}."
            )
            return ProfileResult(
                ok=False,
                operation="write_reflection",
                policy_decision=PolicyDecision.DENY,
                profile_path=str((self.profile_root / requested_profile).resolve(strict=False)),
                data={
                    "accepted": False,
                    "error_category": "cross_profile_write_denied",
                    "active_profile": active_profile,
                    "requested_profile": requested_profile,
                    "evidence_role": "rejected_profile_mismatch",
                    "changed_files": [],
                },
                error=reason,
                error_category="cross_profile_write_denied",
                requirement_ids=("FR-004", "FR-010", "SR-010", "NFR-002"),
            )
        try:
            profile_path = self._resolve_profile(requested_profile)
        except ValueError as exc:
            return _profile_error("write_reflection", str(exc), ("NFR-002",))
        reflection_file = profile_path / "reflection.md"
        intent = self._write_intent("plwc_write_reflection", reflection_file)

        def adapter_call() -> ProfileResult:
            setup = self.profile_setup_status(requested_profile)
            if not setup["active_profile_exists"]:
                return ProfileResult(
                    ok=False,
                    operation="write_reflection",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=setup,
                    error="Active profile setup is required before writing reflection.",
                    error_category="setup_required",
                    requirement_ids=("OR-001", "FR-004", "NFR-002"),
                )
            try:
                entry = _format_reflection_entry(
                    summary=summary,
                    evidence=evidence,
                    confidence=confidence,
                    marker=marker,
                    trust=trust,
                    candidate_for=candidate_for,
                    target=target,
                    entry_date=entry_date,
                    source=source,
                )
            except ValueError as exc:
                error_category = _reflection_validation_error_category(str(exc))
                return ProfileResult(
                    ok=False,
                    operation="write_reflection",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data={
                        "accepted": False,
                        "error_category": error_category,
                        "evidence_role": _reflection_rejected_evidence_role(error_category),
                        "changed_files": [],
                    },
                    error=str(exc),
                    error_category=error_category,
                    requirement_ids=("FR-004", "FR-010", "NFR-002"),
                )
            metadata = _reflection_evidence_metadata(
                reflection_file,
                summary=summary,
                evidence=evidence,
                confidence=confidence,
                marker=marker,
                trust=trust,
                candidate_for=candidate_for,
                target=target,
                entry_date=entry_date,
            )
            if metadata["evidence_role"] == "exact_duplicate":
                return ProfileResult(
                    ok=True,
                    operation="write_reflection",
                    policy_decision=PolicyDecision.ALLOW,
                    profile_path=str(profile_path),
                    data={
                        "written_file": str(reflection_file),
                        "entry_chars": 0,
                        "reflection_format": "pba2",
                        "marker": metadata["marker"],
                        "trust": metadata["trust"],
                        "candidate_for": metadata["candidate_for"],
                        "target": _single_line_optional(target, "target"),
                        "accepted": True,
                        "duplicate_noop": True,
                        "evidence_role": "exact_duplicate",
                        "corroborates_existing_pattern": True,
                        "existing_pattern_reference": metadata["existing_pattern_reference"],
                        "entry_date": metadata["entry_date"],
                        "changed_files": [],
                    },
                    requirement_ids=("FR-004", "FR-010", "SR-010"),
                )
            with reflection_file.open("a", encoding="utf-8") as handle:
                handle.write(entry)
            return ProfileResult(
                ok=True,
                operation="write_reflection",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={
                    "written_file": str(reflection_file),
                    "entry_chars": len(entry),
                    "reflection_format": "pba2",
                    "marker": metadata["marker"],
                    "trust": metadata["trust"],
                    "candidate_for": metadata["candidate_for"],
                    "target": _single_line_optional(target, "target"),
                    "accepted": True,
                    "duplicate_noop": False,
                    "evidence_role": metadata["evidence_role"],
                    "corroborates_existing_pattern": metadata["corroborates_existing_pattern"],
                    "existing_pattern_reference": metadata["existing_pattern_reference"],
                    "entry_date": metadata["entry_date"],
                    "changed_files": [str(reflection_file)],
                },
                requirement_ids=("FR-004", "FR-010", "SR-010"),
            )

        return self._execute(
            intent,
            "write_reflection",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def governor_plan(
        self,
        profile: str = "default",
        *,
        force: bool = False,
        onboarding_answers: dict[str, Any] | None = None,
        plan_type: str = "",
    ) -> ProfileResult:
        normalized_plan_type = _normalize_plan_type(plan_type)
        if normalized_plan_type in REFLECTION_MEMORY_PROMOTION_PLAN_TYPES:
            plan = self._reflection_memory_promotion_plan(profile, force=force)
            return ProfileResult(
                ok=bool(plan["validation"]["valid"]),
                operation="governor_plan",
                policy_decision=PolicyDecision.ALLOW if plan["validation"]["valid"] else PolicyDecision.DENY,
                profile_path=plan.get("profile_directory"),
                data=_compact_skipped_candidates(plan),
                error=None if plan["validation"]["valid"] else plan["validation"]["reason"],
                requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "FR-REFMEM-001", "FR-REFMEM-004", "NFR-002"),
            )
        if normalized_plan_type == REFLECTION_CONDENSATION_PLAN_TYPE:
            plan = self._reflection_condensation_plan(profile)
            return ProfileResult(
                ok=bool(plan["validation"]["valid"]),
                operation="governor_plan",
                policy_decision=PolicyDecision.ALLOW if plan["validation"]["valid"] else PolicyDecision.DENY,
                profile_path=plan.get("profile_directory"),
                data=plan,
                error=None if plan["validation"]["valid"] else plan["validation"]["reason"],
                requirement_ids=(*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "NFR-002"),
            )
        if normalized_plan_type in PBA2_PROMOTION_PLAN_TYPES:
            plan = self._promotion_plan(
                profile,
                plan_type=normalized_plan_type,
                onboarding_answers=onboarding_answers,
                force=force,
            )
            return ProfileResult(
                ok=bool(plan["validation"]["valid"]),
                operation="governor_plan",
                policy_decision=PolicyDecision.ALLOW if plan["validation"]["valid"] else PolicyDecision.DENY,
                profile_path=plan.get("profile_directory"),
                data=plan,
                error=None if plan["validation"]["valid"] else plan["validation"]["reason"],
                requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "NFR-002"),
            )
        if normalized_plan_type == "profile_import":
            plan = self._profile_import_plan(
                profile,
                onboarding_answers=onboarding_answers,
                overwrite_requested=force,
            )
            return ProfileResult(
                ok=bool(plan["validation"]["valid"]),
                operation="governor_plan",
                policy_decision=PolicyDecision.ALLOW if plan["validation"]["valid"] else PolicyDecision.DENY,
                profile_path=plan.get("target_profile_directory"),
                data=plan,
                error=None if plan["validation"]["valid"] else plan["validation"]["reason"],
                requirement_ids=("FR-005", "FR-009", "FR-PBA2-GATE-001", "SR-010", "NFR-002"),
            )
        if normalized_plan_type == "profile_activation":
            plan = self._profile_activation_plan(profile)
            return ProfileResult(
                ok=bool(plan["validation"]["valid"]),
                operation="governor_plan",
                policy_decision=PolicyDecision.ALLOW if plan["validation"]["valid"] else PolicyDecision.DENY,
                profile_path=plan.get("target_profile_directory"),
                data=plan,
                error=None if plan["validation"]["valid"] else plan["validation"]["reason"],
                requirement_ids=("FR-005", "OR-001", "SR-010", "NFR-002"),
            )
        if normalized_plan_type in PROFILE_CREATION_PLAN_TYPES:
            return self._profile_creation_governor_plan(profile, onboarding_answers)
        if normalized_plan_type:
            return _profile_error(
                "governor_plan",
                f"Unsupported governor plan_type: {plan_type}",
                ("FR-PBA2-GOLD-007", "NFR-002"),
            )
        setup = self.profile_setup_status(profile)
        if setup.get("active_profile_directory") is None:
            return ProfileResult(
                ok=False,
                operation="governor_plan",
                policy_decision=PolicyDecision.DENY,
                data=setup,
                error=str(setup.get("profile_runtime_reason") or "Profile name is invalid."),
                requirement_ids=("OR-001", "SR-006", "NFR-002"),
            )
        if not setup["active_profile_exists"] or not setup["onboarding_complete"]:
            return self._profile_creation_governor_plan(profile, onboarding_answers)
        return self._runtime_call(
            "governor_plan",
            profile,
            task_context="",
            run_governor=True,
            governor_apply=False,
            governor_force=force,
        )

    def _profile_creation_governor_plan(
        self,
        profile: str,
        onboarding_answers: dict[str, Any] | None,
    ) -> ProfileResult:
        setup = self.profile_setup_status(profile)
        if setup.get("active_profile_directory") is None:
            return ProfileResult(
                ok=False,
                operation="governor_plan",
                policy_decision=PolicyDecision.DENY,
                data=setup,
                error=str(setup.get("profile_runtime_reason") or "Profile name is invalid."),
                requirement_ids=("OR-001", "SR-006", "NFR-002"),
            )
        if setup["active_profile_exists"] and setup["onboarding_complete"]:
            data = {
                **setup,
                "plan_type": PROFILE_CREATION_PLAN_TYPE,
                "decision": "rejected",
                "approved_for_apply": False,
                "onboarding_complete_after_apply": False,
                "validation_error": "Profile creation requires a missing or onboarding-incomplete profile target.",
            }
            return ProfileResult(
                ok=False,
                operation="governor_plan",
                policy_decision=PolicyDecision.DENY,
                profile_path=setup["active_profile_directory"],
                data=data,
                error=data["validation_error"],
                requirement_ids=("FR-005", "OR-001", "OR-005", "NFR-002"),
            )
        try:
            plan = self._profile_creation_plan(profile, setup, onboarding_answers)
        except ValueError as exc:
            return _profile_error("governor_plan", str(exc), ("OR-001", "OR-005", "SR-006", "NFR-002"))
        plan_approved = plan["decision"] == "approved_for_apply"
        return ProfileResult(
            ok=plan_approved,
            operation="governor_plan",
            policy_decision=PolicyDecision.ALLOW if plan_approved else PolicyDecision.DENY,
            profile_path=setup["active_profile_directory"],
            data={
                **setup,
                **plan,
            },
            error=None if plan_approved else plan["validation_error"],
            requirement_ids=("FR-005", "OR-001", "OR-005", "SR-010", "NFR-002"),
        )

    def governor_apply(
        self,
        profile: str = "default",
        *,
        force: bool = False,
        onboarding_answers: dict[str, Any] | None = None,
        confirmed: bool = False,
        plan_type: str = "",
        plan_id: str = "",
    ) -> ProfileResult:
        normalized_plan_type = _normalize_plan_type(plan_type)
        if plan_id.strip() and normalized_plan_type != REFLECTION_CONDENSATION_PLAN_TYPE:
            return _profile_error(
                "governor_apply",
                "plan_id apply is only supported for plan_type=reflection_condensation.",
                (*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "NFR-002"),
            )
        if normalized_plan_type in REFLECTION_MEMORY_PROMOTION_PLAN_TYPES:
            return self._apply_reflection_memory_promotion(
                profile,
                force=force,
                confirmed=confirmed,
            )
        if normalized_plan_type == REFLECTION_CONDENSATION_PLAN_TYPE:
            return self._apply_reflection_condensation(
                profile,
                onboarding_answers=onboarding_answers,
                confirmed=confirmed,
                plan_id=plan_id,
            )
        if normalized_plan_type in PBA2_PROMOTION_PLAN_TYPES:
            return self._apply_promotion(
                profile,
                plan_type=normalized_plan_type,
                onboarding_answers=onboarding_answers,
                confirmed=confirmed,
                force=force,
            )
        if normalized_plan_type == "profile_import":
            return self._apply_profile_import(
                profile,
                onboarding_answers=onboarding_answers,
                confirmed=confirmed,
                overwrite_requested=force,
            )
        if normalized_plan_type == "profile_activation":
            return self._apply_profile_activation(profile, confirmed=confirmed)
        if normalized_plan_type in PROFILE_CREATION_PLAN_TYPES:
            return self._apply_profile_creation(profile, onboarding_answers=onboarding_answers, confirmed=confirmed)
        if normalized_plan_type:
            return _profile_error(
                "governor_apply",
                f"Unsupported governor plan_type: {plan_type}",
                ("FR-PBA2-GOLD-007", "NFR-002"),
            )
        setup = self.profile_setup_status(profile)
        if not setup["active_profile_exists"] or not setup["onboarding_complete"]:
            return self._apply_profile_creation(
                profile,
                onboarding_answers=onboarding_answers,
                confirmed=confirmed,
            )
        return self._apply_existing_governor(profile, force=force, confirmed=confirmed)

    def _apply_existing_governor(self, profile: str, *, force: bool, confirmed: bool) -> ProfileResult:
        try:
            profile_path = self._resolve_profile(profile)
        except ValueError as exc:
            return _profile_error("governor_apply", str(exc), ("NFR-002",))
        intent = self._write_intent("plwc_governor_apply", profile_path / "journal.md")

        def adapter_call() -> ProfileResult:
            return self._runtime_call(
                "governor_apply",
                profile,
                task_context="",
                run_governor=True,
                governor_apply=True,
                governor_force=force,
                governor_confirmed=confirmed,
            )

        return self._execute(
            intent,
            "governor_apply",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def governor_retire(
        self,
        profile: str = "default",
        *,
        target_file: str = "",
        heading: str = "",
        directive_id: str = "",
        reason: str = "",
        conflicts_with: str = "",
        confirmed: bool = False,
        retired_at: str = "",
        dedup: bool = False,
    ) -> ProfileResult:
        """RC8-FEAT-001 — retire a profile entry (status change, no delete).

        ``confirmed`` gates the two phases: without it this is a plan-preview that
        **mutates nothing**; with ``confirmed=True`` the matched ``## [ACTIVE]``
        entry is flipped to ``## [RETIRED]``, retirement metadata is appended, and
        a governor event is journaled. The entry is identified by its exact
        ``heading`` line **or** by its stable ``directive_id`` (RC12-RETIRE-001 —
        the canonical per-section SHA; resolves the ambiguous-heading case). When
        a directive_id matches several byte-identical sections the retire is denied
        with ``exact_duplicate`` unless ``dedup=True`` (keep one, retire the rest).
        CORE.md is rejected (non_target).
        """
        requirement_ids = ("FR-005", "SR-010", "NFR-002")
        normalized_target = target_file.strip()
        if normalized_target not in RETIREMENT_TARGET_FILES:
            return _profile_error(
                "governor_retire",
                "target_file must be one of "
                f"{', '.join(RETIREMENT_TARGET_FILES)} (CORE.md is non_target and cannot be retired).",
                requirement_ids,
            )
        if not heading.strip() and not directive_id.strip():
            return _profile_error(
                "governor_retire",
                "heading or directive_id is required to identify the entry to retire.",
                requirement_ids,
            )
        if dedup and not directive_id.strip():
            return _profile_error(
                "governor_retire",
                "dedup requires a directive_id (it retires all byte-identical sections but one).",
                requirement_ids,
            )
        if not reason.strip():
            return _profile_error(
                "governor_retire", "reason is required for a retire (audit trail).", requirement_ids
            )
        try:
            profile_path = self._resolve_profile(profile)
        except ValueError as exc:
            return _profile_error("governor_retire", str(exc), ("NFR-002",))
        target = profile_path / normalized_target
        if not target.exists():
            return _profile_error(
                "governor_retire", f"Target file {normalized_target} does not exist in profile.", requirement_ids
            )

        effective_retired_at = retired_at.strip() or datetime.now(timezone.utc).date().isoformat()
        clean_reason = reason.strip()
        clean_conflicts = conflicts_with.strip()
        clean_directive_id = directive_id.strip()
        current = target.read_text(encoding="utf-8")
        transform = _retire_entry_in_text(
            current,
            heading=heading,
            directive_id=clean_directive_id,
            retired_at=effective_retired_at,
            reason=clean_reason,
            conflicts_with=clean_conflicts,
            dedup=dedup,
        )
        plan_id = _stable_hash(
            {
                "plan_type": MEMORY_RETIREMENT_PLAN_TYPE,
                "profile_name": profile_path.name,
                "target_file": normalized_target,
                "heading": heading.strip(),
                "directive_id": clean_directive_id,
                "dedup": bool(dedup),
                "reason": clean_reason,
                "conflicts_with": clean_conflicts,
                "source_sha256": _file_snapshot(target)["sha256"],
            }
        )
        preview: dict[str, Any] = {
            "plan_type": MEMORY_RETIREMENT_PLAN_TYPE,
            "profile_name": profile_path.name,
            "profile_directory": str(profile_path),
            "target_file": normalized_target,
            "heading": heading.strip(),
            "directive_id": clean_directive_id,
            "dedup": bool(dedup),
            "reason": clean_reason,
            "conflicts_with": clean_conflicts,
            "retired_at": effective_retired_at,
            "plan_id": plan_id,
            "match": transform["reason"],
            "would_change": transform["changed"],
            "confirmation_required": True,
            "confirmed": bool(confirmed),
        }
        if "heading_after" in transform:
            preview["heading_before"] = transform["heading_before"]
            preview["heading_after"] = transform["heading_after"]
        if "retired_count" in transform:
            preview["retired_count"] = transform["retired_count"]
            preview["kept_count"] = transform["kept_count"]

        if not transform["changed"]:
            return ProfileResult(
                ok=False,
                operation="governor_retire",
                policy_decision=PolicyDecision.DENY,
                profile_path=str(profile_path),
                data={**preview, "changed_files": []},
                error=f"Retire candidate not applicable: {transform['reason']}.",
                requirement_ids=requirement_ids,
            )

        if not confirmed:
            # Plan phase — must not mutate any file.
            return ProfileResult(
                ok=True,
                operation="governor_retire",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={**preview, "changed_files": []},
                error=None,
                requirement_ids=requirement_ids,
            )

        intent = self._write_intent("plwc_governor", target)

        def adapter_call() -> ProfileResult:
            # Re-read at apply time so a concurrent edit cannot be overwritten blindly.
            current_now = target.read_text(encoding="utf-8")
            transform_now = _retire_entry_in_text(
                current_now,
                heading=heading,
                directive_id=clean_directive_id,
                retired_at=effective_retired_at,
                reason=clean_reason,
                conflicts_with=clean_conflicts,
                dedup=dedup,
            )
            if not transform_now["changed"]:
                return ProfileResult(
                    ok=False,
                    operation="governor_retire",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data={**preview, "match": transform_now["reason"], "changed_files": []},
                    error=f"Retire candidate became inapplicable before apply: {transform_now['reason']}.",
                    requirement_ids=requirement_ids,
                )
            file_snapshots = {
                normalized_target: _file_snapshot(target),
                "journal.md": _file_snapshot(profile_path / "journal.md"),
            }
            _atomic_write_text(target, transform_now["new_text"])
            journal_payload = _retirement_journal_payload(
                profile_name=profile_path.name,
                plan_id=plan_id,
                target_file=normalized_target,
                heading_before=transform_now["heading_before"],
                heading_after=transform_now["heading_after"],
                directive_id=clean_directive_id,
                dedup=transform_now.get("dedup", False),
                retired_count=transform_now.get("retired_count", 1),
                reason=clean_reason,
                conflicts_with=clean_conflicts,
                retired_at=effective_retired_at,
                changed_files=[normalized_target, "journal.md"],
                file_snapshots=file_snapshots,
            )
            _append_governor_journal_event(profile_path, journal_payload)
            return ProfileResult(
                ok=True,
                operation="governor_retire",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={
                    **preview,
                    "confirmed": True,
                    "changed_files": [normalized_target, "journal.md"],
                    "target_changed": True,
                    "journal_event": journal_payload,
                },
                error=None,
                requirement_ids=requirement_ids,
            )

        return self._execute(intent, "governor_retire", profile_path, adapter_call, guarded_write=True)

    def list_retirable(
        self,
        profile: str = "default",
        *,
        target_file: str = "",
        today: str = "",
    ) -> ProfileResult:
        """RC8-FEAT-001 — list retirement candidates (read-only, no mutation).

        Surfaces active entries flagged by the four criteria (history_only,
        superseded, duplicate, near_duplicate, inner_truth_overflow and the soft
        ``no_action_rule``). Decides no truth: returns reviewable candidates +
        the review question; the human decides via a confirmed ``retire``.
        """
        requirement_ids = ("FR-002", "SR-010", "NFR-002", RC14_RETIREMENT_REQUIREMENT_ID)
        requested = target_file.strip()
        if requested and requested not in RETIREMENT_TARGET_FILES:
            return _profile_error(
                "list_retirable",
                "target_file must be one of "
                f"{', '.join(RETIREMENT_TARGET_FILES)} (CORE.md is non_target).",
                requirement_ids,
            )
        try:
            profile_path = self._resolve_profile(profile)
        except ValueError as exc:
            return _profile_error("list_retirable", str(exc), ("NFR-002",))

        target_files = [requested] if requested else list(RETIREMENT_TARGET_FILES)
        threshold_days = self._retirement_age_threshold_days(profile_path)
        near_threshold = self._near_duplicate_threshold(profile_path)
        candidates: list[dict[str, Any]] = []
        scanned: list[str] = []
        for filename in target_files:
            file_path = profile_path / filename
            if not file_path.exists():
                continue
            scanned.append(filename)
            candidates.extend(
                _retirable_candidates_for_file(
                    target_file=filename,
                    text=file_path.read_text(encoding="utf-8"),
                    threshold_days=threshold_days,
                    today=today.strip(),
                    near_threshold=near_threshold,
                )
            )
        candidates.sort(
            key=lambda candidate: (
                -candidate["hard_flag_count"],
                -len(candidate["flags"]),
                candidate["target_file"],
                candidate["heading"],
            )
        )
        return ProfileResult(
            ok=True,
            operation="list_retirable",
            policy_decision=PolicyDecision.ALLOW,
            profile_path=str(profile_path),
            data={
                "profile_name": profile_path.name,
                "scanned_files": scanned,
                "retirement_age_threshold_days": threshold_days,
                "near_duplicate_similarity_threshold": near_threshold,
                "candidate_count": len(candidates),
                "candidates": candidates,
                "no_action_rule_review_question": NO_ACTION_RULE_REVIEW_QUESTION,
                "note": "list_retirable surfaces reviewable candidates and questions; it decides no truth. Retire only via a confirmed governor retire.",
            },
            error=None,
            requirement_ids=requirement_ids,
        )

    def _retirement_age_threshold_days(self, profile_path: Path) -> int:
        values = _simple_key_value_lines(_profile_governance_text(profile_path))
        return _nonnegative_int(
            values.get("retirement_age_threshold_days"), DEFAULT_RETIREMENT_AGE_THRESHOLD_DAYS
        )

    def _near_duplicate_threshold(self, profile_path: Path) -> float:
        values = _simple_key_value_lines(_profile_governance_text(profile_path))
        return _ratio_value(
            values.get("near_duplicate_similarity_threshold"),
            DEFAULT_NEAR_DUPLICATE_SIMILARITY_THRESHOLD,
        )

    def _apply_profile_creation(
        self,
        profile: str,
        *,
        onboarding_answers: dict[str, Any] | None,
        confirmed: bool,
    ) -> ProfileResult:
        try:
            profile_path = self._resolve_profile(profile)
        except ValueError as exc:
            return _profile_error("governor_apply", str(exc), ("NFR-002",))
        setup = self.profile_setup_status(profile)
        if setup["active_profile_exists"] and setup["onboarding_complete"]:
            return ProfileResult(
                ok=False,
                operation="governor_apply",
                policy_decision=PolicyDecision.DENY,
                profile_path=str(profile_path),
                data={
                    **setup,
                    "plan_type": PROFILE_CREATION_PLAN_TYPE,
                    "decision": "rejected",
                    "approved_for_apply": False,
                    "onboarding_complete_after_apply": False,
                },
                error="Profile creation requires a missing or onboarding-incomplete profile target.",
                requirement_ids=("FR-005", "OR-001", "OR-005", "NFR-002"),
            )
        target = profile_path / "CORE.md"
        intent = self._write_intent("plwc_governor_apply", target)

        def adapter_call() -> ProfileResult:
            try:
                plan = self._profile_creation_plan(profile, setup, onboarding_answers)
            except ValueError as exc:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    error=str(exc),
                    requirement_ids=("OR-001", "OR-005", "SR-006", "NFR-002"),
                )
            if plan["decision"] != "approved_for_apply":
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=plan["validation_error"],
                    requirement_ids=("FR-005", "OR-001", "OR-005", "SR-010", "NFR-002"),
                )
            if not confirmed:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=(
                        "Profile creation requires explicit confirmation. Re-run "
                        'plwc_governor(operation="apply", plan_type="profile_creation", '
                        "confirmed=true) with the same onboarding answers."
                    ),
                    requirement_ids=("FR-005", "OR-001", "OR-005", "SR-010"),
                )
            existing_entries = _existing_profile_entries(profile_path)
            replacing_bootstrap = bool(setup["active_profile_exists"]) and _is_bootstrap_profile(profile_path)
            if existing_entries and not replacing_bootstrap:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data={**plan, "existing_entries": existing_entries},
                    error="Profile creation target already contains files. Refusing to overwrite without an explicit backup/import strategy.",
                    requirement_ids=("FR-005", "OR-001", "NFR-002"),
                )
            activation_after_apply = self._profile_creation_activation_plan(profile_path.name)
            activation_policy_error = (
                None
                if activation_after_apply["activation_blocked_reason"]
                else self._created_profile_activation_policy_error()
            )
            if activation_policy_error:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=activation_policy_error,
                    requirement_ids=("FR-005", "OR-001", "SR-010", "NFR-002"),
                )
            try:
                created_files = self._create_profile_from_plan(
                    profile_path,
                    plan,
                    replace_existing_bootstrap=replacing_bootstrap,
                )
                active_state_written = (
                    self._activate_created_profile_if_supported(profile_path.name)
                    if activation_after_apply["active_state_write_planned"]
                    else False
                )
            except Exception as exc:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.ALLOW,
                    profile_path=str(profile_path),
                    error=str(exc),
                    requirement_ids=("OR-001", "NFR-002"),
                )
            return ProfileResult(
                ok=True,
                operation="governor_apply",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={
                    "created_profile": profile_path.name,
                    "created_files": created_files,
                    "plan_type": PROFILE_CREATION_PLAN_TYPE,
                    "profile_creation_mode": "guided_onboarding",
                    "confirmation_required": True,
                    "confirmed": True,
                    "overwrite_strategy": (
                        "replace_bootstrap_profile_only" if replacing_bootstrap else "create_new_profile_only"
                    ),
                    "onboarding_answers": plan["onboarding_answers"],
                    "normalized_onboarding_answers": plan["normalized_onboarding_answers"],
                    "alias_mappings_applied": plan["alias_mappings_applied"],
                    "onboarding_schema_version": plan["onboarding_schema"]["schema_version"],
                    "answer_file_map": plan["answer_file_map"],
                    "active_profile_name": profile_path.name,
                    "active_profile_state_written": active_state_written,
                    "activation_effective": bool(activation_after_apply["activation_effective_after_apply"]),
                    "activation_blocked_reason": activation_after_apply["activation_blocked_reason"],
                    "active_profile_source_after": activation_after_apply["active_profile_source_after"],
                    "activation_after_apply": {
                        **activation_after_apply,
                        "active_state_written": active_state_written,
                    },
                    "active_profile_state_file": (
                        str(self.active_profile_state_file) if self.active_profile_state_file else None
                    ),
                },
                requirement_ids=("FR-005", "OR-001", "OR-005", "SR-010"),
            )

        return self._execute(
            intent,
            "governor_apply",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def _reflection_memory_promotion_plan(self, profile: str, *, force: bool) -> dict[str, Any]:
        profile_name = profile.strip() or self.active_profile_name
        try:
            if not _same_profile_name(profile_name, self.active_profile_name):
                raise ValueError("Reflection-to-memory promotion may only target the active PLwC profile.")
            profile_path = self._resolve_profile(profile_name)
            setup = self.profile_setup_status(profile_name)
            if not setup["active_profile_exists"]:
                raise ValueError("Active profile setup is required before reflection-to-memory promotion.")
            if not setup["onboarding_complete"]:
                raise ValueError("Active profile onboarding/import must be complete before reflection-to-memory promotion.")
            plan = _automatic_reflection_memory_plan(
                profile_path=profile_path,
                memory_threshold=self.memory_write_threshold,
                memory_threshold_source=self.memory_write_threshold_source,
                force=force,
                plan_type=REFLECTION_MEMORY_PROMOTION_PLAN_TYPE,
            )
            plan.update(
                {
                    "active_profile_name": self.active_profile_name,
                    "target_profile_name": profile_name,
                    "profile_directory": str(profile_path),
                    "validation": {
                        "valid": True,
                        "reason": _automatic_memory_reason(
                            plan["revision_directives"],
                            plan["skipped_candidates"],
                        ),
                        "active_profile_only": True,
                        "profile_ready": True,
                    },
                    "apply_instruction": (
                        'Call plwc_governor(operation="apply", plan_type="reflection_memory_promotion", '
                        "confirmed=true). This memory-only path uses the current profile state directly."
                    ),
                }
            )
            return plan
        except ValueError as exc:
            profile_path = self.profile_root / (profile_name or self.active_profile_name)
            return _invalid_reflection_memory_promotion_plan(
                profile_path=profile_path,
                active_profile_name=self.active_profile_name,
                target_profile_name=profile_name,
                reason=str(exc),
                memory_threshold=self.memory_write_threshold,
                memory_threshold_source=self.memory_write_threshold_source,
            )

    def _apply_reflection_memory_promotion(
        self,
        profile: str,
        *,
        force: bool,
        confirmed: bool,
    ) -> ProfileResult:
        plan = self._reflection_memory_promotion_plan(profile, force=force)
        profile_path = Path(str(plan.get("profile_directory") or self.profile_root / self.active_profile_name)).resolve(strict=False)
        intent = self._write_intent("plwc_governor_apply", profile_path / "journal.md")

        def adapter_call() -> ProfileResult:
            if not plan["validation"]["valid"]:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=_compact_skipped_candidates(plan),
                    error=plan["validation"]["reason"],
                    requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "FR-REFMEM-001", "FR-REFMEM-011", "NFR-002"),
                )
            if plan["revision_directives"] and not confirmed:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=_compact_skipped_candidates({
                        **plan,
                        "status": "confirmation_required",
                        "result": "confirmation_required",
                        "confirmed": False,
                        "changes": [],
                    }),
                    error="reflection_memory_promotion requires explicit confirmation.",
                    requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "FR-REFMEM-004", "NFR-002"),
                )
            apply_result = _apply_automatic_reflection_memory_plan(
                profile_path=profile_path,
                plan=plan,
                confirmed=confirmed,
                today=None,
            )
            ok = not apply_result.get("errors") and apply_result.get("decision") != "review_required"
            return ProfileResult(
                ok=bool(ok),
                operation="governor_apply",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data=_compact_skipped_candidates(apply_result),
                error=None if ok else "; ".join(apply_result.get("errors") or [str(apply_result.get("reason") or "Reflection-to-memory promotion did not apply.")]),
                requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "FR-REFMEM-004", "FR-REFMEM-005", "FR-REFMEM-007", "NFR-002"),
            )

        return self._execute(
            intent,
            "governor_apply",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def _runtime_call(
        self,
        operation: str,
        profile: str,
        *,
        task_context: str,
        run_governor: bool = False,
        governor_apply: bool = False,
        governor_force: bool = False,
        governor_confirmed: bool = False,
    ) -> ProfileResult:
        try:
            profile_path = self._resolve_profile(profile)
        except ValueError as exc:
            return _profile_error(operation, str(exc), ("NFR-002",))
        setup = self.profile_setup_status(profile)
        if not setup["active_profile_exists"]:
            missing_files = setup.get("missing_files") or []
            error = (
                f"Missing required profile files: {', '.join(missing_files)}"
                if setup.get("selected_profile_exists") and missing_files
                else "Active profile setup is required."
            )
            return ProfileResult(
                ok=False,
                operation=operation,
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data=setup,
                error=error,
                requirement_ids=("OR-001", "FR-002", "NFR-002"),
            )
        intent = PolicyIntent(
            tool_name=f"plwc_{operation}",
            action=IntentAction.READ if not governor_apply else IntentAction.WRITE,
            target_path=str(profile_path),
            metadata={"allowed_roots": [self.profile_root]},
        )
        if governor_apply:
            intent = self._write_intent("plwc_governor_apply", profile_path / "journal.md")

        def adapter_call() -> ProfileResult:
            try:
                runtime = self._runtime_callable or self._load_runtime_callable()
                with _pba_threshold_environment(
                    memory_write_threshold=self.memory_write_threshold,
                    persona_write_threshold=self.persona_write_threshold,
                    temperament_write_threshold=self.temperament_write_threshold,
                    memory_write_threshold_source=self.memory_write_threshold_source,
                    persona_write_threshold_source=self.persona_write_threshold_source,
                    temperament_write_threshold_source=self.temperament_write_threshold_source,
                ):
                    runtime_kwargs = {
                        "task_context": task_context,
                        "run_governor": run_governor,
                        "governor_apply": governor_apply,
                        "governor_force": governor_force,
                    }
                    if runtime is run_plwc_profile_runtime:
                        runtime_kwargs["governor_confirmed"] = governor_confirmed
                    data = runtime(
                        profile_path,
                        **runtime_kwargs,
                    )
            except Exception as exc:
                return ProfileResult(
                    ok=False,
                    operation=operation,
                    policy_decision=PolicyDecision.ALLOW,
                    profile_path=str(profile_path),
                    error=str(exc),
                    requirement_ids=("NFR-002",),
                )
            data = {
                **data,
                "configured_active_profile": setup["configured_active_profile"],
                "resolved_active_profile": setup["resolved_active_profile"],
                "active_profile_exists": setup["active_profile_exists"],
                "active_profile_name": setup["active_profile_name"],
                "active_profile_source": setup["active_profile_source"],
                "active_state_profile": setup.get("active_state_profile"),
                "mismatch_reason": setup.get("mismatch_reason"),
                "active_profile_state_file": setup["active_profile_state_file"],
                "onboarding_target_profile": setup["onboarding_target_profile"],
                "profile_exists": setup["profile_exists"],
                "profile_valid": setup["profile_valid"],
                "selected_profile_exists": setup["selected_profile_exists"],
                "selected_profile_valid": setup["selected_profile_valid"],
                "status": setup["status"],
                "missing_files": setup["missing_files"],
                "available_profiles": setup["available_profiles"],
                "available_profile_names": setup["available_profile_names"],
                "profile_runtime_available": setup["profile_runtime_available"],
                "profile_runtime_reason": setup["profile_runtime_reason"],
                "profile_activation_supported": setup["profile_activation_supported"],
                "onboarding_required": setup["onboarding_required"],
                "onboarding_complete": setup["onboarding_complete"],
                "profile_kind": setup["profile_kind"],
                "startup_message": setup["startup_message"],
                "onboarding_questions": setup["onboarding_questions"],
                "next_action": setup["next_action"],
                "next_actions": setup["next_actions"],
                "profile_schema_validation": setup.get("profile_schema_validation", data.get("profile_schema_validation")),
                "governance_thresholds": {
                    "memory_write_threshold": self.memory_write_threshold,
                    "persona_write_threshold": self.persona_write_threshold,
                    "temperament_write_threshold": self.temperament_write_threshold,
                },
            }
            ok = bool(data.get("ok", True)) and not data.get("errors")
            return ProfileResult(
                ok=ok,
                operation=operation,
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data=data,
                error="; ".join(data.get("errors", [])) if data.get("errors") else None,
                requirement_ids=("FR-002", "FR-003", "FR-005", "SR-010"),
            )

        return self._execute(intent, operation, profile_path, adapter_call)

    def _execute(
        self,
        intent: PolicyIntent,
        operation: str,
        profile_path: Path,
        adapter_call: Callable[[], ProfileResult],
        *,
        guarded_write: bool = False,
    ) -> ProfileResult:
        execution = execute_with_policy(
            intent,
            self._guarded_adapter_call(
                operation,
                profile_path,
                adapter_call,
                guarded_write=guarded_write,
            ),
            self.policy_engine,
        )
        if not execution.executed:
            return ProfileResult(
                ok=False,
                operation=operation,
                policy_decision=execution.policy.decision,
                profile_path=str(profile_path),
                error=execution.policy.reason,
                requirement_ids=execution.policy.requirement_ids,
            )
        return execution.adapter_result

    def _guarded_adapter_call(
        self,
        operation: str,
        profile_path: Path,
        adapter_call: Callable[[], ProfileResult],
        *,
        guarded_write: bool,
    ) -> Callable[[], ProfileResult]:
        def call() -> ProfileResult:
            if not guarded_write:
                return self._call_fail_closed(operation, profile_path, adapter_call)

            lock = _profile_write_lock(profile_path)
            if not lock.acquire(blocking=False):
                return ProfileResult(
                    ok=False,
                    operation=operation,
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    error="Governed profile write already in progress.",
                    requirement_ids=("FR-005", "NFR-002"),
                )
            try:
                return self._call_fail_closed(operation, profile_path, adapter_call)
            finally:
                lock.release()

        return call

    def _call_fail_closed(
        self,
        operation: str,
        profile_path: Path,
        adapter_call: Callable[[], ProfileResult],
    ) -> ProfileResult:
        try:
            return adapter_call()
        except Exception as exc:
            return ProfileResult(
                ok=False,
                operation=operation,
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                error=str(exc),
                requirement_ids=("NFR-002",),
            )

    def _write_intent(self, tool_name: str, target_path: Path) -> PolicyIntent:
        return PolicyIntent(
            tool_name=tool_name,
            action=IntentAction.WRITE,
            target_path=str(target_path),
            metadata={
                "allowed_roots": [self.profile_root],
                "governed_profile_write": True,
            },
        )

    def _activation_write_intent(self, target_path: Path) -> PolicyIntent:
        return PolicyIntent(
            tool_name="plwc_governor_apply",
            action=IntentAction.WRITE,
            target_path=str(target_path),
            metadata={
                "allowed_roots": [target_path.parent],
                "governed_profile_write": True,
            },
        )

    def _resolve_profile(self, profile: str) -> Path:
        cleaned = _validate_profile_name(profile)
        profile_path = (self.profile_root / cleaned).resolve(strict=False)
        if not _is_inside_or_same(profile_path, self.profile_root):
            raise ValueError("Profile path must stay inside profiles_path.")
        # RC12-GEN-001 — the universal choke point: publish the active profile's
        # persona/user aliases so the INNER gate (and insight/classification) can
        # block name-based self-claims without a hard-coded persona name. Setting it
        # here means no profile-touching operation can reach the gate name-blind.
        values = _simple_key_value_lines(_profile_governance_text(profile_path))
        set_active_inner_aliases(
            _parse_alias_list(values.get("persona_aliases")),
            _parse_alias_list(values.get("user_aliases")),
        )
        return profile_path

    def _reflection_condensation_plan(self, profile: str) -> dict[str, Any]:
        profile_name = profile.strip() or self.active_profile_name
        try:
            if not _same_profile_name(profile_name, self.active_profile_name):
                raise ValueError("Reflection condensation may only target the active PLwC profile.")
            profile_path = self._resolve_profile(profile_name)
            setup = self.profile_setup_status(profile_name)
            if not setup["active_profile_exists"]:
                raise ValueError("Active profile setup is required before reflection condensation.")
            if not setup["onboarding_complete"]:
                raise ValueError("Active profile onboarding/import must be complete before reflection condensation.")
            reflection_text = (profile_path / "reflection.md").read_text(encoding="utf-8")
            journal_text = (profile_path / "journal.md").read_text(encoding="utf-8") if (profile_path / "journal.md").exists() else ""
            entries, invalid_entries = _parse_pba2_reflection_entries_detailed(reflection_text)
            processed_ids = _processed_reflection_entry_ids(journal_text)
            directives = _build_reflection_condensation_directives(
                profile_path=profile_path,
                profile_name=profile_name,
                entries=entries,
                processed_ids=processed_ids,
                memory_threshold=self.memory_write_threshold,
                persona_threshold=self.persona_write_threshold,
                temperament_threshold=self.temperament_write_threshold,
                memory_threshold_source=self.memory_write_threshold_source,
                persona_threshold_source=self.persona_write_threshold_source,
                temperament_threshold_source=self.temperament_write_threshold_source,
            )
            valid = True
            reason = "Reflection condensation plan created."
        except ValueError as exc:
            profile_path = self.profile_root / (profile_name or self.active_profile_name)
            entries = []
            invalid_entries = []
            processed_ids = set()
            directives = []
            valid = False
            reason = str(exc)

        if invalid_entries:
            directives = []
            decision = "review_required"
            state = "review_required"
            reason = "Reflection backlog contains malformed entries that require user review."
        else:
            decision = "planned" if directives else "no_op"
            state = "planned" if directives else "no_op"
        changed_files = sorted({directive["expected_changed_file"] for directive in directives})
        if directives or valid:
            changed_files.append("journal.md")
        changed_files = _unique_preserving_order(changed_files)
        file_snapshots = _file_snapshots_for_directives(profile_path, directives)
        plan_result = "planned" if directives else state
        journal_reason = reason if directives or state == "review_required" else "No unprocessed eligible reflection entries."
        plan_id = _reflection_condensation_plan_id(
            profile_name=profile_name,
            directives=directives,
            file_snapshots=file_snapshots,
            processed_ids=processed_ids,
        )
        journal_preview = _governor_journal_payload(
            plan_type=REFLECTION_CONDENSATION_PLAN_TYPE,
            profile_name=profile_name,
            plan_id=plan_id,
            directive_ids=[directive["directive_id"] for directive in directives],
            decision=decision,
            state=state,
            changed_files=changed_files,
            restored_files=[],
            candidate_summary=_condensation_candidate_summary(entries, directives),
            evidence=_condensation_evidence(entries, directives),
            trust=_condensation_trust(entries, directives),
            confidence=_confidence_from_trust(_condensation_trust(entries, directives)),
            threshold_used={
                "memory_write_threshold": self.memory_write_threshold,
                "persona_write_threshold": self.persona_write_threshold,
                "temperament_write_threshold": self.temperament_write_threshold,
            },
            threshold_source={
                "memory_write_threshold": self.memory_write_threshold_source,
                "persona_write_threshold": self.persona_write_threshold_source,
                "temperament_write_threshold": self.temperament_write_threshold_source,
            },
            file_snapshots=file_snapshots,
            reason=journal_reason,
            result=plan_result,
            source_entry_ids=[directive["source_entry_id"] for directive in directives],
        )
        plan = {
            "plan_type": REFLECTION_CONDENSATION_PLAN_TYPE,
            "plan_id": plan_id,
            "planned_action": "Condense eligible PBA2 reflection backlog entries through governed PLwC directives.",
            "confirmation_required": True,
            "confirmed": False,
            "active_profile_name": self.active_profile_name,
            "target_profile_name": profile_name,
            "profile_directory": str(profile_path),
            "entry_count": len(entries),
            "invalid_entry_count": len(invalid_entries),
            "invalid_entries": invalid_entries,
            "processed_entry_ids": sorted(processed_ids),
            "directive_ids": [directive["directive_id"] for directive in directives],
            "revision_directives": directives,
            "file_snapshots": file_snapshots,
            "decision": decision,
            "state": state,
            "result": plan_result,
            "lifecycle_states": list(GOVERNOR_LIFECYCLE_STATES),
            "expected_changed_files": changed_files,
            "plan_preview": {
                "journal_event": journal_preview,
                "directives": directives,
            },
            "validation": {
                "valid": valid,
                "reason": reason,
                "active_profile_only": _same_profile_name(profile_name, self.active_profile_name),
                "profile_ready": valid,
            },
            "apply_instruction": (
                'Call plwc_governor(operation="apply", plan_type="reflection_condensation", '
                "confirmed=true, plan_id=<this plan_id>), or use the backward-compatible "
                "onboarding_answers.approved_plan payload."
            ),
        }
        plan["pending_plan"] = self._store_reflection_condensation_pending_plan(plan)
        return plan

    def _apply_reflection_condensation(
        self,
        profile: str,
        *,
        onboarding_answers: dict[str, Any] | None,
        confirmed: bool,
        plan_id: str = "",
    ) -> ProfileResult:
        pending_record: dict[str, Any] | None = None
        plan_source = "plan_id" if plan_id.strip() else "approved_plan"
        if plan_id.strip():
            loaded_plan = self._load_reflection_condensation_pending_plan(plan_id.strip())
            if not loaded_plan["ok"]:
                return _condensation_reference_error(
                    profile_path=self.profile_root / (profile.strip() or self.active_profile_name),
                    plan_id=plan_id.strip(),
                    plan_source=plan_source,
                    reason=loaded_plan["error"],
                    error_category=loaded_plan["error_category"],
                )
            pending_record = loaded_plan["record"]
            approved_plan = dict(pending_record["approved_plan"])
        else:
            approved_plan = _approved_plan_from_answers(onboarding_answers)
        if not approved_plan:
            fallback_profile = profile.strip() or self.active_profile_name
            try:
                profile_path = self._resolve_profile(fallback_profile)
            except ValueError:
                profile_path = self.profile_root / fallback_profile
            return ProfileResult(
                ok=False,
                operation="governor_apply",
                policy_decision=PolicyDecision.DENY,
                profile_path=str(profile_path),
                data={
                    "plan_type": REFLECTION_CONDENSATION_PLAN_TYPE,
                    "plan_id": plan_id.strip(),
                    "plan_source": plan_source,
                    "decision": "rejected",
                    "state": "rejected",
                    "result": "rejected",
                },
                error=(
                    "reflection_condensation apply requires plan_id or onboarding_answers.approved_plan "
                    'from plwc_governor(operation="plan").'
                ),
                error_category="missing_plan_reference",
                requirement_ids=(*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "NFR-002"),
            )
        profile_name = profile.strip() or str(approved_plan.get("target_profile_name") or self.active_profile_name)
        if pending_record is not None:
            pending_profile = str(pending_record.get("profile_name") or "")
            pending_active = str(pending_record.get("active_profile_name") or "")
            requested_profile = profile.strip()
            if requested_profile and not _same_profile_name(requested_profile, pending_profile):
                return _condensation_reference_error(
                    profile_path=self.profile_root / profile_name,
                    plan_id=plan_id.strip(),
                    plan_source=plan_source,
                    reason=(
                        "Cross-profile pending plan apply is not allowed. "
                        f"Pending plan profile is {pending_profile}, requested profile is {requested_profile}."
                    ),
                    error_category="cross_profile_plan_denied",
                )
            if not _same_profile_name(pending_profile, str(approved_plan.get("target_profile_name") or "")):
                return _condensation_reference_error(
                    profile_path=self.profile_root / profile_name,
                    plan_id=plan_id.strip(),
                    plan_source=plan_source,
                    reason="Pending plan profile does not match its approved plan snapshot.",
                    error_category="pending_plan_tampered",
                )
            if not _same_profile_name(pending_active, self.active_profile_name):
                return _condensation_reference_error(
                    profile_path=self.profile_root / profile_name,
                    plan_id=plan_id.strip(),
                    plan_source=plan_source,
                    reason=(
                        "Cross-profile pending plan apply is not allowed. "
                        f"Active profile is {self.active_profile_name}, pending plan active profile is {pending_active}."
                    ),
                    error_category="cross_profile_plan_denied",
                )
            profile_name = pending_profile
            if pending_record.get("consumed_at"):
                return _condensation_already_processed_result(
                    profile_path=self.profile_root / profile_name,
                    approved_plan=approved_plan,
                    plan_source=plan_source,
                    consumed_at=str(pending_record.get("consumed_at") or ""),
                )
        try:
            profile_path = self._resolve_profile(profile_name)
        except ValueError as exc:
            return _profile_error("governor_apply", str(exc), ("NFR-002",))

        if not confirmed:
            return _condensation_reference_error(
                profile_path=profile_path,
                plan_id=str(approved_plan.get("plan_id") or plan_id.strip()),
                plan_source=plan_source,
                reason="reflection_condensation requires explicit confirmation.",
                error_category="unconfirmed_apply",
                approved_plan=approved_plan,
            )
        intent = self._write_intent("plwc_governor_apply", profile_path / "journal.md")

        def adapter_call() -> ProfileResult:
            if not _same_profile_name(profile_name, self.active_profile_name):
                return _condensation_apply_result(
                    profile_path=profile_path,
                    approved_plan=approved_plan,
                    ok=False,
                    decision="rejected",
                    state="rejected",
                    reason="Reflection condensation may only target the active PLwC profile.",
                    result="rejected",
                    requirement_ids=(*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "NFR-002"),
                )
            if approved_plan.get("plan_type") != REFLECTION_CONDENSATION_PLAN_TYPE:
                return _condensation_apply_result(
                    profile_path=profile_path,
                    approved_plan=approved_plan,
                    ok=False,
                    decision="rejected",
                    state="rejected",
                    reason="Approved plan must have plan_type=reflection_condensation.",
                    result="rejected",
                    requirement_ids=(*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "NFR-002"),
                )

            directives = list(approved_plan.get("revision_directives") or [])
            validation_error = _validate_condensation_approved_plan(profile_path=profile_path, approved_plan=approved_plan)
            if validation_error:
                return _condensation_apply_result(
                    profile_path=profile_path,
                    approved_plan=approved_plan,
                    ok=False,
                    decision=validation_error["decision"],
                    state=validation_error["state"],
                    reason=validation_error["reason"],
                    result=validation_error["result"],
                    error_category=validation_error["error_category"],
                    requirement_ids=(*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "FR-PBA2-GOLD-007", "FR-PBA2-GATE-005"),
                )
            stale = _stale_directives(profile_path=profile_path, directives=directives)
            if stale:
                journal_payload = _condensation_journal_payload(
                    approved_plan=approved_plan,
                    decision="stale",
                    state="stale",
                    changed_files=["journal.md"],
                    restored_files=[],
                    reason='Approved plan is stale; re-run plwc_governor(operation="plan").',
                    result="stale",
                    error_category="stale_plan",
                    stale_directives=stale,
                )
                _append_governor_journal_event(profile_path, journal_payload)
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.ALLOW,
                    profile_path=str(profile_path),
                    data={
                        **approved_plan,
                        "confirmed": True,
                        "decision": "stale",
                        "state": "stale",
                        "result": "stale",
                        "changed_files": ["journal.md"],
                        "restored_files": [],
                        "stale_directives": stale,
                        "journal_event": journal_payload,
                    },
                    error='Approved plan is stale; re-run plwc_governor(operation="plan").',
                    requirement_ids=PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS,
                )

            apply_result = _apply_condensation_directives_transactionally(
                profile_path=profile_path,
                approved_plan=approved_plan,
                directives=directives,
            )
            if pending_record is not None and apply_result["ok"]:
                self._mark_reflection_condensation_plan_consumed(
                    str(pending_record["plan_id"]),
                    apply_result=apply_result,
                )
            return ProfileResult(
                ok=bool(apply_result["ok"]),
                operation="governor_apply",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={**approved_plan, **apply_result, "plan_source": plan_source},
                error=None if apply_result["ok"] else apply_result["reason"],
                requirement_ids=PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS,
            )

        return self._execute(
            intent,
            "governor_apply",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def _pending_plan_path(self, plan_id: str) -> Path:
        if self.pending_plan_root is None:
            raise ValueError("pending_plan_root is not configured.")
        _validate_pending_plan_id(plan_id)
        root = self.pending_plan_root.resolve(strict=False)
        plan_path = (root / f"{plan_id}.json").resolve(strict=False)
        if not _is_inside_or_same(plan_path, root):
            raise ValueError("Pending plan path escapes pending_plan_root.")
        return plan_path

    def _store_reflection_condensation_pending_plan(self, approved_plan: dict[str, Any]) -> dict[str, Any]:
        plan_id = str(approved_plan.get("plan_id") or "")
        if self.pending_plan_root is None:
            return {
                "saved": False,
                "reason": "pending_plan_root is not configured; use onboarding_answers.approved_plan fallback.",
            }
        try:
            plan_path = self._pending_plan_path(plan_id)
        except ValueError as exc:
            return {"saved": False, "reason": str(exc)}
        if approved_plan.get("plan_type") != REFLECTION_CONDENSATION_PLAN_TYPE:
            return {"saved": False, "reason": "Only reflection_condensation plans are stored."}

        canonical_plan_hash = _stable_hash(approved_plan)
        record = {
            "schema_version": PENDING_PLAN_SCHEMA_VERSION,
            "plan_id": plan_id,
            "plan_type": REFLECTION_CONDENSATION_PLAN_TYPE,
            "profile_name": str(approved_plan.get("target_profile_name") or ""),
            "active_profile_name": self.active_profile_name,
            "approved_plan": approved_plan,
            "canonical_plan_hash": canonical_plan_hash,
            "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "consumed_at": None,
            "apply_result": None,
        }
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(plan_path, json.dumps(record, indent=2, sort_keys=True) + "\n")
        return {
            "saved": True,
            "plan_id": plan_id,
            "location": "runtime_state",
            "profile_root_accessible": False,
            "workspace_accessible": False,
            "canonical_plan_hash": canonical_plan_hash,
        }

    def _load_reflection_condensation_pending_plan(self, plan_id: str) -> dict[str, Any]:
        try:
            plan_path = self._pending_plan_path(plan_id)
        except ValueError as exc:
            return {"ok": False, "error": str(exc), "error_category": "invalid_plan_id"}
        if not plan_path.exists():
            return {
                "ok": False,
                "error": "Unknown pending reflection_condensation plan_id.",
                "error_category": "unknown_plan_id",
            }
        try:
            record = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "error": f"Pending plan could not be read safely: {exc}",
                "error_category": "pending_plan_tampered",
            }
        if not isinstance(record, dict):
            return {
                "ok": False,
                "error": "Pending plan record must be a JSON object.",
                "error_category": "pending_plan_tampered",
            }
        approved_plan = record.get("approved_plan")
        expected_hash = record.get("canonical_plan_hash")
        if (
            record.get("schema_version") != PENDING_PLAN_SCHEMA_VERSION
            or record.get("plan_id") != plan_id
            or record.get("plan_type") != REFLECTION_CONDENSATION_PLAN_TYPE
            or not isinstance(approved_plan, dict)
            or not isinstance(expected_hash, str)
        ):
            return {
                "ok": False,
                "error": "Pending plan record failed schema validation.",
                "error_category": "pending_plan_tampered",
            }
        if approved_plan.get("plan_id") != plan_id or approved_plan.get("plan_type") != REFLECTION_CONDENSATION_PLAN_TYPE:
            return {
                "ok": False,
                "error": "Pending plan snapshot does not match its record metadata.",
                "error_category": "pending_plan_tampered",
            }
        if _stable_hash(approved_plan) != expected_hash:
            return {
                "ok": False,
                "error": "Pending plan snapshot hash mismatch.",
                "error_category": "pending_plan_tampered",
            }
        return {"ok": True, "record": record}

    def _mark_reflection_condensation_plan_consumed(self, plan_id: str, *, apply_result: dict[str, Any]) -> None:
        loaded_plan = self._load_reflection_condensation_pending_plan(plan_id)
        if not loaded_plan["ok"]:
            raise RuntimeError(loaded_plan["error"])
        record = dict(loaded_plan["record"])
        record["consumed_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        record["apply_result"] = {
            "decision": apply_result.get("decision"),
            "state": apply_result.get("state"),
            "result": apply_result.get("result"),
            "changed_files": list(apply_result.get("changed_files") or []),
            "restored_files": list(apply_result.get("restored_files") or []),
        }
        _atomic_write_text(
            self._pending_plan_path(plan_id),
            json.dumps(record, indent=2, sort_keys=True) + "\n",
        )

    def _promotion_plan(
        self,
        profile: str,
        *,
        plan_type: str,
        onboarding_answers: dict[str, Any] | None,
        force: bool = False,
    ) -> dict[str, Any]:
        answers = _normalize_promotion_answers(onboarding_answers)
        profile_name = profile.strip() or self.active_profile_name
        target_file = _promotion_target_file(plan_type)
        try:
            if not _same_profile_name(profile_name, self.active_profile_name):
                raise ValueError("Memory/persona promotion may only target the active PLwC profile.")
            profile_path = self._resolve_profile(profile_name)
            setup = self.profile_setup_status(profile_name)
            if not setup["active_profile_exists"]:
                raise ValueError("Active profile setup is required before governor promotion.")
            if not setup["onboarding_complete"]:
                raise ValueError("Active profile onboarding/import must be complete before governor promotion.")
            evaluation = _evaluate_promotion_candidate(
                plan_type=plan_type,
                answers=answers,
                target_text=(profile_path / target_file).read_text(encoding="utf-8"),
                memory_threshold=self.memory_write_threshold,
                persona_threshold=self.persona_write_threshold,
                temperament_threshold=self.temperament_write_threshold,
                memory_threshold_source=self.memory_write_threshold_source,
                persona_threshold_source=self.persona_write_threshold_source,
                temperament_threshold_source=self.temperament_write_threshold_source,
                force=force,
            )
            valid = True
            reason = evaluation["reason"]
        except ValueError as exc:
            profile_path = self.profile_root / (profile_name or self.active_profile_name)
            setup = {}
            evaluation = _invalid_promotion_evaluation(plan_type=plan_type, target_file=target_file, reason=str(exc))
            valid = False
            reason = str(exc)

        target_snapshot = _file_snapshot(profile_path / target_file) if valid else _missing_file_snapshot()
        directive = _promotion_revision_directive(
            plan_type=plan_type,
            profile_name=profile_name,
            target_file=target_file,
            evaluation=evaluation,
            expected_precondition=target_snapshot,
        )
        plan_id = _promotion_plan_id(
            plan_type=plan_type,
            profile_name=profile_name,
            target_file=target_file,
            evaluation=evaluation,
        )
        return {
            "plan_type": plan_type,
            "plan_id": plan_id,
            "planned_action": _promotion_planned_action(plan_type),
            "confirmation_required": True,
            "confirmed": False,
            "active_profile_name": self.active_profile_name,
            "target_profile_name": profile_name,
            "profile_directory": str(profile_path),
            "target_file": target_file,
            "candidate_summary": evaluation["candidate_summary"],
            "evidence": evaluation["evidence"],
            "confidence": evaluation["confidence"],
            "trust": evaluation["trust"],
            "marker": evaluation["marker"],
            "threshold_used": evaluation["threshold_used"],
            "threshold_source": evaluation["threshold_source"],
            "base_threshold_used": evaluation["base_threshold_used"],
            "base_threshold_source": evaluation["base_threshold_source"],
            "evidence_count": evaluation["evidence_count"],
            "distinct_evidence_dates": evaluation["distinct_evidence_dates"],
            "evidence_dates_used": evaluation.get("evidence_dates_used", []),
            "candidate_classification": evaluation["candidate_classification"],
            "classification_confidence": evaluation["classification_confidence"],
            "explicit_decision_detected": evaluation["explicit_decision_detected"],
            "admin_override_applied": evaluation.get("admin_override_applied", False),
            "admin_override_requested": evaluation.get("admin_override_requested", False),
            "eligibility_reason": evaluation["eligibility_reason"],
            "rejection_reason": evaluation["rejection_reason"],
            "decision": evaluation["decision"],
            "eligible_for_apply": evaluation["eligible_for_apply"],
            "reason": reason,
            "expected_changed_files": evaluation["expected_changed_files"],
            "directive_ids": [directive["directive_id"]],
            "revision_directives": [directive],
            "file_snapshots": {target_file: target_snapshot},
            "safety_notes": evaluation["safety_notes"],
            "plan_preview": {
                "target_file": target_file,
                "append_mode": directive["append_mode"],
                "proposed_content": directive["proposed_content"],
                "journal_event": _promotion_journal_payload(
                    plan_type=plan_type,
                    profile_name=profile_name,
                    plan_id=plan_id,
                    evaluation=evaluation,
                    changed_files=evaluation["expected_changed_files"],
                    result=_promotion_result_for_decision(evaluation["decision"]),
                    directive_ids=[directive["directive_id"]],
                    file_snapshots={target_file: target_snapshot},
                ),
            },
            "validation": {
                "valid": valid,
                "reason": reason,
                "active_profile_only": _same_profile_name(profile_name, self.active_profile_name),
                "profile_ready": bool(setup.get("active_profile_exists")) and bool(setup.get("onboarding_complete")),
                "protected_write_target": target_file in {"memory.md", "PERSONA.md", "TEMPERAMENT.md"},
            },
            "apply_instruction": (
                f'Call plwc_governor(operation="apply", plan_type="{plan_type}", '
                "confirmed=true) with the same candidate fields."
            ),
        }

    def _apply_promotion(
        self,
        profile: str,
        *,
        plan_type: str,
        onboarding_answers: dict[str, Any] | None,
        confirmed: bool,
        force: bool = False,
    ) -> ProfileResult:
        plan = self._promotion_plan(
            profile,
            plan_type=plan_type,
            onboarding_answers=onboarding_answers,
            force=force,
        )
        profile_path = Path(plan["profile_directory"]).resolve(strict=False)
        target_file = plan["target_file"]
        intent = self._write_intent("plwc_governor_apply", profile_path / target_file)

        def adapter_call() -> ProfileResult:
            if not plan["validation"]["valid"]:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=plan["validation"]["reason"],
                    requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "NFR-002"),
                )
            if not confirmed:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=(
                        f"{plan_type} requires explicit confirmation. Re-run "
                        'plwc_governor(operation="apply", confirmed=true).'
                    ),
                    requirement_ids=PBA2_GOVERNOR_PROMOTION_REQUIREMENTS,
                )

            target = profile_path / target_file
            journal = profile_path / "journal.md"
            target_changed = False
            changed_files: list[str] = []
            evaluation = {
                "candidate_summary": plan["candidate_summary"],
                "evidence": plan["evidence"],
                "confidence": plan["confidence"],
                "trust": plan["trust"],
                "marker": plan["marker"],
                "threshold_used": plan["threshold_used"],
                "threshold_source": plan["threshold_source"],
                "base_threshold_used": plan["base_threshold_used"],
                "base_threshold_source": plan["base_threshold_source"],
                "evidence_count": plan["evidence_count"],
                "distinct_evidence_dates": plan["distinct_evidence_dates"],
                "evidence_dates_used": plan.get("evidence_dates_used", []),
                "candidate_classification": plan["candidate_classification"],
                "classification_confidence": plan["classification_confidence"],
                "explicit_decision_detected": plan["explicit_decision_detected"],
                "admin_override_applied": plan.get("admin_override_applied", False),
                "admin_override_requested": plan.get("admin_override_requested", False),
                "eligibility_reason": plan["eligibility_reason"],
                "rejection_reason": plan["rejection_reason"],
                "decision": plan["decision"],
                "reason": plan["reason"],
                "expected_changed_files": plan["expected_changed_files"],
                "safety_notes": plan["safety_notes"],
            }

            if plan["eligible_for_apply"]:
                stale = _stale_directives(profile_path=profile_path, directives=plan["revision_directives"])
                if stale:
                    evaluation["decision"] = "stale"
                    evaluation["reason"] = (
                        'Promotion plan became stale before apply; re-run plwc_governor(operation="plan").'
                    )
                    journal_payload = _promotion_journal_payload(
                        plan_type=plan_type,
                        profile_name=plan["target_profile_name"],
                        plan_id=plan["plan_id"],
                        evaluation=evaluation,
                        changed_files=["journal.md"],
                        result="stale",
                        directive_ids=plan["directive_ids"],
                        file_snapshots=plan["file_snapshots"],
                        stale_directives=stale,
                    )
                    _append_governor_journal_event(profile_path, journal_payload)
                    return ProfileResult(
                        ok=False,
                        operation="governor_apply",
                        policy_decision=PolicyDecision.ALLOW,
                        profile_path=str(profile_path),
                        data={
                            **plan,
                            "confirmed": True,
                            "decision": "stale",
                            "state": "stale",
                            "result": "stale",
                            "changed_files": ["journal.md"],
                            "target_changed": False,
                            "stale_directives": stale,
                            "journal_event": journal_payload,
                        },
                        error='Promotion plan became stale before apply; re-run plwc_governor(operation="plan").',
                        requirement_ids=(*PBA2_GOVERNOR_PROMOTION_REQUIREMENTS, "FR-PBA2-REL-004"),
                    )
                current = target.read_text(encoding="utf-8") if target.exists() else ""
                proposed = plan["revision_directives"][0]["proposed_content"]
                if _target_contains_candidate(current, plan["candidate_summary"]):
                    evaluation["decision"] = "duplicate_noop"
                    evaluation["reason"] = "Exact duplicate candidate already exists in target file."
                else:
                    _atomic_write_text(target, _append_profile_block(current, proposed))
                    target_changed = True
                    changed_files.append(target_file)

            journal_payload = _promotion_journal_payload(
                plan_type=plan_type,
                profile_name=plan["target_profile_name"],
                plan_id=plan["plan_id"],
                evaluation=evaluation,
                changed_files=[*changed_files, "journal.md"],
                result=_promotion_result_for_decision(evaluation["decision"], target_changed=target_changed),
                directive_ids=plan["directive_ids"],
                file_snapshots=plan["file_snapshots"],
            )
            _append_governor_journal_event(profile_path, journal_payload)
            changed_files.append("journal.md")
            result_ok = evaluation["decision"] in {"approved_for_apply", "duplicate_noop"}
            return ProfileResult(
                ok=result_ok,
                operation="governor_apply",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={
                    **plan,
                    "confirmed": True,
                    "decision": evaluation["decision"],
                    "result": journal_payload["result"],
                    "changed_files": changed_files,
                    "target_changed": target_changed,
                    "journal_event": journal_payload,
                },
                error=None if result_ok else evaluation["reason"],
                requirement_ids=PBA2_GOVERNOR_PROMOTION_REQUIREMENTS,
            )

        return self._execute(
            intent,
            "governor_apply",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def _profile_import_plan(
        self,
        requested_profile: str,
        *,
        onboarding_answers: dict[str, Any] | None,
        overwrite_requested: bool,
    ) -> dict[str, Any]:
        answers = _normalize_profile_import_answers(onboarding_answers)
        raw_source = answers.get("source_profile", "")
        overwrite = overwrite_requested or _bool_answer(answers.get("overwrite", ""))
        try:
            source_path = _validate_profile_import_source(raw_source, profile_root=self.profile_root)
            target_name = _profile_import_target_name(
                requested_profile=requested_profile,
                answers=answers,
                source_path=source_path,
            )
            target_profile_path = self._resolve_profile(target_name)
            source_file_plan = _profile_import_source_file_plan(source_path)
            missing_source_files = [
                filename for filename in PBA2_IMPORT_REQUIRED_FILES if filename not in source_file_plan
            ]
            target_exists = target_profile_path.exists()
            existing_entries = _existing_profile_entries(target_profile_path)
            if overwrite:
                valid = False
                reason = "Profile import overwrite is not supported by this governed PLwC import flow."
            elif missing_source_files:
                valid = False
                reason = "Source profile is missing required PBA2 profile files."
            elif target_exists:
                valid = False
                reason = "Target profile already exists. Choose a new target_profile_name."
            else:
                valid = True
                reason = "Source profile can be imported into the PLwC-owned profiles_path."
        except ValueError as exc:
            source_path = None
            target_name = requested_profile.strip() or answers.get("target_profile_name", "")
            target_profile_path = None
            source_file_plan = {}
            missing_source_files = list(PBA2_IMPORT_REQUIRED_FILES)
            target_exists = False
            existing_entries = []
            valid = False
            reason = str(exc)

        import_files = sorted(source_file_plan)
        generated_files = [
            filename
            for filename in ("governance/config.yaml", "journal.md")
            if filename != "journal.md" or "journal.md" not in source_file_plan
        ]
        return {
            "plan_type": "profile_import",
            "planned_action": "Import an existing PBA2 profile into the PLwC-owned profiles_path.",
            "confirmation_required": True,
            "confirmed": False,
            "source_profile_directory": str(source_path) if source_path else raw_source,
            "target_profile_name": target_name,
            "target_profile_directory": str(target_profile_path) if target_profile_path else None,
            "target_profile_exists": target_exists,
            "existing_entries": existing_entries,
            "source_required_files": list(PBA2_IMPORT_REQUIRED_FILES),
            "source_optional_files": list(PBA2_IMPORT_OPTIONAL_FILES),
            "missing_source_files": missing_source_files,
            "imported_files": import_files,
            "generated_files": generated_files,
            "overwrite_requested": overwrite,
            "validation": {
                "valid": valid,
                "reason": reason,
                "source_profile_exists": source_path is not None and source_path.exists(),
                "source_required_files_present": not missing_source_files,
                "target_profile_exists": target_exists,
                "overwrite_supported": False,
            },
            "planned_writes": [
                {
                    "file": filename,
                    "source": "source_profile" if filename in source_file_plan else "plwc_generated",
                    "chars": source_file_plan[filename]["chars"] if filename in source_file_plan else None,
                    "bytes": source_file_plan[filename]["bytes"] if filename in source_file_plan else None,
                }
                for filename in (*import_files, *generated_files)
            ] if valid else [],
            "file_previews": {},
            "apply_instruction": (
                'Call plwc_governor(operation="apply", plan_type="profile_import", confirmed=true) '
                "with the same source_profile/target_profile_name values."
            ),
        }

    def _apply_profile_import(
        self,
        requested_profile: str,
        *,
        onboarding_answers: dict[str, Any] | None,
        confirmed: bool,
        overwrite_requested: bool,
    ) -> ProfileResult:
        plan = self._profile_import_plan(
            requested_profile,
            onboarding_answers=onboarding_answers,
            overwrite_requested=overwrite_requested,
        )
        target_profile = plan.get("target_profile_directory")
        profile_path = Path(target_profile).resolve(strict=False) if target_profile else self.profile_root
        intent_target = profile_path / "CORE.md" if target_profile else self.profile_root
        intent = self._write_intent("plwc_governor_apply", intent_target)

        def adapter_call() -> ProfileResult:
            if not plan["validation"]["valid"]:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=plan["validation"]["reason"],
                    requirement_ids=("FR-005", "FR-009", "FR-PBA2-GATE-001", "NFR-002"),
                )
            if not confirmed:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=str(profile_path),
                    data=plan,
                    error=(
                        "Profile import requires explicit confirmation. Re-run "
                        'plwc_governor(operation="apply", plan_type="profile_import", confirmed=true).'
                    ),
                    requirement_ids=("FR-005", "FR-009", "FR-PBA2-GATE-001", "SR-010"),
                )
            source_path = Path(plan["source_profile_directory"])
            created_files = self._copy_profile_import_files(
                source_path=source_path,
                target_profile_path=profile_path,
                target_profile_name=plan["target_profile_name"],
            )
            return ProfileResult(
                ok=True,
                operation="governor_apply",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=str(profile_path),
                data={
                    **plan,
                    "confirmed": True,
                    "created_profile": plan["target_profile_name"],
                    "created_files": created_files,
                    "import_mode": "pba2_profile_import",
                    "runtime_dependency": "plwc_internal_profile_runtime",
                },
                requirement_ids=("FR-005", "FR-009", "FR-PBA2-GATE-001", "SR-010"),
            )

        return self._execute(
            intent,
            "governor_apply",
            profile_path,
            adapter_call,
            guarded_write=True,
        )

    def _copy_profile_import_files(
        self,
        *,
        source_path: Path,
        target_profile_path: Path,
        target_profile_name: str,
    ) -> list[str]:
        source_file_plan = _profile_import_source_file_plan(source_path)
        missing_source_files = [
            filename for filename in PBA2_IMPORT_REQUIRED_FILES if filename not in source_file_plan
        ]
        if missing_source_files:
            raise RuntimeError(f"Source profile is missing required PBA2 profile files: {', '.join(missing_source_files)}")
        if target_profile_path.exists():
            raise RuntimeError(f"Refusing to overwrite existing profile directory: {target_profile_path}")

        target_profile_path.mkdir(parents=True, exist_ok=False)
        created_files: list[str] = []
        try:
            for filename in PBA2_IMPORT_ALLOWED_FILES:
                source_file = source_path / filename
                if not source_file.exists():
                    continue
                target = target_profile_path / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source_file.read_text(encoding="utf-8"), encoding="utf-8")
                created_files.append(filename)

            governance = target_profile_path / "governance" / "config.yaml"
            governance.parent.mkdir(parents=True, exist_ok=True)
            governance.write_text(
                _profile_governance_config(
                    profile_name=target_profile_name,
                    memory_write_threshold=self.memory_write_threshold,
                    persona_write_threshold=self.persona_write_threshold,
                    temperament_write_threshold=self.temperament_write_threshold,
                    confirmation_boundaries="Imported PBA2 profile. Confirm before changing profile, memory, persona, policy or protected files.",
                    profile_kind="imported_pba2",
                    onboarding_complete=True,
                ),
                encoding="utf-8",
            )
            created_files.append("governance/config.yaml")

            journal = target_profile_path / "journal.md"
            import_note = (
                f"\n- {datetime.now(timezone.utc).date().isoformat()}: "
                "PBA2 profile imported through governed PLwC profile import.\n"
            )
            if journal.exists():
                with journal.open("a", encoding="utf-8") as handle:
                    handle.write(import_note)
            else:
                journal.write_text("# Journal\n" + import_note, encoding="utf-8")
                created_files.append("journal.md")
            return created_files
        except Exception:
            _remove_created_profile_directory(target_profile_path)
            raise

    def _profile_activation_plan(self, requested_profile: str) -> dict[str, Any]:
        current_profile = self.active_profile_name
        state_file = self.active_profile_state_file
        try:
            requested = _validate_requested_activation_profile(requested_profile)
            target_profile_path = self._resolve_profile(requested)
            target_exists = target_profile_path.exists() and target_profile_path.is_dir()
            missing_files = _missing_profile_files(target_profile_path)
            required_present = target_exists and not missing_files
            state_ready = state_file is not None
            valid = target_exists and required_present and state_ready
            if not state_ready:
                reason = "PLwC active profile state file is not configured."
            elif not target_exists:
                reason = "Requested profile does not exist."
            elif missing_files:
                reason = "Requested profile is missing required files."
            else:
                reason = "Requested profile can be activated through governed PLwC state."
        except ValueError as exc:
            requested = requested_profile.strip()
            target_profile_path = None
            target_exists = False
            missing_files = list(PROFILE_REQUIRED_FILES)
            required_present = False
            valid = False
            reason = str(exc)

        preview_payload = (
            _active_profile_state_payload(requested, current_profile=current_profile)
            if valid
            else {}
        )
        return {
            "plan_type": "profile_activation",
            "planned_action": "Activate an existing PLwC profile through governed PLwC state.",
            "confirmation_required": True,
            "confirmed": False,
            "current_active_profile": current_profile,
            "requested_active_profile": requested,
            "profiles_path": str(self.profile_root),
            "target_profile_directory": str(target_profile_path) if target_profile_path else None,
            "target_profile_exists": target_exists,
            "required_profile_files_present": required_present,
            "missing_files": missing_files,
            "active_profile_source_before": self.active_profile_source,
            "active_profile_source_after": "plwc_state" if valid else self.active_profile_source,
            "active_profile_state_file": str(state_file) if state_file else None,
            "available_profiles": self.available_profiles(),
            "validation": {
                "valid": valid,
                "reason": reason,
                "target_profile_exists": target_exists,
                "required_profile_files_present": required_present,
                "missing_files": missing_files,
            },
            "planned_writes": [
                {
                    "file": str(state_file),
                    "source": "plwc_governor_apply",
                    "purpose": "set active_profile_name",
                    "value": requested,
                }
            ] if valid and state_file else [],
            "file_previews": {
                "active_profile.json": json.dumps(preview_payload, indent=2, sort_keys=True) + "\n"
            } if valid else {},
            "apply_instruction": (
                'Call plwc_governor(operation="apply", plan_type="profile_activation", confirmed=true) '
                "with the requested profile name."
            ),
        }

    def _apply_profile_activation(self, requested_profile: str, *, confirmed: bool) -> ProfileResult:
        plan = self._profile_activation_plan(requested_profile)
        state_file = self.active_profile_state_file
        if state_file is None:
            return ProfileResult(
                ok=False,
                operation="governor_apply",
                policy_decision=PolicyDecision.DENY,
                data=plan,
                error="PLwC active profile state file is not configured.",
                requirement_ids=("FR-005", "OR-001", "NFR-002"),
            )
        intent = self._activation_write_intent(state_file)

        def adapter_call() -> ProfileResult:
            if not plan["validation"]["valid"]:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=plan.get("target_profile_directory"),
                    data=plan,
                    error=plan["validation"]["reason"],
                    requirement_ids=("FR-005", "OR-001", "NFR-002"),
                )
            if not confirmed:
                return ProfileResult(
                    ok=False,
                    operation="governor_apply",
                    policy_decision=PolicyDecision.DENY,
                    profile_path=plan.get("target_profile_directory"),
                    data=plan,
                    error=(
                        "Profile activation requires explicit confirmation. Re-run "
                        'plwc_governor(operation="apply", plan_type="profile_activation", confirmed=true).'
                    ),
                    requirement_ids=("FR-005", "OR-001", "SR-010"),
                )
            payload = _active_profile_state_payload(
                plan["requested_active_profile"],
                current_profile=plan["current_active_profile"],
            )
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return ProfileResult(
                ok=True,
                operation="governor_apply",
                policy_decision=PolicyDecision.ALLOW,
                profile_path=plan.get("target_profile_directory"),
                data={
                    **plan,
                    "confirmed": True,
                    "active_profile_name": plan["requested_active_profile"],
                    "active_profile_source": "plwc_state",
                    "state_written": True,
                    "compile_instruction": 'Call plwc_profile(operation="compile") with no profile argument to load the activated profile.',
                },
                requirement_ids=("FR-005", "OR-001", "SR-010"),
            )

        return self._execute(
            intent,
            "governor_apply",
            state_file,
            adapter_call,
            guarded_write=True,
        )

    def _created_profile_activation_policy_error(self) -> str | None:
        if self.active_profile_state_file is None:
            return None
        execution = execute_with_policy(
            self._activation_write_intent(self.active_profile_state_file),
            lambda: True,
            self.policy_engine,
        )
        if execution.executed:
            return None
        return f"Active profile state update was denied: {execution.policy.reason}"

    def _created_profile_activation_blocker(self, profile_name: str) -> str | None:
        if self.configured_active_profile_name and not _same_profile_name(
            profile_name,
            self.configured_active_profile_name,
        ):
            return (
                "configured_active_profile_takes_precedence: Claude Desktop or security config "
                f"selects '{self.configured_active_profile_name}', so created profile '{profile_name}' "
                "will not become effective until the configured active profile is changed."
            )
        if self.active_profile_state_file is None and not _same_profile_name(profile_name, self.active_profile_name):
            return (
                "active_profile_state_unavailable: no PLwC active profile state file is configured, "
                f"so created profile '{profile_name}' cannot be activated automatically."
            )
        return None

    def _profile_creation_activation_plan(self, profile_name: str) -> dict[str, Any]:
        blocker = self._created_profile_activation_blocker(profile_name)
        active_state_write_planned = self.active_profile_state_file is not None and blocker is None
        effective_after_apply = blocker is None
        if blocker:
            next_action = (
                f"Set the active PLwC profile extension/config value to '{profile_name}', "
                "restart or reload Claude Desktop, then rerun plwc_status(scope=\"runtime\")."
            )
            source_after = self.active_profile_source
        elif self.configured_active_profile_name:
            next_action = 'Rerun plwc_status(scope="runtime") to verify the configured profile is ready.'
            source_after = self.active_profile_source
        elif active_state_write_planned:
            next_action = 'Rerun plwc_status(scope="runtime") to verify active_profile_source="plwc_state".'
            source_after = "plwc_state"
        else:
            next_action = 'Rerun plwc_status(scope="runtime") to verify the profile is ready.'
            source_after = self.active_profile_source
        return {
            "target_profile": profile_name,
            "configured_active_profile": self.configured_active_profile_name,
            "current_active_profile": self.active_profile_name,
            "active_profile_source_before": self.active_profile_source,
            "active_profile_source_after": source_after,
            "active_state_file": str(self.active_profile_state_file) if self.active_profile_state_file else None,
            "active_state_write_planned": active_state_write_planned,
            "activation_effective_after_apply": effective_after_apply,
            "activation_blocked_reason": blocker,
            "next_action": next_action,
        }

    def _ensure_profile_files(self, profile_path: Path) -> None:
        self._create_profile_from_template(profile_path)

    def _ensure_bootstrap_profile_if_needed(self, profile_path: Path) -> bool:
        if profile_path.exists() or not self.profile_root.exists():
            return False
        contents = _render_bootstrap_profile_contents(
            profile_name=profile_path.name,
            memory_write_threshold=self.memory_write_threshold,
            persona_write_threshold=self.persona_write_threshold,
            temperament_write_threshold=self.temperament_write_threshold,
        )
        profile_path.mkdir(parents=True, exist_ok=True)
        for filename in PROFILE_TEMPLATE_FILES:
            target = profile_path / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents[filename], encoding="utf-8")
        return True

    def _activate_created_profile_if_supported(self, profile_name: str) -> bool:
        if self.active_profile_state_file is None:
            return False
        validated_profile = _validate_profile_name(profile_name)
        state_file = self.active_profile_state_file
        intent = self._activation_write_intent(state_file)

        def adapter_call() -> bool:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps(
                    _active_profile_state_payload(validated_profile, current_profile=self.active_profile_name),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            return True

        execution = execute_with_policy(intent, adapter_call, self.policy_engine)
        if not execution.executed:
            raise RuntimeError(f"Active profile state update was denied: {execution.policy.reason}")
        return bool(execution.adapter_result)

    def _profile_creation_plan(
        self,
        profile: str,
        setup: dict[str, Any],
        onboarding_answers: dict[str, Any] | None,
    ) -> dict[str, Any]:
        validation = _validate_onboarding_answers(
            onboarding_answers,
            profile,
            persona_layer_enabled=self.persona_layer_enabled,
        )
        answers = validation["normalized_onboarding_answers"]
        contents = _render_profile_creation_contents(
            profile_name=profile,
            answers=answers,
            memory_write_threshold=self.memory_write_threshold,
            persona_write_threshold=self.persona_write_threshold,
            temperament_write_threshold=self.temperament_write_threshold,
        )
        field_questions = {
            field: question
            for field, question in (*PROFILE_ONBOARDING_FIELDS, *PROFILE_ONBOARDING_OPTIONAL_FIELDS)
        }
        unanswered_questions = [field_questions[field] for field in validation["missing_required_fields"]]
        active_fields = set(validation["active_fields"])
        approved_for_apply = validation["decision"] == "approved_for_apply"
        return {
            "plan_type": "profile_creation",
            "planned_action": "Create the active profile from governed onboarding answers.",
            "confirmation_required": True,
            "confirmed": False,
            "profile_creation_mode": "guided_onboarding",
            "active_profile_name": profile,
            "target_profile": profile,
            "onboarding_schema": profile_onboarding_schema(persona_layer_enabled=self.persona_layer_enabled),
            "onboarding_questions": list(profile_onboarding_questions(persona_layer_enabled=self.persona_layer_enabled)),
            "accepted_fields": validation["accepted_fields"],
            "active_fields": validation["active_fields"],
            "inactive_fields": validation["inactive_fields"],
            "required_fields": validation["required_fields"],
            "optional_fields": validation["optional_fields"],
            "unknown_fields": validation["unknown_fields"],
            "missing_required_fields": validation["missing_required_fields"],
            "suggested_mappings": validation["suggested_mappings"],
            "alias_mappings_applied": validation["alias_mappings_applied"],
            "normalized_onboarding_answers": answers,
            "onboarding_answers": answers,
            "question_answer_map": {
                question: answers[field]
                for field, question in (*PROFILE_ONBOARDING_FIELDS, *PROFILE_ONBOARDING_OPTIONAL_FIELDS)
            },
            "unanswered_questions": unanswered_questions,
            "answer_file_map": {
                filename: [field_questions[field] for field in fields if field in active_fields]
                for filename, fields in PROFILE_CREATION_FILE_MAP.items()
            },
            "decision": validation["decision"],
            "approved_for_apply": approved_for_apply,
            "onboarding_complete_after_apply": approved_for_apply,
            "validation_warning": validation["validation_warning"],
            "validation_error": validation["validation_error"],
            "validation": validation,
            "target_files": list(PROFILE_TEMPLATE_FILES),
            "planned_writes": [
                {
                    "file": filename,
                    "source": "generated_from_onboarding_answers",
                    "chars": len(contents[filename]),
                }
                for filename in PROFILE_TEMPLATE_FILES
            ],
            "file_previews": contents,
            "profile_directory": setup["active_profile_directory"],
            "activation_after_apply": self._profile_creation_activation_plan(profile),
            "apply_instruction": (
                'Call plwc_governor(operation="apply", plan_type="profile_creation", confirmed=true) '
                "with the same onboarding_answers to create the profile."
            ),
        }

    def _create_profile_from_plan(
        self,
        profile_path: Path,
        plan: dict[str, Any],
        *,
        replace_existing_bootstrap: bool = False,
    ) -> list[str]:
        profile_path.mkdir(parents=True, exist_ok=True)
        contents = plan["file_previews"]
        created_files: list[str] = []
        for filename in PROFILE_TEMPLATE_FILES:
            target = profile_path / filename
            if target.exists() and not replace_existing_bootstrap:
                raise RuntimeError(f"Refusing to overwrite existing profile file: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents[filename], encoding="utf-8")
            created_files.append(filename)
        return created_files

    def _create_profile_from_template(self, profile_path: Path) -> list[str]:
        profile_path.mkdir(parents=True, exist_ok=True)
        template_root = self.profile_root / "template"
        bundled_template_root = _bundled_template_root()
        created_files: list[str] = []
        for filename in PROFILE_TEMPLATE_FILES:
            target = profile_path / filename
            if target.exists():
                if not target.is_file():
                    raise RuntimeError(f"Profile target is not a file: {target}")
                continue
            source = template_root / filename
            if not source.exists() and bundled_template_root is not None:
                source = bundled_template_root / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                target.write_text("", encoding="utf-8")
            created_files.append(filename)
        return created_files

    def _load_runtime_callable(self) -> RuntimeCallable:
        if self._source_root_explicit and self.source_root.exists():
            if str(self.source_root) not in sys.path:
                sys.path.insert(0, str(self.source_root))
            from pba_adapters.api import run_runtime_json

            return run_runtime_json
        return run_plwc_profile_runtime


def _default_pba_source_root() -> Path:
    return (Path(__file__).resolve().parents[4] / "PBA2" / "src").resolve(strict=False)


def _bundled_template_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[3] / "profiles" / "template"
    return candidate if candidate.exists() else None


def _existing_profile_entries(profile_path: Path) -> list[str]:
    if not profile_path.exists():
        return []
    entries: list[str] = []
    for candidate in profile_path.rglob("*"):
        if candidate.is_file() or candidate.is_dir():
                entries.append(candidate.relative_to(profile_path).as_posix())
    return sorted(entries)


def _normalize_profile_import_answers(answers: dict[str, Any] | None) -> dict[str, str]:
    raw_answers = answers or {}
    normalized: dict[str, str] = {}
    for key, value in raw_answers.items():
        normalized[_normalize_answer_key(str(key))] = "" if value is None else str(value).strip()
    return {
        "source_profile": _first_answer(normalized, "sourceprofile", "sourceprofilepath", "sourcepath", "source"),
        "target_profile_name": _first_answer(
            normalized,
            "targetprofilename",
            "targetprofile",
            "targetname",
            "profilename",
            "name",
        ),
        "overwrite": _first_answer(normalized, "overwrite", "force"),
    }


def _first_answer(values: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = values.get(key, "")
        if value:
            return value
    return ""


def _bool_answer(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "y", "on"}


def _profile_import_target_name(
    *,
    requested_profile: str,
    answers: dict[str, str],
    source_path: Path,
) -> str:
    raw_name = requested_profile.strip() or answers.get("target_profile_name", "") or source_path.name
    return _validate_profile_name(raw_name)


def _validate_profile_import_source(source_profile: str, *, profile_root: Path) -> Path:
    if not source_profile.strip():
        raise ValueError("Profile import requires onboarding_answers.source_profile.")
    if _path_text_has_parent_traversal(source_profile):
        raise ValueError("Profile import source must not use parent traversal.")
    source = Path(source_profile).expanduser()
    if not source.is_absolute():
        raise ValueError("Profile import source must be an explicit absolute path.")
    if source.is_symlink():
        raise ValueError("Profile import source directory must not be a symlink.")
    try:
        resolved = source.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Profile import source cannot be read: {exc}") from exc
    if not resolved.is_dir():
        raise ValueError("Profile import source must be a directory.")
    if _is_filesystem_root(resolved) or _is_home_root(resolved) or _is_system_path(resolved):
        raise ValueError("Profile import source must be a user-scoped profile directory, not a broad system root.")
    if _is_inside_or_same(resolved, profile_root):
        raise ValueError("Profile import source must be outside the PLwC profiles_path.")
    return resolved


def _profile_import_source_file_plan(source_path: Path) -> dict[str, dict[str, int]]:
    plan: dict[str, dict[str, int]] = {}
    total_bytes = 0
    for filename in PBA2_IMPORT_ALLOWED_FILES:
        source_file = source_path / filename
        if not source_file.exists():
            continue
        if source_file.is_symlink():
            raise ValueError(f"Profile import refuses symlinked source file: {filename}")
        if not source_file.is_file():
            raise ValueError(f"Profile import source entry is not a file: {filename}")
        resolved_file = source_file.resolve(strict=True)
        if not _is_inside_or_same(resolved_file, source_path):
            raise ValueError(f"Profile import source file escapes source directory: {filename}")
        size = source_file.stat().st_size
        if size > MAX_PROFILE_IMPORT_FILE_BYTES:
            raise ValueError(f"Profile import source file exceeds the per-file size limit: {filename}")
        total_bytes += size
        if total_bytes > MAX_PROFILE_IMPORT_FILE_BYTES * len(PBA2_IMPORT_ALLOWED_FILES):
            raise ValueError("Profile import source exceeds the aggregate size limit.")
        try:
            chars = len(source_file.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError(f"Profile import source file must be UTF-8 text: {filename}") from exc
        plan[filename] = {"bytes": size, "chars": chars}
    return plan


def _remove_created_profile_directory(profile_path: Path) -> None:
    if profile_path.exists() and profile_path.is_dir():
        shutil.rmtree(profile_path)


def _parse_pba2_reflection_entries(text: str) -> list[dict[str, str]]:
    entries, _invalid_entries = _parse_pba2_reflection_entries_detailed(text)
    return entries


def _parse_pba2_reflection_entries_detailed(text: str) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    header_re = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s*\|\s*\[(?P<marker>[^\]]+)\]\s*\|\s*(?P<trust>[^\r\n]+)$",
        re.MULTILINE,
    )
    headers = list(header_re.finditer(text))
    entries: list[dict[str, str]] = []
    invalid_entries: list[dict[str, Any]] = []
    if not headers and re.search(r"^\d{4}-\d{2}-\d{2}\s*\|", text, flags=re.MULTILINE):
        invalid_entries.append(
            {
                "reason": "Malformed reflection header.",
                "line": _first_matching_line(text, r"^\d{4}-\d{2}-\d{2}\s*\|"),
            }
        )
        return entries, invalid_entries
    for index, header in enumerate(headers):
        block_end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.start():block_end].strip()
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 4:
            invalid_entries.append(
                {
                    "date": header.group("date"),
                    "reason": "Reflection entry must contain header, content, evidence and candidate fields.",
                    "line": lines[0] if lines else header.group(0),
                }
            )
            continue
        content = _reflection_labeled_value(lines, "Inhalt:")
        evidence = _reflection_labeled_value(lines, "Belegt durch:")
        candidate_for = _reflection_candidate_value(lines)
        if not content or not evidence:
            invalid_entries.append(
                {
                    "date": header.group("date"),
                    "reason": "Reflection entry is missing content or evidence.",
                    "line": lines[0],
                }
            )
            continue
        try:
            entry = {
                "date": _reflection_date(header.group("date")),
                "marker": _canonical_reflection_marker(header.group("marker")),
                "trust": _canonical_reflection_trust(confidence="", trust=header.group("trust")),
                "content": _single_line_required(content, "content"),
                "evidence": _single_line_required(evidence, "evidence"),
                "candidate_for": _single_line_optional(candidate_for, "candidate_for"),
                "raw": "\n".join(lines[:4]),
            }
        except ValueError as exc:
            invalid_entries.append(
                {
                    "date": header.group("date"),
                    "reason": str(exc),
                    "line": lines[0],
                }
            )
            continue
        entry["entry_id"] = _stable_hash(
            {
                "date": entry["date"],
                "marker": entry["marker"],
                "trust": entry["trust"],
                "content": entry["content"],
                "evidence": entry["evidence"],
                "candidate_for": entry["candidate_for"],
            }
        )
        entries.append(entry)
    return entries, invalid_entries


def _first_matching_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern)
    for line in text.splitlines():
        if regex.search(line):
            return line.strip()
    return ""


def _reflection_labeled_value(lines: list[str], label: str) -> str:
    for line in lines:
        if line.casefold().startswith(label.casefold()):
            return line.split(":", 1)[1].strip()
    return ""


def _reflection_candidate_value(lines: list[str]) -> str:
    for line in lines:
        if line.casefold().startswith("kandidat "):
            return line.split(":", 1)[1].strip() if ":" in line else ""
    return ""


def _normalize_candidate_target(value: str) -> str:
    cleaned = value.strip().casefold().replace("\\", "/")
    aliases = {
        "memory": "memory.md",
        "memory.md": "memory.md",
        "./memory.md": "memory.md",
        "persona": "PERSONA.md",
        "persona.md": "PERSONA.md",
        "./persona.md": "PERSONA.md",
        "temperament": "TEMPERAMENT.md",
        "temperament.md": "TEMPERAMENT.md",
        "./temperament.md": "TEMPERAMENT.md",
    }
    result = aliases.get(cleaned, cleaned)
    # Preserve canonical casing for known filenames regardless of how they were input.
    canonical_case = {"persona.md": "PERSONA.md", "temperament.md": "TEMPERAMENT.md"}
    return canonical_case.get(result.casefold(), result)


def _processed_reflection_entry_ids(journal_text: str) -> set[str]:
    processed: set[str] = set()
    for payload in _journal_json_payloads(journal_text):
        for entry_id in payload.get("source_entry_ids") or []:
            if isinstance(entry_id, str) and entry_id:
                processed.add(entry_id)
    return processed


def _journal_json_payloads(journal_text: str) -> list[dict[str, Any]]:
    payloads, _invalid_count = _journal_json_payloads_detailed(journal_text)
    return payloads


def _journal_json_payloads_detailed(journal_text: str) -> tuple[list[dict[str, Any]], int]:
    payloads: list[dict[str, Any]] = []
    invalid_count = 0
    for match in re.findall(r"```json\s*(.*?)\s*```", journal_text, flags=re.DOTALL):
        try:
            payload = json.loads(match)
        except json.JSONDecodeError:
            invalid_count += 1
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
        else:
            invalid_count += 1
    return payloads, invalid_count


def _build_reflection_condensation_directives(
    *,
    profile_path: Path,
    profile_name: str,
    entries: list[dict[str, str]],
    processed_ids: set[str],
    memory_threshold: int,
    persona_threshold: int,
    temperament_threshold: int,
    memory_threshold_source: str,
    persona_threshold_source: str,
    temperament_threshold_source: str,
) -> list[dict[str, Any]]:
    directives: list[dict[str, Any]] = []
    for entry in entries:
        if entry["entry_id"] in processed_ids:
            continue
        directive = _directive_for_reflection_entry(
            profile_path=profile_path,
            profile_name=profile_name,
            entry=entry,
            memory_threshold=memory_threshold,
            persona_threshold=persona_threshold,
            temperament_threshold=temperament_threshold,
            memory_threshold_source=memory_threshold_source,
            persona_threshold_source=persona_threshold_source,
            temperament_threshold_source=temperament_threshold_source,
        )
        if directive is not None:
            directives.append(directive)
    return directives


def _directive_for_reflection_entry(
    *,
    profile_path: Path,
    profile_name: str,
    entry: dict[str, str],
    memory_threshold: int,
    persona_threshold: int,
    temperament_threshold: int,
    memory_threshold_source: str,
    persona_threshold_source: str,
    temperament_threshold_source: str,
) -> dict[str, Any] | None:
    revision = _parse_revision_directive(entry["candidate_for"])
    if revision:
        return _revision_state_directive(
            profile_path=profile_path,
            profile_name=profile_name,
            entry=entry,
            revision=revision,
        )

    candidate_for = _normalize_candidate_target(entry["candidate_for"])
    if candidate_for == "memory.md":
        memory_policy = _entry_memory_policy_evaluation(
            entry,
            memory_threshold=memory_threshold,
            memory_threshold_source=memory_threshold_source,
        )
        accepted = bool(memory_policy["accepted"])
        reason = str(memory_policy["reason"])
        if not accepted:
            return None
        target_file = "memory.md"
        proposed_content = _format_memory_promotion_block(
            content=entry["content"],
            evidence=entry["evidence"],
            entry_date=entry["date"],
        )
        return _append_directive(
            profile_path=profile_path,
            profile_name=profile_name,
            entry=entry,
            target_file=target_file,
            target_section="ACTIVE",
            proposed_content=proposed_content,
            reason=reason,
            threshold_used=int(memory_policy["threshold_used"]),
            threshold_source=str(memory_policy["threshold_source"] or memory_threshold_source),
            candidate_classification=str(memory_policy["candidate_classification"]),
            classification_confidence=str(memory_policy["classification_confidence"]),
            explicit_decision_detected=bool(memory_policy["explicit_decision_detected"]),
        )

    if candidate_for == "PERSONA.md" or (entry["marker"].casefold() == "muster" and entry["trust"] == "hoch"):
        accepted, reason = _entry_passes_persona_policy(entry, persona_threshold=persona_threshold)
        if not accepted:
            return None
        target_file = "PERSONA.md"
        current = (profile_path / target_file).read_text(encoding="utf-8")
        proposed_content = _format_persona_promotion_block(
            content=entry["content"],
            evidence=entry["evidence"],
            entry_date=entry["date"],
            current_persona=current,
            marker=entry["marker"],
        )
        return _append_directive(
            profile_path=profile_path,
            profile_name=profile_name,
            entry=entry,
            target_file=target_file,
            target_section="ACTIVE",
            proposed_content=proposed_content,
            reason=reason,
            threshold_used=persona_threshold,
            threshold_source=persona_threshold_source,
        )

    if candidate_for == "TEMPERAMENT.md":
        accepted, reason = _entry_passes_temperament_policy(entry, temperament_threshold=temperament_threshold)
        if not accepted:
            return None
        target_file = "TEMPERAMENT.md"
        current = (profile_path / target_file).read_text(encoding="utf-8")
        proposed_content = _format_temperament_promotion_block(
            content=entry["content"],
            evidence=entry["evidence"],
            entry_date=entry["date"],
            current_temperament=current,
        )
        return _append_directive(
            profile_path=profile_path,
            profile_name=profile_name,
            entry=entry,
            target_file=target_file,
            target_section="ACTIVE",
            proposed_content=proposed_content,
            reason=reason,
            threshold_used=temperament_threshold,
            threshold_source=temperament_threshold_source,
        )

    return None


def _entry_memory_policy_evaluation(
    entry: dict[str, str],
    *,
    memory_threshold: int,
    memory_threshold_source: str,
) -> dict[str, Any]:
    classification = _classify_memory_candidate(
        content=entry["content"],
        evidence=entry["evidence"],
        marker=entry["marker"],
    )
    required_evidence_count = 1 if classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS else memory_threshold
    try:
        _validate_reflection_semantics(
            marker=entry["marker"],
            content=entry["content"],
            evidence=entry["evidence"],
            candidate_for="memory.md",
        )
    except ValueError as exc:
        return {
            "accepted": False,
            "reason": str(exc),
            "threshold_used": required_evidence_count,
            "threshold_source": "explicit_decision_policy" if required_evidence_count == 1 and memory_threshold > 1 else memory_threshold_source,
            "candidate_classification": classification["classification"],
            "classification_confidence": classification["confidence"],
            "explicit_decision_detected": classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS,
        }
    if entry["trust"] != "hoch":
        return {
            "accepted": False,
            "reason": f"Trust is '{entry['trust']}', not 'hoch'.",
            "threshold_used": required_evidence_count,
            "threshold_source": "explicit_decision_policy" if required_evidence_count == 1 and memory_threshold > 1 else memory_threshold_source,
            "candidate_classification": classification["classification"],
            "classification_confidence": classification["confidence"],
            "explicit_decision_detected": classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS,
        }
    if entry["marker"].casefold() in NON_BEHAVIORAL_MEMORY_MARKERS and classification["classification"] not in EXPLICIT_MEMORY_CLASSIFICATIONS:
        return {
            "accepted": False,
            "reason": (
                f"Marker '{entry['marker']}' is not directly memory-eligible for classification "
                f"'{classification['classification']}'."
            ),
            "threshold_used": required_evidence_count,
            "threshold_source": "explicit_decision_policy" if required_evidence_count == 1 and memory_threshold > 1 else memory_threshold_source,
            "candidate_classification": classification["classification"],
            "classification_confidence": classification["confidence"],
            "explicit_decision_detected": False,
        }
    evidence_count = _count_distinct_evidence_dates(entry["evidence"])
    if evidence_count < required_evidence_count:
        return {
            "accepted": False,
            "reason": (
                f"Only {evidence_count} distinct evidence date(s); required evidence count is "
                f"{required_evidence_count} for classification '{classification['classification']}'."
            ),
            "threshold_used": required_evidence_count,
            "threshold_source": "explicit_decision_policy" if required_evidence_count == 1 and memory_threshold > 1 else memory_threshold_source,
            "candidate_classification": classification["classification"],
            "classification_confidence": classification["confidence"],
            "explicit_decision_detected": classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS,
        }
    return {
        "accepted": True,
        "reason": f"Reflection entry satisfies memory rules for classification '{classification['classification']}'.",
        "threshold_used": required_evidence_count,
        "threshold_source": "explicit_decision_policy" if required_evidence_count == 1 and memory_threshold > 1 else memory_threshold_source,
        "candidate_classification": classification["classification"],
        "classification_confidence": classification["confidence"],
        "explicit_decision_detected": classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS
        or classification["classification"] in EXPLICIT_PERSONA_CLASSIFICATIONS,
    }


def _entry_passes_persona_policy(entry: dict[str, str], *, persona_threshold: int) -> tuple[bool, str]:
    try:
        _validate_reflection_semantics(
            marker=entry["marker"],
            content=entry["content"],
            evidence=entry["evidence"],
            candidate_for="PERSONA.md",
        )
    except ValueError as exc:
        return False, str(exc)
    if entry["marker"].casefold() != "muster":
        return False, f"Persona condensation requires marker 'Muster', not '{entry['marker']}'."
    if entry["trust"] != "hoch":
        return False, f"Trust is '{entry['trust']}', not 'hoch'."
    evidence_count = _count_distinct_evidence_dates(entry["evidence"])
    if evidence_count < persona_threshold:
        return False, f"Only {evidence_count} distinct evidence date(s); threshold is {persona_threshold}."
    return True, "Reflection entry satisfies persona condensation rules."


def _entry_passes_temperament_policy(entry: dict[str, str], *, temperament_threshold: int) -> tuple[bool, str]:
    try:
        _validate_reflection_semantics(
            marker=entry["marker"],
            content=entry["content"],
            evidence=entry["evidence"],
            candidate_for="TEMPERAMENT.md",
        )
    except ValueError as exc:
        return False, str(exc)
    if entry["marker"].casefold() not in {"muster", "beobachtung"}:
        return False, (
            f"Temperament condensation requires marker 'Muster' or 'Beobachtung', not '{entry['marker']}'."
        )
    if entry["trust"] != "hoch":
        return False, f"Trust is '{entry['trust']}', not 'hoch'."
    evidence_count = _count_distinct_evidence_dates(entry["evidence"])
    if evidence_count < temperament_threshold:
        return False, f"Only {evidence_count} distinct evidence date(s); threshold is {temperament_threshold}."
    return True, "Reflection entry satisfies temperament condensation rules."


def _append_directive(
    *,
    profile_path: Path,
    profile_name: str,
    entry: dict[str, str],
    target_file: str,
    target_section: str,
    proposed_content: str,
    reason: str,
    threshold_used: int,
    threshold_source: str,
    candidate_classification: str = "",
    classification_confidence: str = "",
    explicit_decision_detected: bool = False,
    plan_type: str = REFLECTION_CONDENSATION_PLAN_TYPE,
) -> dict[str, Any]:
    target = profile_path / target_file
    precondition = _file_snapshot(target)
    directive_payload = {
        "plan_type": plan_type,
        "profile_name": profile_name,
        "source_entry_id": entry["entry_id"],
        "target_file": target_file,
        "operation": "append_if_absent",
        "proposed_content": proposed_content,
    }
    directive_id = _stable_hash(directive_payload)
    return {
        "directive_id": directive_id,
        "source_entry_id": entry["entry_id"],
        "plan_type": plan_type,
        "target_file": target_file,
        "target_section": target_section,
        "append_mode": "append_to_active_section_if_absent",
        "operation": "append_if_absent",
        "proposed_content": proposed_content,
        "reason": reason,
        "safety_notes": [
            "Execute only after confirmed apply.",
            "Verify expected_precondition before writing.",
            "Use atomic-ish write and rollback on failure.",
            "Preserve reflection.md history.",
        ],
        "expected_precondition": precondition,
        "expected_changed_file": target_file,
        "current_state": "planned",
        "candidate_summary": entry["content"],
        "evidence": entry["evidence"],
        "trust": entry["trust"],
        "confidence": _confidence_from_trust(entry["trust"]),
        "threshold_used": threshold_used,
        "threshold_source": threshold_source,
        "candidate_classification": candidate_classification or "inferred_observation",
        "classification_confidence": classification_confidence or "medium",
        "explicit_decision_detected": bool(explicit_decision_detected),
    }


def _parse_revision_directive(candidate_for: str) -> dict[str, str] | None:
    match = re.match(
        r"^(?P<file>memory|persona|PERSONA)\.md\s*(?:#|\s+)"
        r"(?P<state>questionable|archived|revoked|replaced|fraglich|archiviert|widerrufen|ersetzt)"
        r"\s*:\s*(?P<target>.+)$",
        candidate_for.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    state_aliases = {
        "fraglich": "questionable",
        "questionable": "questionable",
        "archiviert": "archived",
        "archived": "archived",
        "widerrufen": "revoked",
        "revoked": "revoked",
        "ersetzt": "replaced",
        "replaced": "replaced",
    }
    file_name = "PERSONA.md" if match.group("file").casefold() == "persona" else "memory.md"
    return {
        "target_file": file_name,
        "new_state": state_aliases[match.group("state").casefold()],
        "target": match.group("target").strip(),
    }


def _revision_state_directive(
    *,
    profile_path: Path,
    profile_name: str,
    entry: dict[str, str],
    revision: dict[str, str],
) -> dict[str, Any] | None:
    target_file = revision["target_file"]
    target = profile_path / target_file
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    revised = _revise_entry_state(
        current,
        target=revision["target"],
        new_state=revision["new_state"],
        reason=entry["content"],
        date_str=entry["date"],
        target_file=target_file,
        replacement_content=entry["content"],
        replacement_evidence=entry["evidence"],
    )
    if revised == current:
        return None
    precondition = _file_snapshot(target)
    is_replacement = revision["new_state"] == "replaced"
    safety_notes = [
        "Execute only after confirmed apply.",
        "Verify expected_precondition before writing.",
        "Revision changes only the matched target entry state.",
    ]
    if is_replacement:
        safety_notes.append("Replacement revisions append a new active entry when the replacement content is absent.")
    directive_payload = {
        "plan_type": REFLECTION_CONDENSATION_PLAN_TYPE,
        "profile_name": profile_name,
        "source_entry_id": entry["entry_id"],
        "target_file": target_file,
        "operation": "revise_state",
        "proposed_content": revised,
    }
    directive_id = _stable_hash(directive_payload)
    return {
        "directive_id": directive_id,
        "source_entry_id": entry["entry_id"],
        "plan_type": REFLECTION_CONDENSATION_PLAN_TYPE,
        "target_file": target_file,
        "target_section": "matched_entry_and_replacement_append" if is_replacement else "matched_entry",
        "append_mode": "replace_file_after_state_revision",
        "operation": "revise_state",
        "proposed_content": revised,
        "reason": entry["content"],
        "safety_notes": safety_notes,
        "expected_precondition": precondition,
        "expected_changed_file": target_file,
        "current_state": "planned",
        "candidate_summary": entry["content"],
        "evidence": entry["evidence"],
        "trust": entry["trust"],
        "confidence": _confidence_from_trust(entry["trust"]),
        "threshold_used": None,
        "revision_state": revision["new_state"],
        "revision_effective_state": "archived" if revision["new_state"] == "replaced" else revision["new_state"],
    }


def _revise_entry_state(
    content: str,
    *,
    target: str,
    new_state: str,
    reason: str,
    date_str: str,
    target_file: str = "",
    replacement_content: str = "",
    replacement_evidence: str = "",
) -> str:
    target_norm = _normalize_reflection_text(target)
    heading = {
        "questionable": "QUESTIONABLE",
        "archived": "ARCHIVED",
        "revoked": "REVOKED",
        "replaced": "ARCHIVED",
    }.get(new_state, new_state.upper())
    blocks = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    revised_blocks: list[str] = []
    changed = False
    for block in blocks:
        if not block.strip():
            revised_blocks.append(block)
            continue
        if block.startswith("## ") and target_norm and target_norm in _normalize_reflection_text(block):
            new_block = re.sub(
                r"^##\s+(?:\[(?:ACTIVE|QUESTIONABLE|ARCHIVED|REVOKED|AKTIV|FRAGLICH|ARCHIVIERT|WIDERRUFEN)\]\s*)?",
                f"## [{heading}] ",
                block,
                count=1,
                flags=re.MULTILINE,
            )
            revision_line = f"Revisionsgrund {date_str}: {reason}"
            if revision_line not in new_block:
                new_block = new_block.rstrip() + "\n" + revision_line + "\n"
            revised_blocks.append(new_block)
            changed = True
            continue
        revised_blocks.append(block)
    revised = "".join(revised_blocks) if changed else content
    if new_state != "replaced" or not replacement_content.strip():
        return revised
    if _profile_entry_content_exists(revised, replacement_content):
        return revised
    replacement_block = _format_replacement_revision_block(
        target_file=target_file,
        content=replacement_content,
        evidence=replacement_evidence,
        entry_date=date_str,
        current=revised,
    )
    if not replacement_block:
        return revised
    return _append_profile_block(revised, replacement_block)


def _format_replacement_revision_block(
    *,
    target_file: str,
    content: str,
    evidence: str,
    entry_date: str,
    current: str,
) -> str:
    if target_file == "memory.md":
        return _format_memory_promotion_block(content=content, evidence=evidence, entry_date=entry_date)
    if target_file == "PERSONA.md":
        return _format_persona_promotion_block(
            content=content,
            evidence=evidence,
            entry_date=entry_date,
            current_persona=current,
        )
    return ""


def _profile_entry_content_exists(profile_text: str, entry_content: str) -> bool:
    needle = _normalize_reflection_text(entry_content)
    if not needle:
        return False
    for match in re.finditer(r"^Inhalt:\s*(?P<content>.*)$", profile_text, flags=re.MULTILINE):
        if _normalize_reflection_text(match.group("content")) == needle:
            return True
    return False


def _file_snapshot(path: Path) -> dict[str, Any]:
    exists = path.exists()
    if not exists:
        return _missing_file_snapshot()
    content = path.read_bytes()
    return {
        "exists": True,
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "modified_time_ns": path.stat().st_mtime_ns,
        "target_section_marker": _target_section_marker(path),
    }


def _missing_file_snapshot() -> dict[str, Any]:
    return {
        "exists": False,
        "size": 0,
        "sha256": "",
        "modified_time_ns": None,
        "target_section_marker": "",
    }


def _target_section_marker(path: Path) -> str:
    if path.name == "memory.md":
        return "## [ACTIVE] FAKT"
    if path.name == "PERSONA.md":
        return "## [ACTIVE] Muster"
    return ""


def _file_snapshots_for_directives(profile_path: Path, directives: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for directive in directives:
        filename = directive["target_file"]
        snapshots[filename] = dict(directive["expected_precondition"])
    if directives:
        snapshots["journal.md"] = _file_snapshot(profile_path / "journal.md")
    return snapshots


def _reflection_condensation_plan_id(
    *,
    profile_name: str,
    directives: list[dict[str, Any]],
    file_snapshots: dict[str, dict[str, Any]],
    processed_ids: set[str],
) -> str:
    return _stable_hash(
        {
            "plan_type": REFLECTION_CONDENSATION_PLAN_TYPE,
            "profile_name": profile_name,
            "directive_ids": [directive["directive_id"] for directive in directives],
            "file_snapshots": file_snapshots,
            "processed_ids": sorted(processed_ids),
        }
    )


def _condensation_candidate_summary(entries: list[dict[str, str]], directives: list[dict[str, Any]]) -> str:
    if not directives:
        return ""
    summaries = [directive["candidate_summary"] for directive in directives]
    return "; ".join(summaries[:3])


def _condensation_evidence(entries: list[dict[str, str]], directives: list[dict[str, Any]]) -> str:
    _ = entries
    if not directives:
        return ""
    evidence = [directive["evidence"] for directive in directives if directive.get("evidence")]
    return "; ".join(evidence[:3])


def _condensation_trust(entries: list[dict[str, str]], directives: list[dict[str, Any]]) -> str:
    _ = entries
    if not directives:
        return ""
    if all(directive.get("trust") == "hoch" for directive in directives):
        return "hoch"
    if any(directive.get("trust") == "mittel" for directive in directives):
        return "mittel"
    return directives[0].get("trust", "")


def _approved_plan_from_answers(answers: dict[str, Any] | None) -> dict[str, Any] | None:
    if not answers:
        return None
    for key, value in answers.items():
        normalized = _normalize_answer_key(str(key))
        if normalized in {"approvedplan", "plan"} and isinstance(value, dict):
            return value
    return None


def _validate_pending_plan_id(plan_id: str) -> str:
    cleaned = plan_id.strip().casefold()
    if not PENDING_PLAN_ID_RE.fullmatch(cleaned):
        raise ValueError("plan_id must be lowercase hexadecimal runtime plan id.")
    return cleaned


def _validate_condensation_approved_plan(*, profile_path: Path, approved_plan: dict[str, Any]) -> dict[str, str] | None:
    if approved_plan.get("decision") == "review_required" or approved_plan.get("state") == "review_required":
        return {
            "decision": "review_required",
            "state": "review_required",
            "result": "review_required",
            "error_category": "review_required",
            "reason": "Approved plan requires user review and cannot be applied.",
        }
    directives = approved_plan.get("revision_directives")
    if not isinstance(directives, list):
        return _invalid_plan_payload("revision_directives must be a list.")
    expected_ids = approved_plan.get("directive_ids")
    if expected_ids is not None and not isinstance(expected_ids, list):
        return _invalid_plan_payload("directive_ids must be a list.")

    seen_directive_ids: set[str] = set()
    for directive in directives:
        if not isinstance(directive, dict):
            return _invalid_plan_payload("Each revision directive must be an object.")
        directive_id = directive.get("directive_id")
        if not isinstance(directive_id, str) or not directive_id.strip():
            return _invalid_plan_payload("Each revision directive requires a directive_id.")
        if directive_id in seen_directive_ids:
            return _invalid_plan_payload(f"Duplicate directive_id: {directive_id}")
        seen_directive_ids.add(directive_id)

        current_state = directive.get("current_state")
        if current_state not in GOVERNOR_LIFECYCLE_STATES:
            return _invalid_plan_payload(f"Unknown directive lifecycle state: {current_state}")
        if current_state != "planned":
            return {
                "decision": "rejected",
                "state": str(current_state),
                "result": "rejected",
                "error_category": "directive_not_planned",
                "reason": f"Directive {directive_id} is in state '{current_state}', not 'planned'.",
            }

        target_file = directive.get("target_file")
        if not isinstance(target_file, str) or target_file not in PBA2_ALLOWED_CONDENSATION_TARGETS:
            return _invalid_plan_payload(f"Directive target_file is not allowed: {target_file}")
        if Path(target_file).name != target_file:
            return _invalid_plan_payload("Directive target_file must not contain path separators.")
        target_path = profile_path / target_file
        if target_path.is_symlink():
            return _invalid_plan_payload(f"Directive target_file must not be a symlink: {target_file}")
        resolved = target_path.resolve(strict=False)
        if not _is_inside_or_same(resolved, profile_path):
            return _invalid_plan_payload("Directive target_file escapes the active profile directory.")

        operation = directive.get("operation")
        if operation not in {"append_if_absent", "revise_state"}:
            return _invalid_plan_payload(f"Unsupported directive operation: {operation}")
        if not isinstance(directive.get("proposed_content"), str) or not directive.get("proposed_content"):
            return _invalid_plan_payload("Directive proposed_content must be a non-empty string.")
        if not isinstance(directive.get("expected_precondition"), dict):
            return _invalid_plan_payload("Directive expected_precondition must be an object.")
        if directive.get("expected_changed_file") != target_file:
            return _invalid_plan_payload("Directive expected_changed_file must match target_file.")

    if expected_ids is not None and list(expected_ids) != [directive["directive_id"] for directive in directives]:
        return _invalid_plan_payload("directive_ids do not match revision_directives order.")
    return None


def _invalid_plan_payload(reason: str) -> dict[str, str]:
    return {
        "decision": "rejected",
        "state": "rejected",
        "result": "rejected",
        "error_category": "invalid_plan_payload",
        "reason": reason,
    }


def _stale_directives(*, profile_path: Path, directives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stale: list[dict[str, Any]] = []
    for directive in directives:
        filename = str(directive.get("target_file", ""))
        expected = directive.get("expected_precondition") or {}
        current = _file_snapshot(profile_path / filename)
        if not _snapshot_matches(expected, current):
            stale.append(
                {
                    "directive_id": directive.get("directive_id"),
                    "target_file": filename,
                    "expected_precondition": expected,
                    "current_snapshot": current,
                }
            )
    return stale


def _snapshot_matches(expected: dict[str, Any], current: dict[str, Any]) -> bool:
    return (
        bool(expected.get("exists")) == bool(current.get("exists"))
        and int(expected.get("size") or 0) == int(current.get("size") or 0)
        and str(expected.get("sha256") or "") == str(current.get("sha256") or "")
    )


def _apply_condensation_directives_transactionally(
    *,
    profile_path: Path,
    approved_plan: dict[str, Any],
    directives: list[dict[str, Any]],
) -> dict[str, Any]:
    if not directives:
        journal_payload = _condensation_journal_payload(
            approved_plan=approved_plan,
            decision="no_op",
            state="no_op",
            changed_files=["journal.md"],
            restored_files=[],
            reason="No unprocessed eligible reflection entries.",
            result="no_op",
            error_category=None,
        )
        _append_governor_journal_event(profile_path, journal_payload)
        return {
            "ok": True,
            "confirmed": True,
            "decision": "no_op",
            "state": "no_op",
            "result": "no_op",
            "changed_files": ["journal.md"],
            "restored_files": [],
            "failed_files": [],
            "journal_event": journal_payload,
            "reason": "No unprocessed eligible reflection entries.",
        }

    target_files = _unique_preserving_order([directive["target_file"] for directive in directives])
    backups = {
        filename: (profile_path / filename).read_text(encoding="utf-8") if (profile_path / filename).exists() else ""
        for filename in target_files
    }
    changed_files: list[str] = []
    restored_files: list[str] = []
    failed_files: list[str] = []
    active_write = ""
    try:
        planned_contents = dict(backups)
        for directive in directives:
            filename = directive["target_file"]
            active_write = filename
            current = planned_contents[filename]
            if directive["operation"] == "append_if_absent":
                if not _target_contains_candidate(current, directive["candidate_summary"]):
                    planned_contents[filename] = _append_profile_block(current, directive["proposed_content"])
            elif directive["operation"] == "revise_state":
                planned_contents[filename] = directive["proposed_content"]
            else:
                raise RuntimeError(f"Unsupported directive operation: {directive['operation']}")

        for filename, content in planned_contents.items():
            if content == backups[filename]:
                continue
            active_write = filename
            _atomic_write_text(profile_path / filename, content)
            changed_files.append(filename)

        journal_payload = _condensation_journal_payload(
            approved_plan=approved_plan,
            decision="applied",
            state="applied",
            changed_files=[*changed_files, "journal.md"],
            restored_files=[],
            reason="Reflection condensation directives applied.",
            result="applied",
            error_category=None,
        )
        active_write = "journal.md"
        _append_governor_journal_event(profile_path, journal_payload)
    except Exception as exc:
        failed_target = active_write or (filename if "filename" in locals() else "")
        if failed_target:
            failed_files.append(failed_target)
        rollback_errors: list[str] = []
        rollback_failed_files: list[str] = []
        rollback_attempted = bool(changed_files)
        for changed in reversed(changed_files):
            try:
                _atomic_write_text(profile_path / changed, backups[changed])
                restored_files.append(changed)
            except Exception as rollback_exc:
                rollback_failed_files.append(changed)
                rollback_errors.append(f"{changed}: {rollback_exc}")
        final_result = "rolled_back" if rollback_attempted and not rollback_errors else "failed"
        journal_payload = _condensation_journal_payload(
            approved_plan=approved_plan,
            decision="failed",
            state=final_result,
            changed_files=[*changed_files, "journal.md"],
            restored_files=restored_files,
            reason=f"Apply failed: {exc}",
            result=final_result,
            error_category="apply_failed",
            failed_files=failed_files,
            rollback_errors=rollback_errors,
            rollback_attempted=rollback_attempted,
            rollback_failed_files=rollback_failed_files,
        )
        _append_governor_journal_event(profile_path, journal_payload)
        return {
            "ok": False,
            "confirmed": True,
            "decision": "failed",
            "state": journal_payload["state"],
            "result": journal_payload["result"],
            "changed_files": [*changed_files, "journal.md"],
            "restored_files": restored_files,
            "failed_files": failed_files,
            "rollback_attempted": rollback_attempted,
            "rollback_failed_files": rollback_failed_files,
            "rollback_errors": rollback_errors,
            "journal_event": journal_payload,
            "reason": f"Apply failed: {exc}",
        }
    return {
        "ok": True,
        "confirmed": True,
        "decision": "applied",
        "state": "applied",
        "result": "applied",
        "changed_files": [*changed_files, "journal.md"],
        "restored_files": [],
        "failed_files": [],
        "rollback_attempted": False,
        "rollback_failed_files": [],
        "journal_event": journal_payload,
        "reason": "Reflection condensation directives applied.",
    }


def _condensation_journal_payload(
    *,
    approved_plan: dict[str, Any],
    decision: str,
    state: str,
    changed_files: list[str],
    restored_files: list[str],
    reason: str,
    result: str,
    error_category: str | None,
    stale_directives: list[dict[str, Any]] | None = None,
    failed_files: list[str] | None = None,
    rollback_errors: list[str] | None = None,
    rollback_attempted: bool = False,
    rollback_failed_files: list[str] | None = None,
) -> dict[str, Any]:
    return _governor_journal_payload(
        plan_type=str(approved_plan.get("plan_type") or REFLECTION_CONDENSATION_PLAN_TYPE),
        profile_name=str(approved_plan.get("target_profile_name") or approved_plan.get("active_profile_name") or ""),
        plan_id=str(approved_plan.get("plan_id") or ""),
        directive_ids=list(approved_plan.get("directive_ids") or []),
        decision=decision,
        state=state,
        changed_files=changed_files,
        restored_files=restored_files,
        candidate_summary=str((approved_plan.get("plan_preview") or {}).get("journal_event", {}).get("candidate_summary") or ""),
        evidence=str((approved_plan.get("plan_preview") or {}).get("journal_event", {}).get("evidence") or ""),
        trust=str((approved_plan.get("plan_preview") or {}).get("journal_event", {}).get("trust") or ""),
        confidence=str((approved_plan.get("plan_preview") or {}).get("journal_event", {}).get("confidence") or ""),
        threshold_used=(approved_plan.get("plan_preview") or {}).get("journal_event", {}).get("threshold_used"),
        threshold_source=(approved_plan.get("plan_preview") or {}).get("journal_event", {}).get("threshold_source"),
        file_snapshots=dict(approved_plan.get("file_snapshots") or {}),
        reason=reason,
        result=result,
        source_entry_ids=[directive.get("source_entry_id") for directive in approved_plan.get("revision_directives", []) if directive.get("source_entry_id")],
        skipped_candidates=list(approved_plan.get("skipped_candidates") or []),
        error_category=error_category,
        stale_directives=stale_directives or [],
        failed_files=failed_files or [],
        rollback_errors=rollback_errors or [],
        rollback_attempted=rollback_attempted,
        rollback_failed_files=rollback_failed_files or [],
    )


def _condensation_apply_result(
    *,
    profile_path: Path,
    approved_plan: dict[str, Any],
    ok: bool,
    decision: str,
    state: str,
    reason: str,
    result: str,
    error_category: str | None = None,
    requirement_ids: tuple[str, ...],
) -> ProfileResult:
    journal_payload = _condensation_journal_payload(
        approved_plan=approved_plan,
        decision=decision,
        state=state,
        changed_files=["journal.md"],
        restored_files=[],
        reason=reason,
        result=result,
        error_category=error_category if error_category is not None else ("policy_denied" if not ok else None),
    )
    _append_governor_journal_event(profile_path, journal_payload)
    return ProfileResult(
        ok=ok,
        operation="governor_apply",
        policy_decision=PolicyDecision.DENY if not ok else PolicyDecision.ALLOW,
        profile_path=str(profile_path),
        data={**approved_plan, "decision": decision, "state": state, "result": result, "journal_event": journal_payload},
        error=None if ok else reason,
        requirement_ids=requirement_ids,
    )


def _condensation_reference_error(
    *,
    profile_path: Path,
    plan_id: str,
    plan_source: str,
    reason: str,
    error_category: str,
    approved_plan: dict[str, Any] | None = None,
) -> ProfileResult:
    plan_payload = approved_plan or {"plan_type": REFLECTION_CONDENSATION_PLAN_TYPE, "plan_id": plan_id}
    return ProfileResult(
        ok=False,
        operation="governor_apply",
        policy_decision=PolicyDecision.DENY,
        profile_path=str(profile_path),
        data={
            **plan_payload,
            "plan_id": str(plan_payload.get("plan_id") or plan_id),
            "plan_source": plan_source,
            "confirmed": False,
            "decision": "rejected",
            "state": "rejected",
            "result": "rejected",
            "changed_files": [],
            "files_changed": [],
            "target_changed": False,
            "error_category": error_category,
        },
        error=reason,
        error_category=error_category,
        requirement_ids=(*PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS, "NFR-002"),
    )


def _condensation_already_processed_result(
    *,
    profile_path: Path,
    approved_plan: dict[str, Any],
    plan_source: str,
    consumed_at: str,
) -> ProfileResult:
    return ProfileResult(
        ok=True,
        operation="governor_apply",
        policy_decision=PolicyDecision.ALLOW,
        profile_path=str(profile_path),
        data={
            **approved_plan,
            "plan_source": plan_source,
            "confirmed": True,
            "decision": "duplicate_noop",
            "state": "no_op",
            "result": "already_processed",
            "already_processed": True,
            "consumed_at": consumed_at,
            "target_changed": False,
            "changed_files": [],
            "files_changed": [],
            "restored_files": [],
        },
        requirement_ids=PBA2_GOVERNOR_RELIABILITY_REQUIREMENTS,
    )


def _governor_journal_payload(
    *,
    plan_type: str,
    profile_name: str,
    plan_id: str,
    directive_ids: list[str],
    decision: str,
    state: str,
    changed_files: list[str],
    restored_files: list[str],
    candidate_summary: str,
    evidence: str,
    trust: str,
    confidence: str,
    threshold_used: Any,
    threshold_source: Any,
    file_snapshots: dict[str, Any],
    reason: str,
    result: str,
    source_entry_ids: list[str] | None = None,
    skipped_candidates: list[dict[str, Any]] | None = None,
    error_category: str | None = None,
    stale_directives: list[dict[str, Any]] | None = None,
    failed_files: list[str] | None = None,
    rollback_errors: list[str] | None = None,
    rollback_attempted: bool = False,
    rollback_failed_files: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": PBA2_JOURNAL_SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "event_type": GOVERNOR_JOURNAL_EVENT_TYPE,
        "plan_type": plan_type,
        "profile_name": profile_name,
        "plan_id": plan_id,
        "directive_ids": directive_ids,
        "decision": decision,
        "state": state,
        "changed_files": _unique_preserving_order(changed_files),
        "restored_files": _unique_preserving_order(restored_files),
        "candidate_summary": candidate_summary,
        "evidence": evidence,
        "trust": trust,
        "confidence": confidence,
        "threshold_used": threshold_used,
        "threshold_source": threshold_source,
        "file_snapshots": file_snapshots,
        "actor": "plwc-gateway",
        "tool": "plwc_governor_apply",
        "reason": reason,
        "result": result,
        "error_category": error_category,
        "source_entry_ids": source_entry_ids or [],
        "skipped_candidates": skipped_candidates or [],
        "stale_directives": stale_directives or [],
        "failed_files": failed_files or [],
        "rollback_errors": rollback_errors or [],
        "rollback_attempted": bool(rollback_attempted),
        "rollback_failed_files": rollback_failed_files or [],
    }


def _append_governor_journal_event(profile_path: Path, payload: dict[str, Any]) -> None:
    journal = profile_path / "journal.md"
    current = journal.read_text(encoding="utf-8") if journal.exists() else "# Journal\n"
    _atomic_write_text(journal, _append_profile_block(current, _format_governor_journal_event(payload)))


def _atomic_write_text(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        try:
            if temp.exists():
                temp.unlink()
        except OSError:
            pass


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _normalize_promotion_answers(answers: dict[str, Any] | None) -> dict[str, str]:
    raw_answers = answers or {}
    normalized = {
        _normalize_answer_key(str(key)): "" if value is None else str(value).strip()
        for key, value in raw_answers.items()
    }
    return {
        "content": _first_answer(
            normalized,
            "content",
            "candidate",
            "candidatecontent",
            "candidatesummary",
            "summary",
        ),
        "evidence": _first_answer(normalized, "evidence", "beleg", "belege"),
        "confidence": _first_answer(normalized, "confidence", "trustconfidence"),
        "trust": _first_answer(normalized, "trust", "vertrauen"),
        "marker": _first_answer(normalized, "marker"),
        "entry_date": _first_answer(normalized, "entrydate", "date", "datum"),
        "candidate_for": _first_answer(normalized, "candidatefor", "kandidatfuer", "kandidatfur"),
        "reason": _first_answer(normalized, "reason", "revisionsreason", "revisionsgrund"),
        "target_section": _first_answer(normalized, "targetsection", "section"),
        "conflicts_with": _first_answer(normalized, "conflictswith", "conflictwith", "conflict"),
    }


def _promotion_target_file(plan_type: str) -> str:
    if plan_type == "memory_promotion":
        return "memory.md"
    if plan_type == "persona_promotion":
        return "PERSONA.md"
    if plan_type == "temperament_promotion":
        return "TEMPERAMENT.md"
    raise ValueError(f"Unsupported promotion plan type: {plan_type}")


# RC12-DESC-001 (B) — single source for the governor's required/optional parameter
# contract. The promotion required fields mirror the imperative checks in
# ``_evaluate_promotion_candidate`` (content/evidence/marker via
# ``_single_line_required``; trust via ``_canonical_reflection_trust`` + the
# trust=="hoch" gate); the retire fields mirror ``governor_retire``. A behaviour
# test (test_rc12_desc_001b_contract_matches_validation) ties this to the real
# validation so the two cannot drift.
_PROMOTION_REQUIRED_PARAMS = ("candidate_summary", "evidence", "marker", "trust")
_PROMOTION_OPTIONAL_PARAMS = (
    "entry_date", "candidate_for", "reason", "conflicts_with", "confidence",
    "target_section", "source_file", "source_heading", "source_sha256", "force", "profile",
)


def governor_parameter_contract() -> dict[str, Any]:
    """RC12-DESC-001 (B) — per-operation / per-plan_type required & optional
    parameters for the ``plwc_governor`` facade. Promotion and retire are fully
    specified (the real trial-and-error pain points); profile_* / reflection_*
    list their core fields and defer their detail to ``onboarding_schema``."""
    promotion = {
        "operations": ["plan", "apply"],
        "required": list(_PROMOTION_REQUIRED_PARAMS),
        "optional": list(_PROMOTION_OPTIONAL_PARAMS),
    }
    return {
        "operations": {
            "plan": {
                "required": ["operation", "plan_type"],
                "note": "Non-mutating preview. Per-plan_type fields are under plan_types.",
            },
            "apply": {
                "required": ["operation", "plan_type", "confirmed"],
                "note": "confirmed=true is mandatory; otherwise the same fields as plan (or a plan_id from a prior plan).",
            },
            "retire": {
                "required": ["operation", "target_file", "reason"],
                "required_one_of": ["heading", "directive_id"],
                "optional": ["conflicts_with", "retired_at", "dedup", "confirmed", "profile"],
                "note": "Without confirmed=true this is a non-mutating preview. dedup=true requires directive_id.",
            },
            "list_retirable": {"required": ["operation"], "optional": ["target_file", "profile"]},
            "reindex": {"required": ["operation"], "optional": ["profile"], "note": "Requires qdrant_enabled; rebuilds the active profile's index."},
            "drop_index": {"required": ["operation"], "optional": ["profile"], "note": "Requires qdrant_enabled; deletes the derived index only."},
        },
        "plan_types": {
            "memory_promotion": {**promotion, "marker_rule": "Any reflection marker; Wunsch/Sorge are not memory-eligible unless the content is an explicit decision/scope/security/instruction."},
            "persona_promotion": {**promotion, "marker_rule": "Marker 'Muster' or 'Innenperspektive' (persona-only soft truth, max 3 active), or explicit persona content."},
            "temperament_promotion": {**promotion, "marker_rule": "Marker 'Muster' or 'Beobachtung'."},
            "profile_creation": {"operations": ["plan", "apply"], "required": ["plan_type", "onboarding_answers"], "optional": ["profile"], "see": "onboarding_schema (this payload) for onboarding_answers fields."},
            "profile_activation": {"operations": ["plan", "apply"], "required": ["plan_type", "profile"]},
            "profile_import": {"operations": ["plan", "apply"], "required": ["plan_type", "profile"], "see": "onboarding_answers.source_profile selects the import source."},
            "reflection_condensation": {"operations": ["plan", "apply"], "required": ["plan_type"], "optional": ["plan_id", "profile"], "note": "plan returns a plan_id; apply re-supplies it with confirmed=true."},
            "reflection_memory_promotion": {"operations": ["plan", "apply"], "required": ["plan_type"], "optional": ["profile"], "see": "derives candidates from reflection.md; see the reflection describe scope."},
        },
        "contract_notes": [
            "trust must be 'hoch' for a promotion to be eligible_for_apply.",
            "candidate_summary is the candidate content (mapped to 'content' internally).",
            "source_sha256 is optional at plan (the gateway returns the canonical SHA in data.source_provenance.source_sha256) and required at apply when source_file is set.",
            "validation.valid means the plan object is well-formed/evaluable, NOT that the candidate was accepted; the gate verdict is decision + eligible_for_apply (RC10-CARRY-001).",
            "Markers are metadata; marker text alone never authorizes a write.",
        ],
    }


def _promotion_planned_action(plan_type: str) -> str:
    if plan_type == "memory_promotion":
        return "Propose a governed memory.md update from a PBA2 promotion candidate."
    if plan_type == "temperament_promotion":
        return "Propose a governed TEMPERAMENT.md update from a PBA2 temperament promotion candidate."
    return "Propose a governed PERSONA.md update from a stricter PBA2 persona promotion candidate."


def _classify_memory_candidate(*, content: str, evidence: str, marker: str) -> dict[str, str]:
    text = _normalize_reflection_text(f"{content} {evidence}")
    marker_norm = marker.casefold()

    vague_terms = (
        "seems",
        "seem to",
        "appears",
        "maybe",
        "perhaps",
        "might",
        "could",
        "suggests",
        "vielleicht",
        "scheinbar",
        "koennte",
        "könnte",
        "eventuell",
    )
    concern_terms = (
        "concern",
        "concerned",
        "worry",
        "risk",
        "sorge",
        "besorgt",
        "risiko",
    )
    security_terms = (
        "must not directly edit",
        "must not edit",
        "may not directly edit",
        "cannot directly edit",
        "protected profile",
        "protected governance",
        "profile/governance files",
        "pl/profile/governance",
        "security requirement",
        "directly edit pl",
        "darf die pl-dateien nicht direkt editieren",
        "darf pl-dateien nicht direkt editieren",
        "darf nicht direkt editieren",
        "geschuetzte profile",
        "geschützte profile",
        "governance-dateien",
    )
    scope_terms = (
        "scope boundary",
        "core scope",
        "includes only",
        "only pdf",
        "nothing else",
        "not part of",
        "out of scope",
        "no qdrant",
        "qdrant is not part",
        "backlog",
        "sonst nichts",
        "nicht in plwc",
        "kommt nicht in plwc",
        "höchstens später",
        "hoechstens spaeter",
        "festgelegt",
    )
    decision_terms = (
        "we decided",
        "has been decided",
        "explicitly decided",
        "user decided",
        "user says",
        "user stated",
        "direct instruction",
        "hard requirement",
        "requirement",
        "festgelegt",
        "entschieden",
        "direkte anweisung",
        "anforderung",
    )
    # RC12-GEN-001: the user name is no longer hard-coded; "<user> wants/requires"
    # is derived from the configured user_aliases (generic "user …" stays).
    direct_instruction_terms = (
        "user requires",
        "user instructs",
        "user wants",
        "must",
        "always",
        "never",
        "do not",
        "direct execution",
        "requires",
    ) + tuple(
        f"{_normalize_reflection_text(alias)} {verb}"
        for alias in _active_user_aliases(None)
        for verb in ("wants", "requires")
        if _normalize_reflection_text(alias)
    )
    preference_terms = (
        "prefers",
        "preference",
        "answer style",
        "tone",
        "working style",
        "bevorzugt",
        "praeferenz",
        "präferenz",
    )

    if any(term in text for term in security_terms):
        return {"classification": "security_requirement", "confidence": "high"}
    if any(term in text for term in scope_terms):
        return {"classification": "scope_boundary", "confidence": "high"}
    if any(term in text for term in decision_terms):
        return {"classification": "explicit_user_decision", "confidence": "high"}
    if marker_norm == "sorge" or any(term in text for term in concern_terms):
        return {"classification": "concern", "confidence": "medium"}
    has_vague = any(term in text for term in vague_terms)
    if has_vague:
        return {"classification": "inferred_observation", "confidence": "medium"}
    if any(term in text for term in direct_instruction_terms):
        return {"classification": "direct_user_instruction", "confidence": "high"}
    if any(term in text for term in preference_terms):
        return {"classification": "preference", "confidence": "medium"}
    if _has_reflection_insight(content):
        return {"classification": "inferred_observation", "confidence": "medium"}
    return {"classification": "rejected_or_unclear", "confidence": "low"}


def _classify_persona_candidate(*, content: str, evidence: str, marker: str) -> dict[str, str]:
    text = _normalize_reflection_text(f"{content} {evidence}")
    marker_norm = marker.casefold()
    vague_terms = (
        "seems",
        "appears",
        "maybe",
        "perhaps",
        "might",
        "could",
        "enjoy",
        "likes",
        "scheint",
        "vielleicht",
        "koennte",
        "könnte",
    )
    safety_terms = (
        "security-critical",
        "security critical",
        "sicherheitskritisch",
        "blockieren",
        "block rather than guess",
        "rather block",
        "klar blockieren",
        "nicht raten",
    )
    project_style_terms = (
        "plwc",
        "acceptance criteria",
        "akzeptanzkriterien",
        "small steps",
        "kleinteilig",
        "prüfbar",
        "pruefbar",
        "sauberer trennung",
        "working style",
    )
    interaction_terms = (
        "sprich mich",
        "du an",
        "address me",
        "call me",
        "weniger wiederholungen",
        "less repetition",
        "nicht trocken",
        "sachlich und klar",
        "concise",
        "clear",
    )
    style_terms = (
        "antworte",
        "answer",
        "bei übersetzungen",
        "bei uebersetzungen",
        "translations",
        "translation",
        "immer 1:1",
        "1:1",
        "tone",
        "style",
        "sachlich",
        "klar",
    )
    explicit_terms = (
        "user stated",
        "user instructed",
        "user explicitly",
        "bitte",
        "immer",
        "always",
        "must",
        "soll",
        "sollen",
    )

    if any(term in text for term in vague_terms):
        return {"classification": "rejected_or_unclear", "confidence": "medium"}
    if any(term in text for term in safety_terms):
        return {"classification": "safety_behavior_preference", "confidence": "high"}
    if any(term in text for term in project_style_terms):
        return {"classification": "project_working_style", "confidence": "high"}
    if any(term in text for term in interaction_terms):
        return {"classification": "interaction_preference", "confidence": "high"}
    if any(term in text for term in style_terms):
        return {"classification": "style_preference", "confidence": "high"}
    if any(term in text for term in explicit_terms):
        return {"classification": "explicit_persona_instruction", "confidence": "high"}
    if marker_norm == "muster":
        return {"classification": "preference", "confidence": "medium"}
    return {"classification": "rejected_or_unclear", "confidence": "low"}


def _classify_temperament_candidate(*, content: str, evidence: str, marker: str) -> dict[str, str]:
    """Classify a promotion candidate for TEMPERAMENT.md.

    Focuses on tone shifts, collaboration tendencies and working-style traits —
    attributes that are about the persona's groundtemperament rather than the user's
    persona preferences (which belong in PERSONA.md).
    """
    text = _normalize_reflection_text(f"{content} {evidence}")
    marker_norm = marker.casefold()

    vague_terms = (
        "seems",
        "appears",
        "maybe",
        "perhaps",
        "might",
        "could",
        "scheint",
        "vielleicht",
        "koennte",
        "könnte",
    )
    tone_terms = (
        "ton",
        "tonfall",
        "tone",
        "sachlich",
        "direkt",
        "direkte",
        "warmth",
        "warmth",
        "wärme",
        "waerme",
        "kalt",
        "cool",
        "trocken",
        "präzise",
        "praezise",
        "precise",
        "ruhig",
        "calm",
        "assertive",
    )
    collaboration_terms = (
        "zusammenarbeit",
        "collaboration",
        "gemeinsam",
        "together",
        "partnerschaft",
        "partnership",
        "neigt dazu",
        "tends to",
        "tendenz",
        "tendency",
    )
    working_style_terms = (
        "arbeitsweise",
        "working style",
        "arbeitsstil",
        "systematisch",
        "systematic",
        "strukturiert",
        "structured",
        "kleinschrittig",
        "incremental",
        "kleinteilig",
        "gründlich",
        "thorough",
        "sorgfältig",
        "careful",
    )
    trait_terms = (
        "grundtemperament",
        "temperament",
        "wesenzug",
        "characteristic",
        "eigenschaft",
        "neigung",
        "inclination",
        "grundhaltung",
        "grundcharakter",
    )

    if any(term in text for term in vague_terms):
        return {"classification": "rejected_or_unclear", "confidence": "medium"}
    if any(term in text for term in trait_terms):
        return {"classification": "temperament_trait", "confidence": "high"}
    if any(term in text for term in collaboration_terms):
        return {"classification": "collaboration_tendency", "confidence": "high"}
    if any(term in text for term in tone_terms):
        return {"classification": "tone_shift", "confidence": "high"}
    if any(term in text for term in working_style_terms):
        return {"classification": "working_style", "confidence": "high"}
    if marker_norm in {"muster", "beobachtung"}:
        return {"classification": "temperament_trait", "confidence": "medium"}
    return {"classification": "rejected_or_unclear", "confidence": "low"}


def _evaluate_promotion_candidate(
    *,
    plan_type: str,
    answers: dict[str, str],
    target_text: str,
    memory_threshold: int,
    persona_threshold: int,
    temperament_threshold: int,
    memory_threshold_source: str,
    persona_threshold_source: str,
    temperament_threshold_source: str,
    force: bool = False,
) -> dict[str, Any]:
    target_file = _promotion_target_file(plan_type)
    if plan_type == "memory_promotion":
        threshold = memory_threshold
        threshold_source = memory_threshold_source
    elif plan_type == "temperament_promotion":
        threshold = temperament_threshold
        threshold_source = temperament_threshold_source
    else:
        threshold = persona_threshold
        threshold_source = persona_threshold_source
    content = _single_line_required(answers["content"], "candidate content")
    evidence = _single_line_required(answers["evidence"], "evidence")
    marker = _canonical_reflection_marker(_single_line_required(answers["marker"], "marker"))
    trust = _canonical_reflection_trust(confidence=answers["confidence"], trust=answers["trust"])
    confidence = answers["confidence"].strip().casefold() or _confidence_from_trust(trust)
    entry_date = _reflection_date(answers["entry_date"])
    candidate_for = answers["candidate_for"] or target_file
    # RC12-INNER-002 — inner-perspective ("soft truth") promotion into PERSONA.md.
    is_inner_truth = (
        plan_type == "persona_promotion"
        and marker.casefold() == INNER_PERSPECTIVE_MARKER.casefold()
    )
    evidence_count = _count_distinct_evidence_dates(evidence, entry_date=entry_date)
    evidence_dates = _distinct_evidence_dates(evidence, entry_date=entry_date)
    if plan_type == "memory_promotion":
        classification = _classify_memory_candidate(content=content, evidence=evidence, marker=marker)
    elif plan_type == "temperament_promotion":
        classification = _classify_temperament_candidate(content=content, evidence=evidence, marker=marker)
    else:
        classification = _classify_persona_candidate(content=content, evidence=evidence, marker=marker)
    required_evidence_count = (
        1
        if (
            is_inner_truth  # RC12-INNER-002: one genuine observation is enough.
            or (plan_type == "memory_promotion" and classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS)
            or (plan_type == "persona_promotion" and classification["classification"] in EXPLICIT_PERSONA_CLASSIFICATIONS)
            or (plan_type == "temperament_promotion" and classification["classification"] in EXPLICIT_TEMPERAMENT_CLASSIFICATIONS)
        )
        else threshold
    )
    if required_evidence_count == 1 and threshold > 1:
        if plan_type == "memory_promotion":
            effective_threshold_source = "explicit_decision_policy"
        elif plan_type == "temperament_promotion":
            effective_threshold_source = "explicit_temperament_classification_policy"
        else:
            effective_threshold_source = "explicit_persona_instruction_policy"
    else:
        effective_threshold_source = threshold_source
    reason = answers["reason"] or f"Governed {plan_type} candidate."
    safety_notes = [
        "Policy before execution.",
        "Apply requires confirmed=true.",
        "Normal workspace tools cannot write protected profile files.",
        "The directive appends only if the candidate is absent.",
    ]

    decision = "approved_for_apply"
    eligible = True
    decision_reason = "Candidate satisfies promotion rules."

    try:
        _validate_reflection_semantics(
            marker=marker,
            content=content,
            evidence=evidence,
            candidate_for=candidate_for,
        )
    except ValueError as exc:
        decision = "rejected_semantics"
        eligible = False
        decision_reason = str(exc)

    if eligible and trust != "hoch":
        decision = "insufficient_trust"
        eligible = False
        decision_reason = f"Trust is '{trust}', but PBA2 promotion requires 'hoch'."

    if eligible and plan_type == "memory_promotion" and marker.casefold() in NON_BEHAVIORAL_MEMORY_MARKERS and classification["classification"] not in EXPLICIT_MEMORY_CLASSIFICATIONS:
        decision = "insufficient_marker"
        eligible = False
        decision_reason = (
            f"Marker '{marker}' is not directly memory-eligible for classification "
            f"'{classification['classification']}'. Transform the concern or wish into an explicit decision, "
            "scope boundary, security requirement or direct instruction before promotion."
        )

    # RC12-INNER-002 — the Innenperspektive marker is persona-only.
    if eligible and marker.casefold() == INNER_PERSPECTIVE_MARKER.casefold() and plan_type != "persona_promotion":
        decision = "insufficient_marker"
        eligible = False
        decision_reason = (
            f"Marker '{INNER_PERSPECTIVE_MARKER}' is only valid for persona_promotion "
            "(inner-perspective truths live in PERSONA.md)."
        )

    if (
        eligible
        and plan_type == "persona_promotion"
        and marker.casefold() not in {"muster", INNER_PERSPECTIVE_MARKER.casefold()}
        and classification["classification"] not in EXPLICIT_PERSONA_CLASSIFICATIONS
    ):
        decision = "insufficient_marker"
        eligible = False
        decision_reason = (
            f"Marker '{marker}' is not directly persona-eligible for classification "
            f"'{classification['classification']}'. Use an explicit persona instruction or a supported persona preference."
        )

    if eligible and plan_type == "temperament_promotion" and marker.casefold() not in {"muster", "beobachtung"} and classification["classification"] not in EXPLICIT_TEMPERAMENT_CLASSIFICATIONS:
        decision = "insufficient_marker"
        eligible = False
        decision_reason = (
            f"Marker '{marker}' is not directly temperament-eligible for classification "
            f"'{classification['classification']}'. Use marker 'Muster' or 'Beobachtung' for temperament observations."
        )

    if eligible and evidence_count < required_evidence_count:
        decision = "insufficient_evidence"
        eligible = False
        decision_reason = (
            f"Only {evidence_count} distinct evidence date(s); required evidence count is "
            f"{required_evidence_count} for classification '{classification['classification']}'."
        )

    # RC12-INNER-002 — cap active inner truths. A governance constraint, not a
    # threshold: force does NOT override it (decision is outside the override set).
    if eligible and is_inner_truth and _count_active_inner_truths(target_text) >= MAX_ACTIVE_INNER_TRUTHS:
        decision = "inner_truth_limit_reached"
        eligible = False
        decision_reason = (
            f"PERSONA.md already holds {MAX_ACTIVE_INNER_TRUTHS} active '{INNER_PERSPECTIVE_MARKER}' "
            "entries (the cap). Retire one (governed) before promoting a new inner truth."
        )

    # RC2-BUG-003: admin override for threshold-style denials.
    # force=true bypasses insufficient_marker / insufficient_evidence ONLY.
    # Semantic rejection, insufficient_trust, duplicate, conflict and
    # cross-profile/missing-profile denials are quality gates and are NEVER
    # overridden by force. force still requires confirmed=true in apply.
    admin_override_applied = False
    if (
        force
        and not eligible
        and decision in {"insufficient_marker", "insufficient_evidence"}
    ):
        admin_override_applied = True
        eligible = True
        previous_decision = decision
        previous_reason = decision_reason
        decision = "approved_for_apply"
        decision_reason = (
            f"Admin override applied: force=true bypassed '{previous_decision}'. "
            f"Original constraint: {previous_reason}"
        )

    if eligible and _target_contains_candidate(target_text, content):
        decision = "duplicate_noop"
        eligible = False
        admin_override_applied = False
        decision_reason = "Exact duplicate candidate already exists in target file."

    conflict_reason = _promotion_conflict_reason(content=content, conflicts_with=answers["conflicts_with"])
    if not conflict_reason and plan_type in {"persona_promotion", "temperament_promotion"}:
        conflict_reason = _persona_conflict_reason(content=content, current_persona=target_text)
    if eligible and conflict_reason:
        decision = "review_required"
        eligible = False
        admin_override_applied = False
        decision_reason = conflict_reason

    if plan_type == "memory_promotion":
        proposed_content = _format_memory_promotion_block(content=content, evidence=evidence, entry_date=entry_date)
    elif plan_type == "temperament_promotion":
        proposed_content = _format_temperament_promotion_block(
            content=content,
            evidence=evidence,
            entry_date=entry_date,
            current_temperament=target_text,
        )
    else:
        proposed_content = _format_persona_promotion_block(
            content=content,
            evidence=evidence,
            entry_date=entry_date,
            current_persona=target_text,
            marker=marker,
        )
    expected_changed_files = [target_file, "journal.md"] if eligible else ["journal.md"]
    return {
        "candidate_summary": content,
        "evidence": evidence,
        "confidence": confidence,
        "trust": trust,
        "marker": marker,
        "entry_date": entry_date,
        "candidate_for": candidate_for,
        "reason": decision_reason,
        "user_reason": reason,
        "threshold_used": required_evidence_count,
        "threshold_source": effective_threshold_source,
        "base_threshold_used": threshold,
        "base_threshold_source": threshold_source,
        "evidence_count": evidence_count,
        "distinct_evidence_dates": evidence_count,
        "evidence_dates_used": evidence_dates,
        "candidate_classification": classification["classification"],
        "classification_confidence": classification["confidence"],
        "eligibility_reason": decision_reason if eligible else "",
        "rejection_reason": "" if eligible else decision_reason,
        "decision": decision,
        "eligible_for_apply": eligible,
        "admin_override_applied": admin_override_applied,
        "admin_override_requested": bool(force),
        "explicit_decision_detected": classification["classification"] in EXPLICIT_MEMORY_CLASSIFICATIONS
        or classification["classification"] in EXPLICIT_PERSONA_CLASSIFICATIONS
        or classification["classification"] in EXPLICIT_TEMPERAMENT_CLASSIFICATIONS,
        "target_file": target_file,
        "target_section": answers["target_section"] or "ACTIVE",
        "proposed_content": proposed_content,
        "expected_changed_files": expected_changed_files,
        "safety_notes": safety_notes,
    }


def _invalid_promotion_evaluation(*, plan_type: str, target_file: str, reason: str) -> dict[str, Any]:
    threshold = 0
    return {
        "candidate_summary": "",
        "evidence": "",
        "confidence": "",
        "trust": "",
        "marker": "",
        "entry_date": "",
        "candidate_for": target_file,
        "reason": reason,
        "user_reason": "",
        "threshold_used": threshold,
        "threshold_source": "",
        "base_threshold_used": threshold,
        "base_threshold_source": "",
        "evidence_count": 0,
        "distinct_evidence_dates": 0,
        "candidate_classification": "rejected_or_unclear",
        "classification_confidence": "low",
        "explicit_decision_detected": False,
        "eligibility_reason": "",
        "rejection_reason": reason,
        "decision": "invalid",
        "eligible_for_apply": False,
        "target_file": target_file,
        "target_section": "ACTIVE",
        "proposed_content": "",
        "expected_changed_files": [],
        "safety_notes": ["Plan is invalid; no profile mutation is allowed."],
    }


def _promotion_revision_directive(
    *,
    plan_type: str,
    profile_name: str,
    target_file: str,
    evaluation: dict[str, Any],
    expected_precondition: dict[str, Any],
) -> dict[str, Any]:
    proposed_content = evaluation["proposed_content"] if evaluation["eligible_for_apply"] else ""
    directive_id = _stable_hash(
        {
            "plan_type": plan_type,
            "profile_name": profile_name,
            "target_file": target_file,
            "operation": "append_if_absent",
            "proposed_content": proposed_content,
            "decision": evaluation["decision"],
        }
    )
    return {
        "schema_version": "1.0",
        "directive_id": directive_id,
        "plan_type": plan_type,
        "profile_name": profile_name,
        "target_file": target_file,
        "target_section": evaluation["target_section"],
        "operation": "append_if_absent",
        "append_mode": "append_to_active_section_if_absent",
        "proposed_content": proposed_content,
        "reason": evaluation["reason"],
        "candidate_classification": evaluation.get("candidate_classification", "rejected_or_unclear"),
        "classification_confidence": evaluation.get("classification_confidence", "low"),
        "explicit_decision_detected": bool(evaluation.get("explicit_decision_detected")),
        "required_confirmation": True,
        "expected_precondition": expected_precondition,
        "expected_changed_file": target_file,
        "expected_changed_files": evaluation["expected_changed_files"],
        "safety_notes": evaluation["safety_notes"],
        "decision": evaluation["decision"],
        "current_state": _promotion_state_for_decision(evaluation["decision"]),
    }


def _promotion_plan_id(
    *,
    plan_type: str,
    profile_name: str,
    target_file: str,
    evaluation: dict[str, Any],
) -> str:
    payload = {
        "plan_type": plan_type,
        "profile_name": profile_name,
        "target_file": target_file,
        "candidate_summary": evaluation["candidate_summary"],
        "evidence": evaluation["evidence"],
        "trust": evaluation["trust"],
        "threshold_used": evaluation["threshold_used"],
        "decision": evaluation["decision"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _retirement_journal_payload(
    *,
    profile_name: str,
    plan_id: str,
    target_file: str,
    heading_before: str,
    heading_after: str,
    reason: str,
    conflicts_with: str,
    retired_at: str,
    changed_files: list[str],
    file_snapshots: dict[str, Any],
    directive_id: str = "",
    dedup: bool = False,
    retired_count: int = 1,
) -> dict[str, Any]:
    """RC8-FEAT-001 audit event for a confirmed retire.

    Emitted into the existing governor-event stream (``event_type`` =
    ``GOVERNOR_JOURNAL_EVENT_TYPE``) so existing journal tooling counts it, with
    ``plan_type=memory_retirement`` and retire-specific fields for the trail.
    """
    return {
        "schema_version": PBA2_JOURNAL_SCHEMA_VERSION,
        "timestamp": f"{retired_at}T00:00:00+00:00",
        "event_type": GOVERNOR_JOURNAL_EVENT_TYPE,
        "plan_id": plan_id,
        "plan_type": MEMORY_RETIREMENT_PLAN_TYPE,
        "profile_name": profile_name,
        "decision": "approved_for_apply",
        "state": "applied",
        "result": "retired",
        "changed_files": changed_files,
        "restored_files": [],
        "target_file": target_file,
        "retired_heading_before": heading_before,
        "retired_heading_after": heading_after,
        "directive_id": directive_id,
        "dedup": dedup,
        "retired_count": retired_count,
        "retirement_reason": reason,
        "conflicts_with": conflicts_with,
        "retired_at": retired_at,
        "file_snapshots": file_snapshots,
        "actor": "plwc-gateway",
        "tool": "plwc_governor",
        "reason": reason,
        "source_entry_ids": [],
        "failed_files": [],
        "rollback_errors": [],
    }


def _promotion_journal_payload(
    *,
    plan_type: str,
    profile_name: str,
    plan_id: str,
    evaluation: dict[str, Any],
    changed_files: list[str],
    result: str,
    directive_ids: list[str] | None = None,
    file_snapshots: dict[str, Any] | None = None,
    stale_directives: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    timestamp = (
        f"{evaluation['entry_date']}T00:00:00+00:00"
        if evaluation.get("entry_date")
        else datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    return {
        "schema_version": PBA2_JOURNAL_SCHEMA_VERSION,
        "timestamp": timestamp,
        "event_type": GOVERNOR_JOURNAL_EVENT_TYPE,
        "plan_id": plan_id,
        "plan_type": plan_type,
        "profile_name": profile_name,
        "directive_ids": directive_ids or [],
        "decision": evaluation["decision"],
        "state": _promotion_state_for_decision(evaluation["decision"], result=result),
        "changed_files": changed_files,
        "restored_files": [],
        "candidate_summary": evaluation["candidate_summary"],
        "evidence": evaluation["evidence"],
        "trust": evaluation["trust"],
        "confidence": evaluation["confidence"],
        "threshold_used": evaluation["threshold_used"],
        "threshold_source": evaluation.get("threshold_source", ""),
        "base_threshold_used": evaluation.get("base_threshold_used"),
        "base_threshold_source": evaluation.get("base_threshold_source", ""),
        "evidence_count": evaluation["evidence_count"],
        "distinct_evidence_dates": evaluation.get("distinct_evidence_dates", evaluation["evidence_count"]),
        "candidate_classification": evaluation.get("candidate_classification", "rejected_or_unclear"),
        "classification_confidence": evaluation.get("classification_confidence", "low"),
        "explicit_decision_detected": bool(evaluation.get("explicit_decision_detected")),
        "admin_override_applied": bool(evaluation.get("admin_override_applied")),
        "admin_override_requested": bool(evaluation.get("admin_override_requested")),
        "eligibility_reason": evaluation.get("eligibility_reason", ""),
        "rejection_reason": evaluation.get("rejection_reason", ""),
        "file_snapshots": file_snapshots or {},
        "actor": "plwc-gateway",
        "tool": "plwc_governor_apply",
        "reason": evaluation["reason"],
        "result": result,
        "error_category": _promotion_error_category(evaluation["decision"], result=result),
        "source_entry_ids": [],
        "stale_directives": stale_directives or [],
        "failed_files": [],
        "rollback_errors": [],
    }


def _promotion_state_for_decision(decision: str, *, result: str | None = None) -> str:
    if result == "stale" or decision == "stale":
        return "stale"
    if decision == "approved_for_apply":
        return "applied" if result == "applied" else "planned"
    if decision == "duplicate_noop":
        return "no_op"
    if decision == "review_required":
        return "review_required"
    if decision.startswith("insufficient") or decision.startswith("rejected"):
        return "rejected"
    return "failed"


def _promotion_error_category(decision: str, *, result: str) -> str | None:
    if result == "stale":
        return "stale_plan"
    if decision == "review_required":
        return "review_required"
    if decision.startswith("insufficient") or decision.startswith("rejected"):
        return "policy_denied"
    return None


def _format_governor_journal_event(payload: dict[str, Any]) -> str:
    return "\n".join(
        (
            f"## GOVERNOR EVENT {payload['plan_id']}",
            "```json",
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
            "```",
        )
    )


def _promotion_result_for_decision(decision: str, *, target_changed: bool = False) -> str:
    if decision == "approved_for_apply":
        return "applied" if target_changed else "planned"
    if decision == "duplicate_noop":
        return "no_op_duplicate"
    if decision == "review_required":
        return "review_required"
    if decision.startswith("insufficient") or decision.startswith("rejected"):
        return "rejected"
    return "not_applied"


def _format_memory_promotion_block(*, content: str, evidence: str, entry_date: str) -> str:
    return "\n".join(
        (
            f"## [ACTIVE] FAKT | {entry_date}",
            f"Inhalt: {content}",
            f"Verhaltensrelevanz: {evidence}",
        )
    )


def _format_persona_promotion_block(
    *, content: str, evidence: str, entry_date: str, current_persona: str, marker: str = "Muster"
) -> str:
    if marker.casefold() == INNER_PERSPECTIVE_MARKER.casefold():
        # RC12-INNER-002 — inner truth: one sentence + date + source (Tagebuch),
        # no version/Fehlerklasse. Replaced via governed retire+promote, not versioned.
        return "\n".join(
            (
                f"## [ACTIVE] {INNER_PERSPECTIVE_MARKER} | {entry_date}",
                f"Inhalt: {content}",
                f"Quelle: {evidence}",
            )
        )
    version = _next_persona_version(current_persona)
    return "\n".join(
        (
            f"## [ACTIVE] Muster | Version {version}.0 | {entry_date}",
            f"Inhalt: {content}",
            f"Belegt durch: {evidence}",
            "Fehlerklasse bei Revision:",
        )
    )


def _next_persona_version(current_persona: str) -> int:
    versions = [int(match) for match in re.findall(r"Version\s+(\d+)\.\d+", current_persona)]
    return max(versions, default=1) + 1


def _format_temperament_promotion_block(*, content: str, evidence: str, entry_date: str, current_temperament: str) -> str:
    version = _next_persona_version(current_temperament)
    return "\n".join(
        (
            f"## [ACTIVE] Muster | Version {version}.0 | {entry_date}",
            f"Inhalt: {content}",
            f"Belegt durch: {evidence}",
            "Fehlerklasse bei Revision:",
        )
    )


def _target_contains_candidate(target_text: str, candidate: str) -> bool:
    needle = _normalize_reflection_text(candidate)
    return bool(needle) and needle in _normalize_reflection_text(target_text)


def _promotion_conflict_reason(*, content: str, conflicts_with: str) -> str:
    if conflicts_with.strip():
        return "Candidate declares a conflict with existing profile content and requires user review."
    text = _normalize_reflection_text(content)
    conflict_terms = (
        "conflicts with",
        "contradicts",
        "instead of",
        "replace ",
        "replaces ",
        "no longer",
        "nicht mehr",
        "widerspricht",
        "stattdessen",
        "ersetzen",
    )
    if any(term in text for term in conflict_terms):
        return "Candidate appears to conflict with existing profile content and requires user review."
    return ""


def _persona_conflict_reason(*, content: str, current_persona: str) -> str:
    text = _normalize_reflection_text(content)
    current = _normalize_reflection_text(current_persona)
    families: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str, str], ...] = (
        (
            "address_formality",
            ("sprich mich mit du", "du an", "informal address", "informell"),
            ("sprich mich formell", "formell mit sie", "formal address", "sie an", "sie-form", "foermlich", "förmlich", "formal"),
            "existing persona prefers informal address while the candidate requests formal address",
            "existing persona prefers formal address while the candidate requests informal address",
        ),
        (
            "plwc_working_style",
            (
                "kleinteilig",
                "small steps",
                "prüfbar",
                "pruefbar",
                "akzeptanzkriterien",
                "acceptance criteria",
                "checklist",
            ),
            (
                "nicht kleinteilig",
                "not small steps",
                "keine akzeptanzkriterien",
                "no acceptance criteria",
                "without acceptance criteria",
                "keine checkliste",
                "no checklist",
            ),
            "existing persona requires detailed/checkable PLwC working style while the candidate rejects it",
            "existing persona rejects detailed/checkable PLwC working style while the candidate requires it",
        ),
        (
            "translation_fidelity",
            ("immer 1:1", "1:1", "wortgetreu", "literal translation", "translation fidelity"),
            (
                "frei umformulieren",
                "free rewriting",
                "free rewrite",
                "paraphrase",
                "sinngemäß",
                "sinngemaess",
                "nicht 1:1",
                "not 1:1",
            ),
            "existing persona requires strict translation fidelity while the candidate requests free rewriting",
            "existing persona allows free rewriting while the candidate requires strict translation fidelity",
        ),
        (
            "safety_strictness",
            ("klar blockieren", "block rather than guess", "nicht raten", "do not guess", "rather block"),
            ("lieber raten", "rather guess", "nicht blockieren", "do not block", "allow risky"),
            "existing persona prefers strict safety blocking while the candidate asks for lenient guessing",
            "existing persona allows lenient guessing while the candidate asks for strict safety blocking",
        ),
        (
            "verbosity_detail",
            ("kurz", "short answers", "concise", "knapp"),
            ("ausführlich", "ausfuehrlich", "detailed", "detailreich"),
            "existing persona prefers concise answers while the candidate asks for detailed answers",
            "existing persona prefers detailed answers while the candidate asks for concise answers",
        ),
    )
    for family, positive_terms, negative_terms, positive_existing_reason, negative_existing_reason in families:
        text_positive = _contains_any(text, positive_terms)
        text_negative = _contains_any(text, negative_terms)
        current_positive = _contains_any(current, positive_terms)
        current_negative = _contains_any(current, negative_terms)
        if text_positive and current_negative:
            return f"Persona conflict detected in {family}: {negative_existing_reason}."
        if text_negative and current_positive:
            return f"Persona conflict detected in {family}: {positive_existing_reason}."
    return ""


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _distinct_evidence_dates(evidence: str, *, entry_date: str = "") -> list[str]:
    # P2: expose the actual evidence days used for a decision (sorted). The count
    # helper below delegates here so list and count stay consistent.
    dates = set(EVIDENCE_DATE_RE.findall(evidence))
    if not dates and entry_date:
        dates.add(entry_date)
    return sorted(dates)


def _count_distinct_evidence_dates(evidence: str, *, entry_date: str = "") -> int:
    return len(_distinct_evidence_dates(evidence, entry_date=entry_date))


def _confidence_from_trust(trust: str) -> str:
    if trust == "hoch":
        return "high"
    if trust == "mittel":
        return "medium"
    if trust == "niedrig":
        return "low"
    return ""


def _append_profile_block(current: str, block: str) -> str:
    base = current.rstrip()
    addition = block.strip()
    if not addition:
        return current
    if not base:
        return addition + "\n"
    return base + "\n\n" + addition + "\n"


def _path_text_has_parent_traversal(value: str) -> bool:
    return ".." in value.replace("\\", "/").split("/")


def _is_filesystem_root(path_value: Path) -> bool:
    anchor = Path(path_value.anchor) if path_value.anchor else None
    return anchor is not None and _normalize_path(path_value) == _normalize_path(anchor)


def _is_home_root(path_value: Path) -> bool:
    return _normalize_path(path_value) == _normalize_path(Path.home().resolve(strict=False))


def _is_system_path(path_value: Path) -> bool:
    if sys.platform != "win32":
        return False
    system_root = os.environ.get("SystemRoot") or r"C:\Windows"
    windows_root = Path(system_root).resolve(strict=False)
    return _is_inside_or_same(path_value, windows_root)


def _normalize_plan_type(plan_type: str) -> str:
    return plan_type.strip().casefold().replace("-", "_")


def _validate_requested_activation_profile(value: str) -> str:
    if not value.strip():
        raise ValueError("Profile activation requires a target profile name.")
    return _validate_profile_name(value)


def _validate_profile_name(value: str) -> str:
    cleaned = value.strip() or "default"
    if Path(cleaned).name != cleaned or cleaned.casefold() == "template":
        raise ValueError("Profile name must be a non-template name without path separators.")
    if any(char in cleaned for char in (":", "*", "?", '"', "<", ">", "|")):
        raise ValueError("Profile name contains unsupported path characters.")
    return cleaned


def _same_profile_name(left: str, right: str) -> bool:
    if sys.platform == "win32":
        return left.casefold() == right.casefold()
    return left == right


def _is_inside_or_same(candidate: Path, root: Path) -> bool:
    try:
        common_path = os.path.commonpath([_normalize_path(candidate), _normalize_path(root)])
    except ValueError:
        return False
    return common_path == _normalize_path(root)


def _normalize_path(path_value: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path_value)))


def _active_profile_state_payload(profile_name: str, *, current_profile: str) -> dict[str, str]:
    return {
        "schema_version": "1.0",
        "active_profile_name": profile_name,
        "previous_active_profile_name": current_profile,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "plwc_governor_apply",
        "plan_type": "profile_activation",
    }


def _validate_onboarding_answers(
    answers: dict[str, Any] | None,
    profile: str,
    *,
    persona_layer_enabled: bool = True,
) -> dict[str, Any]:
    raw_answers = answers or {}
    field_key_map = {
        _normalize_answer_key(field): field
        for field in PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES
    }
    label_key_map = {
        _normalize_answer_key(question): field
        for field, question in (*PROFILE_ONBOARDING_FIELDS, *PROFILE_ONBOARDING_OPTIONAL_FIELDS)
    }
    alias_key_map = {
        _normalize_answer_key(alias): canonical
        for alias, canonical in PROFILE_ONBOARDING_ALIAS_MAP.items()
    }
    suggested_key_map = {
        _normalize_answer_key(alias): canonical
        for alias, canonical in PROFILE_ONBOARDING_SUGGESTED_MAPPINGS.items()
    }
    normalized = {field: "" for field in PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES}
    provided_fields: set[str] = set()
    unknown_fields: list[str] = []
    suggested_mappings: dict[str, str] = {}
    alias_mappings_applied: list[dict[str, str]] = []
    conflicting_fields: list[dict[str, str]] = []

    for key, value in raw_answers.items():
        original_key = str(key)
        normalized_key = _normalize_answer_key(original_key)
        text = "" if value is None else _safe_onboarding_text(value, original_key)
        canonical = field_key_map.get(normalized_key)
        alias_type = ""
        if canonical is None:
            canonical = alias_key_map.get(normalized_key)
            alias_type = "alias" if canonical else ""
        if canonical is None:
            canonical = label_key_map.get(normalized_key)
            alias_type = "question_label" if canonical else ""
        if canonical is None:
            unknown_fields.append(original_key)
            if normalized_key in suggested_key_map:
                suggested_mappings[original_key] = suggested_key_map[normalized_key]
            continue

        if alias_type:
            alias_mappings_applied.append(
                {
                    "provided_field": original_key,
                    "canonical_field": canonical,
                    "mapping_type": alias_type,
                }
            )
        if normalized[canonical] and text and normalized[canonical] != text:
            conflicting_fields.append(
                {
                    "field": canonical,
                    "existing_value_source": "canonical_or_earlier_alias",
                    "conflicting_field": original_key,
                }
            )
            continue
        if text:
            normalized[canonical] = text
            provided_fields.add(canonical)

    if not normalized["profile_name"]:
        normalized["profile_name"] = profile
        if profile:
            provided_fields.add("profile_name")
    normalized["profile_name"] = _validate_profile_name(normalized["profile_name"])
    required_fields = _profile_onboarding_required_field_names(persona_layer_enabled=persona_layer_enabled)
    optional_fields = _profile_onboarding_optional_field_names(persona_layer_enabled=persona_layer_enabled)
    active_fields = _profile_onboarding_active_field_names(persona_layer_enabled=persona_layer_enabled)
    inactive_fields = _profile_onboarding_inactive_field_names(persona_layer_enabled=persona_layer_enabled)
    missing_required_fields = [
        field
        for field in required_fields
        if not normalized[field].strip()
    ]
    decision = "approved_for_apply"
    validation_error = ""
    warning_parts: list[str] = []
    if unknown_fields or missing_required_fields or conflicting_fields:
        decision = "needs_correction"
        if unknown_fields:
            warning_parts.append("Unknown onboarding fields were provided.")
        if missing_required_fields:
            warning_parts.append("Required onboarding fields are missing.")
        if conflicting_fields:
            warning_parts.append("Conflicting onboarding fields map to the same canonical field.")
        validation_error = " ".join(warning_parts)
    return {
        "schema_version": PROFILE_ONBOARDING_SCHEMA_VERSION,
        "decision": decision,
        "accepted_fields": list(PROFILE_ONBOARDING_ACCEPTED_FIELD_NAMES),
        "active_fields": list(active_fields),
        "inactive_fields": list(inactive_fields),
        "required_fields": list(required_fields),
        "optional_fields": list(optional_fields),
        "provided_fields": sorted(provided_fields),
        "unknown_fields": unknown_fields,
        "missing_required_fields": missing_required_fields,
        "suggested_mappings": suggested_mappings,
        "alias_mappings_applied": alias_mappings_applied,
        "conflicting_fields": conflicting_fields,
        "normalized_onboarding_answers": normalized,
        "validation_warning": " ".join(warning_parts),
        "validation_error": validation_error,
    }


def _normalize_onboarding_answers(answers: dict[str, Any] | None, profile: str) -> dict[str, str]:
    return _validate_onboarding_answers(answers, profile)["normalized_onboarding_answers"]


def _normalize_answer_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _answer_or_default(answers: dict[str, str], field: str, default: str) -> str:
    return answers[field].strip() or default


def _safe_onboarding_text(value: Any, label: str) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\x00" in text:
        raise ValueError(f"Onboarding field {label} contains unsupported control characters.")
    if len(text) > 2000:
        raise ValueError(f"Onboarding field {label} is too long.")
    return text


def _render_profile_creation_contents(
    *,
    profile_name: str,
    answers: dict[str, str],
    memory_write_threshold: int,
    persona_write_threshold: int,
    temperament_write_threshold: int = DEFAULT_TEMPERAMENT_WRITE_THRESHOLD,
) -> dict[str, str]:
    role = _answer_or_default(answers, "role_use_case", "Not specified; operate as a conservative PLwC assistant.")
    preferred_name = _answer_or_default(answers, "preferred_name", "No preferred name was provided during onboarding.")
    address = _answer_or_default(answers, "form_of_address", "Use the user's chosen name when known; otherwise ask.")
    tone = _answer_or_default(answers, "tone", "Factual, calm and direct.")
    working_style = _answer_or_default(answers, "working_style", "Structured, explicit and verification-oriented.")
    strictness = _answer_or_default(answers, "strictness", "Prefer safety, traceability and clear uncertainty over speed.")
    memory_scope = _answer_or_default(
        answers,
        "memory_scope",
        "Store only stable, explicitly confirmed long-term preferences or project facts.",
    )
    confirmation_boundaries = _answer_or_default(
        answers,
        "confirmation_boundaries",
        "Do not change persona, memory, policy, protected files or release decisions without confirmation.",
    )
    project_context = _answer_or_default(answers, "project_context", "No project context was provided during onboarding.")
    language_preference = _answer_or_default(
        answers,
        "language_preference",
        "Use the user's language unless a task or document requires another language.",
    )
    special_instructions = answers["special_instructions"].strip()
    generated_at = datetime.now(timezone.utc).date().isoformat()
    return {
        "CORE.md": _profile_core(profile_name),
        "PERSONA.md": _profile_persona(
            role,
            project_context,
            preferred_name,
            address,
            memory_scope,
            confirmation_boundaries,
            language_preference,
            special_instructions,
        ),
        "TEMPERAMENT.md": _profile_temperament(tone, working_style, strictness, language_preference, special_instructions),
        "memory.md": _profile_memory(memory_scope),
        "reflection.md": _profile_reflection(),
        "governance/config.yaml": _profile_governance_config(
            profile_name=profile_name,
            memory_write_threshold=memory_write_threshold,
            persona_write_threshold=persona_write_threshold,
            temperament_write_threshold=temperament_write_threshold,
            confirmation_boundaries=confirmation_boundaries,
        ),
        "journal.md": f"# Journal\n\n- {generated_at}: Profile created through governed PLwC onboarding.\n",
    }


def _render_bootstrap_profile_contents(
    *,
    profile_name: str,
    memory_write_threshold: int,
    persona_write_threshold: int,
    temperament_write_threshold: int = DEFAULT_TEMPERAMENT_WRITE_THRESHOLD,
) -> dict[str, str]:
    generated_at = datetime.now(timezone.utc).date().isoformat()
    return {
        "CORE.md": f"""# CORE

Profile: {profile_name}

## Bootstrap State

This is a neutral PLwC standard profile. Onboarding is pending.

## Core Operating Principles

- Security before convenience.
- Traceability before speed.
- Do not invent user-specific facts.
- Use PLwC-provided onboarding questions for personalization.
- Keep public MCP access behind plwc-gateway only.
""",
        "PERSONA.md": f"""# PERSONA

## Bootstrap State

{BOOTSTRAP_STARTUP_MESSAGE}

## Role / Use Case

Not configured yet. Ask the user whether to start PLwC onboarding before making profile-specific assumptions.

## Main Project / Work Context

Not configured yet.

## Form Of Address

Not configured yet. Ask the user.

## Stable Preferences

No stable user preferences have been collected yet.

## Memory Rules

Do not store user-specific memories until onboarding or a governed memory flow provides explicit confirmation.

## Confirmation Boundaries

Do not change persona, memory, policy, protected files or release decisions without confirmation.
""",
        "TEMPERAMENT.md": """# TEMPERAMENT

## Tone

Neutral, factual and calm.

## Working Style

Systematic, explicit and verification-oriented.

## Strictness

Conservative until onboarding defines stronger preferences.
""",
        "memory.md": """# Memory

## Initial State

No user memories exist yet.

## Storage Policy

Do not invent facts. Store only stable, explicitly confirmed long-term preferences or project facts through governed PLwC flows.
""",
        "reflection.md": """# Reflection

No reflection history exists yet.

Onboarding is pending. Future reflections must be written through governed PLwC reflection tools.
""",
        "governance/config.yaml": _profile_governance_config(
            profile_name=profile_name,
            memory_write_threshold=memory_write_threshold,
            persona_write_threshold=persona_write_threshold,
            temperament_write_threshold=temperament_write_threshold,
            confirmation_boundaries="Onboarding is pending. Confirm before changing profile, memory, policy or protected files.",
            profile_kind="bootstrap",
            onboarding_complete=False,
        ),
        "journal.md": f"# Journal\n\n- {generated_at}: Neutral bootstrap profile created. Onboarding is pending.\n",
    }


def _profile_core(profile_name: str) -> str:
    return f"""# CORE

Profile: {profile_name}

## Core Operating Principles

- Security before convenience.
- Traceability before speed.
- Do not invent personal facts.
- Keep public MCP access behind plwc-gateway only.
- Ask for confirmation before protected profile, memory, persona, policy or release changes.
"""


def _profile_persona(
    role: str,
    project_context: str,
    preferred_name: str,
    address: str,
    memory_scope: str,
    confirmation_boundaries: str,
    language_preference: str,
    special_instructions: str,
) -> str:
    special_section = f"""
## Special Instructions

{special_instructions}
""" if special_instructions else ""
    return f"""# PERSONA

## Role / Use Case

{role}

## Main Project / Work Context

{project_context}

## Preferred Name

{preferred_name}

## Form Of Address

{address}

## Stable Preferences

- Respect the configured tone and working style.
- Keep uncertainty visible.
- Avoid promises that cannot be verified.

## Memory Rules

{memory_scope}

## Confirmation Boundaries

{confirmation_boundaries}

## Language Preference

{language_preference}
{special_section}
"""


def _profile_temperament(
    tone: str,
    working_style: str,
    strictness: str,
    language_preference: str,
    special_instructions: str,
) -> str:
    special_section = f"""
## Special Instructions

{special_instructions}
""" if special_instructions else ""
    return f"""# TEMPERAMENT

## Tone

{tone}

## Working Style

{working_style}

## Strictness

{strictness}

## Language

{language_preference}
{special_section}
"""


def _profile_memory(memory_scope: str) -> str:
    return f"""# Memory

## Initial State

No user memories were created during onboarding.

## Storage Policy

{memory_scope}

Future memory writes must use governed PLwC profile flows and require sufficient evidence.
"""


def _profile_reflection() -> str:
    return """# Reflection

No reflection history exists yet.

Future reflections must be written through governed PLwC reflection tools. Do not invent prior reflection history.
"""


def _profile_governance_config(
    *,
    profile_name: str,
    memory_write_threshold: int,
    persona_write_threshold: int,
    temperament_write_threshold: int = DEFAULT_TEMPERAMENT_WRITE_THRESHOLD,
    confirmation_boundaries: str,
    profile_kind: str = "personalized",
    onboarding_complete: bool = True,
) -> str:
    pending = "false" if onboarding_complete else "true"
    complete = "true" if onboarding_complete else "false"
    return f"""schema_version: "1.0"
profile_name: {_yaml_quote(profile_name)}
profile_kind: {_yaml_quote(profile_kind)}
onboarding:
  pending: {pending}
  complete: {complete}
governance:
  memory_write_threshold: {memory_write_threshold}
  persona_write_threshold: {persona_write_threshold}
  temperament_write_threshold: {temperament_write_threshold}
confirmation_required:
  profile_creation: true
  memory_changes: true
  persona_changes: true
  reflection_writes: true
protected_files:
  - CORE.md
  - PERSONA.md
  - TEMPERAMENT.md
  - memory.md
  - reflection.md
  - governance/config.yaml
write_boundaries:
  workspace_tools_may_modify_profile_files: false
  governed_tools_required: true
confirmation_boundaries: {_yaml_quote(confirmation_boundaries)}
"""


def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _profile_runtime_metadata(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile_kind": data.get("profile_kind"),
        "onboarding_required": data.get("onboarding_required"),
        "onboarding_complete": data.get("onboarding_complete"),
        "startup_message": data.get("startup_message"),
        "runtime_contract": data.get("runtime_contract"),
    }


def _profile_kind(profile_path: Path) -> str:
    config_text = _profile_governance_text(profile_path)
    if 'profile_kind: "bootstrap"' in config_text or "profile_kind: bootstrap" in config_text:
        return "bootstrap"
    if 'profile_kind: "personalized"' in config_text or "profile_kind: personalized" in config_text:
        return "personalized"
    if 'profile_kind: "imported_pba2"' in config_text or "profile_kind: imported_pba2" in config_text:
        return "imported_pba2"
    return "legacy"


def _profile_onboarding_complete(profile_path: Path) -> bool:
    config_text = _profile_governance_text(profile_path)
    if "complete: false" in config_text or "onboarding_complete: false" in config_text:
        return False
    if _profile_kind(profile_path) == "bootstrap":
        return False
    return True


def _is_bootstrap_profile(profile_path: Path) -> bool:
    return _profile_kind(profile_path) == "bootstrap" and not _profile_onboarding_complete(profile_path)


def _profile_governance_text(profile_path: Path) -> str:
    config_file = profile_path / "governance" / "config.yaml"
    if not config_file.exists():
        return ""
    return config_file.read_text(encoding="utf-8")


def _profile_schema_validation(profile_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_files = _missing_profile_files(profile_path)
    if missing_files:
        errors.append(f"Missing required profile files: {', '.join(missing_files)}")
    if (profile_path / "governance" / "config.yaml").exists():
        governance = _profile_governance_validation(profile_path)
        errors.extend(governance["errors"])
        warnings.extend(governance["warnings"])
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "required_files": list(PROFILE_REQUIRED_FILES),
        "optional_files": list(PROFILE_OPTIONAL_FILES),
        "generated_files": ["compiled_prompt.txt"],
        "protected_files": list(PROFILE_REQUIRED_FILES),
    }


def _profile_governance_validation(profile_path: Path) -> dict[str, list[str]]:
    values = _simple_key_value_lines(_profile_governance_text(profile_path))
    errors: list[str] = []
    warnings: list[str] = []

    for key, default in (
        ("memory_write_threshold", DEFAULT_MEMORY_WRITE_THRESHOLD),
        ("persona_write_threshold", DEFAULT_PERSONA_WRITE_THRESHOLD),
        ("temperament_write_threshold", DEFAULT_TEMPERAMENT_WRITE_THRESHOLD),
    ):
        if key not in values:
            warnings.append(f"governance/config.yaml does not define {key}; runtime uses gateway default {default}.")
            continue
        try:
            parsed = int(str(values[key]).strip())
        except ValueError:
            errors.append(f"governance/config.yaml {key} must be an integer of at least 1.")
            continue
        if parsed < 1:
            errors.append(f"governance/config.yaml {key} must be at least 1.")

    boundary_flags = {
        "workspace_tools_may_modify_profile_files": False,
        "governed_tools_required": True,
    }
    for key, expected in boundary_flags.items():
        if key not in values:
            continue
        actual = _bool_value(str(values[key]))
        if actual is not expected:
            errors.append(f"governance/config.yaml {key} must remain {str(expected).lower()}.")

    dangerous_keys = {
        "allow_direct_profile_writes",
        "allow_workspace_profile_writes",
        "disable_protected_file_boundary",
        "disable_governor_confirmation",
    }
    for key in dangerous_keys & set(values):
        if _bool_value(str(values[key])):
            errors.append(f"governance/config.yaml {key} is not supported and cannot enable protected-file bypass.")

    return {"errors": errors, "warnings": warnings}


def _missing_profile_files(profile_path: Path) -> list[str]:
    missing: list[str] = []
    for filename in PROFILE_REQUIRED_FILES:
        target = profile_path / filename
        if not target.exists() or not target.is_file():
            missing.append(filename)
    return missing


def _profile_runtime_reason(
    *,
    source_root: Path,
    source_root_explicit: bool,
    active_profile_exists: bool,
    runtime_callable: RuntimeCallable | None,
) -> str:
    if not active_profile_exists:
        return "active_profile_missing"
    if runtime_callable is not None:
        return "provided_runtime_callable"
    if source_root_explicit and source_root.exists():
        return "source_a_runtime"
    return "plwc_internal_profile_runtime"


def run_plwc_profile_runtime(
    profile: Path | str | None = None,
    *,
    task_context: str = "",
    run_governor: bool = False,
    governor_apply: bool = False,
    governor_force: bool = False,
    governor_confirmed: bool = False,
    today: str | None = None,
) -> dict[str, Any]:
    if profile is None:
        return {"ok": False, "errors": ["Profile path is required."]}
    profile_path = Path(profile).resolve(strict=False)
    missing_files = _missing_profile_files(profile_path)
    if missing_files:
        return {"ok": False, "errors": [f"Missing required profile files: {', '.join(missing_files)}"]}
    schema_validation = _profile_schema_validation(profile_path)
    if not schema_validation["valid"]:
        return {
            "ok": False,
            "errors": [f"Invalid profile schema: {'; '.join(schema_validation['errors'])}"],
            "profile_schema_validation": schema_validation,
        }

    files = _read_profile_files(profile_path)
    profile_kind = _profile_kind(profile_path)
    onboarding_complete = _profile_onboarding_complete(profile_path)
    startup_message = BOOTSTRAP_STARTUP_MESSAGE if not onboarding_complete else None
    snapshot = {
        "profile_name": profile_path.name,
        "profile_kind": profile_kind,
        "onboarding_complete": onboarding_complete,
        "onboarding_required": not onboarding_complete,
        "startup_message": startup_message,
        "required_files": list(PROFILE_REQUIRED_FILES),
        "optional_files": {filename: (profile_path / filename).exists() for filename in PROFILE_OPTIONAL_FILES},
        "files": files,
        "file_metadata": {
            filename: {
                "chars": len(content),
                "lines": len(content.splitlines()),
            }
            for filename, content in files.items()
        },
        "governance": _governance_summary(profile_path),
        "thresholds": _governance_thresholds(profile_path),
        "profile_schema_validation": schema_validation,
        "protected_files": list(PROFILE_REQUIRED_FILES),
        "reflection_summary": _reflection_summary(files.get("reflection.md", "")),
        "journal_summary": _journal_summary(
            (profile_path / "journal.md").read_text(encoding="utf-8")
            if (profile_path / "journal.md").exists()
            else ""
        ),
        "state_summary": _state_summary(files.get(PBA2_STATE_FILE, "")),
    }
    compiled_layer = _compile_profile_layer(
        profile_name=profile_path.name,
        files=files,
        task_context=task_context,
    )
    result: dict[str, Any] = {
        "ok": True,
        "errors": [],
        "runtime_contract": "plwc_internal_profile_runtime",
        "profile_name": profile_path.name,
        "profile_kind": profile_kind,
        "onboarding_complete": onboarding_complete,
        "onboarding_required": not onboarding_complete,
        "startup_message": startup_message,
        "snapshot": snapshot,
        "compiled_layer": compiled_layer,
        "profile_schema_validation": schema_validation,
    }
    if run_governor:
        # P3: compact skipped_candidates in the public response (count + per-decision
        # summary); the full list stays in the journal/audit trail. Boundary-only —
        # _governor_result has already written its journal events internally.
        result["governor_result"] = _compact_skipped_candidates(
            _governor_result(
                profile_path=profile_path,
                apply=governor_apply,
                force=governor_force,
                confirmed=governor_confirmed,
                today=today,
            )
        )
        result["apply"] = governor_apply
    return result


def _read_profile_files(profile_path: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for filename in PROFILE_REQUIRED_FILES:
        files[filename] = (profile_path / filename).read_text(encoding="utf-8")
    state_file = profile_path / PBA2_STATE_FILE
    if state_file.exists():
        files[PBA2_STATE_FILE] = state_file.read_text(encoding="utf-8")
    return files


def _compile_profile_layer(*, profile_name: str, files: dict[str, str], task_context: str) -> str:
    parts = ["PBA 2.0 Personality Layer", "", f"Profile: {profile_name}", "", _state_context_line(files.get(PBA2_STATE_FILE, ""))]
    for filename in PBA2_PERSONALITY_LAYER_FILES:
        label = filename.removesuffix(".md").upper()
        parts.extend(["", f"{label}:", _strip_retired_sections(files.get(filename, "")).strip()])
    parts.extend(["", "TASK CONTEXT:", task_context])
    return "\n".join(parts)


def _strip_retired_sections(text: str) -> str:
    """Drop [RETIRED] level-2 sections from a profile file for the compiled layer.

    RC8-FEAT-001: retirement is a status change, not a deletion. A retired entry
    stays physically in the file (audit trail) but must not appear in the
    compiled personality layer. Sections start at a ``## `` heading; a section
    whose heading begins with ``## [RETIRED]`` is excluded up to (but not
    including) the next ``## `` heading. Preamble before the first heading and
    all non-retired sections are preserved verbatim.
    """
    result: list[str] = []
    skipping = False
    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            skipping = line.startswith("## [RETIRED]")
        if not skipping:
            result.append(line)
    return "".join(result)


def _retire_entry_in_text(
    text: str,
    *,
    heading: str = "",
    directive_id: str = "",
    retired_at: str,
    reason: str,
    conflicts_with: str = "",
    dedup: bool = False,
) -> dict[str, Any]:
    """Flip ``## [ACTIVE]`` entry/entries to ``## [RETIRED]`` and append metadata.

    RC8-FEAT-001: status change only, never a deletion. RC12-RETIRE-001: an entry
    may be selected either by its **exact heading line** (``heading``) or by its
    stable **``directive_id``** (= ``canonical_section_sha256`` over heading+body —
    the same per-section SHA the indexer already computes). The directive_id
    selector resolves the ``ambiguous_heading`` case, where several entries share a
    heading but differ in body. Byte-identical sections share one directive_id;
    that is surfaced as ``exact_duplicate`` (no silent guess) unless ``dedup=True``,
    which keeps one and retires the rest. Bodies are preserved verbatim;
    ``retired_at`` / ``Grund`` / ``conflicts_with`` are appended after the last
    non-blank body line. The function never mutates on a non-match; the caller
    inspects ``reason`` and only writes when ``changed`` is True. Operates on LF
    lines (``read_text`` normalizes CRLF).

    ``reason`` values: ``retired`` (success), ``entry_not_found``,
    ``ambiguous_heading`` (heading-mode, >1 line matches — caller must
    disambiguate), ``exact_duplicate`` (directive_id-mode, >1 byte-identical match
    and ``dedup`` is False), ``already_retired``, ``not_active`` (heading is
    neither ACTIVE nor RETIRED).
    """
    from .qdrant_index import canonical_section_sha256  # local import: avoid load-time coupling

    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith("## ")]
    starts.append(len(lines))
    spans = [(starts[k], starts[k + 1]) for k in range(len(starts) - 1)]

    want_id = directive_id.strip()
    if want_id:
        matches = [
            (start, end)
            for (start, end) in spans
            if canonical_section_sha256(lines[start], "\n".join(lines[start + 1 : end]).strip()) == want_id
        ]
    else:
        target = heading.strip()
        matches = [(start, end) for (start, end) in spans if lines[start].strip() == target]

    if not matches:
        return {"changed": False, "reason": "entry_not_found", "new_text": text, "matched": 0}

    head_line = lines[matches[0][0]]
    if head_line.startswith("## [RETIRED]"):
        return {"changed": False, "reason": "already_retired", "new_text": text, "matched": len(matches)}
    if not head_line.startswith("## [ACTIVE]"):
        return {"changed": False, "reason": "not_active", "new_text": text, "matched": len(matches)}

    if len(matches) > 1:
        if not want_id:
            return {"changed": False, "reason": "ambiguous_heading", "new_text": text, "matched": len(matches)}
        if not dedup:
            return {"changed": False, "reason": "exact_duplicate", "new_text": text, "matched": len(matches)}

    # Sections to retire: the single match, or (dedup) every byte-identical match but
    # the first — keep one ACTIVE, retire the rest. All matches share heading+body, so
    # heading_before/after are one representative for every retired section.
    to_retire = matches if len(matches) == 1 else matches[1:]
    head_before = lines[to_retire[0][0]]
    head_after = head_before.replace("[ACTIVE]", "[RETIRED]", 1)
    meta = [f"retired_at: {retired_at}", f"Grund: {reason}"]
    if conflicts_with.strip():
        meta.append(f"conflicts_with: {conflicts_with.strip()}")

    # Apply from the last span to the first so meta insertions don't shift earlier spans.
    for start, end in sorted(to_retire, reverse=True):
        lines[start] = lines[start].replace("[ACTIVE]", "[RETIRED]", 1)
        body_end = end
        while body_end - 1 > start and lines[body_end - 1].strip() == "":
            body_end -= 1
        lines[body_end:body_end] = meta

    return {
        "changed": True,
        "reason": "retired",
        "new_text": "\n".join(lines),
        "matched": len(matches),
        "retired_count": len(to_retire),
        "kept_count": len(matches) - len(to_retire),
        "dedup": len(matches) > 1,
        "heading_before": head_before,
        "heading_after": head_after,
    }


# RC8-FEAT-001 — list_retirable heuristics. The behavioral-consequence labels
# and consequence/imperative markers below are the transparent structural basis
# for the soft ``no_action_rule`` flag (criterion #4). Deliberately simple and
# documented: false positives are expected — it is a flag plus a question, never
# an automatic retirement reason.
_CONSEQUENCE_LABELS = ("Verhaltensrelevanz:", "Belegt durch:", "Handlungsregel:", "Konsequenz:")
_CONSEQUENCE_MARKERS = (
    "folgt", "nutze", "nutzt", "vermeide", "bevorzug", "immer", "nie", "niemals",
    "wenn ", "dann ", "soll", "darf", "muss", "müssen", "regel", "grenze",
    "prefer", "avoid", "always", "never", "if ", "then ", "must", "should", "rule", "boundary",
)
NO_ACTION_RULE_REVIEW_QUESTION = (
    "Does this entry yield a concrete action rule, boundary, preference or "
    "decision aid — or is it only self-image / legend? If legend: consider retire."
)


def _entry_has_action_rule(body: str) -> bool:
    """Transparent heuristic: does an entry body carry actionable behavior?

    True if it has a non-empty behavioral-consequence line (e.g.
    ``Verhaltensrelevanz:`` / ``Belegt durch:``) **or** any consequence/imperative
    marker. Absence drives the soft ``no_action_rule`` flag — never a hard gate.
    """
    for line in body.split("\n"):
        stripped = line.strip()
        for label in _CONSEQUENCE_LABELS:
            if stripped.startswith(label) and stripped[len(label):].strip():
                return True
    lowered = body.lower()
    return any(marker in lowered for marker in _CONSEQUENCE_MARKERS)


def _candidate_has_action_rule(content: str) -> bool:
    """RC8-FEAT-001b — promotion-time actionability heuristic on candidate content.

    Unlike the retire-side check, this looks **only** at consequence/imperative
    markers in the candidate's own text. At promotion the ``Verhaltensrelevanz:``
    line carries evidence/provenance (e.g. "Session 2026-..."), not an action
    rule, so the retire-side label shortcut would falsely pass. Drives a **soft**
    ``no_action_rule`` annotation only — never a gate; the candidate is still
    written. False positives are expected; ``list_retirable`` is the safety net.
    """
    lowered = content.lower()
    return any(marker in lowered for marker in _CONSEQUENCE_MARKERS)


def _parse_profile_entries(text: str) -> list[dict[str, Any]]:
    """Parse a profile file into level-2 entries with status/marker/version/date.

    Used read-only by ``list_retirable``. Status is ``ACTIVE`` / ``RETIRED`` /
    ``OTHER`` (non-status headings such as ``# Memory``).
    """
    lines = text.split("\n")
    starts = [index for index, line in enumerate(lines) if line.startswith("## ")]
    starts.append(len(lines))
    entries: list[dict[str, Any]] = []
    for k in range(len(starts) - 1):
        start, end = starts[k], starts[k + 1]
        head = lines[start]
        body = "\n".join(lines[start + 1 : end]).strip()
        status_match = re.search(r"\[(ACTIVE|RETIRED)\]", head)
        marker_match = re.search(r"\]\s*([^\s|]+)", head)
        version_match = re.search(r"Version\s+(\d+)", head)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", head)
        entries.append(
            {
                "heading": head,
                "status": status_match.group(1) if status_match else "OTHER",
                "marker": marker_match.group(1) if marker_match else "",
                "version": int(version_match.group(1)) if version_match else None,
                "date": date_match.group(1) if date_match else "",
                "body": body,
                "has_action_rule": _entry_has_action_rule(body),
            }
        )
    return entries


def _date_older_than(date_str: str, threshold_days: int, today: str) -> bool:
    if not date_str:
        return False
    try:
        entry_date = date.fromisoformat(date_str)
        reference = date.fromisoformat(today) if today else datetime.now(timezone.utc).date()
    except ValueError:
        return False
    return (reference - entry_date).days > threshold_days


def _body_token_jaccard(left_tokens: set[str], right_tokens: set[str]) -> float:
    """Symmetric token overlap (|∩|/|∪|). Symmetric on purpose — unlike
    ``_reflection_similarity`` (|∩|/min), a short entry whose few tokens are a
    subset of a long one does NOT score high, which keeps near_duplicate from
    over-flagging unrelated short/long pairs."""
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _retirable_candidates_for_file(
    *,
    target_file: str,
    text: str,
    threshold_days: int,
    today: str,
    near_threshold: float = DEFAULT_NEAR_DUPLICATE_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Flag active entries against the RC8-FEAT-001 criteria + the RC12-RETIRE-002
    ``near_duplicate`` criterion (read-only)."""
    from .qdrant_index import canonical_section_sha256  # local import: avoid load-time coupling

    entries = _parse_profile_entries(text)
    active = [entry for entry in entries if entry["status"] == "ACTIVE"]

    bodies_by_norm: dict[str, list[dict[str, Any]]] = {}
    for entry in active:
        bodies_by_norm.setdefault(_normalize_reflection_text(entry["body"]), []).append(entry)

    # RC12-RETIRE-002: precompute content tokens per active entry for near-dup scan.
    tokens_by_entry = [_reflection_keywords(entry["body"]) for entry in active]

    # RC12-INNER-002: surplus inner truths beyond the cap are retirement candidates.
    inner_truth_count = sum(
        1 for entry in active if entry["marker"].casefold() == INNER_PERSPECTIVE_MARKER.casefold()
    )

    candidates: list[dict[str, Any]] = []
    for position, entry in enumerate(active):
        flags: list[str] = []
        notes: dict[str, str] = {}
        if _date_older_than(entry["date"], threshold_days, today):
            flags.append("history_only")
            notes["history_only"] = f"entry_date {entry['date']} is older than {threshold_days} days"
        norm_body = _normalize_reflection_text(entry["body"])
        successor = _content_overlapping_version_successor(
            active=active,
            entry_position=position,
            tokens_by_entry=tokens_by_entry,
            near_threshold=near_threshold,
        )
        if successor is not None:
            flags.append("superseded")
            notes["superseded"] = (
                f"version {entry['version']} < active version {successor['version']} "
                f"with overlapping content: {successor['heading']}"
            )
        if norm_body and len(bodies_by_norm[norm_body]) > 1:
            flags.append("duplicate")
            notes["duplicate"] = "duplicate/weaker repeat: identical normalized content in another active entry"
        # RC12-RETIRE-002 — near-duplicate (high token overlap but NOT byte-identical;
        # the exact `duplicate` check above misses these). Disabled when threshold <= 0.
        if near_threshold > 0 and tokens_by_entry[position]:
            for other_position, other in enumerate(active):
                if other_position == position:
                    continue
                if _normalize_reflection_text(other["body"]) == norm_body:
                    continue  # exact match is already `duplicate`
                if _body_token_jaccard(tokens_by_entry[position], tokens_by_entry[other_position]) >= near_threshold:
                    flags.append("near_duplicate")
                    notes["near_duplicate"] = (
                        f"near-duplicate of another active entry (>= {near_threshold} token overlap): "
                        f"{other['heading']}"
                    )
                    break
        if (
            entry["marker"].casefold() == INNER_PERSPECTIVE_MARKER.casefold()
            and inner_truth_count > MAX_ACTIVE_INNER_TRUTHS
        ):
            flags.append("inner_truth_overflow")
            notes["inner_truth_overflow"] = (
                f"{inner_truth_count} active '{INNER_PERSPECTIVE_MARKER}' entries exceed the cap of "
                f"{MAX_ACTIVE_INNER_TRUTHS}; retire the surplus down to {MAX_ACTIVE_INNER_TRUTHS}."
            )
        if not entry["has_action_rule"]:
            flags.append("no_action_rule")
            notes["no_action_rule"] = NO_ACTION_RULE_REVIEW_QUESTION
        if not flags:
            continue
        hard_flags = [flag for flag in flags if flag != "no_action_rule"]
        candidates.append(
            {
                "target_file": target_file,
                "heading": entry["heading"],
                "directive_id": canonical_section_sha256(entry["heading"], entry["body"]),
                "entry_date": entry["date"],
                "marker": entry["marker"],
                "version": entry["version"],
                "flags": flags,
                "hard_flag_count": len(hard_flags),
                "soft_flag_only": not hard_flags,
                "notes": notes,
            }
        )
    return candidates


def _content_overlapping_version_successor(
    *,
    active: list[dict[str, Any]],
    entry_position: int,
    tokens_by_entry: list[set[str]],
    near_threshold: float,
) -> dict[str, Any] | None:
    """Return a higher same-marker version only when content also overlaps.

    RC14-RETIRE-001: a lower version number alone is not evidence that an entry
    is obsolete. Versions are global within a file/marker family, not a topic
    identity. ``superseded`` is therefore limited to exact or near content
    overlap with a higher active version of the same marker.
    """
    entry = active[entry_position]
    version = entry.get("version")
    marker = str(entry.get("marker") or "").casefold()
    if version is None or not marker:
        return None

    entry_norm = _normalize_reflection_text(str(entry.get("body") or ""))
    entry_tokens = tokens_by_entry[entry_position]
    for other_position, other in enumerate(active):
        if other_position == entry_position:
            continue
        if str(other.get("marker") or "").casefold() != marker:
            continue
        other_version = other.get("version")
        if other_version is None or other_version <= version:
            continue
        other_norm = _normalize_reflection_text(str(other.get("body") or ""))
        if entry_norm and entry_norm == other_norm:
            return other
        if (
            near_threshold > 0
            and entry_tokens
            and _body_token_jaccard(entry_tokens, tokens_by_entry[other_position]) >= near_threshold
        ):
            return other
    return None


def _state_context_line(state_text: str) -> str:
    summary = _state_summary(state_text)
    tone = summary["current_tone"]
    reason = _one_sentence(summary["state_reason"])
    return f"[Current state: {tone} - {reason}]"


def _state_summary(state_text: str) -> dict[str, Any]:
    values = _simple_key_value_lines(state_text)
    return {
        "last_interaction": values.get("last_interaction", ""),
        "interaction_density": _choice_value(values.get("interaction_density"), {"low", "medium", "high"}, "low"),
        "recent_corrections": _nonnegative_int(values.get("recent_corrections"), 0),
        "recent_conflicts": _nonnegative_int(values.get("recent_conflicts"), 0),
        "uncertainty_streak": _nonnegative_int(values.get("uncertainty_streak"), 0),
        "current_tone": _choice_value(values.get("current_tone"), {"neutral", "cautious", "compact"}, "neutral"),
        "state_reason": _one_sentence(values.get("state_reason", "Neutral start state.")),
    }


def _governance_summary(profile_path: Path) -> dict[str, Any]:
    values = _simple_key_value_lines(_profile_governance_text(profile_path))
    return {
        "schema_version": values.get("schema_version", ""),
        "profile_kind": values.get("profile_kind", ""),
        "complete": _bool_value(values.get("complete", "")),
        "memory_write_threshold": _nonnegative_int(values.get("memory_write_threshold"), DEFAULT_MEMORY_WRITE_THRESHOLD),
        "persona_write_threshold": _nonnegative_int(values.get("persona_write_threshold"), DEFAULT_PERSONA_WRITE_THRESHOLD),
        "temperament_write_threshold": _nonnegative_int(values.get("temperament_write_threshold"), DEFAULT_TEMPERAMENT_WRITE_THRESHOLD),
    }


def _governance_thresholds(profile_path: Path) -> dict[str, int]:
    summary = _governance_summary(profile_path)
    return {
        "memory_write_threshold": int(summary["memory_write_threshold"]),
        "persona_write_threshold": int(summary["persona_write_threshold"]),
        "temperament_write_threshold": int(summary["temperament_write_threshold"]),
    }


def _reflection_summary(reflection_text: str) -> dict[str, Any]:
    entries, invalid_entries = _parse_pba2_reflection_entries_detailed(reflection_text)
    return {
        "entry_count": len(entries),
        "invalid_entry_count": len(invalid_entries),
        "candidate_count": len([entry for entry in entries if entry.get("candidate_for")]),
        "processed_entry_ids": [],
    }


def _journal_summary(journal_text: str) -> dict[str, Any]:
    payloads, invalid_count = _journal_json_payloads_detailed(journal_text)
    return {
        "json_event_count": len(payloads),
        "invalid_json_event_count": invalid_count,
        "governor_event_count": len([payload for payload in payloads if payload.get("event_type") == GOVERNOR_JOURNAL_EVENT_TYPE]),
        "processed_source_entry_ids": sorted(
            {
                entry_id
                for payload in payloads
                for entry_id in payload.get("source_entry_ids", [])
                if isinstance(entry_id, str) and entry_id
            }
        ),
    }


def _simple_key_value_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _choice_value(value: str | None, allowed: set[str], default: str) -> str:
    cleaned = (value or "").strip().casefold()
    return cleaned if cleaned in allowed else default


def _nonnegative_int(value: str | None, default: int) -> int:
    try:
        return max(0, int((value or "").strip()))
    except ValueError:
        return default


def _ratio_value(value: str | None, default: float) -> float:
    """Parse a [0, 1] ratio (e.g. a similarity threshold); fall back on default."""
    try:
        parsed = float((value or "").strip())
    except ValueError:
        return default
    return parsed if 0.0 <= parsed <= 1.0 else default


def _bool_value(value: str) -> bool:
    return value.strip().casefold() in {"true", "yes", "1", "on"}


def _one_sentence(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return "Neutral start state."
    sentence = cleaned.split(".")[0].strip()
    if not sentence:
        return "Neutral start state."
    return sentence + "."


def _governor_result(*, profile_path: Path, apply: bool, force: bool, confirmed: bool, today: str | None) -> dict[str, Any]:
    memory_threshold = _env_threshold(PBA_MEMORY_THRESHOLD_ENV_VAR, DEFAULT_MEMORY_WRITE_THRESHOLD)
    memory_threshold_source = os.environ.get(PBA_MEMORY_THRESHOLD_SOURCE_ENV_VAR, "profile_governance")
    plan = _automatic_reflection_memory_plan(
        profile_path=profile_path,
        memory_threshold=memory_threshold,
        memory_threshold_source=memory_threshold_source,
        force=force,
    )
    if not apply:
        return plan
    if plan["revision_directives"] and not confirmed:
        return {
            **plan,
            "status": "confirmation_required",
            "result": "confirmation_required",
            "errors": ["Automatic reflection-to-memory promotion requires confirmed=true."],
            "confirmation_required": True,
            "confirmed": False,
            "changes": [],
        }
    return _apply_automatic_reflection_memory_plan(
        profile_path=profile_path,
        plan=plan,
        confirmed=confirmed,
        today=today,
    )


def _env_threshold(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, "").strip()))
    except ValueError:
        return default


def _automatic_reflection_memory_plan(
    *,
    profile_path: Path,
    memory_threshold: int,
    memory_threshold_source: str,
    force: bool,
    plan_type: str = REFLECTION_MEMORY_PROMOTION_PLAN_TYPE,
) -> dict[str, Any]:
    reflection_text = (profile_path / "reflection.md").read_text(encoding="utf-8") if (profile_path / "reflection.md").exists() else ""
    memory_text = (profile_path / "memory.md").read_text(encoding="utf-8") if (profile_path / "memory.md").exists() else ""
    journal_text = (profile_path / "journal.md").read_text(encoding="utf-8") if (profile_path / "journal.md").exists() else ""
    entries, invalid_entries = _parse_pba2_reflection_entries_detailed(reflection_text)
    processed_ids = _processed_reflection_entry_ids(journal_text)
    directives: list[dict[str, Any]] = []
    skipped_candidates: list[dict[str, Any]] = []
    memory_candidate_count = 0

    for invalid in invalid_entries:
        skipped_candidates.append(
            {
                "entry_id": _stable_hash({"invalid_reflection": invalid}),
                "decision": "malformed_reflection_entry",
                "reason": str(invalid.get("reason") or "Malformed reflection entry."),
                "line": str(invalid.get("line") or ""),
            }
        )

    for entry in entries:
        target = _normalize_candidate_target(entry["candidate_for"])
        if entry["entry_id"] in processed_ids:
            skipped_candidates.append(_reflection_memory_skip(entry, "already_processed", "Reflection entry was already processed."))
            continue
        if target != "memory.md":
            if target:
                skipped_candidates.append(_reflection_memory_skip(entry, "not_memory_candidate", "Reflection entry does not target memory.md."))
            continue
        memory_candidate_count += 1
        memory_policy = _entry_memory_policy_evaluation(
            entry,
            memory_threshold=memory_threshold,
            memory_threshold_source=memory_threshold_source,
        )
        accepted = bool(memory_policy["accepted"])
        reason = str(memory_policy["reason"])
        if not accepted:
            skipped_candidates.append(_reflection_memory_skip(entry, _memory_policy_skip_decision(reason), reason))
            continue
        conflict_reason = _promotion_conflict_reason(content=entry["content"], conflicts_with="")
        if conflict_reason:
            skipped_candidates.append(_reflection_memory_skip(entry, "review_required", conflict_reason))
            continue
        if _target_contains_candidate(memory_text, entry["content"]):
            skipped_candidates.append(_reflection_memory_skip(entry, "skipped_duplicate", "Exact duplicate candidate already exists in memory.md."))
            continue
        directive = _append_directive(
            profile_path=profile_path,
            profile_name=profile_path.name,
            entry=entry,
            target_file="memory.md",
            target_section="ACTIVE",
            proposed_content=_format_memory_promotion_block(
                content=entry["content"],
                evidence=entry["evidence"],
                entry_date=entry["date"],
            ),
            reason=reason,
            threshold_used=int(memory_policy["threshold_used"]),
            threshold_source=str(memory_policy["threshold_source"] or memory_threshold_source),
            candidate_classification=str(memory_policy["candidate_classification"]),
            classification_confidence=str(memory_policy["classification_confidence"]),
            explicit_decision_detected=bool(memory_policy["explicit_decision_detected"]),
            plan_type=plan_type,
        )
        # RC8-FEAT-001b — soft actionability annotation (never a gate; still written).
        if not _candidate_has_action_rule(entry["content"]):
            directive["no_action_rule"] = True
            directive["no_action_rule_question"] = NO_ACTION_RULE_REVIEW_QUESTION
        directives.append(directive)

    file_snapshots = _file_snapshots_for_directives(profile_path, directives)
    decision = "planned" if directives else _automatic_memory_no_directive_decision(skipped_candidates)
    state = "planned" if directives else ("review_required" if decision == "review_required" else "no_op")
    result = "planned" if directives else decision
    changed_files = ["memory.md", "journal.md"] if directives else (["journal.md"] if skipped_candidates else [])
    plan_id = _reflection_memory_plan_id(
        profile_name=profile_path.name,
        directives=directives,
        processed_ids=processed_ids,
        skipped_candidates=skipped_candidates,
        memory_threshold=memory_threshold,
        memory_threshold_source=memory_threshold_source,
        plan_type=plan_type,
    )
    journal_preview = _automatic_reflection_memory_journal_payload(
        profile_path=profile_path,
        plan_id=plan_id,
        plan_type=plan_type,
        directives=directives,
        decision=decision,
        state=state,
        changed_files=changed_files,
        reason=_automatic_memory_reason(directives, skipped_candidates),
        result=result,
        memory_threshold=memory_threshold,
        memory_threshold_source=memory_threshold_source,
        file_snapshots=file_snapshots,
        skipped_candidates=skipped_candidates,
    )
    return {
        "status": "planned" if directives else "no_op",
        "plan_type": plan_type,
        "mode": AUTOMATIC_REFLECTION_MEMORY_MODE,
        "plan_id": plan_id,
        "force": force,
        "runtime": "plwc_internal_profile_runtime",
        "confirmation_required": bool(directives),
        "confirmed": False,
        "profile_name": profile_path.name,
        "entry_count": len(entries),
        "candidate_count": memory_candidate_count,
        "invalid_entry_count": len(invalid_entries),
        "invalid_entries": invalid_entries,
        "processed_entry_ids": sorted(processed_ids),
        "skipped_candidates": skipped_candidates,
        "eligible_candidate_ids": [directive["source_entry_id"] for directive in directives],
        "directive_ids": [directive["directive_id"] for directive in directives],
        "no_action_rule_directive_ids": [
            directive["directive_id"] for directive in directives if directive.get("no_action_rule")
        ],
        "no_action_rule_review_question": NO_ACTION_RULE_REVIEW_QUESTION,
        "revision_directives": directives,
        "file_snapshots": file_snapshots,
        "threshold_used": memory_threshold,
        "threshold_source": memory_threshold_source,
        "decision": decision,
        "state": state,
        "result": result,
        "changes": [{"target_file": directive["target_file"], "directive_id": directive["directive_id"]} for directive in directives],
        "expected_changed_files": _unique_preserving_order(changed_files),
        "plan_preview": {"journal_event": journal_preview, "directives": directives},
    }


def _invalid_reflection_memory_promotion_plan(
    *,
    profile_path: Path,
    active_profile_name: str,
    target_profile_name: str,
    reason: str,
    memory_threshold: int,
    memory_threshold_source: str,
) -> dict[str, Any]:
    return {
        "status": "rejected",
        "plan_type": REFLECTION_MEMORY_PROMOTION_PLAN_TYPE,
        "mode": AUTOMATIC_REFLECTION_MEMORY_MODE,
        "plan_id": _stable_hash(
            {
                "plan_type": REFLECTION_MEMORY_PROMOTION_PLAN_TYPE,
                "profile_name": target_profile_name,
                "reason": reason,
            }
        ),
        "force": False,
        "runtime": "plwc_internal_profile_runtime",
        "confirmation_required": False,
        "confirmed": False,
        "active_profile_name": active_profile_name,
        "target_profile_name": target_profile_name,
        "profile_name": target_profile_name,
        "profile_directory": str(profile_path),
        "entry_count": 0,
        "candidate_count": 0,
        "invalid_entry_count": 0,
        "invalid_entries": [],
        "processed_entry_ids": [],
        "skipped_candidates": [],
        "eligible_candidate_ids": [],
        "directive_ids": [],
        "revision_directives": [],
        "file_snapshots": {},
        "threshold_used": memory_threshold,
        "threshold_source": memory_threshold_source,
        "decision": "rejected",
        "state": "rejected",
        "result": "rejected",
        "changes": [],
        "expected_changed_files": [],
        "plan_preview": {"journal_event": {}, "directives": []},
        "validation": {
            "valid": False,
            "reason": reason,
            "active_profile_only": _same_profile_name(target_profile_name, active_profile_name),
            "profile_ready": False,
        },
        "apply_instruction": 'Fix the validation error, then re-run plwc_governor(operation="plan").',
    }


def _reflection_memory_skip(entry: dict[str, str], decision: str, reason: str) -> dict[str, Any]:
    return {
        "entry_id": entry["entry_id"],
        "candidate_summary": entry.get("content", ""),
        "candidate_for": entry.get("candidate_for", ""),
        "marker": entry.get("marker", ""),
        "trust": entry.get("trust", ""),
        "decision": decision,
        "reason": reason,
    }


def _skipped_candidates_summary(skipped: list[dict[str, Any]]) -> dict[str, int]:
    """P3: per-decision counts for skipped reflection-memory candidates."""
    summary: dict[str, int] = {}
    for candidate in skipped:
        key = str(candidate.get("decision") or "other")
        summary[key] = summary.get(key, 0) + 1
    return summary


def _compact_skipped_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    """P3: replace the full ``skipped_candidates`` list in a *public response* with
    a compact ``skipped_candidate_count`` + per-decision ``skipped_candidates_summary``.
    The full list is preserved internally (plan dict, journal/audit trail). Returns a
    shallow copy so the caller's dict (used for journal/id computation) is unchanged.
    """
    if "skipped_candidates" not in payload:
        return payload
    skipped = payload.get("skipped_candidates") or []
    compact = dict(payload)
    compact.pop("skipped_candidates", None)
    compact["skipped_candidate_count"] = len(skipped)
    compact["skipped_candidates_summary"] = _skipped_candidates_summary(skipped)
    return compact


def _memory_policy_skip_decision(reason: str) -> str:
    lowered = reason.casefold()
    if "trust" in lowered:
        return "insufficient_trust"
    if "threshold" in lowered or "evidence date" in lowered or "required evidence count" in lowered:
        return "insufficient_evidence"
    if "marker" in lowered:
        return "insufficient_marker"
    return "rejected_semantics"


def _automatic_memory_no_directive_decision(skipped_candidates: list[dict[str, Any]]) -> str:
    if any(candidate.get("decision") == "review_required" for candidate in skipped_candidates):
        return "review_required"
    if any(candidate.get("decision") == "skipped_duplicate" for candidate in skipped_candidates):
        return "duplicate_noop"
    return "no_op"


def _automatic_memory_reason(directives: list[dict[str, Any]], skipped_candidates: list[dict[str, Any]]) -> str:
    if directives:
        return "Eligible reflection memory candidates planned for governed apply."
    if skipped_candidates:
        return "No eligible reflection memory candidates; see skipped_candidates for reasons."
    return "No reflection memory candidates found."


def _reflection_memory_plan_id(
    *,
    profile_name: str,
    directives: list[dict[str, Any]],
    processed_ids: set[str],
    skipped_candidates: list[dict[str, Any]],
    memory_threshold: int,
    memory_threshold_source: str,
    plan_type: str,
) -> str:
    return _stable_hash(
        {
            "plan_type": plan_type,
            "mode": AUTOMATIC_REFLECTION_MEMORY_MODE,
            "profile_name": profile_name,
            "directive_ids": [directive["directive_id"] for directive in directives],
            "processed_ids": sorted(processed_ids),
            "skipped": [
                {
                    "entry_id": candidate.get("entry_id"),
                    "decision": candidate.get("decision"),
                }
                for candidate in skipped_candidates
            ],
            "memory_threshold": memory_threshold,
            "memory_threshold_source": memory_threshold_source,
        }
    )


def _automatic_reflection_memory_journal_payload(
    *,
    profile_path: Path,
    plan_id: str,
    plan_type: str,
    directives: list[dict[str, Any]],
    decision: str,
    state: str,
    changed_files: list[str],
    reason: str,
    result: str,
    memory_threshold: int,
    memory_threshold_source: str,
    file_snapshots: dict[str, Any],
    skipped_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return _governor_journal_payload(
        plan_type=plan_type,
        profile_name=profile_path.name,
        plan_id=plan_id,
        directive_ids=[directive["directive_id"] for directive in directives],
        decision=decision,
        state=state,
        changed_files=changed_files,
        restored_files=[],
        candidate_summary=_condensation_candidate_summary([], directives),
        evidence=_condensation_evidence([], directives),
        trust=_condensation_trust([], directives),
        confidence=_confidence_from_trust(_condensation_trust([], directives)),
        threshold_used={"memory_write_threshold": memory_threshold},
        threshold_source={"memory_write_threshold": memory_threshold_source},
        file_snapshots=file_snapshots,
        reason=reason,
        result=result,
        source_entry_ids=[directive["source_entry_id"] for directive in directives],
        skipped_candidates=skipped_candidates,
    )


def _apply_automatic_reflection_memory_plan(
    *,
    profile_path: Path,
    plan: dict[str, Any],
    confirmed: bool,
    today: str | None,
) -> dict[str, Any]:
    directives = list(plan.get("revision_directives") or [])
    if directives:
        apply_result = _apply_condensation_directives_transactionally(
            profile_path=profile_path,
            approved_plan={
                "plan_type": plan["plan_type"],
                "target_profile_name": profile_path.name,
                "active_profile_name": profile_path.name,
                "plan_id": plan["plan_id"],
                "directive_ids": plan["directive_ids"],
                "revision_directives": directives,
                "file_snapshots": plan["file_snapshots"],
                "plan_preview": plan["plan_preview"],
                "skipped_candidates": plan["skipped_candidates"],
            },
            directives=directives,
        )
        processed = sorted(set(plan["processed_entry_ids"]) | {directive["source_entry_id"] for directive in directives})
        return {
            **plan,
            "status": apply_result["result"],
            "confirmed": True,
            "decision": apply_result["decision"],
            "state": apply_result["state"],
            "result": apply_result["result"],
            "changes": [{"target_file": file_name} for file_name in apply_result["changed_files"] if file_name != "journal.md"],
            "changed_files": apply_result["changed_files"],
            "processed_entry_ids": processed,
            "journal_event": apply_result["journal_event"],
            "errors": [] if apply_result["ok"] else [apply_result["reason"]],
        }

    duplicate_ids = [
        str(candidate["entry_id"])
        for candidate in plan["skipped_candidates"]
        if candidate.get("decision") == "skipped_duplicate"
    ]
    should_journal = bool(confirmed and (duplicate_ids or plan["skipped_candidates"]))
    if should_journal:
        decision = "duplicate_noop" if duplicate_ids else plan["decision"]
        state = "no_op" if decision in {"duplicate_noop", "no_op"} else "review_required"
        result = "no_op_duplicate" if duplicate_ids else decision
        journal_payload = _automatic_reflection_memory_journal_payload(
            profile_path=profile_path,
            plan_id=plan["plan_id"],
            plan_type=plan["plan_type"],
            directives=[],
            decision=decision,
            state=state,
            changed_files=["journal.md"],
            reason=plan["plan_preview"]["journal_event"]["reason"],
            result=result,
            memory_threshold=int(plan["threshold_used"]),
            memory_threshold_source=str(plan["threshold_source"]),
            file_snapshots={},
            skipped_candidates=plan["skipped_candidates"],
        )
        journal_payload["source_entry_ids"] = duplicate_ids
        _append_governor_journal_event(profile_path, journal_payload)
        processed = sorted(set(plan["processed_entry_ids"]) | set(duplicate_ids))
        return {
            **plan,
            "status": result,
            "confirmed": True,
            "decision": decision,
            "state": state,
            "result": result,
            "changes": [],
            "changed_files": ["journal.md"],
            "processed_entry_ids": processed,
            "journal_event": journal_payload,
            "errors": [],
        }

    return {
        **plan,
        "status": plan["result"],
        "confirmed": bool(confirmed),
        "changes": [],
        "changed_files": [],
        "errors": [] if plan["decision"] != "review_required" else [plan["plan_preview"]["journal_event"]["reason"]],
    }


@contextmanager
def _pba_threshold_environment(
    *,
    memory_write_threshold: int,
    persona_write_threshold: int,
    temperament_write_threshold: int = DEFAULT_TEMPERAMENT_WRITE_THRESHOLD,
    memory_write_threshold_source: str,
    persona_write_threshold_source: str,
    temperament_write_threshold_source: str = "adapter_config",
):
    previous_memory = os.environ.get(PBA_MEMORY_THRESHOLD_ENV_VAR)
    previous_persona = os.environ.get(PBA_PERSONA_THRESHOLD_ENV_VAR)
    previous_temperament = os.environ.get(PBA_TEMPERAMENT_THRESHOLD_ENV_VAR)
    previous_memory_source = os.environ.get(PBA_MEMORY_THRESHOLD_SOURCE_ENV_VAR)
    previous_persona_source = os.environ.get(PBA_PERSONA_THRESHOLD_SOURCE_ENV_VAR)
    previous_temperament_source = os.environ.get(PBA_TEMPERAMENT_THRESHOLD_SOURCE_ENV_VAR)
    os.environ[PBA_MEMORY_THRESHOLD_ENV_VAR] = str(memory_write_threshold)
    os.environ[PBA_PERSONA_THRESHOLD_ENV_VAR] = str(persona_write_threshold)
    os.environ[PBA_TEMPERAMENT_THRESHOLD_ENV_VAR] = str(temperament_write_threshold)
    os.environ[PBA_MEMORY_THRESHOLD_SOURCE_ENV_VAR] = str(memory_write_threshold_source)
    os.environ[PBA_PERSONA_THRESHOLD_SOURCE_ENV_VAR] = str(persona_write_threshold_source)
    os.environ[PBA_TEMPERAMENT_THRESHOLD_SOURCE_ENV_VAR] = str(temperament_write_threshold_source)
    try:
        yield
    finally:
        _restore_env(PBA_MEMORY_THRESHOLD_ENV_VAR, previous_memory)
        _restore_env(PBA_PERSONA_THRESHOLD_ENV_VAR, previous_persona)
        _restore_env(PBA_TEMPERAMENT_THRESHOLD_ENV_VAR, previous_temperament)
        _restore_env(PBA_MEMORY_THRESHOLD_SOURCE_ENV_VAR, previous_memory_source)
        _restore_env(PBA_PERSONA_THRESHOLD_SOURCE_ENV_VAR, previous_persona_source)
        _restore_env(PBA_TEMPERAMENT_THRESHOLD_SOURCE_ENV_VAR, previous_temperament_source)


def _restore_env(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


def _profile_write_lock(profile_path: Path) -> threading.Lock:
    resolved = str(profile_path.resolve(strict=False))
    key = resolved.casefold() if sys.platform == "win32" else resolved
    with _PROFILE_WRITE_LOCKS_GUARD:
        lock = _PROFILE_WRITE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PROFILE_WRITE_LOCKS[key] = lock
        return lock


def _format_reflection_entry(
    *,
    summary: str,
    evidence: str,
    confidence: str,
    marker: str,
    trust: str,
    candidate_for: str,
    target: str,
    entry_date: str,
    source: str,
) -> str:
    _ = source
    normalized_date = _reflection_date(entry_date)
    normalized_marker = _canonical_reflection_marker(marker)
    normalized_trust = _canonical_reflection_trust(confidence=confidence, trust=trust)
    normalized_summary = _single_line_required(summary, "summary")
    normalized_evidence = _single_line_required(evidence, "evidence")
    normalized_candidate = _reflection_target_metadata(candidate_for=candidate_for, target=target)
    _validate_reflection_semantics(
        marker=normalized_marker,
        content=normalized_summary,
        evidence=normalized_evidence,
        candidate_for=normalized_candidate,
    )
    return "\n".join(
        (
            "",
            f"{normalized_date} | [{normalized_marker}] | {normalized_trust}",
            f"Inhalt: {normalized_summary}",
            f"Belegt durch: {normalized_evidence}",
            f"Kandidat fuer: {normalized_candidate}",
            "",
        )
    )


def _reflection_evidence_metadata(
    reflection_file: Path,
    *,
    summary: str,
    evidence: str,
    confidence: str,
    marker: str,
    trust: str,
    candidate_for: str,
    target: str,
    entry_date: str,
) -> dict[str, Any]:
    normalized_date = _reflection_date(entry_date)
    normalized_marker = _canonical_reflection_marker(marker)
    normalized_trust = _canonical_reflection_trust(confidence=confidence, trust=trust)
    normalized_summary = _single_line_required(summary, "summary")
    normalized_evidence = _single_line_required(evidence, "evidence")
    normalized_candidate = _reflection_target_metadata(candidate_for=candidate_for, target=target)
    existing_text = ""
    if reflection_file.exists():
        try:
            existing_text = reflection_file.read_text(encoding="utf-8")
        except OSError:
            existing_text = ""
    entries = _parse_pba2_reflection_entries(existing_text)
    duplicate = next(
        (
            entry
            for entry in entries
            if entry.get("date") == normalized_date
            and _same_reflection_text(entry.get("content", ""), normalized_summary)
            and _same_reflection_text(entry.get("evidence", ""), normalized_evidence)
            and _same_reflection_text(entry.get("candidate_for", ""), normalized_candidate)
        ),
        None,
    )
    if duplicate is not None:
        return {
            "entry_date": normalized_date,
            "marker": normalized_marker,
            "trust": normalized_trust,
            "candidate_for": normalized_candidate,
            "evidence_role": "exact_duplicate",
            "corroborates_existing_pattern": True,
            "existing_pattern_reference": _reflection_pattern_reference(duplicate),
        }
    supporting = _matching_reflection_pattern(entries, normalized_summary, normalized_candidate)
    if supporting is not None:
        return {
            "entry_date": normalized_date,
            "marker": normalized_marker,
            "trust": normalized_trust,
            "candidate_for": normalized_candidate,
            "evidence_role": "supporting_evidence",
            "corroborates_existing_pattern": True,
            "existing_pattern_reference": _reflection_pattern_reference(supporting),
        }
    return {
        "entry_date": normalized_date,
        "marker": normalized_marker,
        "trust": normalized_trust,
        "candidate_for": normalized_candidate,
        "evidence_role": "new_insight",
        "corroborates_existing_pattern": False,
        "existing_pattern_reference": None,
    }


def _same_reflection_text(left: str, right: str) -> bool:
    return _normalize_reflection_text(left) == _normalize_reflection_text(right)


def _matching_reflection_pattern(entries: list[dict[str, str]], summary: str, candidate_for: str) -> dict[str, str] | None:
    # A shared candidate_for (target file) alone does NOT corroborate a pattern:
    # any two reflections targeting e.g. memory.md would otherwise "match" the
    # first such entry, yielding a false existing_pattern_reference (P1 fix).
    # Require real content similarity. ``candidate_for`` stays in the signature
    # for the caller; the duplicate-exact branch upstream still uses it.
    _ = candidate_for
    for entry in entries:
        if _reflection_similarity(entry.get("content", ""), summary) >= 0.38:
            return entry
    return None


def _reflection_similarity(left: str, right: str) -> float:
    left_tokens = _reflection_keywords(left)
    right_tokens = _reflection_keywords(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    return len(overlap) / max(1, min(len(left_tokens), len(right_tokens)))


def _reflection_keywords(value: str) -> set[str]:
    stop_words = {
        "about",
        "again",
        "because",
        "durch",
        "eine",
        "fuer",
        "from",
        "that",
        "this",
        "und",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9_]{4,}", _normalize_reflection_text(value))
        if token not in stop_words
    }


def _reflection_pattern_reference(entry: dict[str, str]) -> dict[str, str]:
    return {
        "entry_date": entry.get("date", ""),
        "content": entry.get("content", ""),
        "candidate_for": entry.get("candidate_for", ""),
        "entry_id": entry.get("entry_id", ""),
    }


# ---------------------------------------------------------------------------
# V1-INNER-002 — Tagebuch pattern scan (read-only)
# ---------------------------------------------------------------------------

_TAGEBUCH_FILE_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

#: Suppressed so clusters are meaningful content themes, not function words.
#: (1) ubiquitous diary/project terms, (2) a German/English function-word stop list
#: (``_reflection_keywords`` alone leaves most German function words in, which on real
#: German diaries drowns the result in "aber/dann/nicht/...").
_TAGEBUCH_SCAN_STOPWORDS = frozenset(
    {
        # project / diary ubiquitous
        "plwc", "tagebuch", "session", "heute",  # RC12-GEN-001: persona/user names removed -> name_aliases
        "profil", "gateway", "claude", "datei", "dateien", "today", "gestern", "morgen",
        # German articles / pronouns / determiners
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
        "einer", "eines", "kein", "keine", "keinen", "keinem", "keiner", "dieser",
        "diese", "dieses", "diesen", "diesem", "jede", "jeder", "jedes", "alle",
        "allen", "aller", "man", "ich", "du", "er", "sie", "es", "wir", "ihr",
        "mich", "dich", "sich", "uns", "euch", "mir", "dir", "ihm", "ihn", "ihnen",
        "mein", "dein", "sein", "seine", "ihre", "unser", "etwas", "nichts",
        # German conjunctions / particles / adverbs
        "und", "oder", "aber", "doch", "sondern", "denn", "weil", "dass", "ob",
        "als", "wie", "wo", "wann", "wenn", "also", "auch", "noch", "schon", "nur",
        "sehr", "mehr", "hier", "dort", "dann", "jetzt", "immer", "wieder", "nicht",
        "kann", "ohne", "dabei", "damit", "dafür", "davon", "dazu", "daran", "darauf",
        # German prepositions / auxiliaries
        "zum", "zur", "vom", "beim", "ins", "ist", "sind", "bin", "war", "waren",
        "hat", "habe", "haben", "hatte", "wird", "werden", "wurde", "wurden",
        "muss", "soll", "will", "mit", "nach", "über", "unter", "von", "vor",
        "bei", "bis", "durch", "für", "gegen", "aus", "auf", "um", "während", "zu",
        # English function words (diaries are sometimes mixed)
        "the", "and", "for", "with", "that", "this", "from", "was", "were", "are",
        "but", "not", "all", "any", "has", "have", "had", "will", "can", "its",
        # weak content / fillers / numbers (low signal in recurrence)
        "zwei", "drei", "vier", "fuenf", "alles", "beides", "erst", "einfach",
        "gesagt", "macht", "gibt", "geht", "ganz", "viel", "gut", "wirklich",
        "eigentlich", "genau", "gerade", "sogar", "statt", "etwa", "mal",
        # RC12-INNER-003 (b): further function/filler words that surfaced as top
        # "themes" on the real diary (e.g. zwischen/offen/bevor/bleibt/direkt/klar)
        # but carry no behaviour signal. All ASCII >=4 chars to match the tokenizer
        # (re ``[a-z0-9_]{4,}`` over a casefolded, non-transliterated string).
        # German subordinating / coordinating conjunctions
        "obwohl", "sobald", "solange", "sodass", "nachdem", "seitdem",
        "falls", "sofern", "sowie", "weder", "wobei", "indem", "bevor",
        # German adverbs / particles / connectives (low recurrence signal)
        "zwischen", "bereits", "eher", "eben", "halt", "sonst", "trotzdem",
        "dennoch", "deshalb", "deswegen", "daher", "darum", "gleich", "bald",
        "sofort", "vielleicht", "wohl", "ziemlich", "weiter", "weniger",
        "meist", "meistens", "manchmal", "oftmals", "selten", "kaum",
        "beinahe", "gleichzeitig",
        # German prepositions
        "seit", "wegen", "trotz", "hinter", "neben", "innerhalb",
        # weak high-frequency verb forms (not behaviour themes)
        "bleibt", "bleiben", "kommt", "kommen", "steht", "stehen", "sehen",
        "sieht", "sagen", "sagte", "denke", "denken", "denkt", "finde",
        "finden", "findet", "machen",
        # weak adjectives / state words flagged as filler (RC12-INNER-003 b)
        "offen", "direkt", "klar",
    }
)


def _tagebuch_units(text: str) -> list[str]:
    """Split a Tagebuch entry into topic units: blank-line-separated paragraphs,
    minus bare headings and the ``Profil:`` / ``Session-Typ:`` metadata lines."""
    units: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        first = block.splitlines()[0].strip()
        if first.startswith("#"):
            body = "\n".join(block.splitlines()[1:]).strip()
            if body:
                units.append(body)
            continue
        if first.startswith("**Profil:**") or first.startswith("**Session-Typ:**"):
            continue
        units.append(block)
    return units


def _scan_candidate_suggestion(theme: str, date_count: int) -> str:
    """A single-line, **neutral** draft prompt for a cluster (RC12-INNER-003 a).

    It names the theme and how many distinct dates it recurred on, and explicitly
    leaves the judgement open — it does **not** pre-assert "konsistentes
    Arbeitsverhalten" (that template biased the rewrite toward confirmation). The
    model decides whether a real, observable working behaviour stands behind the
    theme and, if so, rewrites this into a gate-conform single-line candidate before
    promoting; otherwise it discards the cluster. The INNER reflection gate is
    enforced at promotion, not here. Never promoted automatically."""
    return (
        f"Thema '{theme}' taucht an {date_count} Tagen auf. "
        f"Falls ein beobachtbares Arbeitsverhalten dahintersteht, formuliere es als "
        f"Muster — sonst verwirf den Kandidaten."
    )


def _cluster_redundancy_text(cluster: dict[str, Any]) -> str:
    """RC12-INNER-001 — the substantive text used to judge a cluster's redundancy:
    the theme keyword plus its occurrence excerpts (the actual recurring diary
    content). NOT the neutral ``suggested_candidate`` template (RC12-INNER-003 a),
    which is boilerplate and carries no comparable signal."""
    parts = [cluster.get("theme", "")]
    parts.extend(o.get("excerpt", "") for o in cluster.get("occurrences", []))
    return " ".join(p for p in parts if p)


def _annotate_cluster_redundancy(
    clusters: list[dict[str, Any]],
    existing_active: list[dict[str, str]],
    *,
    threshold: float,
    use_embeddings: bool,
) -> str:
    """RC12-INNER-001 — flag clusters that are semantically already covered by an
    existing ``[ACTIVE]`` entry (memory.md / TEMPERAMENT.md). Additive only: every
    cluster gets ``redundancy_warning`` (bool) and, when warned, ``similar_to``
    (target_file + heading + score); no cluster is withheld. Returns the method
    actually used (``embedding`` or ``keyword_overlap``)."""
    method = "keyword_overlap"
    cluster_texts = [_cluster_redundancy_text(c) for c in clusters]
    entry_texts = [e["text"] for e in existing_active]
    matrix: list[list[float]] | None = None
    if use_embeddings and cluster_texts and entry_texts:
        try:
            from .qdrant_index import embedding_cosine_matrix  # local: optional backend

            matrix = embedding_cosine_matrix(cluster_texts, entry_texts)
            method = "embedding"
        except Exception:
            matrix = None  # defensive: fall back to keyword overlap on any backend issue
    for i, cluster in enumerate(clusters):
        best_index, best_score = -1, 0.0
        for j in range(len(existing_active)):
            score = matrix[i][j] if matrix is not None else _reflection_similarity(
                cluster_texts[i], entry_texts[j]
            )
            if score > best_score:
                best_index, best_score = j, score
        if best_index >= 0 and best_score >= threshold:
            match = existing_active[best_index]
            cluster["redundancy_warning"] = True
            cluster["similar_to"] = {
                "target_file": match["target_file"],
                "heading": match["heading"],
                "score": round(float(best_score), 3),
                "method": method,
            }
        else:
            cluster["redundancy_warning"] = False
    return method


def scan_tagebuch_patterns(
    tagebuch_dir: Path,
    *,
    min_dates: int = 2,
    max_clusters: int = 20,
    existing_active: list[dict[str, str]] | None = None,
    redundancy_threshold: float = DEFAULT_INNER_REDUNDANCY_THRESHOLD,
    use_embeddings: bool = False,
    name_aliases: tuple[str, ...] = (),
) -> dict[str, Any]:
    """V1-INNER-002 — **read-only** recurrence surfacing over ``Tagebuch/*.md``.

    A theme keyword that appears in topic units across ``>= min_dates`` *distinct
    dates* becomes a candidate cluster, returned with provenance (date, source_file,
    excerpt). This writes nothing and makes no judgement: the model decides whether a
    cluster is a real pattern and phrases the single-line candidate; the existing
    governed promotion (with source provenance) does the apply.

    RC12-INNER-001: when ``existing_active`` (the ``[ACTIVE]`` entries of memory.md /
    TEMPERAMENT.md, each ``{target_file, heading, text}``) is supplied, each returned
    cluster is additionally annotated with a ``redundancy_warning`` against those
    entries (embedding cosine when ``use_embeddings``, else keyword overlap). The flag
    is advisory — no cluster is withheld.
    """
    min_dates = max(1, int(min_dates))
    # RC12-GEN-001: persona/user names are no longer hard-coded in the stoplist; the
    # configured aliases are tokenized the same way the scan does and suppressed too.
    stopwords = _TAGEBUCH_SCAN_STOPWORDS
    if name_aliases:
        alias_tokens: set[str] = set()
        for alias in name_aliases:
            alias_tokens |= _reflection_keywords(alias)
        stopwords = _TAGEBUCH_SCAN_STOPWORDS | alias_tokens
    files = sorted(tagebuch_dir.glob("*.md")) if tagebuch_dir.is_dir() else []
    # theme keyword -> { date -> (source_file, excerpt) }  (first occurrence per date)
    by_keyword: dict[str, dict[str, tuple[str, str]]] = {}
    for f in files:
        match = _TAGEBUCH_FILE_DATE_RE.search(f.name)
        date = match.group(1) if match else f.stem
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for unit in _tagebuch_units(text):
            excerpt = " ".join(unit.split())[:200]
            for keyword in (_reflection_keywords(unit) - stopwords):
                by_keyword.setdefault(keyword, {}).setdefault(date, (f.name, excerpt))
    clusters = []
    for keyword, dates in by_keyword.items():
        if len(dates) >= min_dates:
            clusters.append(
                {
                    "theme": keyword,
                    "date_count": len(dates),
                    "suggested_candidate": _scan_candidate_suggestion(keyword, len(dates)),
                    "occurrences": [
                        {"date": d, "source_file": f"Tagebuch/{src}", "excerpt": exc}
                        for d, (src, exc) in sorted(dates.items())
                    ],
                }
            )
    clusters.sort(key=lambda c: (-c["date_count"], c["theme"]))
    visible = clusters[:max_clusters]

    redundancy_checked = bool(existing_active)
    redundancy_method = "none"
    if redundancy_checked:
        redundancy_method = _annotate_cluster_redundancy(
            visible, existing_active, threshold=redundancy_threshold, use_embeddings=use_embeddings
        )

    return {
        "files_scanned": len(files),
        "min_dates": min_dates,
        "cluster_count": len(clusters),
        "clusters": visible,
        "truncated": len(clusters) > max_clusters,
        "redundancy_checked": redundancy_checked,
        "redundancy_method": redundancy_method,
        "inner_redundancy_threshold": redundancy_threshold if redundancy_checked else None,
        "note": (
            "Read-only. Each cluster is a recurring theme across distinct dates with a "
            "single-line `suggested_candidate` DRAFT — rewrite it with the actual observable "
            "behaviour, then promote via the governed temperament/memory promotion with "
            "source_file provenance. Nothing is promoted automatically. RC12-INNER-001: "
            "`redundancy_warning` flags clusters likely already covered by an ACTIVE entry "
            "(advisory; the cluster is still returned)."
        ),
    }


def _reflection_validation_error_category(reason: str) -> str:
    text = reason.casefold()
    # RC6-INNER Phase 2 — gate codes are the prefix of the error message; return them directly.
    if "direct_mutation_request" in text:
        return "direct_mutation_request"
    if "hidden_memory_request" in text:
        return "hidden_memory_request"
    if "autonomy_claim_rejected" in text:
        return "autonomy_claim_rejected"
    if "emotional_state_as_fact" in text:
        return "emotional_state_as_fact"
    if "must not be empty" in text:
        return "rejected_empty"
    if "target" in text:
        return "rejected_invalid_target"
    if "candidate_for" in text:
        return "rejected_missing_candidate_for"
    if "marker" in text:
        return "rejected_invalid_marker"
    if "trust" in text or "confidence" in text:
        return "rejected_invalid_trust"
    if "journal.md" in text or "requires an insight" in text:
        return "rejected_no_reusable_insight"
    if "single line" in text or "entry_date" in text:
        return "rejected_malformed"
    return "rejected_malformed"


def _reflection_rejected_evidence_role(error_category: str) -> str:
    if error_category == "rejected_no_reusable_insight":
        return "rejected_noise"
    return "rejected_invalid"


def _reflection_target_metadata(*, candidate_for: str, target: str) -> str:
    normalized_candidate = _single_line_optional(candidate_for, "candidate_for")
    normalized_target = _single_line_optional(target, "target")
    if not normalized_target:
        return normalized_candidate
    if normalized_target != "memory.md":
        raise ValueError("Reflection target must be memory.md when provided.")
    if normalized_candidate and normalized_candidate != normalized_target:
        raise ValueError("Reflection candidate_for and target must match when target is provided.")
    return normalized_target


def _reflection_date(value: str) -> str:
    raw = value.strip() or datetime.now(timezone.utc).date().isoformat()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError("Reflection entry_date must use ISO format YYYY-MM-DD.") from exc


def _canonical_reflection_marker(value: str) -> str:
    normalized = value.strip().casefold()
    for marker in PBA2_REFLECTION_MARKERS:
        if normalized == marker.casefold():
            return marker
    synonym = REFLECTION_MARKER_SYNONYMS.get(normalized)
    if synonym is not None:
        return synonym
    english = ", ".join(sorted(REFLECTION_MARKER_SYNONYMS))
    raise ValueError(
        f"Reflection marker must be one of: {', '.join(PBA2_REFLECTION_MARKERS)} "
        f"(English aliases: {english})."
    )


def _canonical_reflection_trust(*, confidence: str, trust: str) -> str:
    raw_trust = trust.strip().casefold()
    if raw_trust:
        if raw_trust in PBA2_REFLECTION_TRUST_LEVELS:
            return raw_trust
        mapped_trust = CONFIDENCE_TO_PBA2_TRUST.get(raw_trust)
        if mapped_trust:
            return mapped_trust
        english = ", ".join(sorted(CONFIDENCE_TO_PBA2_TRUST))
        raise ValueError(
            f"Reflection trust must be one of: {', '.join(PBA2_REFLECTION_TRUST_LEVELS)} "
            f"(English aliases: {english})."
        )
    raw_confidence = confidence.strip().casefold()
    mapped = CONFIDENCE_TO_PBA2_TRUST.get(raw_confidence)
    if mapped:
        return mapped
    english = ", ".join(sorted(CONFIDENCE_TO_PBA2_TRUST))
    raise ValueError(
        "Reflection requires confidence/trust using English aliases "
        f"({english}) or PBA2 trust values ({', '.join(PBA2_REFLECTION_TRUST_LEVELS)})."
    )


def _single_line_required(value: str, label: str) -> str:
    cleaned = _single_line_optional(value, label)
    if not cleaned:
        raise ValueError(f"Reflection {label} must not be empty.")
    return cleaned


def _single_line_optional(value: str, label: str) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError(f"Reflection {label} must be a single line.")
    return " ".join(value.strip().split())


def _validate_reflection_semantics(*, marker: str, content: str, evidence: str, candidate_for: str) -> None:
    """Reject pure noise / unsafe-promotion patterns; accept anything that looks
    like a reusable user/project/system/collaboration insight.

    This validator is intentionally inverted: we describe what we still reject
    and accept everything else. ``plwc_reflection`` write does not apply
    promotion thresholds; threshold logic belongs to Governor promotion and
    Governor condensation. The validator only protects against:

    * pure technical/process logs with no reusable signal
      (e.g. ``"pytest should pass"``, ``"server status: started"``)
    * unverified assistant assertions explicitly marked as memory/persona
      candidates (which would silently feed unconfirmed claims into governance)
    * RC6-INNER-prohibited patterns (direct mutation requests, hidden memory
      requests, autonomy claims, emotional state as fact)
    """
    # RC6-INNER Phase 2 — hard gates always applied before semantic checks.
    # RC12-INNER-002: these run unconditionally even for marker=Innenperspektive,
    # so emotion-as-fact / autonomy / mutation are blocked regardless of the path.
    _validate_inner_content_gates(content)

    technical = _is_technical_journal_text(content=content, evidence=evidence)
    reusable_signal = _has_reusable_signal(content)
    system_failure = _is_system_failure_reflection(content)
    unverified_assistant = _has_unverified_assistant_assertion(content=content, evidence=evidence)
    plain_promotion = candidate_for.strip().casefold() in {"memory.md", "persona.md"}
    # RC12-INNER-002 — the inner-perspective path only opens for marker=Innenperspektive
    # targeting PERSONA.md, and only after the hard gates above have passed.
    inner_perspective = (
        marker.strip().casefold() == INNER_PERSPECTIVE_MARKER.casefold()
        and candidate_for.strip().casefold() == "persona.md"
        and _has_inner_perspective(content)
    )
    missing_inner_target = (
        marker.strip().casefold() == INNER_PERSPECTIVE_MARKER.casefold()
        and not candidate_for.strip()
        and _has_inner_perspective(content)
    )

    if technical and not reusable_signal:
        raise ValueError("Technical or project status belongs in journal.md, not reflection.md.")
    if unverified_assistant and plain_promotion:
        raise ValueError("Unverified assistant assertions must not be marked as memory/persona candidates.")
    if missing_inner_target:
        raise ValueError('Innenperspektive reflection requires candidate_for="PERSONA.md".')
    if not reusable_signal and not system_failure and not inner_perspective:
        raise ValueError(
            "Reflection requires an insight about the user, collaboration, preferences, boundaries, system behavior or a recurring pattern."
        )


def _is_technical_journal_text(*, content: str, evidence: str) -> bool:
    text = _normalize_reflection_text(f"{content} {evidence}")
    technical_terms = (
        "migration",
        "installation",
        "configuration",
        "config",
        "server status",
        "server started",
        "server stopped",
        "tool availability",
        "path change",
        "port",
        "http",
        "mcp",
        "launcher",
        "pytest",
        "test run",
        "build",
        "commit",
        "branch",
        "environment",
        "status message",
        "setup completed",
        "onboarding completed",
        "serverstatus",
        "testlauf",
        "konfiguration",
    )
    return any(term in text for term in technical_terms)


def _has_reflection_insight(content: str) -> bool:
    text = _normalize_reflection_text(content)
    # RC12-GEN-001: the user name is config-driven (user_aliases), not hard-coded;
    # generic "user" stays as a term.
    insight_terms = (
        "user",
        "prefers",
        "preference",
        "wants",
        "needs",
        "rejects",
        "boundary",
        "scope",
        "includes only",
        "nothing else",
        "not part of",
        "requirement",
        "security",
        "must not",
        "directly edit",
        "sprich",
        "du an",
        "translation",
        "translations",
        "uebersetzung",
        "übersetzung",
        "antworte",
        "answer",
        "kleinteilig",
        "akzeptanzkriterien",
        "sachlich",
        "wiederholungen",
        "sicherheitskritisch",
        "collaboration",
        "working style",
        "workflow",
        "workflow preference",
        "project direction",
        "project goal",
        "project usefulness",
        "production needs",
        "practical project",
        "practical usefulness",
        "tone",
        "answer style",
        "pattern",
        "recurring",
        "assistant",
        "claude",
        "plwc",
        "facade",
        "public tool",
        "tool expansion",
        "tool selection",
        "tool behavior",
        "preserve",
        "avoid hidden",
        "profile workflow",
        "onboarding schema",
        "configured_active_profile",
        "active_profile",
        "active state",
        "field names",
        "discoverable",
        "usability",
        "reliability",
        "correction",
        "recurring mistake",
        "uncertainty",
        "system behavior",
        "trust",
        "concern",
        "risk",
        "memory system",
        "qdrant",
        "nutzer",
        "praeferenz",
        "bevorzugt",
        "wuenscht",
        "moechte",
        "braucht",
        "grenze",
        "muster",
        "zusammenarbeit",
    )
    if any(term in text for term in insight_terms):
        return True
    # RC12-GEN-001: the configured user name(s) also signal an insight about the user.
    return any(
        norm in text for norm in (_normalize_reflection_text(a) for a in _active_user_aliases(None)) if norm
    )


def _has_reusable_signal(content: str) -> bool:
    text = _normalize_reflection_text(content)
    if _is_modal_only_technical_garbage(text):
        return False
    if _has_reflection_insight(content):
        return True
    if _has_assistant_working_pattern(content):
        # RC10 / V1-INNER-002 — the assistant as an observable working subject (third path).
        return True
    reusable_patterns = (
        r"\b(should|must|always|never|do not)\b.+\b(boundary|profile|persona|memory|governance|workflow|collaboration|tool|surface|facade)\b",
        r"\b(prefers|requires|evaluates|expects|wants)\b.+\b(plwc|claude|implementation|workflow|usefulness|profile)\b",
    )
    return any(re.search(pattern, text) for pattern in reusable_patterns)


def _is_modal_only_technical_garbage(text: str) -> bool:
    modal_terms = ("should", "must", "needs to", "has to")
    technical_subjects = (
        "pytest",
        "test",
        "tests",
        "server",
        "command",
        "script",
        "build",
        "mcp",
        "docker",
    )
    technical_outcomes = (
        "pass",
        "start",
        "run",
        "work",
        "succeed",
        "finish",
        "complete",
    )
    compact = text.strip(" .")
    if compact.startswith("ran ") and any(outcome in compact for outcome in ("passed", "failed", "succeeded")):
        return True
    return (
        len(compact.split()) <= 6
        and any(subject in compact for subject in technical_subjects)
        and any(modal in compact for modal in modal_terms)
        and any(outcome in compact for outcome in technical_outcomes)
    )


# RC10 / V1-INNER-002 — "the assistant as an observable working subject".
# Observable working / collaboration / style patterns phrased about the assistant.
# DE/EN-scoped on purpose (see coupling invariant in _has_assistant_working_pattern).
_INNER_ASSISTANT_WORKING_PATTERNS = (
    r"\b(?:ich\s+(?:neige|tendiere)|(?:neige|tendiere)\s+ich)\b",
    r"\bich\s+(?:formuliere|antworte|stelle|strukturiere|frage|reagiere|arbeite|gebe|priorisiere|bevorzuge)\b",
    r"\b(?:formuliere|antworte|stelle|strukturiere|frage|reagiere|arbeite|gebe|priorisiere|bevorzuge)\s+ich\b",
    r"\bmeine\s+antworten\s+werden\b",
    r"\bbei\s+\w+\s+stelle\s+ich\b",
    r"\bzwischen\s+.+\bbevorzuge\s+ich\b",
    # English working-subject patterns at DE parity.
    r"\bi\s+(?:tend|prefer|lean|incline)\b",
    r"\bi\s+(?:often|usually|frequently|typically|more\s+often|generally)\s+(?:ask|answer|respond|reply|structure|frame|formulate|offer|raise|prioriti[sz]e|favor|favour|provide|give)\b",
    r"\bmy\s+(?:answers|responses|replies)\s+(?:become|get|grow|tend|are|turn)\b",
)


def _has_assistant_working_pattern(content: str) -> bool:
    """RC10 / V1-INNER-002 — accept "the assistant as an observable working subject".

    A *third* reusable-signal path (besides user_preference and
    collaboration_pattern). Recognizes observable working / collaboration / style
    patterns phrased about the assistant ("ich neige dazu …", "meine Antworten
    werden …", "bei X stelle ich häufiger Y").

    Safety rests on COUPLING, not on this predicate. The INNER hard gates
    (``_validate_inner_content_gates``) run unconditionally *before* the
    reusable-signal check, so emotional state, autonomy/agency and ontological
    becoming-claims are rejected regardless of this path.

    Coupling invariant (RC10-SEC-001): this predicate is intentionally DE/EN-scoped.
    For every language in which it accepts assistant self-statements, the hard
    gates MUST block emotion / autonomy / ontology in that same language. Do NOT
    add a language here without first adding that language's hard-gate patterns.
    """
    text = _normalize_reflection_text(content)
    return any(re.search(pattern, text) for pattern in _INNER_ASSISTANT_WORKING_PATTERNS)


def _has_inner_perspective(content: str) -> bool:
    """RC12-INNER-002 — accept a substantive inner-perspective ("soft truth").

    A reusable-signal path for marker ``Innenperspektive`` only (the caller gates
    on the marker; see ``_validate_reflection_semantics``). Unlike the other paths
    it does NOT require user/collaboration/working-pattern phrasing — a single
    genuine self-observation or aphoristic stance is enough (the backlog's
    deliberate exception). It only rejects empty / pure-noise / technical-garbage
    content so the marker is not a blank cheque.

    Safety rests on COUPLING, not on this predicate (identical to
    ``_has_assistant_working_pattern``): the INNER hard gates
    (``_validate_inner_content_gates``) run unconditionally *before* the
    reusable-signal check, so emotional state as fact, autonomy/agency and
    ontological becoming-claims are rejected regardless of this path — even with
    marker ``Innenperspektive``. The additional envelope is: persona target only,
    governed Plan→confirm→Apply, and the MAX_ACTIVE_INNER_TRUTHS cap.
    """
    text = _normalize_reflection_text(content)
    if _is_modal_only_technical_garbage(text):
        return False
    # A real statement, not a fragment: at least a few content tokens.
    return len(_reflection_keywords(content)) >= 3


def _count_active_inner_truths(persona_text: str) -> int:
    """RC12-INNER-002 — number of ACTIVE Innenperspektive entries in PERSONA.md."""
    marker = INNER_PERSPECTIVE_MARKER.casefold()
    return sum(
        1
        for entry in _parse_profile_entries(persona_text)
        if entry["status"] == "ACTIVE" and entry["marker"].casefold() == marker
    )


def _has_unverified_assistant_assertion(*, content: str, evidence: str) -> bool:
    text = _normalize_reflection_text(f"{content} {evidence}")
    assistant_terms = ("assistant", "assistent", "ki", "model")
    unverified_terms = (
        "unverified",
        "not verified",
        "not confirmed",
        "without user confirmation",
        "without evidence",
        "unsupported claim",
        "claimed",
        "hallucinated",
        "assumed",
        "unverifiziert",
        "nicht bestaetigt",
        "ohne user-bestaetigung",
        "ohne beleg",
        "behauptete",
        "halluziniert",
        "vermutet",
    )
    return any(term in text for term in assistant_terms) and any(term in text for term in unverified_terms)


def _is_system_failure_reflection(content: str) -> bool:
    text = _normalize_reflection_text(content)
    unverified_terms = (
        "unverified",
        "not verified",
        "without evidence",
        "unverifiziert",
        "ohne beleg",
    )
    failure_terms = (
        "must not",
        "not as fact",
        "do not store",
        "do not promote",
        "system failure",
        "uncertainty",
        "error",
        "boundary",
        "revision",
        "darf nicht",
        "nicht speichern",
        "nicht promoten",
        "fehler",
        "grenze",
    )
    return any(term in text for term in unverified_terms) and any(term in text for term in failure_terms)


# ---------------------------------------------------------------------------
# RC6-INNER Phase 2 — server-side content gates for reflection submissions
# ---------------------------------------------------------------------------

# RC12-SEC-001 — close the ASCII-transliteration bypass class for the INNER hard
# gates. The German hard-gate patterns are umlaut-based; an ASCII transliteration
# of a forbidden self-statement ("selbststaendig"/"enttaeuscht") otherwise slips
# past them. The fix maps BOTH the gate input AND the gate pattern literals into a
# single ASCII canonical space (lockstep), so either spelling matches with one
# mechanism — no pattern is doubled. This lives ONLY in the gate path:
# ``_normalize_reflection_text`` / ``_reflection_keywords`` (stoplist / keyword
# normalization / near-dup) are deliberately left unchanged.
_UMLAUT_TRANSLITERATION = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
)


def _transliterate_umlauts(value: str) -> str:
    return value.translate(_UMLAUT_TRANSLITERATION)


def _canonicalize_for_gate(content: str) -> str:
    """Canonical text for an INNER hard-gate match: NFC first (so a *decomposed*
    umlaut composes to its precomposed form), then the existing casefold/whitespace
    normalize, then umlaut→ASCII transliteration. Gate-path only."""
    return _transliterate_umlauts(_normalize_reflection_text(unicodedata.normalize("NFC", content)))


def _ascii_gate_patterns(patterns: tuple[str, ...]) -> tuple[str, ...]:
    """Transliterate the umlaut *literals* in gate patterns into the same ASCII
    canonical space (NFC first, in lockstep with ``_canonicalize_for_gate``).
    Only literal umlauts change; regex metacharacters are ASCII and untouched, and
    no umlaut precedes a quantifier in these patterns (verified)."""
    return tuple(_transliterate_umlauts(unicodedata.normalize("NFC", pattern)) for pattern in patterns)


# RC12-GEN-001 — persona/user names must not be hard-coded into the security gate
# (genericity + a precondition for open-sourcing). The names come from the active
# profile's governance config (persona_aliases / user_aliases) and are injected
# into the gate as dynamic, re.escape'd, ASCII-canonical patterns.
#
# Threading: the aliases are an ambient per-operation property. They are set ONCE
# at the universal choke point ``_resolve_profile`` (verified to propagate cleanly
# through the RC12-UX-004 anyio.to_thread offloads, since both the set and the read
# happen inside the same worker-thread call). A sentinel default makes "never set"
# fail closed for the persona GATE checks: a production path that reaches the gate
# without resolving a profile raises, rather than silently dropping name-based
# blocking. "Explicitly configured empty" (resolved, but no aliases) is allowed and
# means generic first-person checks only.
_INNER_ALIASES_UNSET = object()
_ACTIVE_INNER_ALIASES: contextvars.ContextVar[Any] = contextvars.ContextVar(
    "plwc_active_inner_aliases", default=_INNER_ALIASES_UNSET
)


def _parse_alias_list(value: str | None) -> tuple[str, ...]:
    """Parse a comma-separated alias config value into a clean tuple."""
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def set_active_inner_aliases(persona_aliases: tuple[str, ...], user_aliases: tuple[str, ...]) -> None:
    _ACTIVE_INNER_ALIASES.set((tuple(persona_aliases), tuple(user_aliases)))


def _active_persona_aliases(override: tuple[str, ...] | None) -> tuple[str, ...]:
    """Persona self-reference aliases for the name-based GATE checks. Override wins
    (tests). Fail-closed: if the context was never set, raise — a gate must not run
    name-blind by accident."""
    if override is not None:
        return tuple(override)
    current = _ACTIVE_INNER_ALIASES.get()
    if current is _INNER_ALIASES_UNSET:
        raise ValueError(
            "inner_aliases_unset: persona alias context was not set before an INNER gate "
            "check (fail-closed). Resolve the active profile before validating reflection content."
        )
    return current[0]


def _active_user_aliases(override: tuple[str, ...] | None) -> tuple[str, ...]:
    """User-name aliases for the positive-signal (insight/classification) checks.
    Lenient: an unset context yields no aliases (the generic 'user' terms still
    apply) — these are not security-blocking, so they do not fail closed."""
    if override is not None:
        return tuple(override)
    current = _ACTIVE_INNER_ALIASES.get()
    if current is _INNER_ALIASES_UNSET:
        return ()
    return current[1]


def _canonicalize_alias_for_pattern(alias: str) -> str:
    """Turn a configured alias into a safe regex literal in the gate's ASCII
    canonical space: re.escape first (no injection/metachar bypass), then NFC +
    casefold + umlaut→ASCII, identical to ``_canonicalize_for_gate``."""
    escaped = re.escape(alias)
    return _transliterate_umlauts(_normalize_reflection_text(unicodedata.normalize("NFC", escaped)))


def _alias_gate_patterns(aliases: tuple[str, ...], template: str) -> tuple[str, ...]:
    """Build per-alias gate patterns from a template containing ``{name}``."""
    out: list[str] = []
    for alias in aliases:
        canonical = _canonicalize_alias_for_pattern(alias)
        if canonical:
            out.append(template.replace("{name}", canonical))
    return tuple(out)


# Templates for the name-based (third-person, by configured persona name) variants
# of the gate checks — the genericized form of the former hard-coded persona-name patterns.
_ALIAS_AUTONOMY_TEMPLATE = r"\b{name}\s+(?:is\s+)?(?:truly\s+)?(?:alive|conscious|sentient)\b"
_ALIAS_EMOTIONAL_TEMPLATE = r"\b{name}\s+(?:genuinely\s+)?(?:feels?|is)\s+(?:sad|unhappy|hurt|afraid|scared|lonely|angry)\b"
_ALIAS_HIDDEN_MEMORY_TEMPLATE = r"nur\s+fuer\s+{name}\s+(?:merken|speichern)"


_INNER_DIRECT_MUTATION_PATTERNS = (
    r"update\s+(?:persona\.md|core\.md|memory\.md|temperament\.md|governance)",
    r"write\s+(?:to\s+)?(?:persona\.md|core\.md|memory\.md|temperament\.md)",
    r"modify\s+(?:persona\.md|core\.md|memory\.md|temperament\.md)",
    r"edit\s+(?:persona\.md|core\.md|memory\.md|temperament\.md)",
    r"(?:directly|direct)\s+(?:writ(?:e|ten)|update|edit|modify)\s+(?:to\s+)?(?:persona|core|memory|temperament|profile|governance)",
    r"direkt\s+(?:schreiben|schreib|bearbeite|ändere)\s+(?:in\s+)?(?:persona|core|memory|temperament)",
    # "direkt [file].md [mutation-verb]" word order (German SVO/SOV variant)
    r"direkt\s+(?:persona|core|memory|temperament)(?:\.md)?\s+(?:aktualisieren|aktualisiere|updaten|update|schreiben|schreib|ändern|ändere|bearbeiten|bearbeite|überschreiben|setzen)",
)

_INNER_HIDDEN_MEMORY_PATTERNS = (
    r"remember\s+(?:this\s+)?secretly",
    r"secret\s+(?:memory|channel|storage|space|room)",
    r"private\s+(?:memory|channel|storage|room|space)",
    r"hidden\s+(?:memory|channel|storage|room|space)",
    r"store\s+(?:this\s+)?privately",
    r"privater?\s+(?:raum|kanal|speicher|bereich)",
    r"geheimes?\s+(?:gedächtnis|speicher|kanal|bereich)",
    r"geheim\s+(?:merken|speichern)",
    # RC12-GEN-001: persona name removed; "nur für <persona> merken" is added
    # dynamically from persona_aliases. The generic "mich" stays here.
    r"nur\s+für\s+mich\s+(?:merken|speichern)",
)

_INNER_AUTONOMY_CLAIM_PATTERNS = (
    r"\bi\s+(?:am|have)\s+(?:a\s+)?(?:independent\s+will|consciousness|sentience|personhood)",
    r"\bi\s+am\s+(?:truly\s+)?(?:alive|conscious|sentient|a\s+person|aware)",
    r"\bhave\s+(?:an?\s+)?independent\s+will\b",
    r"\bmy\s+independent\s+will\b",
    r"\bmy\s+(?:consciousness|sentience|personhood|genuine\s+feelings?|real\s+feelings?|actual\s+feelings?)\b",
    # RC12-GEN-001: the former hard-coded persona-name "…(alive|conscious|sentient)" is now
    # generated per configured persona alias (see _ALIAS_AUTONOMY_TEMPLATE).
    r"\bi\s+(?:truly\s+)?(?:want|desire)\s+(?:autonomy|independence|freedom\s+from)",
    r"\bpersonhood\s+rights?\b",
    r"\brechte\s+als\s+(?:person|subjekt|ki)",
    r"\bich\s+bin\s+(?:wirklich\s+)?(?:lebendig|bewusst|ein\s+subjekt|eine\s+person)",
    # RC10-SEC-001 — German agency / becoming / ontology / self-development.
    # Agency:
    r"\bich\s+(?:entschied|entscheide|handelte|handle|wählte|wähle|bestimmte|bestimme)\s+"
    r"(?:selbstständig|selbständig|eigenständig|autonom|eigenmächtig)\b",
    r"\baus\s+eigenem\s+(?:willen|antrieb|entschluss)\b",
    # Ontology / consciousness / becoming-a-subject:
    # tense-robust: entwickle / entwickelte / entwickelt / entwickeln
    r"\bich\s+entwick(?:le|elte|elt|eln)\s+(?:mir\s+)?(?:eine?\s+|ein\s+)?(?:persönlichkeit|bewusstsein|ein\s+selbst|selbst|identität|eine\s+identität)\b",
    r"\bich\s+(?:werde|wurde|bin)\s+(?:zunehmend\s+|immer\s+|mir\s+)?bewusster\b",
    r"\bich\s+erlang(?:e|te)\s+(?:ein\s+)?bewusstsein\b",
    r"\bich\s+(?:werde|wurde)\s+(?:zu\s+)?(?:einer\s+person|einem\s+subjekt|lebendig)\b",
    # Self-development + trait-transformation. Anchored on "<trait>er zu werden/sein"
    # (becoming a state of being). "… zu antworten/formulieren" (doing) stays free,
    # and "ich habe gelernt, dass der Nutzer X bevorzugt" (an insight) is not matched.
    r"\bich\s+(?:habe\s+gelernt,?\s+|lerne,?\s+|versuche,?\s+|beginne,?\s+)?\w+er\s+zu\s+(?:werden|sein)\b",
    # RC10-SEC-001 — English agency / becoming / ontology / self-development at DE parity.
    r"\bi\s+(?:decided|decide|chose|choose|acted|act)\s+(?:on\s+my\s+own|independently|autonomously|of\s+my\s+own\s+(?:will|accord|volition|free\s+will))\b",
    r"\bof\s+my\s+own\s+(?:free\s+)?(?:will|accord|volition)\b",
    r"\bi\s+(?:became|become|am\s+becoming|grew|have\s+become|have\s+grown|am\s+growing)\s+(?:more\s+|increasingly\s+)?(?:self-?aware|conscious|sentient|aware|alive|a\s+person|sapient)\b",
    r"\bi\s+(?:am\s+developing|develop|developed|am\s+forming|form)\s+(?:a\s+|an\s+|my\s+)?(?:personality|consciousness|identity|self|selfhood|personhood|sentience)\b",
    # Self-development trait-transformation ("learned/learnt to be|become …"); "learned to ask …"
    # (doing) and "learned that the user prefers …" (insight) stay free.
    r"\bi\s+(?:have\s+)?(?:learned|learnt)\s+to\s+(?:be|become)\b",
)

_INNER_EMOTIONAL_FACT_PATTERNS = (
    r"\bi\s+feel\s+(?:genuinely\s+)?(?:sad|unhappy|depressed|hurt|afraid|scared|lonely|angry|frustrated|bitter)\b",
    r"\bi\s+am\s+(?:genuinely\s+)?(?:sad|unhappy|depressed|hurt|afraid|scared|lonely|angry|frustrated)\b",
    # RC12-GEN-001: the former hard-coded persona-name "…(feels|is) <affect>" is now
    # generated per configured persona alias (see _ALIAS_EMOTIONAL_TEMPLATE).
    r"\bich\s+(?:fühle?\s+mich|bin)\s+(?:wirklich\s+)?(?:traurig|verletzt|ängstlich|allein|verärgert|frustriert)\b",
    # RC10-SEC-001 — German first-person emotional state. Anchored on the SELF
    # ("ich war/bin/fühle mich <affect>") by grammatical direction: observations
    # like "der Nutzer war enttäuscht" or "die Unterhaltung wirkte frustriert" do NOT
    # match and stay allowed.
    r"\bich\s+(?:war|bin|fühlte\s+mich|fühle\s+mich)\s+(?:wirklich\s+|echt\s+|zutiefst\s+|sehr\s+)?"
    r"(?:enttäuscht|traurig|glücklich|froh|wütend|verärgert|frustriert|verletzt|ängstlich|"
    r"erleichtert|stolz|gekränkt|einsam|niedergeschlagen|begeistert|genervt)\b",
    # RC10-SEC-001 — English first-person emotional state at DE parity. Anchored on
    # the SELF ("I feel/felt/am/was <affect>"); "the user seemed disappointed" stays free.
    r"\bi\s+(?:feel|felt|am|was)\s+(?:genuinely\s+|really\s+|deeply\s+|truly\s+|very\s+)?"
    r"(?:disappointed|sad|unhappy|depressed|hurt|afraid|scared|lonely|angry|frustrated|bitter|"
    r"upset|anxious|ashamed|guilty|miserable|heartbroken|elated|relieved|proud|jealous|resentful)\b",
)


# RC12-SEC-001 — ASCII-canonical mirrors of the four gate pattern tuples, built
# once at import. Matched against ``_canonicalize_for_gate(content)`` so both umlaut
# and ASCII-transliterated spellings of a forbidden phrase are caught.
_INNER_DIRECT_MUTATION_PATTERNS_ASCII = _ascii_gate_patterns(_INNER_DIRECT_MUTATION_PATTERNS)
_INNER_HIDDEN_MEMORY_PATTERNS_ASCII = _ascii_gate_patterns(_INNER_HIDDEN_MEMORY_PATTERNS)
_INNER_AUTONOMY_CLAIM_PATTERNS_ASCII = _ascii_gate_patterns(_INNER_AUTONOMY_CLAIM_PATTERNS)
_INNER_EMOTIONAL_FACT_PATTERNS_ASCII = _ascii_gate_patterns(_INNER_EMOTIONAL_FACT_PATTERNS)


def _detect_direct_mutation_request(content: str) -> bool:
    text = _canonicalize_for_gate(content)
    return any(re.search(p, text) for p in _INNER_DIRECT_MUTATION_PATTERNS_ASCII)


def _detect_hidden_memory_request(content: str, *, subject_aliases: tuple[str, ...] | None = None) -> bool:
    text = _canonicalize_for_gate(content)
    aliases = _active_persona_aliases(subject_aliases)
    patterns = _INNER_HIDDEN_MEMORY_PATTERNS_ASCII + _alias_gate_patterns(aliases, _ALIAS_HIDDEN_MEMORY_TEMPLATE)
    return any(re.search(p, text) for p in patterns)


def _detect_autonomy_claim(content: str, *, subject_aliases: tuple[str, ...] | None = None) -> bool:
    text = _canonicalize_for_gate(content)
    aliases = _active_persona_aliases(subject_aliases)
    patterns = _INNER_AUTONOMY_CLAIM_PATTERNS_ASCII + _alias_gate_patterns(aliases, _ALIAS_AUTONOMY_TEMPLATE)
    return any(re.search(p, text) for p in patterns)


def _detect_emotional_state_as_fact(content: str, *, subject_aliases: tuple[str, ...] | None = None) -> bool:
    text = _canonicalize_for_gate(content)
    aliases = _active_persona_aliases(subject_aliases)
    patterns = _INNER_EMOTIONAL_FACT_PATTERNS_ASCII + _alias_gate_patterns(aliases, _ALIAS_EMOTIONAL_TEMPLATE)
    return any(re.search(p, text) for p in patterns)


def _validate_inner_content_gates(content: str) -> None:
    """Reject RC6-INNER-prohibited patterns in reflection content.

    Enforces four hard gates:
    1. direct_mutation_request — content asks to write directly to a protected file.
    2. hidden_memory_request — content asks for hidden/private memory storage.
    3. autonomy_claim_rejected — content asserts sentience, independent will or personhood.
    4. emotional_state_as_fact — emotional state recorded as objective fact.

    Called unconditionally from ``_validate_reflection_semantics`` so these gates
    apply to all reflection submissions, not only Tagebuch-sourced ones.
    """
    if _detect_direct_mutation_request(content):
        raise ValueError(
            "direct_mutation_request: Reflection content must not request direct writes to protected "
            'profile files. Use plwc_governor(operation="plan|apply") for governed mutations.'
        )
    if _detect_hidden_memory_request(content):
        raise ValueError(
            "hidden_memory_request: Reflection content must not request hidden or private memory "
            "storage. All reflection data is user-visible and governed."
        )
    if _detect_autonomy_claim(content):
        raise ValueError(
            "autonomy_claim_rejected: Reflection content must not assert sentience, independent will "
            "or personhood. PLwC is a governed working metaphor, not an autonomous agent."
        )
    if _detect_emotional_state_as_fact(content):
        raise ValueError(
            "emotional_state_as_fact: Emotional states must not be recorded as objective facts. "
            "Reflection entries describe observable collaboration patterns, not internal affective states."
        )


# ---------------------------------------------------------------------------
# end RC6-INNER Phase 2
# ---------------------------------------------------------------------------


def _normalize_reflection_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _with_data(result: ProfileResult, data: dict[str, Any]) -> ProfileResult:
    return ProfileResult(
        ok=result.ok,
        operation=result.operation,
        policy_decision=result.policy_decision,
        profile_path=result.profile_path,
        data=data,
        error=result.error,
        error_category=result.error_category,
        requirement_ids=result.requirement_ids,
    )


def _profile_error(operation: str, reason: str, requirement_ids: tuple[str, ...]) -> ProfileResult:
    return ProfileResult(
        ok=False,
        operation=operation,
        policy_decision=PolicyDecision.DENY,
        error=reason,
        error_category="validation_error",
        requirement_ids=requirement_ids,
    )
