import assert from "node:assert/strict";
import test from "node:test";

import { decidePolicy } from "./policy";

test("keeps status read-only and requires confirmation for workspace writes", () => {
  assert.deepEqual(decidePolicy("plwc_status", { scope: "runtime" }), {
    readOnly: true,
    requiresConfirmation: false,
    reason: "Read-only PLwC facade.",
  });
  assert.equal(
    decidePolicy("plwc_workspace_operation", { operation: "write", path: "notes.txt" }).requiresConfirmation,
    true,
  );
});

test("always confirms Governor apply and treats unknown operations as mutating", () => {
  assert.equal(decidePolicy("plwc_governor", { operation: "apply" }).requiresConfirmation, true);
  assert.equal(decidePolicy("plwc_governor", { operation: "future_operation" }).requiresConfirmation, true);
  assert.equal(decidePolicy("plwc_document_operation", { operation: "future_operation" }).requiresConfirmation, true);
});
