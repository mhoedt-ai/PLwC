import test from "node:test";

import { runP001BrowserAcceptance } from "./p0-01-browser-acceptance";

test("P0-01 browser lifecycle fixture scenarios pass", () => {
  runP001BrowserAcceptance();
});
