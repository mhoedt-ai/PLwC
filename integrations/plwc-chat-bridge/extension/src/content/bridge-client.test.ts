import assert from "node:assert/strict";
import test from "node:test";

import { normalizeRuntimeErrorMessage } from "./bridge-client";

test("explains stale ChatGPT tabs after extension reloads", () => {
  assert.equal(
    normalizeRuntimeErrorMessage("Extension context invalidated."),
    "PLwC Chat Bridge was reloaded while this ChatGPT tab was open. Reload the ChatGPT tab, then run the PLwC call again.",
  );
});

test("keeps unrelated Chrome runtime errors intact", () => {
  assert.equal(normalizeRuntimeErrorMessage("Could not establish connection."), "Could not establish connection.");
});
