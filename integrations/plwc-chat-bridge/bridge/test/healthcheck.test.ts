import assert from "node:assert/strict";
import { createServer } from "node:net";
import test from "node:test";
import { WebSocketServer } from "ws";
import type { Tool } from "@modelcontextprotocol/sdk/types.js";

import { BUILD_IDENTITY, type BuildIdentity } from "../src/build-identity.js";
import { CANONICAL_TOOL_NAMES } from "../src/contract.js";
import { verifyBridgeHealth } from "../src/healthcheck.js";

const origin = `chrome-extension://${"a".repeat(32)}`;
const canonicalTools: Tool[] = CANONICAL_TOOL_NAMES.map((name) => ({
  inputSchema: {
    type: "object",
    ...(name === "plwc_status"
      ? { properties: { profile_name: { default: "", type: "string" }, scope: { default: "", type: "string" } } }
      : {}),
  },
  name,
}));

async function freePort(): Promise<number> {
  const probe = createServer();
  await new Promise<void>((resolve) => probe.listen(0, "127.0.0.1", resolve));
  const address = probe.address();
  assert.ok(address && typeof address !== "string");
  await new Promise<void>((resolve, reject) => probe.close((error) => (error ? reject(error) : resolve())));
  return address.port;
}

async function healthServer(
  tools: Tool[],
  buildIdentity: BuildIdentity = BUILD_IDENTITY,
): Promise<{ close: () => Promise<void>; endpoint: string }> {
  const port = await freePort();
  const server = new WebSocketServer({
    host: "127.0.0.1",
    path: "/message",
    port,
    verifyClient: ({ origin: requestOrigin }, done) => done(requestOrigin === origin),
  });
  await new Promise<void>((resolve, reject) => {
    server.once("listening", resolve);
    server.once("error", reject);
  });
  server.on("connection", (socket) => {
    socket.on("message", (data) => {
      const request = JSON.parse(data.toString("utf8")) as { id: number; method: string };
      const result = request.method === "build/identity" ? buildIdentity : { tools };
      socket.send(JSON.stringify({ jsonrpc: "2.0", id: request.id, result }));
    });
  });
  return {
    close: async () => {
      for (const socket of server.clients) socket.terminate();
      await new Promise<void>((resolve) => server.close(() => resolve()));
    },
    endpoint: `ws://127.0.0.1:${port}/message`,
  };
}

test("reports ready only for the exact eight-tool WebSocket contract", async () => {
  const server = await healthServer(canonicalTools);
  try {
    assert.deepEqual(await verifyBridgeHealth(server.endpoint, origin), {
      buildIdentity: BUILD_IDENTITY,
      endpoint: server.endpoint,
      toolCount: 8,
    });
  } finally {
    await server.close();
  }
});

test("rejects a healthy bridge carrying a different build identity", async () => {
  const server = await healthServer(canonicalTools, {
    ...BUILD_IDENTITY,
    buildId: "plwc-chat-bridge@0.2.0-rc19.dev17",
    releaseVersion: "0.2.0-rc19.dev17",
    installer: {
      ...BUILD_IDENTITY.installer,
      directoryName: "chat-bridge-0.2.0-rc19.dev17",
    },
  });
  try {
    await assert.rejects(verifyBridgeHealth(server.endpoint, origin), /build identity mismatch/i);
  } finally {
    await server.close();
  }
});

test("rejects a listening WebSocket with an incomplete tool contract", async () => {
  const server = await healthServer(canonicalTools.slice(0, 7));
  try {
    await assert.rejects(verifyBridgeHealth(server.endpoint, origin), /tool contract/i);
  } finally {
    await server.close();
  }
});

test("rejects an unrelated or unavailable loopback port", async () => {
  const port = await freePort();
  await assert.rejects(
    verifyBridgeHealth(`ws://127.0.0.1:${port}/message`, origin, 250),
    /not reachable|timed out/i,
  );
});
