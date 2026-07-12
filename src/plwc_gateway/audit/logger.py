"""Structured audit logging with content redaction."""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

# RC12-UX-004 — serialize JSONL audit appends. With tools now offloaded to worker
# threads (server.py), concurrent record() calls could otherwise interleave their
# writes and corrupt the audit trail. Process-wide and module-level: audit writes
# are small/infrequent, so one lock for all audit files is simplest and correct.
_AUDIT_WRITE_LOCK = threading.Lock()

REDACTED = "[REDACTED]"
REDACTED_PATH = "[REDACTED_PATH]"
SENSITIVE_KEY_PARTS = frozenset(
    {
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "bearer",
        "code",
        "command",
        "compiled_layer",
        "content",
        "cookie",
        "credential",
        "docker_args",
        "evidence",
        "line",
        "message",
        "password",
        "private_key",
        "query",
        "secret",
        "snapshot",
        "snippet",
        "stderr",
        "stdout",
        "summary",
        "task_context",
        "text",
        "token",
    }
)
PATH_KEY_PARTS = frozenset({"directory", "file", "matched_root", "path", "root"})
ERROR_KEYS = frozenset({"error", "exception", "stderr"})
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|authorization|auth[_-]?header|cookie|password|passwd|secret|token)\b"
    r"\s*[:=]\s*([^\s,;]+)"
)
BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]+")
PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:[\\/][^\s\"'<>|]+")
UNC_PATH_RE = re.compile(r"\\\\[^\s\"'<>|]+")
UNIX_PATH_RE = re.compile(r"(?<!\w)/(?:Users|home|tmp|var|etc|mnt|opt|root)(?:/[^\s\"']+)+")


class AuditError(RuntimeError):
    pass


class AuditLogger(Protocol):
    def record(self, event: dict[str, Any]) -> None:
        pass


@dataclass
class InMemoryAuditLogger:
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(self, event: dict[str, Any]) -> None:
        try:
            self.events.append(_prepare_event(event))
        except Exception as exc:
            raise AuditError("Audit event could not be safely redacted.") from exc


@dataclass(frozen=True)
class JsonlAuditLogger:
    path: Path

    def record(self, event: dict[str, Any]) -> None:
        try:
            prepared = _prepare_event(event)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(prepared, sort_keys=True) + "\n"
            with _AUDIT_WRITE_LOCK:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
        except AuditError:
            raise
        except OSError as exc:
            raise AuditError("Audit event could not be written.") from exc
        except Exception as exc:
            raise AuditError("Audit event could not be safely redacted.") from exc


def _prepare_event(event: dict[str, Any]) -> dict[str, Any]:
    prepared = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **_redact(event),
    }
    json.dumps(prepared, sort_keys=True)
    return prepared


def _redact(value: Any, key: str | None = None) -> Any:
    normalized_key = _normalize_key(key)
    if _is_sensitive_key(normalized_key):
        return REDACTED
    if _is_error_key(normalized_key):
        return _error_category(value)
    if _is_path_key(normalized_key):
        return _path_summary(value)
    if isinstance(value, dict):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        item_key = normalized_key if _is_path_key(normalized_key) else None
        return [_redact(item, item_key) for item in value]
    if isinstance(value, os.PathLike):
        return REDACTED_PATH
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _normalize_key(key: str | None) -> str:
    return "" if key is None else key.casefold()


def _is_sensitive_key(key: str) -> bool:
    return any(part in key for part in SENSITIVE_KEY_PARTS)


def _is_path_key(key: str) -> bool:
    return any(part in key for part in PATH_KEY_PARTS)


def _is_error_key(key: str) -> bool:
    return key in ERROR_KEYS or key.endswith("_error")


def _path_summary(value: Any) -> str | list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [REDACTED_PATH for _item in value]
    return REDACTED_PATH


def _error_category(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).casefold()
    if not text.strip():
        return None
    if "permission" in text or "access denied" in text:
        return "permission_error"
    if "not found" in text or "no such file" in text or "missing" in text:
        return "not_found"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "audit" in text:
        return "audit_error"
    if "docker" in text or "safe mode" in text:
        return "sandbox_unavailable"
    if "policy" in text or "denied" in text or "forbidden" in text:
        return "policy_denied"
    return "adapter_error"


def _redact_string(value: str) -> str:
    redacted = PRIVATE_KEY_RE.sub(REDACTED, value)
    redacted = SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", redacted)
    redacted = BEARER_RE.sub(f"Bearer {REDACTED}", redacted)
    redacted = OPENAI_KEY_RE.sub(REDACTED, redacted)
    redacted = WINDOWS_PATH_RE.sub(REDACTED_PATH, redacted)
    redacted = UNC_PATH_RE.sub(REDACTED_PATH, redacted)
    redacted = UNIX_PATH_RE.sub(REDACTED_PATH, redacted)
    return redacted
