import { WebSocket, WebSocketServer } from "ws";

import { BUILD_IDENTITY } from "./build-identity.js";
import type { BridgeConfig } from "./config.js";
import { ToolContractError } from "./contract.js";
import {
  APPROVED_EXTENSION_WEB_SOCKET_ORIGINS,
  EXTENSION_IDENTITY_CONTRACT,
} from "./extension-identity.js";
import { parseGatewaySettingsUpdate, type BridgeSession } from "./gateway-session.js";
import { failure, parseRequest, RpcFault, success, type JsonRpcRequest } from "./rpc.js";

const MAX_PAYLOAD_BYTES = 1024 * 1024;
export const TOOL_CALL_HEARTBEAT_METHOD = "bridge/heartbeat";
const TOOL_CALL_HEARTBEAT_INTERVAL_MS = 5_000;

if (EXTENSION_IDENTITY_CONTRACT.releaseVersion !== BUILD_IDENTITY.releaseVersion) {
  throw new Error("PLwC extension identity and common build versions do not match.");
}

function requireEmptyParams(request: JsonRpcRequest): void {
  if (request.params !== undefined && Object.keys(request.params).length > 0) {
    throw new RpcFault(-32602, "This method does not accept parameters.");
  }
}

function toolCallParams(request: JsonRpcRequest): { name: string; args: Record<string, unknown> } {
  const params = request.params;
  if (params === undefined || typeof params.name !== "string") {
    throw new RpcFault(-32602, "tools/call requires a tool name.");
  }
  const args = params.arguments ?? {};
  if (typeof args !== "object" || args === null || Array.isArray(args)) {
    throw new RpcFault(-32602, "tools/call arguments must be an object.");
  }
  return { name: params.name, args: args as Record<string, unknown> };
}

function settingsUpdateParams(request: JsonRpcRequest) {
  try {
    return parseGatewaySettingsUpdate(request.params?.settings);
  } catch {
    throw new RpcFault(-32602, "Invalid PLwC gateway settings.");
  }
}

function publicFault(error: unknown): RpcFault {
  if (error instanceof RpcFault) {
    return error;
  }
  if (error instanceof ToolContractError) {
    return new RpcFault(-32010, "PLwC gateway tool contract mismatch.");
  }
  return new RpcFault(-32603, "Bridge request failed.");
}

export class LoopbackBridgeServer {
  private webSocketServer: WebSocketServer | undefined;
  private stopping = false;

  constructor(
    private readonly config: BridgeConfig["bridge"],
    private readonly session: BridgeSession,
    private readonly toolCallHeartbeatIntervalMs = TOOL_CALL_HEARTBEAT_INTERVAL_MS,
  ) {}

  async start(): Promise<void> {
    if (this.webSocketServer !== undefined) {
      throw new Error("Bridge server has already been started.");
    }

    await this.session.start();
    const server = new WebSocketServer({
      host: this.config.host,
      port: this.config.port,
      path: this.config.path,
      maxPayload: MAX_PAYLOAD_BYTES,
      perMessageDeflate: false,
      verifyClient: ({ origin }, done) => {
        done(
          origin !== undefined && APPROVED_EXTENSION_WEB_SOCKET_ORIGINS.has(origin),
          403,
          "Approved PLwC extension origin required",
        );
      },
    });

    try {
      await new Promise<void>((resolve, reject) => {
        const onListening = (): void => {
          server.off("error", onError);
          resolve();
        };
        const onError = (): void => {
          server.off("listening", onListening);
          reject(new Error("The loopback listener could not be started."));
        };
        server.once("listening", onListening);
        server.once("error", onError);
      });
    } catch (error) {
      await this.session.close();
      throw error;
    }

    this.webSocketServer = server;
    server.on("connection", (socket) => {
      socket.on("message", (data, isBinary) => {
        void this.handleMessage(socket, isBinary ? undefined : data.toString("utf8"));
      });
    });
  }

  async stop(): Promise<void> {
    if (this.stopping) {
      return;
    }
    this.stopping = true;

    const server = this.webSocketServer;
    this.webSocketServer = undefined;
    if (server !== undefined) {
      for (const socket of server.clients) {
        socket.terminate();
      }
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
    await this.session.close();
  }

  private async handleMessage(socket: WebSocket, source: string | undefined): Promise<void> {
    let request: JsonRpcRequest | undefined;
    let heartbeat: ReturnType<typeof setInterval> | undefined;
    try {
      if (source === undefined) {
        throw new RpcFault(-32600, "Binary requests are not supported.");
      }
      request = parseRequest(source);
      if (request.method === "tools/call") {
        const startedAt = Date.now();
        heartbeat = setInterval(() => {
          this.send(socket, JSON.stringify({
            jsonrpc: "2.0",
            method: TOOL_CALL_HEARTBEAT_METHOD,
            params: {
              elapsed_ms: Date.now() - startedAt,
              request_id: request!.id,
            },
          }));
        }, this.toolCallHeartbeatIntervalMs);
      }
      const result = await this.dispatch(request);
      this.send(socket, success(request.id, result));
    } catch (error) {
      const fault = publicFault(error);
      this.send(socket, failure(request?.id ?? null, { code: fault.code, message: fault.message }));
    } finally {
      if (heartbeat !== undefined) clearInterval(heartbeat);
    }
  }

  private async dispatch(request: JsonRpcRequest): Promise<unknown> {
    switch (request.method) {
      case "build/identity":
        requireEmptyParams(request);
        return BUILD_IDENTITY;
      case "ping":
        requireEmptyParams(request);
        return { ok: true };
      case "tools/list":
        requireEmptyParams(request);
        return { tools: await this.session.listTools() };
      case "settings/get":
        requireEmptyParams(request);
        return this.session.settings();
      case "settings/update":
        return this.session.updateSettings(settingsUpdateParams(request));
      case "settings/reset":
        requireEmptyParams(request);
        return this.session.resetSettings();
      case "tools/call": {
        const { name, args } = toolCallParams(request);
        return this.session.callTool(name, args);
      }
      default:
        throw new RpcFault(-32601, "Method not found.");
    }
  }

  private send(socket: WebSocket, payload: string): void {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(payload);
    }
  }
}
