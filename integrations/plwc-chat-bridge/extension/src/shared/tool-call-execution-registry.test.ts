import assert from "node:assert/strict";
import test from "node:test";

import { createToolCallIdentity } from "./tool-call-identity";
import {
  claimToolCallExecution,
  parseProcessedToolCallRegistry,
} from "./tool-call-execution-registry";

test("claims a conversation and call id identity exactly once", () => {
  const identity = createToolCallIdentity("/c/first", "call-1", "plwc_status", { scope: "runtime" });
  const first = claimToolCallExecution(parseProcessedToolCallRegistry(undefined), identity, 100);
  assert.equal(first.kind, "claimed");

  const restored = parseProcessedToolCallRegistry(JSON.parse(JSON.stringify(first.registry)));
  const duplicate = claimToolCallExecution(restored, identity, 200);
  assert.equal(duplicate.kind, "duplicate");
  assert.equal(duplicate.registry.entries.length, 1);
});

test("rejects changed tool payload for an existing identity as a conflict", () => {
  const original = createToolCallIdentity("/c/first", "call-1", "plwc_status", { scope: "runtime" });
  const changedArguments = createToolCallIdentity("/c/first", "call-1", "plwc_status", { scope: "config" });
  const changedName = createToolCallIdentity("/c/first", "call-1", "plwc_profile", { scope: "runtime" });
  const claimed = claimToolCallExecution(parseProcessedToolCallRegistry(undefined), original, 100);

  assert.equal(claimToolCallExecution(claimed.registry, changedArguments, 200).kind, "conflict");
  assert.equal(claimToolCallExecution(claimed.registry, changedName, 200).kind, "conflict");
});

test("allows the same call id in a different conversation", () => {
  const first = createToolCallIdentity("/c/first", "call-1", "plwc_status", { scope: "runtime" });
  const second = createToolCallIdentity("/c/second", "call-1", "plwc_status", { scope: "runtime" });
  const firstClaim = claimToolCallExecution(parseProcessedToolCallRegistry(undefined), first, 100);
  const secondClaim = claimToolCallExecution(firstClaim.registry, second, 200);

  assert.equal(secondClaim.kind, "claimed");
  assert.equal(secondClaim.registry.entries.length, 2);
});

test("rejects malformed persisted data instead of reopening processed identities", () => {
  assert.throws(
    () => parseProcessedToolCallRegistry({ entries: "invalid", version: 1 }),
    /Invalid persisted PLwC tool call registry/,
  );
});
