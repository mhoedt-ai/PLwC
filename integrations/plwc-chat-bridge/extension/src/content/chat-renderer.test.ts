import assert from "node:assert/strict";
import test from "node:test";

import { runStateLabel } from "./chat-renderer";

test("labels a waiting call as requiring confirmation", () => {
  assert.equal(runStateLabel("awaiting_confirmation"), "CONFIRM REQUIRED");
  assert.equal(runStateLabel("scheduled"), "SCHEDULED");
});
