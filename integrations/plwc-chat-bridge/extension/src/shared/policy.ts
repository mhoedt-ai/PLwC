import type { CanonicalToolName, JsonObject } from "./contracts";

export interface PolicyDecision {
  readOnly: boolean;
  requiresConfirmation: boolean;
  reason: string;
}

const WORKSPACE_READ_OPERATIONS = new Set(["list", "read", "read_binary", "search"]);
const DOCUMENT_READ_OPERATIONS = new Set(["inspect", "read", "extract", "metadata"]);
const GOVERNOR_READ_OPERATIONS = new Set(["plan", "list_retirable"]);

function operationOf(argumentsValue: JsonObject): string {
  return typeof argumentsValue.operation === "string" ? argumentsValue.operation.trim().toLowerCase() : "";
}

export function decidePolicy(toolName: CanonicalToolName, argumentsValue: JsonObject): PolicyDecision {
  if (toolName === "plwc_status" || toolName === "plwc_describe" || toolName === "plwc_profile") {
    return { readOnly: true, requiresConfirmation: false, reason: "Read-only PLwC facade." };
  }

  if (toolName === "plwc_governor") {
    const operation = operationOf(argumentsValue);
    if (operation === "apply") {
      return { readOnly: false, requiresConfirmation: true, reason: "Governor apply always requires confirmation." };
    }
    if (GOVERNOR_READ_OPERATIONS.has(operation)) {
      return { readOnly: true, requiresConfirmation: false, reason: "Governor planning or listing is read-only." };
    }
    return { readOnly: false, requiresConfirmation: true, reason: "Unknown Governor operations are treated as mutating." };
  }

  if (toolName === "plwc_workspace_operation") {
    const readOnly = WORKSPACE_READ_OPERATIONS.has(operationOf(argumentsValue));
    return readOnly
      ? { readOnly: true, requiresConfirmation: false, reason: "Workspace read operation." }
      : { readOnly: false, requiresConfirmation: true, reason: "Workspace mutation or unknown operation." };
  }

  if (toolName === "plwc_document_operation") {
    const readOnly = DOCUMENT_READ_OPERATIONS.has(operationOf(argumentsValue));
    return readOnly
      ? { readOnly: true, requiresConfirmation: false, reason: "Document inspection operation." }
      : { readOnly: false, requiresConfirmation: true, reason: "Document creation, mutation, or unknown operation." };
  }

  if (toolName === "plwc_sandbox_run") {
    return { readOnly: false, requiresConfirmation: true, reason: "Sandbox execution requires confirmation." };
  }

  return { readOnly: false, requiresConfirmation: true, reason: "Reflection writes require confirmation." };
}

export const POLICY_ROWS = [
  ["Status / Describe / Profile", "Read-only; manual by default"],
  ["Workspace / Document", "Reads may run; writes require confirmation"],
  ["Reflection / Sandbox", "Always require confirmation"],
  ["Governor plan", "Read-only planning"],
  ["Governor apply", "Always require confirmation"],
  ["Unknown operation", "Treat as mutating; require confirmation"],
] as const;
