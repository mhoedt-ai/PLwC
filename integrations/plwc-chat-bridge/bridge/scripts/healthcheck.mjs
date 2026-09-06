import process from "node:process";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { verifyBridgeHealth } from "../dist/src/healthcheck.js";

function argument(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

const scriptRoot = dirname(fileURLToPath(import.meta.url));
const identity = JSON.parse(
  readFileSync(resolve(scriptRoot, "../../native/extension-identity.json"), "utf8"),
);
const endpoint = argument("--endpoint", "ws://127.0.0.1:3007/message");
const origin = argument(
  "--origin",
  identity.identities.development.webSocketOrigin,
);
const timeoutMs = Number(argument("--timeout-ms", "4000"));
const expectedBuildId = argument("--expected-build-id", undefined);

try {
  const health = await verifyBridgeHealth(endpoint, origin, timeoutMs, expectedBuildId);
  process.stdout.write(`${JSON.stringify({ ok: true, ...health })}\n`);
} catch (error) {
  const message = error instanceof Error ? error.message : "PLwC Chat Bridge health check failed.";
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
}
