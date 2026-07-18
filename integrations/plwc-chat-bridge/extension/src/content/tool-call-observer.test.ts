import assert from "node:assert/strict";
import test from "node:test";

import { recordExistingToolCalls, takeNewToolCalls } from "./tool-call-observer";
import type { ToolCallTextCandidate } from "./tool-call-parser";

function candidate(name: string, callId: string): ToolCallTextCandidate {
  return {
    sourceKind: "rendered",
    text: [
      JSON.stringify({ call_id: callId, name, type: "function_call_start" }),
      JSON.stringify({ call_id: callId, key: "scope", type: "parameter", value: "runtime" }),
      JSON.stringify({ call_id: callId, type: "function_call_end" }),
    ].join("\n"),
    visible: true,
  };
}

test("records existing chat calls without offering them for execution", () => {
  const seen = new Set<string>();
  const existing = candidate("plwc_status", "old-status");

  recordExistingToolCalls([existing], seen);

  assert.deepEqual(takeNewToolCalls([existing], seen), []);
});

test("offers only calls that appear after the observer baseline", () => {
  const seen = new Set<string>();
  const existing = candidate("plwc_status", "old-status");
  const next = candidate("plwc_status", "new-status");
  recordExistingToolCalls([existing], seen);

  const calls = takeNewToolCalls([existing, next], seen);

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.callId, "new-status");
  assert.deepEqual(takeNewToolCalls([next], seen), []);
});
