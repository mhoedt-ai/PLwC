import assert from "node:assert/strict";
import test from "node:test";

import {
  decideVerifiedToolCacheAction,
  FALLBACK_BRIDGE_STATUS,
  normalizeBridgeStatus,
  shouldOfferSetupDownload,
  shouldRequestNativeAutoStart,
} from "./status";

const readyStatus = {
  ...FALLBACK_BRIDGE_STATUS,
  buildIdentityValidation: {
    actualBuildId: "plwc-chat-bridge@1.0.0",
    expectedBuildId: "plwc-chat-bridge@1.0.0",
    mismatches: [],
    valid: true,
  },
  connection: "connected" as const,
  readiness: {
    buildVerified: true,
    expectedToolCount: 8 as const,
    generation: 1,
    state: "ready" as const,
    toolCount: 8,
    toolsVerified: true,
  },
  toolSet: {
    duplicates: [],
    extra: [],
    invalidSchemas: [],
    missing: [],
    tools: [],
    valid: true,
  },
};

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

test("normalizes the legacy connected but unchecked payload as build verification in progress", () => {
  const status = normalizeBridgeStatus({
    ...FALLBACK_BRIDGE_STATUS,
    buildIdentityValidation: null,
    connection: "connected",
    toolSet: null,
  });

  assert.equal(status.connection, "connected");
  assert.equal(status.buildIdentityValidation, null);
  assert.equal(status.toolSet, null);
  assert.equal(status.readiness.state, "checking_build");
  assert.equal(status.readiness.toolCount, 0);
  assert.equal(status.readiness.buildVerified, false);
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

test("reloads the local tool cache when the bridge recovers to ready", () => {
  assert.equal(decideVerifiedToolCacheAction(readyStatus, false), "reload");
  assert.equal(decideVerifiedToolCacheAction(readyStatus, true), "keep");
});

test("clears a verified local tool cache while bridge readiness is lost", () => {
  assert.equal(decideVerifiedToolCacheAction({
    ...readyStatus,
    connection: "disconnected",
    readiness: {
      ...readyStatus.readiness,
      state: "disconnected",
      toolCount: 0,
      toolsVerified: false,
    },
  }, true), "clear");
});
