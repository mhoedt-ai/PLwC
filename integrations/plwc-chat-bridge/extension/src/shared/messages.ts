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
  readOnlyAutoRun: boolean;
}

export type BridgeRequest =
  | { type: "bridge.connect" }
  | { type: "bridge.status" }
  | { type: "bridge.tools.list" }
  | { type: "bridge.tools.call"; name: string; arguments: JsonObject; confirmed: boolean }
  | { type: "bridge.settings.get" }
  | { type: "bridge.settings.update"; settings: Partial<BridgeSettings> };

export interface ToolListResponse {
  tools: McpTool[];
  validation: ToolSetValidation;
}

export interface ToolCallResponse {
  result: unknown;
  policy: PolicyDecision;
}

export type BridgeResponse<T = unknown> =
  | { ok: true; value: T }
  | { ok: false; error: string; code?: string };
