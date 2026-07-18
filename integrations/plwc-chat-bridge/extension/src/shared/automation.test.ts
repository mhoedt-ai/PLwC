import assert from "node:assert/strict";
import test from "node:test";

import { shouldAutoRun, shouldAutoSubmitResult } from "./automation";
import type { BridgeSettings } from "./messages";

const settings: BridgeSettings = {
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
const sandbox = { readOnly: false, requiresConfirmation: true, reason: "sandbox" };

test("automates read-only calls and recognized writes only after standing confirmation is enabled", () => {
  assert.equal(shouldAutoRun(settings, readOnly), true);
  assert.equal(shouldAutoRun(settings, mutating), false);
  assert.equal(shouldAutoRun({ ...settings, autoConfirmWrites: true }, mutating), true);
  assert.equal(shouldAutoRun({ ...settings, autoConfirmWrites: true }, sandbox), false);
  assert.equal(shouldAutoRun({ ...settings, readOnlyAutoRun: false }, readOnly), false);
});

test("submits read-only and explicitly confirmed results without bypassing confirmation", () => {
  assert.equal(shouldAutoSubmitResult(settings, readOnly, false), true);
  assert.equal(shouldAutoSubmitResult(settings, mutating, false), false);
  assert.equal(shouldAutoSubmitResult(settings, mutating, true), true);
  assert.equal(shouldAutoSubmitResult({ ...settings, autoSubmitResults: false }, readOnly, false), false);
});
