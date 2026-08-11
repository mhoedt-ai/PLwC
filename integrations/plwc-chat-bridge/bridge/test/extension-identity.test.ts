import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  APPROVED_EXTENSION_WEB_SOCKET_ORIGINS,
  EXTENSION_IDENTITY_CONTRACT,
  parseExtensionIdentityContract,
} from "../src/extension-identity.js";

test("loads exactly the development, Chrome Store, and Edge Store identities", () => {
  assert.deepEqual(Object.keys(EXTENSION_IDENTITY_CONTRACT.identities).sort(), [
    "chromeStore",
    "development",
    "edgeStore",
  ]);
  assert.equal(EXTENSION_IDENTITY_CONTRACT.allowedOrigins.length, 3);
  assert.equal(APPROVED_EXTENSION_WEB_SOCKET_ORIGINS.size, 3);
  assert.equal(
    EXTENSION_IDENTITY_CONTRACT.extensionId,
    EXTENSION_IDENTITY_CONTRACT.identities.development.extensionId,
  );
  assert.ok(
    EXTENSION_IDENTITY_CONTRACT.allowedOrigins.every(
      (origin) => /^chrome-extension:\/\/[a-p]{32}\/$/u.test(origin) && !origin.includes("*"),
    ),
  );
});

test("rejects omitted, duplicated, wildcard, and unapproved origins", () => {
  const source = JSON.parse(
    readFileSync(new URL("../../../native/extension-identity.json", import.meta.url), "utf8"),
  ) as Record<string, unknown>;
  const allowedOrigins = source.allowedOrigins as string[];
  for (const invalidOrigins of [
    allowedOrigins.slice(0, 2),
    [allowedOrigins[0], allowedOrigins[0], allowedOrigins[2]],
    [allowedOrigins[0], allowedOrigins[1], "chrome-extension://*/"],
    [allowedOrigins[0], allowedOrigins[1], `chrome-extension://${"a".repeat(32)}/`],
  ]) {
    assert.throws(
      () => parseExtensionIdentityContract({ ...source, allowedOrigins: invalidOrigins }),
      /origins are inconsistent/i,
    );
  }
});
