import assert from "node:assert/strict";
import test from "node:test";

import { AutomaticRunQueue, shouldAutoRun, shouldAutoSubmitResult } from "./automation";
import type { BridgeSettings } from "./messages";

const settings: BridgeSettings = {
  autoConfirmSandbox: false,
  autoConfirmWrites: false,
  autoExecuteDelay: 2,
  autoInsertDelay: 2,
  autoSubmitDelay: 2,
  autoSubmitResults: true,
  readOnlyAutoRun: true,
  renderChatCards: true,
};
const readOnly = { readOnly: true, requiresConfirmation: false, reason: "read" };
const mutating = { automaticConfirmationAllowed: true, readOnly: false, requiresConfirmation: true, reason: "write" };
const sandbox = {
  automaticSandboxConfirmationAllowed: true,
  readOnly: false,
  requiresConfirmation: true,
  reason: "sandbox",
};
const unknown = { readOnly: false, requiresConfirmation: true, reason: "unknown" };

test("automates read-only calls and recognized writes only after standing confirmation is enabled", () => {
  assert.equal(shouldAutoRun(settings, readOnly), true);
  assert.equal(shouldAutoRun(settings, mutating), false);
  assert.equal(shouldAutoRun({ ...settings, autoConfirmWrites: true }, mutating), true);
  assert.equal(shouldAutoRun({ ...settings, autoConfirmWrites: true }, sandbox), false);
  assert.equal(shouldAutoRun({ ...settings, autoConfirmSandbox: true }, sandbox), true);
  assert.equal(
    shouldAutoRun({ ...settings, autoConfirmSandbox: true, autoConfirmWrites: true }, unknown),
    false,
  );
  assert.equal(shouldAutoRun({ ...settings, readOnlyAutoRun: false }, readOnly), false);
});

test("submits read-only and explicitly confirmed results without bypassing confirmation", () => {
  assert.equal(shouldAutoSubmitResult(settings, readOnly, false), true);
  assert.equal(shouldAutoSubmitResult(settings, mutating, false), false);
  assert.equal(shouldAutoSubmitResult(settings, mutating, true), true);
  assert.equal(shouldAutoSubmitResult({ ...settings, autoSubmitResults: false }, readOnly, false), false);
});

test("serializes calls and pauses a dependent call after an incomplete result", async () => {
  const queue = new AutomaticRunQueue();
  const events: string[] = [];
  const first = queue.enqueue(
    "assistant-response-1",
    async () => {
      events.push("first:start");
      await Promise.resolve();
      events.push("first:end");
      return false;
    },
    () => events.push("first:paused"),
  );
  const second = queue.enqueue(
    "assistant-response-1",
    async () => {
      events.push("second:run");
      return true;
    },
    () => events.push("second:paused"),
  );

  assert.deepEqual(await first, { completed: false, sourceId: "assistant-response-1" });
  assert.deepEqual(await second, { completed: false, sourceId: "assistant-response-1" });
  assert.deepEqual(events, ["first:start", "first:end", "second:paused"]);
});

test("allows the next call after a completed result or from a new response", async () => {
  const queue = new AutomaticRunQueue();
  const events: string[] = [];
  await queue.enqueue("assistant-response-1", async () => true, () => events.push("paused"));
  await queue.enqueue("assistant-response-1", async () => {
    events.push("same-source");
    return false;
  }, () => events.push("paused"));
  await queue.enqueue("assistant-response-2", async () => {
    events.push("new-source");
    return true;
  }, () => events.push("paused"));

  assert.deepEqual(events, ["same-source", "new-source"]);
});
