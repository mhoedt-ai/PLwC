import type { JsonObject, McpTool, ToolSetValidation } from "./contracts";
import type { PolicyDecision } from "./policy";

export type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

export interface BridgeStatus {
  connection: ConnectionState;
  endpoint: string;
  lastError: string;
  pendingRequests: number;
  toolSet: ToolSetValidation | null;
}

export interface BridgeSettings {
  autoSubmitResults: boolean;
  renderChatCards: boolean;
  readOnlyAutoRun: boolean;
}

export interface GatewaySettingsSnapshot {
  source: string;
  workspacePath: string | null;
  profilesPath: string | null;
  activeProfileName: string | null;
  securityConfig: string | null;
  memoryWriteThreshold: string | null;
  personaWriteThreshold: string | null;
  temperamentWriteThreshold: string | null;
  qdrantEnabled: string | null;
  personaLayerDisabled: string | null;
}

function nullableSetting(value: unknown, field: string): string | null {
  if (value === null) return null;
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid PLwC gateway setting: ${field}.`);
  }
  return value;
}

export function parseGatewaySettings(value: unknown): GatewaySettingsSnapshot {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Invalid PLwC gateway settings response.");
  }
  const record = value as Record<string, unknown>;
  if (typeof record.source !== "string" || record.source.trim() === "") {
    throw new Error("Invalid PLwC gateway settings source.");
  }
  return {
    source: record.source,
    workspacePath: nullableSetting(record.workspacePath, "workspacePath"),
    profilesPath: nullableSetting(record.profilesPath, "profilesPath"),
    activeProfileName: nullableSetting(record.activeProfileName, "activeProfileName"),
    securityConfig: nullableSetting(record.securityConfig, "securityConfig"),
    memoryWriteThreshold: nullableSetting(record.memoryWriteThreshold, "memoryWriteThreshold"),
    personaWriteThreshold: nullableSetting(record.personaWriteThreshold, "personaWriteThreshold"),
    temperamentWriteThreshold: nullableSetting(record.temperamentWriteThreshold, "temperamentWriteThreshold"),
    qdrantEnabled: nullableSetting(record.qdrantEnabled, "qdrantEnabled"),
    personaLayerDisabled: nullableSetting(record.personaLayerDisabled, "personaLayerDisabled"),
  };
}

export type BridgeRequest =
  | { type: "bridge.connect" }
  | { type: "bridge.status" }
  | { type: "bridge.tools.list" }
  | { type: "bridge.tools.call"; name: string; arguments: JsonObject; confirmed: boolean }
  | { type: "bridge.gateway.settings.get" }
  | { type: "bridge.settings.get" }
  | { type: "bridge.settings.update"; settings: Partial<BridgeSettings> };

export interface ToolListResponse {
  tools: McpTool[];
  validation: ToolSetValidation;
}

export interface ToolCallResponse {
  result: unknown;
  isError: boolean;
  policy: PolicyDecision;
}

export type BridgeResponse<T = unknown> =
  | { ok: true; value: T }
  | { ok: false; error: string; code?: string };
