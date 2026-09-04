import assert from "node:assert/strict";
import test from "node:test";

import {
  isRenderableChatBlock,
  resultAwareRunStateLabel,
  runStateLabel,
  selectCallMaskTarget,
} from "./chat-renderer";

test("labels a waiting call as requiring confirmation", () => {
  assert.equal(runStateLabel("awaiting_confirmation"), "CONFIRM REQUIRED");
  assert.equal(runStateLabel("scheduled"), "SCHEDULED");
  assert.equal(runStateLabel("conflict"), "CONFLICT");
});

test("masks only the rendered PLwC JSON code block for call cards", () => {
  const codeBlock = { id: "plwc-json-block" } as HTMLElement;

  assert.equal(selectCallMaskTarget(codeBlock), codeBlock);
});

test("renders visible ChatGPT blocks but ignores hidden editor copies", () => {
  const documentValue = {
    defaultView: {
      getComputedStyle: (element: HTMLElement) => ({
        display: element.dataset.hidden === "true" ? "none" : "block",
        opacity: "1",
        visibility: "visible",
      }),
    },
  } as unknown as Document;
  const visible = {
    dataset: {},
    getBoundingClientRect: () => ({ height: 40, width: 300 }),
  } as unknown as HTMLElement;
  const hidden = {
    dataset: { hidden: "true" },
    getBoundingClientRect: () => ({ height: 0, width: 0 }),
  } as unknown as HTMLElement;

  assert.equal(isRenderableChatBlock(visible, documentValue), true);
  assert.equal(isRenderableChatBlock(hidden, documentValue), false);
});

test("uses the public failure taxonomy in visible chat-card state labels", () => {
  assert.equal(
    resultAwareRunStateLabel("denied", "plwc_workspace_operation", {
      error_category: "POLICY_DENY",
      ok: false,
    }),
    "Policy denied",
  );
  assert.equal(
    resultAwareRunStateLabel("failed", "plwc_describe", {
      error_category: "INVALID_REQUEST",
      ok: false,
    }),
    "Validation failed",
  );
  assert.equal(
    resultAwareRunStateLabel("failed", "plwc_workspace_operation", {
      error_category: "NOT_FOUND",
      ok: false,
    }),
    "Not found",
  );
  assert.equal(
    resultAwareRunStateLabel("failed", "plwc_status", {
      error_category: "UNAVAILABLE",
      ok: false,
    }),
    "Unavailable",
  );
  assert.equal(resultAwareRunStateLabel("failed"), "Gateway failed");
  assert.equal(resultAwareRunStateLabel("unknown"), "Transport failed");
  assert.equal(
    resultAwareRunStateLabel("succeeded", "plwc_workspace_operation", {
      artifact_origin: "workspace_binary_write",
      ok: true,
      validation_status: "unvalidated",
    }),
    "Unvalidated artifact",
  );
});
