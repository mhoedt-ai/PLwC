import assert from "node:assert/strict";
import test from "node:test";

import {
  localizeBridgeError,
  localizeConnectionState,
  localizeLauncherStatus,
  resolveUiLanguage,
  text,
} from "./i18n";

test("selects German explicitly and falls back to English", () => {
  assert.equal(resolveUiLanguage("de-DE"), "de");
  assert.equal(resolveUiLanguage("en-US"), "en");
  assert.equal(resolveUiLanguage("fr-FR"), "en");
});

test("separates native launcher state from profile onboarding state", () => {
  assert.equal(text("label_launcher", "de"), "Nativer Start");
  assert.equal(text("label_launcher", "en"), "Native start");
  const german = localizeLauncherStatus({
      code: "not_requested",
      message: "",
      state: "not_requested",
    }, "de");
  assert.equal(
    german,
    "Der native Start war nicht erforderlich oder wurde noch nicht angefordert.",
  );
  assert.doesNotMatch(german, /Profil|Onboarding/u);
});

test("localizes setup guidance without exposing repository or PowerShell instructions", () => {
  const status = {
    code: "native_host_missing",
    message: "raw native host failure",
    state: "unavailable" as const,
  };
  const german = localizeLauncherStatus(status, "de");
  const english = localizeLauncherStatus(status, "en");
  assert.match(german, /Einrichtung/);
  assert.match(english, /Setup/);
  assert.doesNotMatch(`${german} ${english}`, /\.ps1|scripts[\\/]|repository/i);
  assert.match(text("launcher_store_boundary", "en"), /Store installs only the extension/);
  assert.match(text("launcher_store_boundary", "de"), /Store installiert nur die Erweiterung/);
});

test("requires 8 of 8 before presenting a launcher response as ready", () => {
  assert.match(localizeLauncherStatus({
    code: "ready",
    message: "",
    state: "started",
    toolCount: 8,
  }, "de"), /8 von 8/);
  assert.doesNotMatch(localizeLauncherStatus({
    message: "started",
    state: "started",
    toolCount: 7,
  }, "en"), /8 of 8/);
});

test("localizes connection state and known WebSocket failures", () => {
  assert.equal(localizeConnectionState("disconnected", "de"), "getrennt");
  assert.equal(localizeConnectionState("connected", "en"), "connected");
  assert.equal(localizeBridgeError("WebSocket connection closed.", "de"), "Keine Verbindung zur lokalen Bridge.");
});
