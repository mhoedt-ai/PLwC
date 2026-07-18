import assert from "node:assert/strict";
import test from "node:test";

import {
  formatPlwcToolResultMessage,
  parsePlwcToolResultMessage,
} from "./tool-result-message";

test("formats and parses a marked PLwC tool result", () => {
  const message = formatPlwcToolResultMessage({
    call_id: "status-17",
    is_error: false,
    name: "plwc_status",
    result: { ok: true, scope: "runtime" },
  });

  assert.match(message, /^# PLwC Tool Result\n\n```json/u);
  assert.deepEqual(parsePlwcToolResultMessage(message), {
    call_id: "status-17",
    is_error: false,
    name: "plwc_status",
    result: { ok: true, scope: "runtime" },
  });
});

test("parses the JSON payload rendered inside a chat code block", () => {
  const payload = JSON.stringify({
    call_id: "describe-3",
    name: "plwc_describe",
    result: { tools: 8 },
  });

  assert.deepEqual(parsePlwcToolResultMessage(payload), {
    call_id: "describe-3",
    is_error: false,
    name: "plwc_describe",
    result: { tools: 8 },
  });
});

test("rejects generic and malformed JSON objects", () => {
  assert.equal(parsePlwcToolResultMessage('{"name":"plwc_status","result":{}}'), null);
  assert.equal(
    parsePlwcToolResultMessage('{"call_id":"1","name":"unknown","result":{}}'),
    null,
  );
  assert.equal(
    parsePlwcToolResultMessage('{"call_id":"1","name":"plwc_status","result":{},"run":true}'),
    null,
  );
});

test("bounds oversized result messages with a structured preview", () => {
  const message = formatPlwcToolResultMessage({
    call_id: "large-1",
    is_error: false,
    name: "plwc_workspace_operation",
    result: { content: '\\"'.repeat(20_000) },
  });
  const parsed = parsePlwcToolResultMessage(message);

  assert.ok(message.length < 12_000);
  assert.deepEqual(
    (parsed?.result as { truncated_by?: string }).truncated_by,
    "PLwC Chat Bridge",
  );
});
