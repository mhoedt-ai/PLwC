import assert from "node:assert/strict";
import test from "node:test";

import {
  buildOnboardingEntryCorrection,
  isPlwcToolCallCorrection,
  PLWC_TOOL_CALL_CORRECTION_PROTOCOL,
} from "./onboarding-correction";

test("corrects an invalid onboarding describe filter to the exact first-run status call", () => {
  const correction = buildOnboardingEntryCorrection(
    {
      arguments: {
        detail: "short",
        format: "json",
        operation: "onboarding",
        scope: "status",
      },
      callId: "plwc-onboarding-describe-001",
      name: "plwc_describe",
    },
    {
      error: "operation filtering is supported only for workspace_operation and document_operation scopes",
      ok: false,
      operation: "describe",
      operation_filter: "onboarding",
      scope: "status",
    },
  );

  assert.deepEqual(correction, {
    instruction:
      "The onboarding entry was requested through an unsupported Describe operation filter. Emit exactly next_call; do not retry onboarding as plwc_describe.",
    next_call: {
      plwc_tool_call: {
        arguments: { scope: "first_run" },
        call_id: "plwc-onboarding-describe-001-first-run",
        name: "plwc_status",
      },
    },
    protocol: PLWC_TOOL_CALL_CORRECTION_PROTOCOL,
    reason: "invalid_onboarding_describe_filter",
  });
  assert.equal(isPlwcToolCallCorrection(correction), true);
});

test("does not correct unrelated Describe validation failures", () => {
  assert.equal(
    buildOnboardingEntryCorrection(
      {
        arguments: { operation: "read", scope: "workspace_operation" },
        callId: "describe-workspace-001",
        name: "plwc_describe",
      },
      { error: "required field missing", ok: false },
    ),
    null,
  );
});
