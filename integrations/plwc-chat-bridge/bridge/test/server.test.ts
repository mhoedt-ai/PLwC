import assert from "node:assert/strict";
import { createServer } from "node:net";
import test from "node:test";
import { WebSocket } from "ws";
import type { CallToolResult, Tool } from "@modelcontextprotocol/sdk/types.js";

import { CANONICAL_TOOL_NAMES } from "../src/contract.js";
import {
  gatewaySettingsFromEnvironment,
  parseGatewaySettingsUpdate,
  type BridgeSession,
  type GatewaySettingsSnapshot,
  type GatewaySettingsUpdate,
} from "../src/gateway-session.js";
import { LoopbackBridgeServer } from "../src/server.js";

const tools: Tool[] = CANONICAL_TOOL_NAMES.map((name) => ({ name, inputSchema: { type: "object" } }));

class FakeSession implements BridgeSession {
  starts = 0;
  calls = 0;
  updates = 0;
  resets = 0;
  private currentSettings = importedSettings();

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

  settings(): GatewaySettingsSnapshot {
    return { ...this.currentSettings };
  }

  async updateSettings(settings: GatewaySettingsUpdate): Promise<GatewaySettingsSnapshot> {
    this.updates += 1;
    this.currentSettings = { source: "PLwC Chat Bridge saved settings", ...settings };
    return this.settings();
  }

  async resetSettings(): Promise<GatewaySettingsSnapshot> {
    this.resets += 1;
    this.currentSettings = importedSettings();
    return this.settings();
  }

  async close(): Promise<void> {}
}

function importedSettings(): GatewaySettingsSnapshot {
  return gatewaySettingsFromEnvironment({
    PLWC_ACTIVE_PROFILE_NAME: "WasIstDas",
    PLWC_CHAT_BRIDGE_SETTINGS_SOURCE: "Claude PLwC configuration",
    PLWC_MEMORY_WRITE_THRESHOLD: "2",
    PLWC_PERSONA_LAYER_DISABLED: "true",
    PLWC_PERSONA_WRITE_THRESHOLD: "3",
    PLWC_QDRANT_ENABLED: "true",
    PLWC_TEMPERAMENT_WRITE_THRESHOLD: "6",
    PLWC_WORKSPACE_ROOT: "C:\\Users\\USER\\Claude_Arbeitsumgebung",
  });
}

const editableSettings: GatewaySettingsUpdate = {
  activeProfileName: "WasIstDas",
  memoryWriteThreshold: "4",
  personaLayerDisabled: "false",
  personaWriteThreshold: "5",
  profilesPath: "C:\\Users\\USER\\AppData\\Roaming\\PLwC\\profiles",
  qdrantEnabled: "true",
  securityConfig: "C:\\Users\\USER\\Claude_Arbeitsumgebung\\config\\security.yaml",
  temperamentWriteThreshold: "6",
  workspacePath: "C:\\Users\\USER\\Claude_Arbeitsumgebung",
};

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

test("serves, updates, and resets allowlisted settings before forwarding a call exactly once", async () => {
  const port = await freePort();
  const session = new FakeSession();
  const bridge = new LoopbackBridgeServer({ host: "127.0.0.1", port, path: "/message" }, session);
  await bridge.start();
  const socket = await connect(`ws://127.0.0.1:${port}/message`);

  try {
    const pong = await request(socket, { jsonrpc: "2.0", id: 1, method: "ping" });
    assert.deepEqual(pong, { jsonrpc: "2.0", id: 1, result: { ok: true } });

    const settings = await request(socket, { jsonrpc: "2.0", id: 2, method: "settings/get" });
    assert.deepEqual(settings, {
      jsonrpc: "2.0",
      id: 2,
      result: {
        activeProfileName: "WasIstDas",
        memoryWriteThreshold: "2",
        personaLayerDisabled: "true",
        personaWriteThreshold: "3",
        profilesPath: null,
        qdrantEnabled: "true",
        securityConfig: null,
        source: "Claude PLwC configuration",
        temperamentWriteThreshold: "6",
        workspacePath: "C:\\Users\\USER\\Claude_Arbeitsumgebung",
      },
    });

    const updated = await request(socket, {
      jsonrpc: "2.0",
      id: 3,
      method: "settings/update",
      params: { settings: editableSettings },
    });
    assert.deepEqual(updated, {
      jsonrpc: "2.0",
      id: 3,
      result: { source: "PLwC Chat Bridge saved settings", ...editableSettings },
    });

    const reset = await request(socket, {
      jsonrpc: "2.0",
      id: 4,
      method: "settings/reset",
    });
    assert.equal((reset.result as GatewaySettingsSnapshot).source, "Claude PLwC configuration");

    const result = await request(socket, {
      jsonrpc: "2.0",
      id: 5,
      method: "tools/call",
      params: { name: "plwc_governor", arguments: { operation: "apply" } },
    });
    assert.equal((result.result as CallToolResult).isError, true);
    assert.equal(session.starts, 1);
    assert.equal(session.calls, 1);
    assert.equal(session.updates, 1);
    assert.equal(session.resets, 1);
  } finally {
    socket.close();
    await bridge.stop();
  }
});

test("validates the complete editable gateway settings contract", () => {
  assert.deepEqual(parseGatewaySettingsUpdate(editableSettings), editableSettings);
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, workspacePath: "relative" }));
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, memoryWriteThreshold: "-1" }));
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, qdrantEnabled: "yes" }));
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, activeProfileName: "bad\nname" }));
  assert.throws(() => {
    const { qdrantEnabled: _removed, ...missing } = editableSettings;
    parseGatewaySettingsUpdate(missing);
  });
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, secretToken: "must-not-pass" }));
});

test("settings snapshot contains only the nine supported PLwC values", () => {
  const settings = gatewaySettingsFromEnvironment({
    PLWC_WORKSPACE_ROOT: "C:\\workspace",
    SECRET_TOKEN: "must-not-leak",
  });

  assert.deepEqual(Object.keys(settings).sort(), [
    "activeProfileName",
    "memoryWriteThreshold",
    "personaLayerDisabled",
    "personaWriteThreshold",
    "profilesPath",
    "qdrantEnabled",
    "securityConfig",
    "source",
    "temperamentWriteThreshold",
    "workspacePath",
  ]);
  assert.equal(JSON.stringify(settings).includes("must-not-leak"), false);
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
