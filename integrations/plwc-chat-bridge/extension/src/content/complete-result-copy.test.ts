import assert from "node:assert/strict";
import test from "node:test";

import { copyCompleteToolResultMessage } from "./complete-result-copy";
import { formatPlwcToolResultMessage } from "./tool-result-message";
import { presentToolResult } from "../shared/tool-result";

test("copies the complete marked result instead of the bounded panel preview", async () => {
  const original = {
    ok: true,
    scope: "first_run",
    payload: Array.from(
      { length: 900 },
      (_, index) => `onboarding-field-${index}-${"x".repeat(60)}`,
    ),
  };
  const message = formatPlwcToolResultMessage({
    call_id: "first-run-large-001",
    is_error: false,
    name: "plwc_status",
    result: presentToolResult("plwc_status", original),
  });
  let copied = "";

  await copyCompleteToolResultMessage(message, {
    writeText: async (text) => {
      copied = text;
    },
  });

  assert.equal(copied, message);
  assert.ok(copied.length > 12_000);
  assert.match(copied, /onboarding-field-899/u);
  assert.doesNotMatch(copied, /output truncated by PLwC Chat Bridge/u);
});
