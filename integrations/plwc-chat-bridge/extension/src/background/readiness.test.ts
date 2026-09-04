import assert from "node:assert/strict";
import test from "node:test";

import { AtomicBridgeReadiness } from "./readiness";

test("publishes ready atomically only after build and exact tool verification", () => {
  const readiness = new AtomicBridgeReadiness();
  const generation = readiness.begin();

  assert.equal(readiness.current.state, "connecting");
  assert.equal(readiness.current.toolCount, 0);
  readiness.connected(generation);
  assert.equal(readiness.current.state, "checking_build");
  readiness.buildVerified(generation);
  assert.equal(readiness.current.state, "loading_tools");
  readiness.toolsVerified(generation, 8);

  assert.deepEqual(readiness.current, {
    buildVerified: true,
    expectedToolCount: 8,
    generation,
    state: "ready",
    toolCount: 8,
    toolsVerified: true,
  });
});

test("disconnect invalidates stale verification results from an older generation", () => {
  const readiness = new AtomicBridgeReadiness();
  const staleGeneration = readiness.begin();
  readiness.connected(staleGeneration);
  const disconnectedGeneration = readiness.disconnect();

  assert.equal(readiness.buildVerified(staleGeneration), false);
  assert.equal(readiness.toolsVerified(staleGeneration, 8), false);
  assert.equal(readiness.current.state, "disconnected");
  assert.equal(readiness.current.generation, disconnectedGeneration);
});

test("a noncanonical tool count becomes incompatible instead of connected zero of eight", () => {
  const readiness = new AtomicBridgeReadiness();
  const generation = readiness.begin();
  readiness.connected(generation);
  readiness.buildVerified(generation);

  assert.equal(readiness.toolsVerified(generation, 7), true);
  assert.equal(readiness.current.state, "incompatible");
  assert.equal(readiness.current.toolCount, 0);
  assert.equal(readiness.current.toolsVerified, false);
});
