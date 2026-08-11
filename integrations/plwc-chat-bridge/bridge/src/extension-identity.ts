import { readFileSync } from "node:fs";

export type ExtensionIdentityName = "development" | "chromeStore" | "edgeStore";

export interface ExtensionIdentity {
  classification: string;
  extensionId: string;
  nativeMessagingOrigin: string;
  webSocketOrigin: string;
}

export interface ExtensionIdentityContract {
  schemaVersion: 2;
  product: "PLwC Chat Bridge";
  releaseVersion: string;
  extensionId: string;
  allowedOrigin: string;
  identities: Record<ExtensionIdentityName, ExtensionIdentity>;
  allowedOrigins: string[];
  webSocketOrigins: string[];
}

const IDENTITY_NAMES: ExtensionIdentityName[] = ["development", "chromeStore", "edgeStore"];
const EXTENSION_ID = /^[a-p]{32}$/u;

function requireRecord(value: unknown, field: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`PLwC extension identity contract has an invalid ${field}.`);
  }
  return value as Record<string, unknown>;
}

function requireString(record: Record<string, unknown>, field: string): string {
  const value = record[field];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`PLwC extension identity contract has an invalid ${field}.`);
  }
  return value;
}

function requireStringArray(record: Record<string, unknown>, field: string): string[] {
  const value = record[field];
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`PLwC extension identity contract has an invalid ${field}.`);
  }
  return [...value] as string[];
}

export function parseExtensionIdentityContract(value: unknown): ExtensionIdentityContract {
  const record = requireRecord(value, "document");
  const rawIdentities = requireRecord(record.identities, "identities");
  if (
    record.schemaVersion !== 2 ||
    record.product !== "PLwC Chat Bridge" ||
    Object.keys(rawIdentities).sort().join(",") !== [...IDENTITY_NAMES].sort().join(",")
  ) {
    throw new Error("PLwC extension identity contract is inconsistent.");
  }

  const identities = {} as Record<ExtensionIdentityName, ExtensionIdentity>;
  for (const name of IDENTITY_NAMES) {
    const identity = requireRecord(rawIdentities[name], `identities.${name}`);
    const extensionId = requireString(identity, "extensionId");
    const nativeMessagingOrigin = requireString(identity, "nativeMessagingOrigin");
    const webSocketOrigin = requireString(identity, "webSocketOrigin");
    if (
      !EXTENSION_ID.test(extensionId) ||
      nativeMessagingOrigin !== `chrome-extension://${extensionId}/` ||
      webSocketOrigin !== `chrome-extension://${extensionId}`
    ) {
      throw new Error(`PLwC extension identity ${name} is inconsistent.`);
    }
    identities[name] = {
      classification: requireString(identity, "classification"),
      extensionId,
      nativeMessagingOrigin,
      webSocketOrigin,
    };
  }

  const allowedOrigins = requireStringArray(record, "allowedOrigins");
  const webSocketOrigins = requireStringArray(record, "webSocketOrigins");
  const expectedAllowedOrigins = IDENTITY_NAMES.map((name) => identities[name].nativeMessagingOrigin);
  const expectedWebSocketOrigins = IDENTITY_NAMES.map((name) => identities[name].webSocketOrigin);
  if (
    new Set(allowedOrigins).size !== IDENTITY_NAMES.length ||
    new Set(webSocketOrigins).size !== IDENTITY_NAMES.length ||
    JSON.stringify(allowedOrigins) !== JSON.stringify(expectedAllowedOrigins) ||
    JSON.stringify(webSocketOrigins) !== JSON.stringify(expectedWebSocketOrigins) ||
    [...allowedOrigins, ...webSocketOrigins].some((origin) => origin.includes("*"))
  ) {
    throw new Error("PLwC extension identity origins are inconsistent.");
  }

  const development = identities.development;
  if (
    record.extensionId !== development.extensionId ||
    record.allowedOrigin !== development.nativeMessagingOrigin
  ) {
    throw new Error("PLwC legacy development identity aliases are inconsistent.");
  }

  return {
    allowedOrigin: development.nativeMessagingOrigin,
    allowedOrigins,
    extensionId: development.extensionId,
    identities,
    product: "PLwC Chat Bridge",
    releaseVersion: requireString(record, "releaseVersion"),
    schemaVersion: 2,
    webSocketOrigins,
  };
}

function loadExtensionIdentityContract(): ExtensionIdentityContract {
  const candidates = [
    new URL("../../native/extension-identity.json", import.meta.url),
    new URL("../../../native/extension-identity.json", import.meta.url),
  ];
  for (const candidate of candidates) {
    try {
      return parseExtensionIdentityContract(JSON.parse(readFileSync(candidate, "utf8")));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  throw new Error("PLwC extension identity contract was not found.");
}

export const EXTENSION_IDENTITY_CONTRACT = loadExtensionIdentityContract();
export const APPROVED_EXTENSION_WEB_SOCKET_ORIGINS = new Set(
  EXTENSION_IDENTITY_CONTRACT.webSocketOrigins,
);
