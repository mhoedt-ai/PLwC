import assert from "node:assert/strict";
import test from "node:test";

import { parseGatewaySettings } from "./messages";

test("gateway settings parser returns only the supported PLwC fields", () => {
  const settings = parseGatewaySettings({
    source: "Claude PLwC configuration",
    workspacePath: "C:\\workspace",
    profilesPath: null,
    activeProfileName: "WasIstDas",
    securityConfig: null,
    memoryWriteThreshold: "2",
    personaWriteThreshold: "3",
    temperamentWriteThreshold: "6",
    qdrantEnabled: "true",
    personaLayerDisabled: "true",
    arbitrarySecret: "must-not-survive",
  });

  assert.equal(settings.workspacePath, "C:\\workspace");
  assert.equal(JSON.stringify(settings).includes("must-not-survive"), false);
  assert.equal(Object.keys(settings).length, 10);
});

test("gateway settings parser rejects missing allowlisted fields", () => {
  assert.throws(() => parseGatewaySettings({ source: "test" }), /workspacePath/);
});
