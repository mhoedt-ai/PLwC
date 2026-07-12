"""Minimal fail-closed policy engine for PLwC Gateway."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .decisions import PolicyDecision
from .intents import IntentAction, PolicyIntent
from .paths import PROTECTED_GOVERNANCE_FILENAMES, guard_path, is_protected_governance_path

GOVERNED_PROFILE_WRITE_TOOLS = frozenset(
    {
        "plwc_reflection",
        "plwc_governor",
        "plwc_write_reflection",
        "plwc_governor_apply",
    }
)


class EvaluatesPolicy(Protocol):
    def evaluate(self, intent: PolicyIntent) -> "PolicyResult":
        pass


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str
    requirement_ids: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW


@dataclass(frozen=True)
class PolicyExecution:
    policy: PolicyResult
    executed: bool
    adapter_result: Any = None


class PolicyEngine:
    def evaluate(self, intent: PolicyIntent) -> PolicyResult:
        tool_name = intent.normalized_tool_name()
        if not tool_name:
            return _deny("Tool name is required.", "SR-010", "NFR-002")

        if intent.action == IntentAction.UNKNOWN:
            return _deny("Unknown policy intent action.", "SR-010", "NFR-002")

        if intent.action == IntentAction.HOST_SHELL:
            return _deny("Direct host shell execution is forbidden.", "SR-001", "SR-010")

        if intent.action == IntentAction.CONFIGURE_POLICY:
            return _deny("Runtime security policy mutation is forbidden.", "SR-005", "SR-010")

        if intent.action in {IntentAction.READ, IntentAction.WRITE}:
            path_operation = "write" if intent.action == IntentAction.WRITE else "read"
            if _is_governed_profile_write_tool(intent) and not is_protected_governance_path(intent.target_path):
                return _deny(
                    "Governed profile writes are limited to approved governance targets.",
                    "SR-004",
                    "SR-010",
                    "NFR-002",
                )
            if _is_governed_profile_write(intent):
                path_operation = "read"

            path_result = guard_path(
                intent.target_path,
                intent.metadata.get("allowed_roots"),
                base_dir=intent.metadata.get("base_dir"),
                operation=path_operation,
                protected_patterns=intent.metadata.get("protected_patterns"),
                pattern_base_dir=intent.metadata.get("pattern_base_dir"),
            )
            if not path_result.allowed:
                return _deny(path_result.reason, *path_result.requirement_ids)

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Intent allowed by minimal policy.",
            requirement_ids=("SR-010",),
        )


def evaluate_intent(intent: PolicyIntent, engine: EvaluatesPolicy | None = None) -> PolicyResult:
    evaluator = engine or PolicyEngine()
    try:
        return evaluator.evaluate(intent)
    except Exception as exc:
        return _deny(f"Policy evaluation failed closed: {exc}", "SR-010", "NFR-002")


def execute_with_policy(
    intent: PolicyIntent,
    adapter_call: Callable[[], Any],
    engine: EvaluatesPolicy | None = None,
) -> PolicyExecution:
    policy = evaluate_intent(intent, engine)
    if not policy.allowed:
        return PolicyExecution(policy=policy, executed=False)

    return PolicyExecution(policy=policy, executed=True, adapter_result=adapter_call())


def _deny(reason: str, *requirement_ids: str) -> PolicyResult:
    return PolicyResult(
        decision=PolicyDecision.DENY,
        reason=reason,
        requirement_ids=tuple(requirement_ids),
    )


def _is_governed_profile_write(intent: PolicyIntent) -> bool:
    if not _is_governed_profile_write_tool(intent):
        return False
    if intent.metadata.get("governed_profile_write") is not True:
        return False
    return is_protected_governance_path(intent.target_path)


def _is_governed_profile_write_tool(intent: PolicyIntent) -> bool:
    if intent.action != IntentAction.WRITE:
        return False
    if intent.normalized_tool_name() not in GOVERNED_PROFILE_WRITE_TOOLS:
        return False
    return True
