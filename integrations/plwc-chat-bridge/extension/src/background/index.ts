import { JsonRpcWebSocketClient, RpcRequestError } from "./transport";
import {
  INITIAL_LAUNCHER_STATUS,
  NATIVE_LAUNCHER_HOST,
  NATIVE_LAUNCHER_PORT,
  NativeLauncherError,
  connectAfterNativeStart,
  isRecoverableConnectionError,
  parseNativeLauncherResponse,
} from "./native-launcher";
import {
  BRIDGE_ENDPOINT,
  CANONICAL_TOOL_NAMES,
  type CanonicalToolName,
  type JsonObject,
  validateToolSet,
} from "../shared/contracts";
import {
  EXTENSION_BUILD_IDENTITY,
  parseBuildIdentity,
  validateBuildIdentity,
  type BuildIdentity,
  type BuildIdentityValidation,
} from "../shared/build-identity";
import type {
  BridgeRequest,
  BridgeResponse,
  BridgeSettings,
  BridgeStatus,
  GatewaySettingsSnapshot,
  GatewaySettingsUpdate,
  LauncherStatus,
  ToolCallResponse,
  ToolListResponse,
} from "../shared/messages";
import {
  localizeLauncherStatus,
  resolveUiLanguage,
  type UiLanguage,
} from "../shared/i18n";
import {
  normalizeAutomationDelay,
  parseGatewaySettings,
  parseGatewaySettingsUpdate,
} from "../shared/messages";
import { decidePolicy, withConfirmedToolArguments } from "../shared/policy";
import { normalizeToolResult } from "../shared/tool-result";
import {
  claimToolCallExecution,
  parseProcessedToolCallRegistry,
  PROCESSED_TOOL_CALLS_STORAGE_KEY,
  type ToolCallClaimOutcome,
} from "../shared/tool-call-execution-registry";
import { createToolCallIdentity, type ToolCallIdentity } from "../shared/tool-call-identity";

const transport = new JsonRpcWebSocketClient(BRIDGE_ENDPOINT);
const HEARTBEAT_INTERVAL_MS = 20_000;
const SETTINGS_REVISION = 6;
const GATEWAY_SETTINGS_STORAGE_KEY = "gatewaySettingsOverrides";
let currentBuildIdentity: BuildIdentity | null = null;
let currentBuildIdentityValidation: BuildIdentityValidation | null = null;
let currentToolSet: ReturnType<typeof validateToolSet> | null = null;
let launcherStatus = INITIAL_LAUNCHER_STATUS;
let toolCallClaimLock: Promise<void> = Promise.resolve();

function uiLanguage(): UiLanguage {
  return resolveUiLanguage(chrome.i18n?.getUILanguage?.());
}

function localizedLauncherStatus(value: LauncherStatus): LauncherStatus {
  return {
    ...value,
    message: localizeLauncherStatus(value, uiLanguage()),
  };
}

function status(): BridgeStatus {
  return {
    buildIdentity: currentBuildIdentity,
    buildIdentityValidation: currentBuildIdentityValidation,
    connection: transport.state,
    endpoint: BRIDGE_ENDPOINT,
    lastError: transport.lastError,
    launcher: launcherStatus,
    pendingRequests: transport.pendingCount,
    toolSet: currentToolSet,
  };
}

function isCanonicalToolName(name: string): name is CanonicalToolName {
  return (CANONICAL_TOOL_NAMES as readonly string[]).includes(name);
}

async function withToolCallClaimLock<T>(operation: () => Promise<T>): Promise<T> {
  const previous = toolCallClaimLock;
  let release: () => void = () => undefined;
  toolCallClaimLock = new Promise<void>((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    return await operation();
  } finally {
    release();
  }
}

async function claimPersistedToolCall(identity: ToolCallIdentity): Promise<ToolCallClaimOutcome> {
  return withToolCallClaimLock(async () => {
    const stored = await chrome.storage.local.get(PROCESSED_TOOL_CALLS_STORAGE_KEY);
    const registry = parseProcessedToolCallRegistry(stored[PROCESSED_TOOL_CALLS_STORAGE_KEY]);
    const outcome = claimToolCallExecution(registry, identity);
    if (outcome.kind === "claimed") {
      await chrome.storage.local.set({
        [PROCESSED_TOOL_CALLS_STORAGE_KEY]: outcome.registry,
      });
    }
    return outcome;
  });
}

function requestToolCallIdentity(
  request: Extract<BridgeRequest, { type: "bridge.tools.call" }>,
): ToolCallIdentity | null {
  const hasCallId = request.callId !== undefined;
  const hasConversationId = request.conversationId !== undefined;
  if (!hasCallId && !hasConversationId) return null;
  if (
    !hasCallId ||
    !hasConversationId ||
    typeof request.callId !== "string" ||
    typeof request.conversationId !== "string"
  ) {
    throw new RpcRequestError(
      "Chat tool calls require both conversation_id and call_id.",
      "invalid_tool_call_identity",
    );
  }
  try {
    return createToolCallIdentity(
      request.conversationId,
      request.callId,
      request.name,
      request.arguments,
    );
  } catch (error) {
    throw new RpcRequestError(
      error instanceof Error ? error.message : "Invalid PLwC tool call identity.",
      "invalid_tool_call_identity",
    );
  }
}

async function getSettings(): Promise<BridgeSettings> {
  const stored = await chrome.storage.local.get([
    "autoConfirmSandbox",
    "autoConfirmWrites",
    "autoExecuteDelay",
    "autoInsertDelay",
    "autoSubmitDelay",
    "autoSubmitResults",
    "bridgeSettingsRevision",
    "composerBusyTimeout",
    "readOnlyAutoRun",
    "renderChatCards",
  ]);
  const isCurrent = stored.bridgeSettingsRevision === SETTINGS_REVISION;
  const settings: BridgeSettings = {
    autoConfirmSandbox: stored.autoConfirmSandbox === true,
    autoConfirmWrites: stored.autoConfirmWrites === true,
    autoExecuteDelay: normalizeAutomationDelay(stored.autoExecuteDelay),
    autoInsertDelay: normalizeAutomationDelay(stored.autoInsertDelay),
    autoSubmitDelay: normalizeAutomationDelay(stored.autoSubmitDelay),
    autoSubmitResults: stored.autoSubmitResults !== false,
    composerBusyTimeout: normalizeAutomationDelay(stored.composerBusyTimeout, 60),
    readOnlyAutoRun: stored.readOnlyAutoRun !== false,
    renderChatCards: stored.renderChatCards !== false,
  };
  if (!isCurrent) {
    await chrome.storage.local.set({ ...settings, bridgeSettingsRevision: SETTINGS_REVISION });
  }
  return settings;
}

async function loadToolSet(): Promise<ToolListResponse> {
  await verifyConnectedBuildIdentity();
  await applySavedGatewaySettings();
  const payload = await transport.request("tools/list", {});
  currentToolSet = validateToolSet(payload);
  return { tools: currentToolSet.tools, validation: currentToolSet };
}

async function verifyConnectedBuildIdentity(): Promise<BuildIdentity> {
  if (currentBuildIdentity !== null && currentBuildIdentityValidation?.valid === true) {
    return currentBuildIdentity;
  }
  let buildIdentity: BuildIdentity;
  try {
    buildIdentity = parseBuildIdentity(await transport.request("build/identity", {}));
  } catch (error) {
    currentBuildIdentity = null;
    currentBuildIdentityValidation = null;
    throw new RpcRequestError(
      error instanceof Error ? error.message : "Bridge returned an invalid build identity.",
      "build_identity_invalid",
    );
  }
  const validation = validateBuildIdentity(buildIdentity);
  currentBuildIdentity = buildIdentity;
  currentBuildIdentityValidation = validation;
  if (!validation.valid) {
    transport.disconnect();
    throw new RpcRequestError(
      `Bridge build identity mismatch: expected ${validation.expectedBuildId}, received ${validation.actualBuildId}.`,
      "build_identity_mismatch",
    );
  }
  return buildIdentity;
}

async function savedGatewaySettings(): Promise<GatewaySettingsUpdate | null> {
  const stored = await chrome.storage.local.get(GATEWAY_SETTINGS_STORAGE_KEY);
  const value = stored[GATEWAY_SETTINGS_STORAGE_KEY];
  if (value === undefined) return null;
  try {
    return parseGatewaySettingsUpdate(value);
  } catch {
    await chrome.storage.local.remove(GATEWAY_SETTINGS_STORAGE_KEY);
    return null;
  }
}

async function applySavedGatewaySettings(): Promise<GatewaySettingsSnapshot | null> {
  const settings = await savedGatewaySettings();
  if (settings === null) return null;
  return parseGatewaySettings(await transport.request("settings/update", { settings }));
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function requestNativeBridgeStart(): Promise<LauncherStatus> {
  if (typeof chrome.runtime.sendNativeMessage !== "function") {
    launcherStatus = localizedLauncherStatus({
      code: "native_launcher_unavailable",
      message: "",
      state: "unavailable",
    });
    return Promise.reject(new RpcRequestError(launcherStatus.message, "native_launcher_unavailable"));
  }

  launcherStatus = localizedLauncherStatus({
    code: "starting",
    message: "",
    state: "starting",
  });
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(
      NATIVE_LAUNCHER_HOST,
      {
        buildId: EXTENSION_BUILD_IDENTITY.buildId,
        command: "start",
        endpoint: BRIDGE_ENDPOINT,
        extensionVersion: EXTENSION_BUILD_IDENTITY.components.browserExtension,
        language: uiLanguage(),
        port: NATIVE_LAUNCHER_PORT,
      },
      (response: unknown) => {
        const runtimeError = chrome.runtime.lastError;
        if (runtimeError) {
          launcherStatus = localizedLauncherStatus({
            code: "native_host_missing",
            message: "",
            state: "unavailable",
          });
          reject(new RpcRequestError(launcherStatus.message, "native_launcher_unavailable"));
          return;
        }
        try {
          launcherStatus = localizedLauncherStatus(parseNativeLauncherResponse(response));
          resolve(launcherStatus);
        } catch (error) {
          launcherStatus = localizedLauncherStatus(error instanceof NativeLauncherError ? error.status : {
            code: "native_launcher_failed",
            message: error instanceof Error ? error.message : "",
            state: "failed",
          });
          reject(error);
        }
      },
    );
  });
}

async function connectBridge(autoStart: boolean): Promise<void> {
  try {
    await transport.connect();
    await verifyConnectedBuildIdentity();
    return;
  } catch (error) {
    if (!autoStart || !isRecoverableConnectionError(error)) {
      throw error;
    }
  }

  try {
    launcherStatus = await connectAfterNativeStart(
      async () => {
        await transport.connect();
        await verifyConnectedBuildIdentity();
      },
      requestNativeBridgeStart,
      wait,
    );
  } catch (error) {
    if (error instanceof RpcRequestError) {
      launcherStatus = localizedLauncherStatus({
        ...launcherStatus,
        code: error.code,
        message: "",
        state: error.code === "native_launcher_unavailable" ? "unavailable" : "failed",
      });
    }
    throw error;
  }
}

async function handleRequest(request: BridgeRequest): Promise<unknown> {
  switch (request.type) {
    case "bridge.connect":
      await connectBridge(request.autoStart === true);
      return status();
    case "bridge.status":
      return status();
    case "bridge.tools.list":
      return loadToolSet();
    case "bridge.tools.call": {
      if (!currentToolSet?.valid) await loadToolSet();
      if (!currentToolSet?.valid) {
        throw new RpcRequestError("Tool execution is locked until the exact eight-tool contract is loaded.", "contract_locked");
      }
      if (!isCanonicalToolName(request.name) || !currentToolSet.tools.some((tool) => tool.name === request.name)) {
        throw new RpcRequestError("Unknown or unadvertised PLwC tool.", "tool_locked");
      }
      const policy = decidePolicy(request.name, request.arguments);
      if (policy.requiresConfirmation && !request.confirmed) {
        throw new RpcRequestError(policy.reason, "confirmation_required");
      }
      const forwardedArguments = withConfirmedToolArguments(request.name, request.arguments, request.confirmed);
      const identity = requestToolCallIdentity(request);
      if (identity) {
        const claim = await claimPersistedToolCall(identity);
        if (claim.kind === "duplicate") {
          throw new RpcRequestError(
            `PLwC tool call ${JSON.stringify(identity.callId)} was already processed for this conversation.`,
            "duplicate_tool_call",
          );
        }
        if (claim.kind === "conflict") {
          throw new RpcRequestError(
            `PLwC tool call ${JSON.stringify(identity.callId)} conflicts with the payload already claimed for this conversation.`,
            "tool_call_conflict",
          );
        }
        if (claim.kind === "capacity") {
          throw new RpcRequestError(
            "The persistent PLwC tool call registry is full; execution is locked to preserve exactly-once behavior.",
            "tool_call_registry_full",
          );
        }
      }
      const rawResult = await transport.request("tools/call", {
        arguments: forwardedArguments,
        name: request.name,
      });
      const { isError, result } = normalizeToolResult(rawResult);
      return { isError, policy, result } satisfies ToolCallResponse;
    }
    case "bridge.gateway.settings.get": {
      const applied = await applySavedGatewaySettings();
      return applied ?? parseGatewaySettings(await transport.request("settings/get", {}));
    }
    case "bridge.gateway.settings.update": {
      const settings = parseGatewaySettingsUpdate(request.settings);
      const updated = parseGatewaySettings(await transport.request("settings/update", { settings }));
      await chrome.storage.local.set({ [GATEWAY_SETTINGS_STORAGE_KEY]: settings });
      currentToolSet = null;
      return updated;
    }
    case "bridge.gateway.settings.reset": {
      const reset = parseGatewaySettings(await transport.request("settings/reset", {}));
      await chrome.storage.local.remove(GATEWAY_SETTINGS_STORAGE_KEY);
      currentToolSet = null;
      return reset;
    }
    case "bridge.settings.get":
      return getSettings();
    case "bridge.settings.update": {
      const settings = await getSettings();
      const next: BridgeSettings = {
        autoConfirmSandbox:
          typeof request.settings.autoConfirmSandbox === "boolean"
            ? request.settings.autoConfirmSandbox
            : settings.autoConfirmSandbox,
        autoConfirmWrites:
          typeof request.settings.autoConfirmWrites === "boolean"
            ? request.settings.autoConfirmWrites
            : settings.autoConfirmWrites,
        autoExecuteDelay: normalizeAutomationDelay(request.settings.autoExecuteDelay, settings.autoExecuteDelay),
        autoInsertDelay: normalizeAutomationDelay(request.settings.autoInsertDelay, settings.autoInsertDelay),
        autoSubmitDelay: normalizeAutomationDelay(request.settings.autoSubmitDelay, settings.autoSubmitDelay),
        autoSubmitResults:
          typeof request.settings.autoSubmitResults === "boolean"
            ? request.settings.autoSubmitResults
            : settings.autoSubmitResults,
        composerBusyTimeout: normalizeAutomationDelay(
          request.settings.composerBusyTimeout,
          settings.composerBusyTimeout,
        ),
        readOnlyAutoRun:
          typeof request.settings.readOnlyAutoRun === "boolean"
            ? request.settings.readOnlyAutoRun
            : settings.readOnlyAutoRun,
        renderChatCards:
          typeof request.settings.renderChatCards === "boolean"
            ? request.settings.renderChatCards
            : settings.renderChatCards,
      };
      await chrome.storage.local.set({ ...next, bridgeSettingsRevision: SETTINGS_REVISION });
      return next;
    }
  }
}

chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
  if (typeof message !== "object" || message === null || !("type" in message)) return false;
  const request = message as BridgeRequest;
  if (typeof request.type !== "string" || !request.type.startsWith("bridge.")) return false;

  void handleRequest(request)
    .then((value) => sendResponse({ ok: true, value } satisfies BridgeResponse))
    .catch((error: unknown) => {
      const rpcError = error instanceof RpcRequestError ? error : null;
      sendResponse({
        code: rpcError?.code,
        error: error instanceof Error ? error.message : "Unexpected PLwC Chat Bridge error.",
        ok: false,
      } satisfies BridgeResponse);
    });
  return true;
});

transport.onStateChange(() => {
  if (transport.state !== "connected") {
    currentBuildIdentity = null;
    currentToolSet = null;
  }
  void chrome.runtime.sendMessage({ type: "bridge.status.changed", value: status() }).catch(() => undefined);
});

setInterval(() => {
  if (transport.state !== "connected") return;
  void transport.request("ping", {}).catch(() => undefined);
}, HEARTBEAT_INTERVAL_MS);

void getSettings().then((settings) => chrome.storage.local.set(settings));
