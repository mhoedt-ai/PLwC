import assert from "node:assert/strict";
import { createServer } from "node:net";
import test from "node:test";
import { WebSocket } from "ws";
import type { CallToolResult, Tool } from "@modelcontextprotocol/sdk/types.js";

import { CANONICAL_TOOL_NAMES } from "../src/contract.js";
import type { BridgeSession } from "../src/gateway-session.js";
import { LoopbackBridgeServer } from "../src/server.js";

const tools: Tool[] = CANONICAL_TOOL_NAMES.map((name) => ({ name, inputSchema: { type: "object" } }));

class FakeSession implements BridgeSession {
  starts = 0;
  calls = 0;

  async start(): Promise<void> {
    this.starts += 1;
  }

  async listTools(): Promise<Tool[]> {
    return tools;
  }

  async callTool(): Promise<CallToolResult> {
    this.calls += 1;
    return { isError: true, content: [{ type: "text", text: "policy denied" }] };
  }

  async close(): Promise<void> {}
}

async function freePort(): Promise<number> {
  const probe = createServer();
  await new Promise<void>((resolve) => probe.listen(0, "127.0.0.1", resolve));
  const address = probe.address();
  assert.ok(address && typeof address !== "string");
  const port = address.port;
  await new Promise<void>((resolve, reject) => probe.close((error) => (error ? reject(error) : resolve())));
  return port;
}

const EXTENSION_ORIGIN = `chrome-extension://${"a".repeat(32)}`;

async function connect(url: string): Promise<WebSocket> {
  const socket = new WebSocket(url, { origin: EXTENSION_ORIGIN });
  await new Promise<void>((resolve, reject) => {
    socket.once("open", resolve);
    socket.once("error", reject);
  });
  return socket;
}

async function request(socket: WebSocket, value: unknown): Promise<Record<string, unknown>> {
  const response = new Promise<Record<string, unknown>>((resolve) => {
    socket.once("message", (data) => resolve(JSON.parse(data.toString("utf8")) as Record<string, unknown>));
  });
  socket.send(JSON.stringify(value));
  return response;
}

test("serves ping and forwards a mutating call exactly once", async () => {
  const port = await freePort();
  const session = new FakeSession();
  const bridge = new LoopbackBridgeServer({ host: "127.0.0.1", port, path: "/message" }, session);
  await bridge.start();
  const socket = await connect(`ws://127.0.0.1:${port}/message`);

  try {
    const pong = await request(socket, { jsonrpc: "2.0", id: 1, method: "ping" });
    assert.deepEqual(pong, { jsonrpc: "2.0", id: 1, result: { ok: true } });

    const result = await request(socket, {
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: { name: "plwc_governor", arguments: { operation: "apply" } },
    });
    assert.equal((result.result as CallToolResult).isError, true);
    assert.equal(session.starts, 1);
    assert.equal(session.calls, 1);
  } finally {
    socket.close();
    await bridge.stop();
  }
});

test("rejects ordinary web-page origins", async () => {
  const port = await freePort();
  const session = new FakeSession();
  const bridge = new LoopbackBridgeServer({ host: "127.0.0.1", port, path: "/message" }, session);
  await bridge.start();

  try {
    await assert.rejects(
      new Promise<void>((resolve, reject) => {
        const socket = new WebSocket(`ws://127.0.0.1:${port}/message`, { origin: "https://chatgpt.com" });
        socket.once("open", resolve);
        socket.once("error", reject);
      }),
    );
  } finally {
    await bridge.stop();
  }
});
