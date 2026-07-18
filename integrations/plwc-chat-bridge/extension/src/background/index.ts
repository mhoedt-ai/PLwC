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
  ToolCallResponse,
  ToolListResponse,
} from "../shared/messages";
import { parseGatewaySettings } from "../shared/messages";
import { decidePolicy } from "../shared/policy";
import { normalizeToolResult } from "../shared/tool-result";

const transport = new JsonRpcWebSocketClient(BRIDGE_ENDPOINT);
const HEARTBEAT_INTERVAL_MS = 20_000;
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
  const stored = await chrome.storage.local.get("readOnlyAutoRun");
  return { readOnlyAutoRun: stored.readOnlyAutoRun === true };
}

async function loadToolSet(): Promise<ToolListResponse> {
  const payload = await transport.request("tools/list", {});
  currentToolSet = validateToolSet(payload);
  return { tools: currentToolSet.tools, validation: currentToolSet };
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
      const rawResult = await transport.request("tools/call", {
        arguments: request.arguments,
        name: request.name,
      });
      const { isError, result } = normalizeToolResult(rawResult);
      return { isError, policy, result } satisfies ToolCallResponse;
    }
    case "bridge.gateway.settings.get":
      return parseGatewaySettings(await transport.request("settings/get", {}));
    case "bridge.settings.get":
      return getSettings();
    case "bridge.settings.update": {
      const settings = await getSettings();
      const next: BridgeSettings = {
        readOnlyAutoRun:
          typeof request.settings.readOnlyAutoRun === "boolean"
            ? request.settings.readOnlyAutoRun
            : settings.readOnlyAutoRun,
      };
      await chrome.storage.local.set(next);
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
