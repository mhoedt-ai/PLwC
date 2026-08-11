import type { BridgeStatus, ConnectionState, LauncherState, LauncherStatus } from "../shared/messages";

const CONNECTION_STATES = new Set<ConnectionState>(["connected", "connecting", "disconnected", "error"]);
const NATIVE_AUTO_START_BLOCKED_STATES = new Set<LauncherState>(["starting", "unavailable", "failed"]);
const NATIVE_SETUP_REQUIRED_CODES = new Set(["native_host_missing", "native_launcher_unavailable"]);

export const FALLBACK_BRIDGE_STATUS: BridgeStatus = {
  buildIdentity: null,
  buildIdentityValidation: null,
  connection: "disconnected",
  endpoint: "ws://127.0.0.1:3007/message",
  lastError: "",
  launcher: {
    code: "not_requested",
    message: "Native launcher has not been requested.",
    state: "not_requested",
  },
  pendingRequests: 0,
  toolSet: null,
};

function normalizeLauncherStatus(value: unknown): LauncherStatus {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return FALLBACK_BRIDGE_STATUS.launcher;
  }
  const record = value as Partial<LauncherStatus>;
  return {
    ...(record.buildIdentity === undefined ? {} : { buildIdentity: record.buildIdentity }),
    ...(record.buildIdentityValidation === undefined
      ? {}
      : { buildIdentityValidation: record.buildIdentityValidation }),
    ...(typeof record.code === "string" ? { code: record.code } : {}),
    ...(typeof record.logPath === "string" ? { logPath: record.logPath } : {}),
    message:
      typeof record.message === "string" && record.message.trim() !== ""
        ? record.message
        : FALLBACK_BRIDGE_STATUS.launcher.message,
    state: record.state ?? FALLBACK_BRIDGE_STATUS.launcher.state,
    ...(typeof record.toolCount === "number" && Number.isSafeInteger(record.toolCount)
      ? { toolCount: record.toolCount }
      : {}),
  };
}

export function normalizeBridgeStatus(value: Partial<BridgeStatus> | null | undefined): BridgeStatus {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return FALLBACK_BRIDGE_STATUS;
  }
  return {
    buildIdentity: value.buildIdentity ?? FALLBACK_BRIDGE_STATUS.buildIdentity,
    buildIdentityValidation:
      value.buildIdentityValidation ?? FALLBACK_BRIDGE_STATUS.buildIdentityValidation,
    connection: CONNECTION_STATES.has(value.connection as ConnectionState)
      ? (value.connection as ConnectionState)
      : FALLBACK_BRIDGE_STATUS.connection,
    endpoint:
      typeof value.endpoint === "string" && value.endpoint.trim() !== ""
        ? value.endpoint
        : FALLBACK_BRIDGE_STATUS.endpoint,
    lastError: typeof value.lastError === "string" ? value.lastError : FALLBACK_BRIDGE_STATUS.lastError,
    launcher: normalizeLauncherStatus(value.launcher),
    pendingRequests:
      typeof value.pendingRequests === "number" && Number.isSafeInteger(value.pendingRequests) && value.pendingRequests >= 0
        ? value.pendingRequests
        : FALLBACK_BRIDGE_STATUS.pendingRequests,
    toolSet: value.toolSet ?? FALLBACK_BRIDGE_STATUS.toolSet,
  };
}

export function shouldRequestNativeAutoStart(value: Partial<BridgeStatus> | null | undefined): boolean {
  const status = normalizeBridgeStatus(value);
  return status.connection !== "connected" && !NATIVE_AUTO_START_BLOCKED_STATES.has(status.launcher.state);
}

export function shouldOfferSetupDownload(value: Partial<BridgeStatus> | null | undefined): boolean {
  const status = normalizeBridgeStatus(value);
  return status.launcher.code !== undefined && NATIVE_SETUP_REQUIRED_CODES.has(status.launcher.code);
}
