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
  autoConfirmSandbox: boolean;
  autoConfirmWrites: boolean;
  autoExecuteDelay: number;
  autoInsertDelay: number;
  autoSubmitDelay: number;
  autoSubmitResults: boolean;
  renderChatCards: boolean;
  readOnlyAutoRun: boolean;
}

export function normalizeAutomationDelay(value: unknown, fallback = 2): number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 60
    ? Math.round(value * 10) / 10
    : fallback;
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

export type GatewaySettingsUpdate = Omit<GatewaySettingsSnapshot, "source">;

const GATEWAY_SETTING_KEYS = [
  "workspacePath",
  "profilesPath",
  "activeProfileName",
  "securityConfig",
  "memoryWriteThreshold",
  "personaWriteThreshold",
  "temperamentWriteThreshold",
  "qdrantEnabled",
  "personaLayerDisabled",
] as const satisfies ReadonlyArray<keyof GatewaySettingsUpdate>;

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

export function parseGatewaySettingsUpdate(value: unknown): GatewaySettingsUpdate {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Invalid editable PLwC gateway settings.");
  }
  const record = value as Record<string, unknown>;
  if (
    Object.keys(record).length !== GATEWAY_SETTING_KEYS.length ||
    Object.keys(record).some((key) => !GATEWAY_SETTING_KEYS.includes(key as keyof GatewaySettingsUpdate))
  ) {
    throw new Error("Editable PLwC gateway settings must contain exactly the supported fields.");
  }
  const parsed = Object.fromEntries(
    GATEWAY_SETTING_KEYS.map((key) => [key, nullableSetting(record[key], key)]),
  ) as unknown as GatewaySettingsUpdate;
  for (const key of ["workspacePath", "profilesPath", "securityConfig"] as const) {
    const settingValue = parsed[key];
    if (settingValue !== null && !/^(?:[A-Za-z]:[\\/]|\\\\|\/)/u.test(settingValue)) {
      throw new Error(`Invalid absolute PLwC path: ${key}.`);
    }
  }
  for (const key of ["memoryWriteThreshold", "personaWriteThreshold", "temperamentWriteThreshold"] as const) {
    const settingValue = parsed[key];
    if (
      settingValue !== null &&
      (!/^(?:0|[1-9][0-9]*)$/u.test(settingValue) || Number(settingValue) > 1_000_000)
    ) {
      throw new Error(`Invalid PLwC threshold: ${key}.`);
    }
  }
  for (const key of ["qdrantEnabled", "personaLayerDisabled"] as const) {
    const settingValue = parsed[key];
    if (settingValue !== null && settingValue !== "true" && settingValue !== "false") {
      throw new Error(`Invalid PLwC boolean: ${key}.`);
    }
  }
  if (Object.values(parsed).some((settingValue) => settingValue !== null && /[\u0000-\u001f\u007f]/u.test(settingValue))) {
    throw new Error("PLwC gateway settings must not contain control characters.");
  }
  return parsed;
}

export type BridgeRequest =
  | { type: "bridge.connect" }
  | { type: "bridge.status" }
  | { type: "bridge.tools.list" }
  | { type: "bridge.tools.call"; name: string; arguments: JsonObject; confirmed: boolean }
  | { type: "bridge.gateway.settings.get" }
  | { type: "bridge.gateway.settings.update"; settings: GatewaySettingsUpdate }
  | { type: "bridge.gateway.settings.reset" }
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
