import assert from "node:assert/strict";
import test from "node:test";

import {
  EXTENSION_BUILD_IDENTITY,
  parseBuildIdentity,
  validateBuildIdentity,
} from "./build-identity";

test("embeds the canonical installer-addressable build identity", () => {
  assert.equal(
    EXTENSION_BUILD_IDENTITY.buildId,
    `plwc-chat-bridge@${EXTENSION_BUILD_IDENTITY.releaseVersion}`,
  );
  assert.equal(EXTENSION_BUILD_IDENTITY.installer.componentId, "chat-bridge");
  assert.equal(EXTENSION_BUILD_IDENTITY.components.nodeBridge, EXTENSION_BUILD_IDENTITY.releaseVersion);
  assert.equal(EXTENSION_BUILD_IDENTITY.components.browserExtension, EXTENSION_BUILD_IDENTITY.releaseVersion);
  assert.equal(EXTENSION_BUILD_IDENTITY.components.nativeLauncher, EXTENSION_BUILD_IDENTITY.releaseVersion);
  assert.equal(validateBuildIdentity(EXTENSION_BUILD_IDENTITY).valid, true);
});

test("reports component and build mismatches without hiding internal versions", () => {
  const actual = parseBuildIdentity({
    ...EXTENSION_BUILD_IDENTITY,
    buildId: "plwc-chat-bridge@0.2.0-rc19.dev17",
    releaseVersion: "0.2.0-rc19.dev17",
    installer: {
      ...EXTENSION_BUILD_IDENTITY.installer,
      directoryName: "bridge",
    },
    components: {
      ...EXTENSION_BUILD_IDENTITY.components,
      nodeBridge: "0.2.0-rc19.dev11",
    },
  });
  const validation = validateBuildIdentity(actual);

  assert.equal(validation.valid, false);
  assert.deepEqual(validation.mismatches, [
    "buildId",
    "releaseVersion",
    "components.nodeBridge",
  ]);
  assert.equal(actual.components.nodeBridge, "0.2.0-rc19.dev11");
});
