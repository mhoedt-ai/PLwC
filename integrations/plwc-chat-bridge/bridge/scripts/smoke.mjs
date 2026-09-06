import assert from "node:assert/strict";
import { resolve } from "node:path";
import process from "node:process";
import { WebSocket } from "ws";

import { loadConfig } from "../dist/src/config.js";
import { CANONICAL_TOOL_NAMES } from "../dist/src/contract.js";
import { GatewayClientSession } from "../dist/src/gateway-session.js";
import { LoopbackBridgeServer } from "../dist/src/server.js";

const configIndex = process.argv.indexOf("--config");
const configArgument = configIndex >= 0 ? process.argv[configIndex + 1] : undefined;
assert.ok(configArgument, "Pass --config <path> to the smoke script.");

const configPath = resolve(configArgument);
const config = await loadConfig(configPath);
const session = new GatewayClientSession(config.gateway);
const bridge = new LoopbackBridgeServer(config.bridge, session);
const endpoint = `ws://${config.bridge.host}:${config.bridge.port}${config.bridge.path}`;
const origin = `chrome-extension://${"a".repeat(32)}`;
let socket;

function connect(url) {
  return new Promise((resolveConnection, reject) => {
    const candidate = new WebSocket(url, { origin });
    candidate.once("open", () => resolveConnection(candidate));
    candidate.once("error", reject);
  });
}

function request(client, id, method, params) {
  return new Promise((resolveResponse, reject) => {
    const timeout = setTimeout(() => reject(new Error(`${method} smoke request timed out.`)), 20_000);
    client.once("message", (data) => {
      clearTimeout(timeout);
      const response = JSON.parse(data.toString("utf8"));
      if (response.error) reject(new Error(response.error.message || `${method} failed.`));
      else resolveResponse(response.result);
    });
    client.send(JSON.stringify({ jsonrpc: "2.0", id, method, ...(params ? { params } : {}) }));
  });
}

try {
  await bridge.start();
  socket = await connect(endpoint);
  const listed = await request(socket, 1, "tools/list");
  assert.deepEqual(
    listed.tools.map((tool) => tool.name),
    CANONICAL_TOOL_NAMES,
  );
  const status = await request(socket, 2, "tools/call", {
    name: "plwc_status",
    arguments: { scope: "runtime" },
  });
  assert.ok(Array.isArray(status.content), "plwc_status must return MCP content.");
  assert.notEqual(status.isError, true, "plwc_status returned an MCP error result.");
  process.stdout.write("PLwC Chat Bridge smoke passed: 8 tools and one runtime status result.\n");
} finally {
  socket?.close();
  await bridge.stop();
}
