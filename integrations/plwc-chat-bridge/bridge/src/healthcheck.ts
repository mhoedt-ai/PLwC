import { WebSocket } from "ws";

import {
  BUILD_IDENTITY,
  parseBuildIdentity,
  type BuildIdentity,
} from "./build-identity.js";
import { assertCanonicalTools } from "./contract.js";

export interface BridgeHealth {
  buildIdentity: BuildIdentity;
  endpoint: string;
  toolCount: number;
}

interface JsonRpcResponse {
  error?: { message?: unknown };
  id?: unknown;
  result?: unknown;
}

function toolList(value: unknown): unknown[] {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("PLwC Chat Bridge returned an invalid tools/list result.");
  }
  const tools = (value as { tools?: unknown }).tools;
  if (!Array.isArray(tools)) {
    throw new Error("PLwC Chat Bridge returned an invalid tools/list result.");
  }
  return tools;
}

export async function verifyBridgeHealth(
  endpoint: string,
  origin: string,
  timeoutMs = 4_000,
  expectedBuildId = BUILD_IDENTITY.buildId,
): Promise<BridgeHealth> {
  return new Promise<BridgeHealth>((resolve, reject) => {
    const socket = new WebSocket(endpoint, {
      handshakeTimeout: timeoutMs,
      origin,
      perMessageDeflate: false,
    });
    let settled = false;
    let verifiedBuildIdentity: BuildIdentity | undefined;
    const timeout = setTimeout(() => finish(new Error("PLwC Chat Bridge health check timed out.")), timeoutMs);

    const finish = (error?: Error, health?: BridgeHealth): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      socket.removeAllListeners();
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.terminate();
      }
      if (error !== undefined) reject(error);
      else resolve(health!);
    };

    socket.once("error", () => finish(new Error("PLwC Chat Bridge WebSocket endpoint is not reachable.")));
    socket.once("open", () => {
      socket.send(JSON.stringify({ jsonrpc: "2.0", id: 1, method: "build/identity" }));
    });
    socket.on("message", (data, isBinary) => {
      if (isBinary) {
        finish(new Error("PLwC Chat Bridge returned a binary health response."));
        return;
      }

      let response: JsonRpcResponse;
      try {
        response = JSON.parse(data.toString("utf8")) as JsonRpcResponse;
      } catch {
        finish(new Error("PLwC Chat Bridge returned invalid health JSON."));
        return;
      }
      if (response.id !== 1 && response.id !== 2) return;
      if (response.error !== undefined) {
        const message =
          typeof response.error.message === "string"
            ? response.error.message
            : "PLwC Chat Bridge rejected the health request.";
        finish(new Error(message));
        return;
      }

      if (response.id === 1) {
        try {
          const buildIdentity = parseBuildIdentity(response.result);
          if (buildIdentity.buildId !== expectedBuildId) {
            throw new Error(
              `PLwC Chat Bridge build identity mismatch: expected ${expectedBuildId}, received ${buildIdentity.buildId}.`,
            );
          }
          verifiedBuildIdentity = buildIdentity;
          socket.send(JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }));
        } catch (error) {
          finish(error instanceof Error ? error : new Error("PLwC Chat Bridge build identity is not ready."));
        }
        return;
      }
      if (response.id === 2) {
        try {
          const tools = toolList(response.result);
          assertCanonicalTools(tools as Parameters<typeof assertCanonicalTools>[0]);
          if (verifiedBuildIdentity === undefined) {
            throw new Error("PLwC Chat Bridge build identity was not verified.");
          }
          finish(undefined, { buildIdentity: verifiedBuildIdentity, endpoint, toolCount: tools.length });
        } catch (error) {
          finish(error instanceof Error ? error : new Error("PLwC Chat Bridge tool contract is not ready."));
        }
      }
    });
  });
}
