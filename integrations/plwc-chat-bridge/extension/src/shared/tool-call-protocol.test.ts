import assert from "node:assert/strict";
import test from "node:test";

import { awaitingConfirmationResponse, outcomeUnknownResponse } from "./tool-call-protocol";

const mutating = {
  automaticConfirmationAllowed: true,
  readOnly: false,
  reason: "Write confirmation required.",
  requiresConfirmation: true,
};

test("represents a missing mutation confirmation as an awaiting state, not an error", () => {
  const response = awaitingConfirmationResponse(mutating);

  assert.equal(response.state, "awaiting_confirmation");
  assert.equal(response.isError, false);
  assert.deepEqual(response.result, {
    confirmation_required: true,
    ok: false,
    reason: mutating.reason,
    state: "awaiting_confirmation",
  });
});

test("locks a mutating call after an ambiguous transport outcome", () => {
  const response = outcomeUnknownResponse(mutating, {
    code: "timeout",
    deliveryState: "outcome_unknown",
    message: "Timed out after dispatch.",
  });

  assert.equal(response?.state, "outcome_unknown");
  assert.equal(response?.isError, true);
  assert.deepEqual(response?.result, {
    error_code: "timeout",
    message: "Timed out after dispatch.",
    mutation_may_have_executed: true,
    ok: false,
    retry_allowed: false,
    state: "outcome_unknown",
  });
});

test("does not recast read-only or definitely unsent failures as ambiguous mutations", () => {
  assert.equal(outcomeUnknownResponse(
    { readOnly: true, reason: "read", requiresConfirmation: false },
    { code: "timeout", deliveryState: "outcome_unknown", message: "timeout" },
  ), null);
  assert.equal(outcomeUnknownResponse(
    mutating,
    { code: "not_connected", deliveryState: "not_sent", message: "not sent" },
  ), null);
});
