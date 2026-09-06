import test from "node:test";

import { runP002Fix02BrowserAcceptance } from "./p0-02-fix-02-browser-acceptance";

test("P0-02 Fix 02 browser onboarding-entry and result-submission scenarios pass", async () => {
  await runP002Fix02BrowserAcceptance();
});
