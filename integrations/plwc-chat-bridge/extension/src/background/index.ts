import { JsonRpcWebSocketClient, RpcRequestError } from "./transport";
import {
  BRIDGE_ENDPOINT,
  CANONICAL_TOOL_NAMES,
  type CanonicalToolName,
  type JsonObject,
  validateToolSet,
} from "../shared/contracts";
import type {
  BridgeRequest,
  BridgeResponse,
  BridgeSettings,
  BridgeStatus,
  GatewaySettingsSnapshot,
  GatewaySettingsUpdate,
  ToolCallResponse,
  ToolListResponse,
} from "../shared/messages";
import {
  normalizeAutomationDelay,
  parseGatewaySettings,
  parseGatewaySettingsUpdate,
} from "../shared/messages";
import { decidePolicy, withConfirmedToolArguments } from "../shared/policy";
import { normalizeToolResult } from "../shared/tool-result";

const transport = new JsonRpcWebSocketClient(BRIDGE_ENDPOINT);
const HEARTBEAT_INTERVAL_MS = 20_000;
const SETTINGS_REVISION = 4;
const GATEWAY_SETTINGS_STORAGE_KEY = "gatewaySettingsOverrides";
let currentToolSet: ReturnType<typeof validateToolSet> | null = null;

function status(): BridgeStatus {
  return {
    connection: transport.state,
    endpoint: BRIDGE_ENDPOINT,
    lastError: transport.lastError,
    pendingRequests: transport.pendingCount,
    toolSet: currentToolSet,
  };
}

function isCanonicalToolName(name: string): name is CanonicalToolName {
  return (CANONICAL_TOOL_NAMES as readonly string[]).includes(name);
}

async function getSettings(): Promise<BridgeSettings> {
  const stored = await chrome.storage.local.get([
    "autoConfirmWrites",
    "autoExecuteDelay",
    "autoInsertDelay",
    "autoSubmitDelay",
    "autoSubmitResults",
    "bridgeSettingsRevision",
    "readOnlyAutoRun",
    "renderChatCards",
  ]);
  const isCurrent = stored.bridgeSettingsRevision === SETTINGS_REVISION;
  const settings: BridgeSettings = {
    autoConfirmWrites: stored.autoConfirmWrites === true,
    autoExecuteDelay: normalizeAutomationDelay(stored.autoExecuteDelay),
    autoInsertDelay: normalizeAutomationDelay(stored.autoInsertDelay),
    autoSubmitDelay: normalizeAutomationDelay(stored.autoSubmitDelay),
    autoSubmitResults: stored.autoSubmitResults !== false,
    readOnlyAutoRun: stored.readOnlyAutoRun !== false,
    renderChatCards: stored.renderChatCards !== false,
  };
  if (!isCurrent) {
    await chrome.storage.local.set({ ...settings, bridgeSettingsRevision: SETTINGS_REVISION });
  }
  return settings;
}

async function loadToolSet(): Promise<ToolListResponse> {
  await applySavedGatewaySettings();
  const payload = await transport.request("tools/list", {});
  currentToolSet = validateToolSet(payload);
  return { tools: currentToolSet.tools, validation: currentToolSet };
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

async function handleRequest(request: BridgeRequest): Promise<unknown> {
  switch (request.type) {
    case "bridge.connect":
      await transport.connect();
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
  void chrome.runtime.sendMessage({ type: "bridge.status.changed", value: status() }).catch(() => undefined);
});

setInterval(() => {
  if (transport.state !== "connected") return;
  void transport.request("ping", {}).catch(() => undefined);
}, HEARTBEAT_INTERVAL_MS);

void getSettings().then((settings) => chrome.storage.local.set(settings));
