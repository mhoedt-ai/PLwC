import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

export async function loadBuildIdentity(projectRoot) {
  const integrationRoot = resolve(projectRoot, "..");
  const [identity, workspacePackage, bridgePackage, extensionPackage, manifest] =
    await Promise.all([
      readJson(resolve(integrationRoot, "build-identity.json")),
      readJson(resolve(integrationRoot, "package.json")),
      readJson(resolve(integrationRoot, "bridge/package.json")),
      readJson(resolve(projectRoot, "package.json")),
      readJson(resolve(projectRoot, "src/manifest.json")),
    ]);

  if (
    identity.schemaVersion !== 1 ||
    identity.product !== "PLwC Chat Bridge" ||
    identity.buildId !== `plwc-chat-bridge@${identity.releaseVersion}` ||
    identity.installer?.componentId !== "chat-bridge" ||
    identity.installer?.directoryName !== "bridge"
  ) {
    throw new Error("PLwC Chat Bridge build identity is inconsistent.");
  }
  const expectedVersions = {
    browserExtension: extensionPackage.version,
    nodeBridge: bridgePackage.version,
    releaseVersion: workspacePackage.version,
  };
  for (const [component, version] of Object.entries(expectedVersions)) {
    const actual = component === "releaseVersion"
      ? identity.releaseVersion
      : identity.components?.[component];
    if (actual !== version) {
      throw new Error(`PLwC Chat Bridge ${component} version mismatch: expected ${version}, received ${actual}.`);
    }
  }
  if (manifest.version_name !== identity.components.browserExtension) {
    throw new Error("Extension manifest version_name does not match the shared build identity.");
  }
  if (
    typeof identity.components?.nativeLauncher !== "string" ||
    identity.components.nativeLauncher.trim() === ""
  ) {
    throw new Error("Native launcher component version is missing from the shared build identity.");
  }
  return identity;
}

export function buildIdentityDefine(identity) {
  return { PLWC_BUILD_IDENTITY: JSON.stringify(identity) };
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}
