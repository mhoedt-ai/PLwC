import type {
  BridgeReadiness,
  BridgeStatus,
  ConnectionState,
  LauncherState,
  LauncherStatus,
} from "../shared/messages";

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
  readiness: {
    buildVerified: false,
    expectedToolCount: 8,
    generation: 0,
    state: "disconnected",
    toolCount: 0,
    toolsVerified: false,
  },
  extension: {
    browserFamily: "chromium",
    extensionId: "unknown",
    packageVersion: "unknown",
    protocolVersion: "1.0.0",
    reportedAt: "",
  },
  storeUpdate: {
    availableVersion: null,
    reportedAt: null,
    source: "not_reported",
    state: "unknown",
  },
  toolSet: null,
};

function legacyReadiness(value: Partial<BridgeStatus>): BridgeReadiness {
  const generation = typeof value.readiness?.generation === "number" ? value.readiness.generation : 0;
  if (value.readiness?.state === "incompatible" || value.readiness?.state === "error") {
    return {
      ...FALLBACK_BRIDGE_STATUS.readiness,
      generation,
      state: value.readiness.state,
    };
  }
  if (value.connection === "connected") {
    if (value.buildIdentityValidation?.valid !== true) {
      return { ...FALLBACK_BRIDGE_STATUS.readiness, generation, state: "checking_build" };
    }
    if (value.toolSet?.valid !== true) {
      return {
        ...FALLBACK_BRIDGE_STATUS.readiness,
        buildVerified: true,
        generation,
        state: "loading_tools",
      };
    }
    return {
      buildVerified: true,
      expectedToolCount: 8,
      generation,
      state: "ready",
      toolCount: 8,
      toolsVerified: true,
    };
  }
  if (value.readiness?.state === "connecting" || value.readiness?.state === "disconnected") {
    return {
      ...FALLBACK_BRIDGE_STATUS.readiness,
      generation,
      state: value.readiness.state,
    };
  }
  if (value.connection === "connecting") {
    return { ...FALLBACK_BRIDGE_STATUS.readiness, generation, state: "connecting" };
  }
  if (value.connection === "error") {
    return { ...FALLBACK_BRIDGE_STATUS.readiness, generation, state: "error" };
  }
  return { ...FALLBACK_BRIDGE_STATUS.readiness, generation };
}

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
  const readiness = legacyReadiness(value);
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
    readiness,
    extension: {
      browserFamily: value.extension?.browserFamily ?? FALLBACK_BRIDGE_STATUS.extension.browserFamily,
      extensionId: value.extension?.extensionId ?? FALLBACK_BRIDGE_STATUS.extension.extensionId,
      packageVersion: value.extension?.packageVersion ?? FALLBACK_BRIDGE_STATUS.extension.packageVersion,
      protocolVersion: "1.0.0",
      reportedAt: value.extension?.reportedAt ?? FALLBACK_BRIDGE_STATUS.extension.reportedAt,
    },
    storeUpdate: {
      availableVersion: value.storeUpdate?.availableVersion ?? null,
      reportedAt: value.storeUpdate?.reportedAt ?? null,
      source: value.storeUpdate?.source === "browser_event" ? "browser_event" : "not_reported",
      state: value.storeUpdate?.state === "available" ? "available" : "unknown",
    },
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

export type VerifiedToolCacheAction = "clear" | "keep" | "reload";

export function decideVerifiedToolCacheAction(
  value: Partial<BridgeStatus> | null | undefined,
  hasVerifiedLocalToolList: boolean,
): VerifiedToolCacheAction {
  const status = normalizeBridgeStatus(value);
  if (status.readiness.state !== "ready") {
    return hasVerifiedLocalToolList ? "clear" : "keep";
  }
  return hasVerifiedLocalToolList ? "keep" : "reload";
}
