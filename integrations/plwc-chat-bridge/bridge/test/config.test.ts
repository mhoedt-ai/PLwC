import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { ConfigurationError, loadConfig } from "../src/config.js";

async function withConfig(value: unknown, run: (path: string) => Promise<void>): Promise<void> {
  const directory = await mkdtemp(join(tmpdir(), "plwc-bridge-test-"));
  const path = join(directory, "config.json");
  try {
    await writeFile(path, JSON.stringify(value), "utf8");
    await run(path);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test("loads a strict loopback configuration", async () => {
  await withConfig(
    {
      bridge: { host: "127.0.0.1", port: 3007, path: "/message" },
      gateway: { command: "plwc-gateway", args: [], env: {} },
    },
    async (path) => {
      const config = await loadConfig(path);
      assert.equal(config.bridge.host, "127.0.0.1");
      assert.equal(config.gateway.command, "plwc-gateway");
    },
  );
});

test("resolves repoRoot relative to the integration config instead of process cwd", async () => {
  await withConfig(
    {
      bridge: { host: "127.0.0.1", port: 3007, path: "/message" },
      gateway: { command: "python", args: ["${repoRoot}/server.py"], env: {} },
    },
    async (path) => {
      const config = await loadConfig(path);
      assert.match(config.gateway.args[0] ?? "", /server\.py$/);
      assert.notEqual(config.gateway.args[0], join(process.cwd(), "server.py"));
    },
  );
});

test("rejects every non-loopback host", async () => {
  await withConfig(
    {
      bridge: { host: "0.0.0.0", port: 3007, path: "/message" },
      gateway: { command: "plwc-gateway", args: [] },
    },
    async (path) => {
      await assert.rejects(loadConfig(path), ConfigurationError);
    },
  );
});

test("does not expose a missing configuration path in its error", async () => {
  const privatePath = join(tmpdir(), "private", "missing-config.json");
  await assert.rejects(loadConfig(privatePath), (error: unknown) => {
    assert.ok(error instanceof ConfigurationError);
    assert.equal(error.message.includes(privatePath), false);
    return true;
  });
});
