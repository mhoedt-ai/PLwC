import assert from "node:assert/strict";
import test from "node:test";

import {
  connectAfterNativeStart,
  isRecoverableConnectionError,
  NativeLauncherError,
  parseNativeLauncherResponse,
} from "./native-launcher";
import {
  EXTENSION_BUILD_IDENTITY,
  validateBuildIdentity,
} from "../shared/build-identity";
import { RpcRequestError } from "./transport";

test("parses successful native launcher responses", () => {
  assert.deepEqual(parseNativeLauncherResponse({
    buildIdentity: EXTENSION_BUILD_IDENTITY,
    code: "ready",
    logPath: "C:\\Users\\Test\\AppData\\Roaming\\PLwC\\logs\\chat-bridge\\native-launcher.log",
    message: "Bridge ready.",
    ok: true,
    state: "started",
    toolCount: 8,
  }), {
    buildIdentity: EXTENSION_BUILD_IDENTITY,
    buildIdentityValidation: validateBuildIdentity(EXTENSION_BUILD_IDENTITY),
    code: "ready",
    logPath: "C:\\Users\\Test\\AppData\\Roaming\\PLwC\\logs\\chat-bridge\\native-launcher.log",
    message: "Bridge ready.",
    state: "started",
    toolCount: 8,
  });
});

test("rejects native launcher failure responses", () => {
  assert.throws(() => parseNativeLauncherResponse({
    code: "node_missing",
    logPath: "bridge.log",
    message: "Node missing",
    ok: false,
    state: "failed",
    toolCount: 0,
  }), (error: unknown) => {
    assert.ok(error instanceof NativeLauncherError);
    assert.equal(error.status.code, "node_missing");
    assert.equal(error.status.logPath, "bridge.log");
    return true;
  });
});

test("rejects success unless the launcher verified exactly eight tools", () => {
  assert.throws(() => parseNativeLauncherResponse({
    buildIdentity: EXTENSION_BUILD_IDENTITY,
    code: "ready",
    message: "started",
    ok: true,
    state: "started",
    toolCount: 7,
  }), /eight-tool/i);
});

test("rejects a successful launcher response from a different common build", () => {
  const mismatchedIdentity = {
    ...EXTENSION_BUILD_IDENTITY,
    buildId: "plwc-chat-bridge@0.2.0-rc19.dev17",
    releaseVersion: "0.2.0-rc19.dev17",
    installer: {
      ...EXTENSION_BUILD_IDENTITY.installer,
      directoryName: "bridge",
    },
  };
  assert.throws(() => parseNativeLauncherResponse({
    buildIdentity: mismatchedIdentity,
    code: "ready",
    message: "started",
    ok: true,
    state: "started",
    toolCount: 8,
  }), (error: unknown) => {
    assert.ok(error instanceof NativeLauncherError);
    assert.equal(error.status.code, "build_identity_mismatch");
    assert.equal(error.status.buildIdentity?.buildId, mismatchedIdentity.buildId);
    return true;
  });
});

test("recognizes recoverable WebSocket connection failures", () => {
  assert.equal(isRecoverableConnectionError(new RpcRequestError("closed", "connection_closed")), true);
  assert.equal(isRecoverableConnectionError(new RpcRequestError("rpc", "rpc_error")), false);
});

test("retries the WebSocket after the native launcher starts", async () => {
  let attempts = 0;
  const status = await connectAfterNativeStart(
    async () => {
      attempts += 1;
      if (attempts === 1) {
        throw new RpcRequestError("closed", "connection_closed");
      }
    },
    async () => ({ code: "ready", message: "started", state: "started", toolCount: 8 }),
    async () => undefined,
    1_000,
    0,
  );

  assert.equal(attempts, 2);
  assert.equal(status.state, "started");
});
