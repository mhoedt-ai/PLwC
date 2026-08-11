import assert from "node:assert/strict";
import test from "node:test";

import { decidePolicy, withConfirmedToolArguments } from "./policy";

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
  assert.equal(
    decidePolicy("plwc_workspace_operation", { operation: "write", path: "notes.txt" }).automaticConfirmationAllowed,
    true,
  );
  assert.equal(decidePolicy("plwc_workspace_operation", { operation: "file_info" }).readOnly, true);
});

test("always confirms Governor apply and treats unknown operations as mutating", () => {
  assert.equal(decidePolicy("plwc_governor", { operation: "apply" }).requiresConfirmation, true);
  assert.equal(decidePolicy("plwc_governor", { operation: "future_operation" }).requiresConfirmation, true);
  assert.equal(decidePolicy("plwc_document_operation", { operation: "future_operation" }).requiresConfirmation, true);
  assert.equal(decidePolicy("plwc_governor", { operation: "apply" }).automaticConfirmationAllowed, true);
  assert.equal(decidePolicy("plwc_governor", { operation: "future_operation" }).automaticConfirmationAllowed, undefined);
  assert.equal(decidePolicy("plwc_sandbox_run", { lang: "python", code: "print(1)" }).automaticConfirmationAllowed, undefined);
  assert.equal(decidePolicy("plwc_sandbox_run", { lang: "python", code: "print(1)" }).automaticSandboxConfirmationAllowed, true);
});

test("never marks unknown public operations as automatically executable", () => {
  for (const [toolName, argumentsValue] of [
    ["plwc_profile", { operation: "future_operation" }],
    ["plwc_reflection", { operation: "future_operation" }],
    ["plwc_governor", { operation: "future_operation" }],
    ["plwc_workspace_operation", { operation: "future_operation" }],
    ["plwc_document_operation", { operation: "future_operation" }],
  ] as const) {
    const decision = decidePolicy(toolName, argumentsValue);
    assert.equal(decision.readOnly, false, toolName);
    assert.equal(decision.requiresConfirmation, true, toolName);
    assert.equal(decision.automaticConfirmationAllowed, undefined, toolName);
    assert.equal(decision.automaticSandboxConfirmationAllowed, undefined, toolName);
  }
  assert.equal(decidePolicy("plwc_profile", { operation: "compile" }).readOnly, true);
});

test("forwards an accepted Governor confirmation as confirmed=true without mutating the source call", () => {
  const source = { operation: "apply", confirmed: false };
  assert.deepEqual(withConfirmedToolArguments("plwc_governor", source, true), {
    operation: "apply",
    confirmed: true,
  });
  assert.equal(source.confirmed, false);
  assert.equal(withConfirmedToolArguments("plwc_workspace_operation", source, true), source);
});
