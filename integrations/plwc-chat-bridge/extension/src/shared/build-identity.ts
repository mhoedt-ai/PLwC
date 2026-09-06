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

export interface BuildIdentityValidation {
  actualBuildId: string;
  expectedBuildId: string;
  mismatches: string[];
  valid: boolean;
}

declare const PLWC_BUILD_IDENTITY: unknown;

function requireRecord(value: unknown, field: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Invalid PLwC Chat Bridge build identity ${field}.`);
  }
  return value as Record<string, unknown>;
}

function requireString(record: Record<string, unknown>, field: string): string {
  const value = record[field];
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid PLwC Chat Bridge build identity ${field}.`);
  }
  return value;
}

export function parseBuildIdentity(value: unknown): BuildIdentity {
  const record = requireRecord(value, "document");
  const installer = requireRecord(record.installer, "installer");
  const components = requireRecord(record.components, "components");
  const releaseVersion = requireString(record, "releaseVersion");
  const buildId = requireString(record, "buildId");
  const directoryName = requireString(installer, "directoryName");
  if (
    record.schemaVersion !== 1 ||
    record.product !== "PLwC Chat Bridge" ||
    buildId !== `plwc-chat-bridge@${releaseVersion}` ||
    installer.componentId !== "chat-bridge" ||
    directoryName !== "bridge"
  ) {
    throw new Error("Inconsistent PLwC Chat Bridge build identity.");
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
      directoryName,
    },
    product: "PLwC Chat Bridge",
    releaseVersion,
    schemaVersion: 1,
  };
}

export const EXTENSION_BUILD_IDENTITY = parseBuildIdentity(PLWC_BUILD_IDENTITY);

export function validateBuildIdentity(
  actual: BuildIdentity,
  expected = EXTENSION_BUILD_IDENTITY,
): BuildIdentityValidation {
  const mismatches: string[] = [];
  if (actual.buildId !== expected.buildId) mismatches.push("buildId");
  if (actual.releaseVersion !== expected.releaseVersion) mismatches.push("releaseVersion");
  if (actual.installer.componentId !== expected.installer.componentId) mismatches.push("installer.componentId");
  if (actual.installer.directoryName !== expected.installer.directoryName) mismatches.push("installer.directoryName");
  for (const component of ["nodeBridge", "browserExtension", "nativeLauncher"] as const) {
    if (actual.components[component] !== expected.components[component]) {
      mismatches.push(`components.${component}`);
    }
  }
  return {
    actualBuildId: actual.buildId,
    expectedBuildId: expected.buildId,
    mismatches,
    valid: mismatches.length === 0,
  };
}
