import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { BUILD_IDENTITY, parseBuildIdentity } from "../src/build-identity.js";

test("loads the canonical installer-addressable build identity", () => {
  assert.equal(BUILD_IDENTITY.buildId, `plwc-chat-bridge@${BUILD_IDENTITY.releaseVersion}`);
  assert.equal(BUILD_IDENTITY.installer.componentId, "chat-bridge");
  assert.equal(
    BUILD_IDENTITY.installer.directoryName,
    `chat-bridge-${BUILD_IDENTITY.releaseVersion}`,
  );
  assert.equal(BUILD_IDENTITY.components.nodeBridge, BUILD_IDENTITY.releaseVersion);
  assert.equal(BUILD_IDENTITY.components.browserExtension, BUILD_IDENTITY.releaseVersion);
  assert.equal(BUILD_IDENTITY.components.nativeLauncher, BUILD_IDENTITY.releaseVersion);
});

test("rejects internally inconsistent build identities", () => {
  const value = JSON.parse(
    readFileSync(new URL("../../../build-identity.json", import.meta.url), "utf8"),
  ) as Record<string, unknown>;
  assert.throws(
    () => parseBuildIdentity({ ...value, buildId: "plwc-chat-bridge@wrong" }),
    /inconsistent/i,
  );
});
