"""Path policy guards for PLwC Gateway."""

from __future__ import annotations

import fnmatch
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .decisions import PolicyDecision

PROTECTED_GOVERNANCE_FILENAMES = frozenset(
    {
        "CORE.md",
        "PERSONA.md",
        "TEMPERAMENT.md",
        "CONSCIENCE.md",
        "memory.md",
        "reflection.md",
        "journal.md",
        "active_profile.json",
        "STATE.md",
        "compiled_prompt.txt",
        "security.yaml",
    }
)
GOVERNANCE_WRITE_OPERATIONS = frozenset(
    {
        "append",
        "create",
        "delete",
        "edit",
        "move",
        "overwrite",
        "rename",
        "replace",
        "truncate",
        "write",
    }
)
_PROTECTED_CASEFOLD = frozenset(name.casefold() for name in PROTECTED_GOVERNANCE_FILENAMES)


@dataclass(frozen=True)
class PathPolicyResult:
    decision: PolicyDecision
    reason: str
    requested_path: str
    absolute_path: str | None = None
    matched_root: str | None = None
    requirement_ids: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        return self.decision == PolicyDecision.ALLOW


def guard_path(
    requested_path: str | os.PathLike[str] | None,
    allowed_roots: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
    *,
    base_dir: str | os.PathLike[str] | None = None,
    operation: str = "read",
    protected_patterns: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None = None,
    pattern_base_dir: str | os.PathLike[str] | None = None,
) -> PathPolicyResult:
    requested = "" if requested_path is None else os.fspath(requested_path)
    if not requested.strip():
        return _deny("Path is required.", requested, "SR-006", "NFR-002")

    if _has_parent_traversal(requested):
        return _deny("Parent traversal is not allowed.", requested, "SR-006", "NFR-002")

    if _is_governance_write(operation, requested):
        return _deny(
            "Protected governance files require governed tools.",
            requested,
            "SR-004",
            "SR-010",
        )

    root_values = _coerce_allowed_roots(allowed_roots)
    if not root_values:
        return _deny("At least one explicit allowed root is required.", requested, "SR-006", "NFR-002")

    base_path = _resolve_base(base_dir)
    pattern_base_path = _resolve_base(pattern_base_dir) if pattern_base_dir is not None else base_path
    root_result = _resolve_allowed_roots(root_values, base_path, requested)
    if isinstance(root_result, PathPolicyResult):
        return root_result
    resolved_roots = root_result

    absolute_path = _resolve_requested_path(requested, base_path)
    if _is_write_operation(operation) and _matches_protected_pattern(
        absolute_path,
        protected_patterns,
        pattern_base_path,
    ):
        return _deny(
            "Protected path patterns require governed tools.",
            requested,
            "SR-004",
            "SR-005",
            "SR-010",
            absolute_path=str(absolute_path),
        )

    for root in resolved_roots:
        if _is_inside_or_same(absolute_path, root):
            return PathPolicyResult(
                decision=PolicyDecision.ALLOW,
                reason="Path is inside an allowed root.",
                requested_path=requested,
                absolute_path=str(absolute_path),
                matched_root=str(root),
                requirement_ids=("SR-006",),
            )

    return _deny(
        "Path is outside the allowed roots.",
        requested,
        "SR-006",
        "NFR-002",
        absolute_path=str(absolute_path),
    )


def is_protected_governance_path(path_value: str | os.PathLike[str] | None) -> bool:
    if path_value is None:
        return False
    path_text = os.fspath(path_value)
    if Path(path_text).name.casefold() in _PROTECTED_CASEFOLD:
        return True
    parts = [part for part in re.split(r"[\\/]+", path_text) if part]
    return len(parts) >= 2 and parts[-2].casefold() == "governance" and parts[-1].casefold() == "config.yaml"


def _is_governance_write(operation: str, requested_path: str) -> bool:
    return _is_write_operation(operation) and is_protected_governance_path(requested_path)


def _is_write_operation(operation: str) -> bool:
    return operation.casefold() in GOVERNANCE_WRITE_OPERATIONS


def _coerce_allowed_roots(
    allowed_roots: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
) -> tuple[str | os.PathLike[str], ...]:
    if allowed_roots is None:
        return ()
    if isinstance(allowed_roots, (str, os.PathLike)):
        return (allowed_roots,)
    return tuple(allowed_roots)


def _coerce_patterns(
    patterns: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
) -> tuple[str | os.PathLike[str], ...]:
    if patterns is None:
        return ()
    if isinstance(patterns, (str, os.PathLike)):
        return (patterns,)
    return tuple(patterns)


def _resolve_allowed_roots(
    allowed_roots: tuple[str | os.PathLike[str], ...],
    base_path: Path,
    requested_path: str,
) -> tuple[Path, ...] | PathPolicyResult:
    resolved_roots: list[Path] = []
    for raw_root in allowed_roots:
        root_text = os.fspath(raw_root)
        if not root_text.strip():
            return _deny("Allowed roots must be non-empty.", requested_path, "SR-006", "NFR-002")

        root = _resolve_requested_path(root_text, base_path)
        if _is_filesystem_root(root):
            return _deny("Filesystem roots are not allowed roots.", requested_path, "SR-006", "NFR-002")
        if _is_home_root(root):
            return _deny("Home directory root is not an allowed root.", requested_path, "SR-006", "NFR-002")
        resolved_roots.append(root)

    return tuple(resolved_roots)


def _resolve_requested_path(path_value: str, base_path: Path) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = base_path / path
    return path.resolve(strict=False)


def _resolve_base(base_dir: str | os.PathLike[str] | None) -> Path:
    if base_dir is None:
        return Path.cwd().resolve(strict=False)
    return Path(base_dir).expanduser().resolve(strict=False)


def _has_parent_traversal(path_value: str) -> bool:
    return ".." in re.split(r"[\\/]+", path_value)


def _is_inside_or_same(candidate: Path, root: Path) -> bool:
    try:
        common_path = os.path.commonpath([_normalize(candidate), _normalize(root)])
    except ValueError:
        return False
    return common_path == _normalize(root)


def _is_filesystem_root(path_value: Path) -> bool:
    anchor = Path(path_value.anchor) if path_value.anchor else None
    return anchor is not None and _normalize(path_value) == _normalize(anchor)


def _is_home_root(path_value: Path) -> bool:
    return _normalize(path_value) == _normalize(Path.home().resolve(strict=False))


def _matches_protected_pattern(
    candidate: Path,
    protected_patterns: Iterable[str | os.PathLike[str]] | str | os.PathLike[str] | None,
    pattern_base_path: Path,
) -> bool:
    candidate_text = _normalize(candidate)
    for raw_pattern in _coerce_patterns(protected_patterns):
        pattern_text = os.fspath(raw_pattern)
        if not pattern_text.strip():
            continue
        pattern_path = Path(pattern_text).expanduser()
        if not pattern_path.is_absolute():
            pattern_path = pattern_base_path / pattern_path
        normalized_pattern = _normalize_pattern(pattern_path)
        if fnmatch.fnmatch(candidate_text, normalized_pattern):
            return True
    return False


def _normalize(path_value: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path_value)))


def _normalize_pattern(path_value: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path_value)))


def _deny(
    reason: str,
    requested_path: str,
    *requirement_ids: str,
    absolute_path: str | None = None,
) -> PathPolicyResult:
    return PathPolicyResult(
        decision=PolicyDecision.DENY,
        reason=reason,
        requested_path=requested_path,
        absolute_path=absolute_path,
        requirement_ids=tuple(requirement_ids),
    )
