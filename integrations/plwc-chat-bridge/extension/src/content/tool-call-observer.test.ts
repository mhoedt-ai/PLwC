import assert from "node:assert/strict";
import test from "node:test";

import {
  recordExistingToolCalls,
  takeNewToolCallObservation,
  takeNewToolCalls,
  ToolCallObservationGate,
} from "./tool-call-observer";
import type { ToolCallTextCandidate } from "./tool-call-parser";

function candidate(
  name: string,
  callId: string,
  scope = "runtime",
  conversationId?: string,
): ToolCallTextCandidate {
  return {
    ...(conversationId === undefined ? {} : { conversationId }),
    sourceKind: "rendered",
    text: JSON.stringify({
      plwc_tool_call: {
        arguments: { scope },
        call_id: callId,
        name,
      },
    }),
    visible: true,
  };
}

test("records existing chat calls without offering them for execution", () => {
  const registry = new Map();
  const existing = candidate("plwc_status", "old-status");

  recordExistingToolCalls([existing], registry);

  assert.deepEqual(takeNewToolCalls([existing], registry), []);
});

test("offers only calls that appear after the observer baseline", () => {
  const registry = new Map();
  const existing = candidate("plwc_status", "old-status");
  const next = candidate("plwc_status", "new-status");
  recordExistingToolCalls([existing], registry);

  const calls = takeNewToolCalls([existing, next], registry);

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.callId, "new-status");
  assert.deepEqual(takeNewToolCalls([next], registry), []);
});

test("offers new calls using the PLwC wrapper", () => {
  const registry = new Map();
  const next = candidate("plwc_status", "new-status");

  const calls = takeNewToolCalls([next], registry);

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.callId, "new-status");
  assert.deepEqual(calls[0]?.arguments, { scope: "runtime" });
});

test("does not collect event-shaped JSON as a candidate", () => {
  const registry = new Map();
  const eventShaped: ToolCallTextCandidate = {
    sourceKind: "rendered",
    text: JSON.stringify({ call_id: "old", name: "plwc_status", type: "tool_event_start" }),
    visible: true,
  };

  assert.deepEqual(takeNewToolCalls([eventShaped], registry), []);
});

test("rejects changed tool arguments for the same conversation and call id", () => {
  const registry = new Map();
  const conflicts = new Set<string>();
  const original = candidate("plwc_status", "shared-call", "runtime", "/c/first");
  const changed = candidate("plwc_status", "shared-call", "config", "/c/first");
  recordExistingToolCalls([original], registry, "/c/first", conflicts);

  const observation = takeNewToolCallObservation([changed], registry, "/c/first", conflicts);

  assert.deepEqual(observation.calls, []);
  assert.equal(observation.conflicts.length, 1);
  assert.equal(observation.conflicts[0]?.existingCall.callId, "shared-call");
  assert.match(observation.conflicts[0]?.message ?? "", /Conflicting PLwC tool call rejected/);
  assert.deepEqual(
    takeNewToolCallObservation([changed], registry, "/c/first", conflicts).conflicts,
    [],
  );
});

test("allows the same call id in a different conversation", () => {
  const registry = new Map();
  const first = candidate("plwc_status", "shared-call", "runtime", "/c/first");
  const second = candidate("plwc_status", "shared-call", "runtime", "/c/second");
  recordExistingToolCalls([first], registry, "/c/first");

  const calls = takeNewToolCalls([second], registry, "/c/second");

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.conversationId, "/c/second");
});

test("keeps hydrating calls in the timed startup baseline", () => {
  const existing = candidate("plwc_status", "old-status");
  const hydrated = candidate("plwc_profile", "old-profile");
  const fresh = candidate("plwc_status", "new-status");
  const gate = new ToolCallObservationGate([existing], "/c/old", 0);

  gate.noteMutation(100);
  assert.deepEqual(gate.scan([existing, hydrated], "/c/old", 220).calls, []);
  assert.deepEqual(gate.scan([existing, hydrated], "/c/old", 1_200).calls, []);

  const result = gate.scan([existing, hydrated, fresh], "/c/old", 1_300);
  assert.deepEqual(result.calls.map(call => call.callId), ["new-status"]);
});

test("browser restart keeps calls from an old chat in the baseline", () => {
  const existing = candidate("plwc_status", "already-processed");
  const gate = new ToolCallObservationGate([existing], "/c/old", 0);

  assert.deepEqual(gate.scan([existing], "/c/old", 1_000), {
    calls: [],
    conflicts: [],
    rescanAfterMs: null,
  });
  assert.deepEqual(gate.scan([existing], "/c/old", 1_100).calls, []);
});

test("reports a changed payload after the baseline without offering a second execution", () => {
  const original = candidate("plwc_status", "shared-call", "runtime");
  const changed = candidate("plwc_status", "shared-call", "config");
  const gate = new ToolCallObservationGate([original], "/c/first", 0);

  gate.scan([original], "/c/first", 1_000);
  const result = gate.scan([original, changed], "/c/first", 1_100);

  assert.deepEqual(result.calls, []);
  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0]?.conflictingCall.callId, "shared-call");
});

test("starts a fresh baseline when the active ChatGPT conversation changes", () => {
  const firstOld = candidate("plwc_status", "first-old");
  const firstNew = candidate("plwc_profile", "first-new");
  const secondOld = candidate("plwc_status", "second-old");
  const secondHydrated = candidate("plwc_profile", "second-hydrated");
  const secondNew = candidate("plwc_status", "second-new");
  const gate = new ToolCallObservationGate([firstOld], "/c/first", 0);

  assert.deepEqual(gate.scan([firstOld], "/c/first", 1_000).calls, []);
  assert.deepEqual(
    gate.scan([firstOld, firstNew], "/c/first", 1_100).calls.map(call => call.callId),
    ["first-new"],
  );

  gate.noteMutation(2_000);
  assert.deepEqual(gate.scan([secondOld], "/c/second", 2_120).calls, []);
  gate.noteMutation(2_200);
  assert.deepEqual(
    gate.scan([secondOld, secondHydrated], "/c/second", 2_320).calls,
    [],
  );
  assert.deepEqual(
    gate.scan([secondOld, secondHydrated], "/c/second", 3_200).calls,
    [],
  );
  assert.deepEqual(
    gate
      .scan([secondOld, secondHydrated, secondNew], "/c/second", 3_300)
      .calls.map(call => call.callId),
    ["second-new"],
  );
});

test("returning to a previous conversation does not reclassify its calls as new", () => {
  const firstOld = candidate("plwc_status", "first-old");
  const firstNew = candidate("plwc_profile", "first-new");
  const secondOld = candidate("plwc_status", "second-old");
  const gate = new ToolCallObservationGate([firstOld], "/c/first", 0);

  gate.scan([firstOld], "/c/first", 1_000);
  assert.deepEqual(
    gate.scan([firstOld, firstNew], "/c/first", 1_100).calls.map(call => call.callId),
    ["first-new"],
  );

  assert.deepEqual(gate.scan([secondOld], "/c/second", 2_000).calls, []);
  assert.deepEqual(gate.scan([secondOld], "/c/second", 3_000).calls, []);
  assert.deepEqual(gate.scan([firstOld, firstNew], "/c/first", 4_000).calls, []);
});
