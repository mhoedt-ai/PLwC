import { readFileSync } from "node:fs";

export interface BuildIdentity {
  schemaVersion: 1;
  product: "PLwC Chat Bridge";
  releaseVersion: string;
  buildId: string;
  installer: {
    componentId: "chat-bridge";
    directoryName: string;
  };
  components: {
    nodeBridge: string;
    browserExtension: string;
    nativeLauncher: string;
  };
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`PLwC Chat Bridge build identity has an invalid ${key}.`);
  }
  return value;
}

function requireRecord(value: unknown, field: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`PLwC Chat Bridge build identity has an invalid ${field}.`);
  }
  return value as Record<string, unknown>;
}

export function parseBuildIdentity(value: unknown): BuildIdentity {
  const record = requireRecord(value, "document");
  const installer = requireRecord(record.installer, "installer");
  const components = requireRecord(record.components, "components");
  const releaseVersion = requireString(record, "releaseVersion");
  const buildId = requireString(record, "buildId");
  if (
    record.schemaVersion !== 1 ||
    record.product !== "PLwC Chat Bridge" ||
    buildId !== `plwc-chat-bridge@${releaseVersion}` ||
    installer.componentId !== "chat-bridge" ||
    requireString(installer, "directoryName") !== `chat-bridge-${releaseVersion}`
  ) {
    throw new Error("PLwC Chat Bridge build identity is inconsistent.");
  }
  return {
    buildId,
    components: {
      browserExtension: requireString(components, "browserExtension"),
      nativeLauncher: requireString(components, "nativeLauncher"),
      nodeBridge: requireString(components, "nodeBridge"),
    },
    installer: {
      componentId: "chat-bridge",
      directoryName: requireString(installer, "directoryName"),
    },
    product: "PLwC Chat Bridge",
    releaseVersion,
    schemaVersion: 1,
  };
}

function loadBuildIdentity(): BuildIdentity {
  const candidates = [
    new URL("../../build-identity.json", import.meta.url),
    new URL("../../../build-identity.json", import.meta.url),
  ];
  for (const candidate of candidates) {
    try {
      return parseBuildIdentity(JSON.parse(readFileSync(candidate, "utf8")));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  throw new Error("PLwC Chat Bridge build identity file was not found.");
}

export const BUILD_IDENTITY = loadBuildIdentity();
