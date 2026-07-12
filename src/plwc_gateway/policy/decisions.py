"""Policy decision constants for PLwC Gateway."""

from enum import Enum


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REWRITE = "REWRITE"
    ASK_USER = "ASK_USER"
    ESCALATE = "ESCALATE"
