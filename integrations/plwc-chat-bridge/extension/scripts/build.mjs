import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { buildIdentityDefine, loadBuildIdentity } from "./build-identity.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = resolve(projectRoot, "dist");
const integrationRoot = resolve(projectRoot, "..");
const buildIdentity = await loadBuildIdentity(projectRoot);
const define = buildIdentityDefine(buildIdentity);

const manifest = JSON.parse(await readFile(resolve(projectRoot, "src/manifest.json"), "utf8"));
const identity = JSON.parse(await readFile(resolve(integrationRoot, "native/extension-identity.json"), "utf8"));
const storeContract = JSON.parse(await readFile(resolve(projectRoot, "store/store-contract.json"), "utf8"));
const nativeManifest = JSON.parse(
  await readFile(resolve(integrationRoot, "native/manifest/plwc.chat_bridge.launcher.json"), "utf8"),
);
const nativeLauncherSource = await readFile(
  resolve(integrationRoot, "native/launcher-host/Plwc.ChatBridge.NativeLauncher.cs"),
  "utf8",
);
const extensionId = [...createHash("sha256")
  .update(Buffer.from(manifest.key, "base64"))
  .digest("hex")
  .slice(0, 32)]
  .map((digit) => String.fromCharCode(97 + Number.parseInt(digit, 16)))
  .join("");
if (identity.schemaVersion !== 2 || identity.releaseVersion !== buildIdentity.releaseVersion) {
  throw new Error("Native messaging identity contract has an invalid schema or release version.");
}
if (extensionId !== identity.identities?.development?.extensionId) {
  throw new Error(`Extension manifest key resolves to ${extensionId}, expected ${identity.extensionId}.`);
}
const identityNames = ["development", "chromeStore", "edgeStore"];
const approvedExtensionIds = identityNames.map((name) => identity.identities?.[name]?.extensionId);
const approvedOrigins = identityNames.map((name) => identity.identities?.[name]?.nativeMessagingOrigin);
const approvedWebSocketOrigins = identityNames.map((name) => identity.identities?.[name]?.webSocketOrigin);
if (
  new Set(approvedExtensionIds).size !== 3 ||
  approvedExtensionIds.some((id) => !/^[a-p]{32}$/.test(id)) ||
  approvedOrigins.some((origin, index) => origin !== `chrome-extension://${approvedExtensionIds[index]}/`) ||
  approvedWebSocketOrigins.some((origin, index) => origin !== `chrome-extension://${approvedExtensionIds[index]}`) ||
  JSON.stringify(identity.allowedOrigins) !== JSON.stringify(approvedOrigins) ||
  JSON.stringify(identity.webSocketOrigins) !== JSON.stringify(approvedWebSocketOrigins) ||
  [...approvedOrigins, ...approvedWebSocketOrigins].some((origin) => origin.includes("*"))
) {
  throw new Error("Native messaging identity contains inconsistent approved origins.");
}
if (identity.extensionId !== extensionId || identity.allowedOrigin !== approvedOrigins[0]) {
  throw new Error("Legacy development identity aliases are inconsistent.");
}
if (JSON.stringify(nativeManifest.allowed_origins) !== JSON.stringify(approvedOrigins)) {
  throw new Error("Native messaging manifest does not allow exactly the approved extension origins.");
}
for (const approvedExtensionId of approvedExtensionIds) {
  if (!nativeLauncherSource.includes(`= "${approvedExtensionId}"`)) {
    throw new Error(`Native launcher does not contain approved extension ID ${approvedExtensionId}.`);
  }
}
if (
  storeContract.schemaVersion !== 2 ||
  storeContract.releaseVersion !== buildIdentity.releaseVersion ||
  storeContract.developmentIdentity.extensionId !== approvedExtensionIds[0] ||
  storeContract.stores.chrome.extensionId !== approvedExtensionIds[1] ||
  storeContract.stores.edge.extensionId !== approvedExtensionIds[2] ||
  JSON.stringify(storeContract.nativeMessaging.allowedOrigins) !== JSON.stringify(approvedOrigins) ||
  storeContract.nativeMessaging.wildcardsAllowed !== false
) {
  throw new Error("Store and native extension identity contracts are inconsistent.");
}

await rm(outputDirectory, { force: true, recursive: true });
await mkdir(resolve(outputDirectory, "icons"), { recursive: true });

await Promise.all([
  build({
    bundle: true,
    define,
    entryPoints: [resolve(projectRoot, "src/background/index.ts")],
    format: "esm",
    outfile: resolve(outputDirectory, "background.js"),
    platform: "browser",
    sourcemap: true,
    target: "chrome120",
  }),
  build({
    bundle: true,
    define,
    entryPoints: [resolve(projectRoot, "src/content/index.ts")],
    format: "iife",
    outfile: resolve(outputDirectory, "content.js"),
    platform: "browser",
    sourcemap: true,
    target: "chrome120",
  }),
  copyFile(resolve(projectRoot, "src/manifest.json"), resolve(outputDirectory, "manifest.json")),
  copyFile(
    resolve(projectRoot, "public/icons/plwc-icon-512.png"),
    resolve(outputDirectory, "icons/plwc-icon-512.png"),
  ),
]);

console.log(`PLwC Chat Bridge extension built at ${outputDirectory}`);
