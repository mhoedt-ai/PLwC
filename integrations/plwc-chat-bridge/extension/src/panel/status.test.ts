import assert from "node:assert/strict";
import test from "node:test";

import {
  FALLBACK_BRIDGE_STATUS,
  normalizeBridgeStatus,
  shouldOfferSetupDownload,
  shouldRequestNativeAutoStart,
} from "./status";

test("normalizes a missing bridge status to the local fallback", () => {
  assert.deepEqual(normalizeBridgeStatus(null), FALLBACK_BRIDGE_STATUS);
});

test("keeps the status panel renderable when launcher is missing from an older background payload", () => {
  const status = normalizeBridgeStatus({
    connection: "connected",
    endpoint: "ws://127.0.0.1:3007/message",
    lastError: "",
    pendingRequests: 0,
    toolSet: null,
  });

  assert.equal(status.connection, "connected");
  assert.equal(status.launcher.state, "not_requested");
  assert.equal(status.launcher.code, "not_requested");
  assert.equal(status.launcher.message, "Native launcher has not been requested.");
});

test("requests native autostart for an offline bridge before a launcher failure", () => {
  assert.equal(shouldRequestNativeAutoStart(null), true);
  assert.equal(shouldRequestNativeAutoStart({
    ...FALLBACK_BRIDGE_STATUS,
    connection: "disconnected",
    launcher: { message: "Native launcher started PLwC Chat Bridge.", state: "started" },
  }), true);
});

test("does not request native autostart when connected or after hard launcher failures", () => {
  assert.equal(shouldRequestNativeAutoStart({
    ...FALLBACK_BRIDGE_STATUS,
    connection: "connected",
  }), false);
  assert.equal(shouldRequestNativeAutoStart({
    ...FALLBACK_BRIDGE_STATUS,
    launcher: { message: "Native launcher is not installed.", state: "unavailable" },
  }), false);
  assert.equal(shouldRequestNativeAutoStart({
    ...FALLBACK_BRIDGE_STATUS,
    launcher: { message: "Native launcher timed out.", state: "failed" },
  }), false);
});

test("offers the official Setup path only when the native host is missing", () => {
  assert.equal(shouldOfferSetupDownload({
    ...FALLBACK_BRIDGE_STATUS,
    launcher: {
      code: "native_host_missing",
      message: "Native launcher is not installed.",
      state: "unavailable",
    },
  }), true);
  assert.equal(shouldOfferSetupDownload({
    ...FALLBACK_BRIDGE_STATUS,
    launcher: {
      code: "native_launcher_unavailable",
      message: "Native messaging is unavailable.",
      state: "unavailable",
    },
  }), true);
  assert.equal(shouldOfferSetupDownload({
    ...FALLBACK_BRIDGE_STATUS,
    launcher: { code: "health_timeout", message: "Timed out.", state: "failed" },
  }), false);
});
