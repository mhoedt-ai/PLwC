import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { extname, resolve } from "node:path";
import test from "node:test";

const extensionRoot = resolve(process.cwd());
const chatBridgeRoot = resolve(extensionRoot, "..");
const repositoryRoot = resolve(extensionRoot, "../../..");
const storeRoot = resolve(extensionRoot, "store");

interface StoreTarget {
  extensionId: string;
  listingUrl: string;
  nativeMessagingOrigin: string;
  packageTarget: "chrome-brave" | "edge";
  webSocketOrigin: string;
}

interface StoreContract {
  schemaVersion: number;
  product: string;
  releaseVersion: string;
  identityContract: string;
  developmentIdentity: {
    extensionId: string;
    nativeMessagingOrigin: string;
    webSocketOrigin: string;
    classification: string;
    source: string;
  };
  publicPages: Record<"privacy" | "support", { url: string; status: string }>;
  stores: Record<"chrome" | "edge", StoreTarget>;
  nativeMessaging: {
    allowedOrigins: string[];
    wildcardsAllowed: boolean;
  };
  setupDownload: {
    releasesUrl: string;
    reviewerArtifactUrl: string | null;
    reviewerArtifactSha256: string;
    status: string;
  };
}

interface RuntimeIdentityContract {
  schemaVersion: number;
  releaseVersion: string;
  extensionId: string;
  allowedOrigin: string;
  identities: Record<"development" | "chromeStore" | "edgeStore", {
    classification: string;
    extensionId: string;
    nativeMessagingOrigin: string;
    webSocketOrigin: string;
  }>;
  allowedOrigins: string[];
  webSocketOrigins: string[];
}

async function readJson<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(path, "utf8")) as T;
}

async function filesBelow(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const children = await Promise.all(entries.map(async (entry) => {
    const path = resolve(directory, entry.name);
    return entry.isDirectory() ? filesBelow(path) : [path];
  }));
  return children.flat();
}

function extensionIdFromPublicKey(key: string): string {
  return [...createHash("sha256").update(Buffer.from(key, "base64")).digest("hex").slice(0, 32)]
    .map((digit) => String.fromCharCode(97 + Number.parseInt(digit, 16)))
    .join("");
}

function validatePublicStoreTarget(store: "chrome" | "edge", target: StoreTarget): void {
  assert.deepEqual(Object.keys(target).sort(), [
    "extensionId",
    "listingUrl",
    "nativeMessagingOrigin",
    "packageTarget",
    "webSocketOrigin",
  ]);
  assert.match(target.extensionId, /^[a-p]{32}$/u);
  assert.equal(target.nativeMessagingOrigin, `chrome-extension://${target.extensionId}/`);
  assert.equal(target.webSocketOrigin, `chrome-extension://${target.extensionId}`);
  assert.equal(target.packageTarget, store === "chrome" ? "chrome-brave" : "edge");
  const url = new URL(target.listingUrl);
  assert.equal(url.protocol, "https:");
  if (store === "chrome") {
    assert.equal(url.hostname, "chromewebstore.google.com");
  } else {
    assert.equal(url.hostname, "microsoftedge.microsoft.com");
  }
  assert.ok(url.pathname.toLowerCase().includes(target.extensionId));
}

test("store identity contract keeps development and public Store identities separate", async () => {
  const manifest = await readJson<Record<string, unknown>>(resolve(extensionRoot, "src/manifest.json"));
  const packageJson = await readJson<{ version: string }>(resolve(extensionRoot, "package.json"));
  const nativeIdentity = await readJson<RuntimeIdentityContract>(
    resolve(chatBridgeRoot, "native/extension-identity.json"),
  );
  const contract = await readJson<StoreContract>(resolve(storeRoot, "store-contract.json"));

  assert.equal(contract.schemaVersion, 2);
  assert.equal(contract.product, "PLwC Chat Bridge");
  assert.equal(manifest.version, packageJson.version);
  assert.equal(manifest.version_name, packageJson.version);
  assert.equal(packageJson.version, "1.0.1");
  assert.deepEqual(Object.keys(contract).sort(), [
    "developmentIdentity",
    "identityContract",
    "nativeMessaging",
    "product",
    "publicPages",
    "releaseVersion",
    "schemaVersion",
    "setupDownload",
    "stores",
  ]);
  assert.equal(contract.identityContract, "../../native/extension-identity.json");
  assert.deepEqual(Object.keys(contract.developmentIdentity).sort(), [
    "classification",
    "extensionId",
    "nativeMessagingOrigin",
    "source",
    "webSocketOrigin",
  ]);
  assert.equal(contract.developmentIdentity.classification, "development_sideload_only");
  assert.equal(contract.developmentIdentity.source, "src/manifest.json key");
  assert.equal(typeof manifest.key, "string");
  assert.equal(extensionIdFromPublicKey(manifest.key as string), contract.developmentIdentity.extensionId);
  assert.equal(nativeIdentity.schemaVersion, 2);
  assert.equal(nativeIdentity.releaseVersion, contract.releaseVersion);
  assert.equal(contract.releaseVersion, "1.0.0");
  assert.equal(nativeIdentity.extensionId, contract.developmentIdentity.extensionId);
  assert.equal(nativeIdentity.allowedOrigin, contract.developmentIdentity.nativeMessagingOrigin);
  assert.equal(
    contract.developmentIdentity.nativeMessagingOrigin,
    `chrome-extension://${contract.developmentIdentity.extensionId}/`,
  );
  assert.equal(
    contract.developmentIdentity.webSocketOrigin,
    `chrome-extension://${contract.developmentIdentity.extensionId}`,
  );

  validatePublicStoreTarget("chrome", contract.stores.chrome);
  validatePublicStoreTarget("edge", contract.stores.edge);
  assert.notEqual(contract.stores.chrome.extensionId, contract.developmentIdentity.extensionId);
  assert.notEqual(contract.stores.edge.extensionId, contract.developmentIdentity.extensionId);
  assert.notEqual(contract.stores.chrome.extensionId, contract.stores.edge.extensionId);

  const expectedIdentities = [
    nativeIdentity.identities.development,
    nativeIdentity.identities.chromeStore,
    nativeIdentity.identities.edgeStore,
  ];
  assert.deepEqual(
    nativeIdentity.allowedOrigins,
    expectedIdentities.map((identity) => identity.nativeMessagingOrigin),
  );
  assert.deepEqual(
    nativeIdentity.webSocketOrigins,
    expectedIdentities.map((identity) => identity.webSocketOrigin),
  );
  assert.deepEqual(contract.nativeMessaging.allowedOrigins, nativeIdentity.allowedOrigins);
  assert.equal(contract.nativeMessaging.wildcardsAllowed, false);
  assert.ok(nativeIdentity.allowedOrigins.every((origin) => !origin.includes("*")));
  assert.equal(contract.stores.chrome.extensionId, nativeIdentity.identities.chromeStore.extensionId);
  assert.equal(contract.stores.edge.extensionId, nativeIdentity.identities.edgeStore.extensionId);
  assert.equal(contract.setupDownload.releasesUrl, "https://github.com/mhoedt-ai/PLwC/releases");
  assert.equal(
    contract.setupDownload.reviewerArtifactUrl,
    "https://github.com/mhoedt-ai/PLwC/releases/download/plwc-setup-1.0.0-installer-r24/PLwC-Setup-1.0.0-installer-r24.exe",
  );
  assert.equal(
    contract.setupDownload.reviewerArtifactSha256,
    "b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0",
  );
  assert.equal(contract.setupDownload.status, "verified_public_explicit_unsigned_candidate");
});

test("Bridge and Native Messaging enforce exactly the three approved origins", async () => {
  const identity = await readJson<RuntimeIdentityContract>(
    resolve(chatBridgeRoot, "native/extension-identity.json"),
  );
  const nativeManifest = await readJson<{ allowed_origins: string[] }>(
    resolve(chatBridgeRoot, "native/manifest/plwc.chat_bridge.launcher.json"),
  );
  const launcher = await readFile(
    resolve(chatBridgeRoot, "native/launcher-host/Plwc.ChatBridge.NativeLauncher.cs"),
    "utf8",
  );
  const bridgeServer = await readFile(resolve(chatBridgeRoot, "bridge/src/server.ts"), "utf8");
  const installer = await readFile(
    resolve(chatBridgeRoot, "scripts/install-native-launcher-windows.ps1"),
    "utf8",
  );

  assert.deepEqual(nativeManifest.allowed_origins, identity.allowedOrigins);
  for (const approved of Object.values(identity.identities)) {
    assert.ok(launcher.includes(`= "${approved.extensionId}"`));
    assert.ok(installer.includes(`"${approved.extensionId}"`));
  }
  assert.ok(launcher.includes("Unapproved PLwC extension ID"));
  assert.ok(launcher.includes("ApprovedWebSocketOrigins()"));
  assert.ok(bridgeServer.includes("APPROVED_EXTENSION_WEB_SOCKET_ORIGINS.has(origin)"));
  assert.doesNotMatch(JSON.stringify(nativeManifest), /\*/u);
});

test("manifest permissions and host scopes match the reviewed least-privilege inventory", async () => {
  const manifest = await readJson<Record<string, unknown>>(resolve(extensionRoot, "src/manifest.json"));
  assert.equal(manifest.manifest_version, 3);
  assert.deepEqual(manifest.permissions, ["storage", "nativeMessaging"]);
  assert.deepEqual(manifest.host_permissions, ["ws://127.0.0.1:3007/*"]);
  assert.deepEqual(manifest.content_scripts, [
    {
      matches: ["https://chatgpt.com/*", "https://chat.openai.com/*"],
      js: ["content.js"],
      run_at: "document_idle",
    },
  ]);
  assert.deepEqual(manifest.web_accessible_resources, [
    {
      resources: ["icons/plwc-icon-512.png"],
      matches: ["https://chatgpt.com/*", "https://chat.openai.com/*"],
    },
  ]);

  const inventory = await readFile(resolve(storeRoot, "permission-data-inventory.md"), "utf8");
  for (const exactValue of [
    "`storage`",
    "`nativeMessaging`",
    "`ws://127.0.0.1:3007/*`",
    "`https://chatgpt.com/*`",
    "`https://chat.openai.com/*`",
    "Personal communications",
    "Website content",
    "Web history or browsing activity",
    "User-generated content",
  ]) {
    assert.ok(inventory.includes(exactValue), `inventory must disclose ${exactValue}`);
  }
});

test("Store disclosures accurately declare no remotely hosted executable code", async () => {
  const sourceFiles = (await filesBelow(resolve(extensionRoot, "src")))
    .filter((path) => extname(path) === ".ts" && !path.endsWith(".test.ts"));
  const source = (await Promise.all(sourceFiles.map((path) => readFile(path, "utf8")))).join("\n");

  for (const forbidden of [
    /\beval\s*\(/u,
    /\bnew\s+Function\s*\(/u,
    /\bimportScripts\s*\(\s*["']https?:/u,
    /\bimport\s*\(\s*["']https?:/u,
  ]) {
    assert.doesNotMatch(source, forbidden);
  }

  const listing = await readFile(resolve(storeRoot, "listing-en.md"), "utf8");
  const inventory = await readFile(resolve(storeRoot, "permission-data-inventory.md"), "utf8");
  assert.ok(listing.includes("Select: `No, I am not using remote code.`"));
  assert.ok(inventory.includes("Answer: **No, the extension does not use remote code.**"));
});

test("public privacy and support pages are complete, indexable, and contract-aligned", async () => {
  const contract = await readJson<StoreContract>(resolve(storeRoot, "store-contract.json"));
  assert.deepEqual(Object.keys(contract.publicPages).sort(), ["privacy", "support"]);
  const expected = {
    privacy: resolve(storeRoot, "public/chat-bridge/privacy/index.html"),
    support: resolve(storeRoot, "public/chat-bridge/support/index.html"),
  } as const;

  for (const name of ["privacy", "support"] as const) {
    const html = await readFile(expected[name], "utf8");
    assert.match(html, /^<!doctype html>/iu);
    assert.match(html, /<html lang="en">/u);
    assert.ok(html.includes(`<link rel="canonical" href="${contract.publicPages[name].url}">`));
    assert.ok(html.includes('<meta name="robots" content="index,follow">'));
    assert.ok(html.includes('href="../store-pages.css"'));
    assert.ok(html.includes("info@plwc.de"));
    assert.ok(html.includes('href="https://www.plwc.de/index.html#security"'));
    assert.doesNotMatch(html, /\b(?:TODO|TBD|REPLACE_ME|example\.com)\b/iu);
    assert.ok(["pending_publication", "verified"].includes(contract.publicPages[name].status));
  }

  const publicPageCss = await readFile(resolve(storeRoot, "public/chat-bridge/store-pages.css"), "utf8");
  for (const brandToken of [
    "--ink: #0d1624",
    "--soft: #f5f7fa",
    "--line: #dfe8f0",
    "--cyan: #39e0d0",
    "--blue: #28a7ff",
    "--radius: 24px",
  ]) {
    assert.ok(publicPageCss.includes(brandToken), `public pages must retain PLwC brand token ${brandToken}`);
  }
  assert.ok(publicPageCss.includes("linear-gradient(90deg, var(--cyan), var(--blue))"));
  assert.ok(publicPageCss.includes("background: #08111c"));

  const privacy = await readFile(expected.privacy, "utf8");
  for (const required of [
    "Data the extension handles",
    "How data is used",
    "Connections and disclosures",
    "Storage and retention",
    "Your controls",
    "Limited Use commitment",
    "Security and data minimization",
    "127.0.0.1",
    "OpenAI",
    "5,000",
  ]) {
    assert.ok(privacy.includes(required), `privacy page must include ${required}`);
  }
  const support = await readFile(expected.support, "utf8");
  for (const required of [
    "The browser Store installs only the extension.",
    "PLwC Windows Setup",
    "8/8",
    "Repair",
    "Never send:",
  ]) {
    assert.ok(support.includes(required), `support page must include ${required}`);
  }
});

test("official requirements cite only first-party Chrome and Microsoft sources", async () => {
  const requirements = await readFile(resolve(storeRoot, "official-requirements.md"), "utf8");
  const urls = [...requirements.matchAll(/\]\((https:\/\/[^)]+)\)/gu)].map((match) => new URL(match[1]!));
  assert.ok(urls.length >= 12);
  for (const url of urls) {
    assert.ok(
      ["developer.chrome.com", "learn.microsoft.com"].includes(url.hostname),
      `non-official Store requirement source: ${url.href}`,
    );
  }
});

test("Store artifacts contain no high-confidence credential or private-key material", async () => {
  const files = [
    ...(await filesBelow(storeRoot)),
    resolve(extensionRoot, "scripts/build-store-draft-seed.ps1"),
    resolve(extensionRoot, "scripts/build-store-packages.ps1"),
    resolve(extensionRoot, "scripts/test-store-packages.ps1"),
    resolve(repositoryRoot, "docs/evidence/BRIDGE_P0_03_ACCEPTANCE_EN.md"),
    resolve(repositoryRoot, "docs/evidence/STORE_G0_01_ACCEPTANCE_EN.md"),
  ];
  const prohibitedExtensions = new Set([".env", ".key", ".p12", ".pem", ".pfx"]);
  for (const path of files) {
    assert.ok(!prohibitedExtensions.has(extname(path).toLowerCase()), `prohibited Store artifact: ${path}`);
    if (![".css", ".html", ".json", ".md", ".txt"].includes(extname(path).toLowerCase())) continue;
    const content = await readFile(path, "utf8");
    assert.doesNotMatch(content, /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/u);
    assert.doesNotMatch(
      content,
      /(?:api[_-]?key|client[_-]?secret|refresh[_-]?token|access[_-]?token|authorization)\s*[:=]\s*["'][A-Za-z0-9_./+\-=]{12,}["']/iu,
    );
  }
});

test("draft identity seed builder strips the development key and cannot look like a submission package", async () => {
  const script = await readFile(resolve(extensionRoot, "scripts/build-store-draft-seed.ps1"), "utf8");
  assert.ok(script.includes('PSObject.Properties.Remove("key")'));
  assert.ok(script.includes("DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT.zip"));
  assert.ok(script.includes("do not submit"));
  assert.ok(script.includes('Extension -in @(".map", ".pem", ".p12", ".pfx", ".key")'));
});

test("final Store package builder is separate, deterministic, allowlisted, and identity-bound", async () => {
  const builder = await readFile(resolve(extensionRoot, "scripts/build-store-packages.ps1"), "utf8");
  const packageTest = await readFile(resolve(extensionRoot, "scripts/test-store-packages.ps1"), "utf8");
  for (const required of [
    'Name = "chrome-brave"',
    'Name = "edge"',
    '-store.zip',
    "PSObject.Properties.Remove(\"key\")",
    "New-DeterministicZip",
    "manifest.json",
    "background.js",
    "content.js",
    "icons/plwc-icon-512.png",
    "Store package secret scan failed",
    "expectedExtensionId",
    "expectedNativeMessagingOrigin",
  ]) {
    assert.ok(builder.includes(required), `final Store package builder must include ${required}`);
  }
  assert.ok(packageTest.includes("output is not reproducible"));
  assert.ok(packageTest.includes("sidecar does not bind its archive"));
  assert.doesNotMatch(builder, /DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT/u);
});

test("listing material includes Store dependency, permissions, privacy, review, and screenshot contracts", async () => {
  const manifest = await readJson<{ description: string }>(resolve(extensionRoot, "src/manifest.json"));
  const listing = await readFile(resolve(storeRoot, "listing-en.md"), "utf8");
  assert.ok(listing.includes(`> ${manifest.description}`));
  assert.ok(manifest.description.length <= 132);
  for (const section of [
    "## Detailed description",
    "## Single-purpose field",
    "## Permission justifications",
    "## Remote-code field",
    "## Data-use disclosure",
    "## Reviewer instructions",
    "## Screenshot and promotional-asset plan",
  ]) {
    assert.ok(listing.includes(section), `listing material must include ${section}`);
  }
  const detailedDescription = listing
    .split("## Detailed description")[1]
    ?.split("## Single-purpose field")[0]
    ?.trim() ?? "";
  assert.ok(detailedDescription.length >= 250 && detailedDescription.length <= 10_000);
  assert.ok(listing.includes("1280 x 800"));
  assert.ok(listing.includes("440 x 280"));
  assert.ok(listing.includes("1400 x 560"));
  assert.ok(listing.includes("https://www.plwc.de/index.html#security"));

  const contract = await readJson<StoreContract>(resolve(storeRoot, "store-contract.json"));
  const panel = await readFile(resolve(extensionRoot, "src/panel/plwc-panel.ts"), "utf8");
  const i18n = await readFile(resolve(extensionRoot, "src/shared/i18n.ts"), "utf8");
  assert.ok(panel.includes(contract.setupDownload.releasesUrl));
  assert.ok(panel.includes("noopener noreferrer"));
  assert.ok(i18n.includes("The browser Store installs only the extension."));
  assert.ok(listing.includes("generic releases page is not a substitute"));
});
