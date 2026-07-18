import type { CanonicalToolName } from "./contracts";

export interface NormalizedToolResult {
  isError: boolean;
  result: unknown;
}

export type ToolResultState = "denied" | "failed" | "succeeded";

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function normalizeToolResult(value: unknown): NormalizedToolResult {
  const envelope = record(value);
  if (!envelope) return { isError: false, result: value };

  const isError = envelope.isError === true;
  if (envelope.structuredContent !== undefined) {
    return { isError, result: envelope.structuredContent };
  }

  if (Array.isArray(envelope.content) && envelope.content.length === 1) {
    const item = record(envelope.content[0]);
    if (item?.type === "text" && typeof item.text === "string") {
      try {
        return { isError, result: JSON.parse(item.text) as unknown };
      } catch {
        return { isError, result: item.text };
      }
    }
  }

  return { isError, result: value };
}

export function classifyToolResult(isError: boolean, result: unknown): ToolResultState {
  const resultRecord = record(result);
  const denied =
    String(resultRecord?.policy_decision ?? "").toUpperCase() === "DENY" ||
    String(resultRecord?.decision ?? "").toLowerCase() === "denied";
  if (denied) return "denied";
  if (isError || resultRecord?.ok === false) return "failed";
  return "succeeded";
}

function presentRuntimeStatus(result: Record<string, unknown>): Record<string, unknown> {
  const profileCompile = record(result.profile_compile);
  return {
    ok: result.ok,
    server: result.server,
    version: result.version,
    scope: result.scope,
    workspace_root: result.workspace_root,
    profile_root: result.profile_root,
    active_profile_name: result.active_profile_name,
    active_profile_source: result.active_profile_source,
    profile_exists: result.profile_exists,
    profile_valid: result.profile_valid,
    policy_config_source: result.policy_config_source,
    security_config_path: result.security_config_path,
    tools: {
      expected: result.expected_public_tool_count,
      registered: result.registered_public_tool_count,
    },
    governance_thresholds: result.governance_thresholds,
    persona_layer_enabled: profileCompile?.persona_layer_enabled,
    setup_warnings: result.setup_warnings,
  };
}

export function presentToolResult(name: CanonicalToolName, result: unknown): unknown {
  const resultRecord = record(result);
  if (name === "plwc_status" && resultRecord?.scope === "runtime") {
    return presentRuntimeStatus(resultRecord);
  }
  return result;
}
