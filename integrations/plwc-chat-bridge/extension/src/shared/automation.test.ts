import assert from "node:assert/strict";
import test from "node:test";

import { shouldAutoRun, shouldAutoSubmitResult } from "./automation";
import type { BridgeSettings } from "./messages";

const settings: BridgeSettings = {
  autoSubmitResults: true,
  readOnlyAutoRun: true,
  renderChatCards: true,
};
const readOnly = { readOnly: true, requiresConfirmation: false, reason: "read" };
const mutating = { readOnly: false, requiresConfirmation: true, reason: "write" };

test("automates only policy-classified read-only execution", () => {
  assert.equal(shouldAutoRun(settings, readOnly), true);
  assert.equal(shouldAutoRun(settings, mutating), false);
  assert.equal(shouldAutoRun({ ...settings, readOnlyAutoRun: false }, readOnly), false);
});

test("submits read-only and explicitly confirmed results without bypassing confirmation", () => {
  assert.equal(shouldAutoSubmitResult(settings, readOnly, false), true);
  assert.equal(shouldAutoSubmitResult(settings, mutating, false), false);
  assert.equal(shouldAutoSubmitResult(settings, mutating, true), true);
  assert.equal(shouldAutoSubmitResult({ ...settings, autoSubmitResults: false }, readOnly, false), false);
});
