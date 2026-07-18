import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeAutomationDelay,
  parseGatewaySettings,
  parseGatewaySettingsUpdate,
  type GatewaySettingsUpdate,
} from "./messages";

const editableSettings: GatewaySettingsUpdate = {
  activeProfileName: "WasIstDas",
  memoryWriteThreshold: "2",
  personaLayerDisabled: "false",
  personaWriteThreshold: "3",
  profilesPath: "C:\\Users\\USER\\AppData\\Roaming\\PLwC\\profiles",
  qdrantEnabled: "true",
  securityConfig: null,
  temperamentWriteThreshold: "6",
  workspacePath: "C:\\Users\\USER\\Claude_Arbeitsumgebung",
};

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

test("editable gateway settings accept only the validated nine-field contract", () => {
  assert.deepEqual(parseGatewaySettingsUpdate(editableSettings), editableSettings);
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, workspacePath: "relative" }));
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, memoryWriteThreshold: "2.5" }));
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, qdrantEnabled: "yes" }));
  assert.throws(() => parseGatewaySettingsUpdate({ ...editableSettings, secret: "no" }));
});

test("automation delays accept tenths from zero through sixty seconds", () => {
  assert.equal(normalizeAutomationDelay(0), 0);
  assert.equal(normalizeAutomationDelay(2.54), 2.5);
  assert.equal(normalizeAutomationDelay(60), 60);
  assert.equal(normalizeAutomationDelay(-1), 2);
  assert.equal(normalizeAutomationDelay(61), 2);
  assert.equal(normalizeAutomationDelay("2"), 2);
});
