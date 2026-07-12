"""Structured policy intents for PLwC Gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class IntentAction(str, Enum):
    STATUS = "STATUS"
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE_SANDBOXED = "EXECUTE_SANDBOXED"
    HOST_SHELL = "HOST_SHELL"
    CONFIGURE_POLICY = "CONFIGURE_POLICY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PolicyIntent:
    tool_name: str
    action: IntentAction
    target_path: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def normalized_tool_name(self) -> str:
        return self.tool_name.strip()
