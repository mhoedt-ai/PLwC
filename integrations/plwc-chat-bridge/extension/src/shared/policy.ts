import type { CanonicalToolName, JsonObject } from "./contracts";

export interface PolicyDecision {
  automaticConfirmationAllowed?: boolean;
  automaticSandboxConfirmationAllowed?: boolean;
  readOnly: boolean;
  requiresConfirmation: boolean;
  reason: string;
}

const WORKSPACE_READ_OPERATIONS = new Set(["batch_read", "file_info", "list", "read", "read_binary", "search"]);
const WORKSPACE_WRITE_OPERATIONS = new Set(["copy", "create_dir", "exact_replace", "move", "rename", "write", "write_binary"]);
const DOCUMENT_READ_OPERATIONS = new Set([
  "inspect_docx", "inspect_ods", "inspect_odp", "inspect_odt", "inspect_pdf", "inspect_pptx", "inspect_xlsx",
  "inspect_zip", "read_image",
]);
const DOCUMENT_WRITE_OPERATIONS = new Set([
  "create_docx", "create_pdf", "create_pptx", "create_xlsx", "create_zip", "edit_docx", "extract_docx_text",
  "extract_ods_data", "extract_odp_text", "extract_odt_text", "extract_pdf", "extract_pdf_text", "extract_pptx_text",
  "extract_xlsx_data", "extract_zip", "merge_pdf", "rotate_pdf", "split_pdf",
]);
const GOVERNOR_READ_OPERATIONS = new Set(["plan", "list_retirable"]);

function operationOf(argumentsValue: JsonObject): string {
  return typeof argumentsValue.operation === "string" ? argumentsValue.operation.trim().toLowerCase() : "";
}

export function withConfirmedToolArguments(
  toolName: CanonicalToolName,
  argumentsValue: JsonObject,
  confirmed: boolean,
): JsonObject {
  if (!confirmed || toolName !== "plwc_governor") return argumentsValue;
  return { ...argumentsValue, confirmed: true };
}

export function decidePolicy(toolName: CanonicalToolName, argumentsValue: JsonObject): PolicyDecision {
  if (toolName === "plwc_status" || toolName === "plwc_describe" || toolName === "plwc_profile") {
    return { readOnly: true, requiresConfirmation: false, reason: "Read-only PLwC facade." };
  }

  if (toolName === "plwc_governor") {
    const operation = operationOf(argumentsValue);
    if (operation === "apply") {
      return { automaticConfirmationAllowed: true, readOnly: false, requiresConfirmation: true, reason: "Governor apply requires confirmation." };
    }
    if (GOVERNOR_READ_OPERATIONS.has(operation)) {
      return { readOnly: true, requiresConfirmation: false, reason: "Governor planning or listing is read-only." };
    }
    return { readOnly: false, requiresConfirmation: true, reason: "Unknown Governor operations are treated as mutating." };
  }

  if (toolName === "plwc_workspace_operation") {
    const operation = operationOf(argumentsValue);
    if (WORKSPACE_READ_OPERATIONS.has(operation)) {
      return { readOnly: true, requiresConfirmation: false, reason: "Workspace read operation." };
    }
    if (WORKSPACE_WRITE_OPERATIONS.has(operation)) {
      return { automaticConfirmationAllowed: true, readOnly: false, requiresConfirmation: true, reason: "Workspace write operation." };
    }
    return { readOnly: false, requiresConfirmation: true, reason: "Unknown workspace operation." };
  }

  if (toolName === "plwc_document_operation") {
    const operation = operationOf(argumentsValue);
    if (DOCUMENT_READ_OPERATIONS.has(operation)) {
      return { readOnly: true, requiresConfirmation: false, reason: "Document inspection operation." };
    }
    if (DOCUMENT_WRITE_OPERATIONS.has(operation)) {
      return { automaticConfirmationAllowed: true, readOnly: false, requiresConfirmation: true, reason: "Document write operation." };
    }
    return { readOnly: false, requiresConfirmation: true, reason: "Unknown document operation." };
  }

  if (toolName === "plwc_sandbox_run") {
    return {
      automaticSandboxConfirmationAllowed: true,
      readOnly: false,
      requiresConfirmation: true,
      reason: "Sandbox execution requires confirmation or the enabled standing sandbox setting.",
    };
  }

  if (operationOf(argumentsValue) === "write") {
    return { automaticConfirmationAllowed: true, readOnly: false, requiresConfirmation: true, reason: "Reflection writes require confirmation." };
  }
  return { readOnly: false, requiresConfirmation: true, reason: "Unknown reflection operation." };
}

export const POLICY_ROWS = [
  ["Status / Describe / Profile", "Read-only; eligible for automatic execution"],
  ["Workspace / Document", "Reads may run; recognized writes require confirmation or the enabled standing write setting"],
  ["Reflection", "Writes require confirmation or the enabled standing write setting"],
  ["Sandbox", "Requires individual confirmation or the enabled standing sandbox setting"],
  ["Governor plan", "Read-only planning"],
  ["Governor apply", "Requires confirmation; the standing write setting may satisfy it"],
  ["Unknown operation", "Never automatic; require individual confirmation"],
] as const;
