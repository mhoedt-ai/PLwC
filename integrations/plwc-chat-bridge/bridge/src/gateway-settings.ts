import { isAbsolute } from "node:path";

export interface GatewaySettingsSnapshot {
  source: string;
  workspacePath: string | null;
  profilesPath: string | null;
  activeProfileName: string | null;
  securityConfig: string | null;
  memoryWriteThreshold: string | null;
  personaWriteThreshold: string | null;
  temperamentWriteThreshold: string | null;
  qdrantEnabled: string | null;
  personaLayerDisabled: string | null;
}

export type GatewaySettingsUpdate = Omit<GatewaySettingsSnapshot, "source">;

export const SETTINGS_ENVIRONMENT = {
  activeProfileName: "PLWC_ACTIVE_PROFILE_NAME",
  memoryWriteThreshold: "PLWC_MEMORY_WRITE_THRESHOLD",
  personaLayerDisabled: "PLWC_PERSONA_LAYER_DISABLED",
  personaWriteThreshold: "PLWC_PERSONA_WRITE_THRESHOLD",
  profilesPath: "PLWC_PROFILE_ROOT",
  qdrantEnabled: "PLWC_QDRANT_ENABLED",
  securityConfig: "PLWC_CONFIG_FILE",
  temperamentWriteThreshold: "PLWC_TEMPERAMENT_WRITE_THRESHOLD",
  workspacePath: "PLWC_WORKSPACE_ROOT",
} as const satisfies Record<keyof GatewaySettingsUpdate, string>;

export const SETTING_KEYS = Object.keys(SETTINGS_ENVIRONMENT) as Array<keyof GatewaySettingsUpdate>;
const PATH_SETTING_KEYS = new Set<keyof GatewaySettingsUpdate>([
  "workspacePath",
  "profilesPath",
  "securityConfig",
]);
const THRESHOLD_SETTING_KEYS = new Set<keyof GatewaySettingsUpdate>([
  "memoryWriteThreshold",
  "personaWriteThreshold",
  "temperamentWriteThreshold",
]);
const BOOLEAN_SETTING_KEYS = new Set<keyof GatewaySettingsUpdate>([
  "qdrantEnabled",
  "personaLayerDisabled",
]);

function setting(
  environment: Readonly<Record<string, string | undefined>>,
  name: string,
): string | null {
  const value = environment[name]?.trim();
  return value ? value : null;
}

export function gatewaySettingsFromEnvironment(
  environment: Readonly<Record<string, string | undefined>>,
): GatewaySettingsSnapshot {
  return {
    source: setting(environment, "PLWC_CHAT_BRIDGE_SETTINGS_SOURCE") ?? "Bridge process / PLwC defaults",
    workspacePath: setting(environment, "PLWC_WORKSPACE_ROOT"),
    profilesPath: setting(environment, "PLWC_PROFILE_ROOT"),
    activeProfileName: setting(environment, "PLWC_ACTIVE_PROFILE_NAME"),
    securityConfig: setting(environment, "PLWC_CONFIG_FILE"),
    memoryWriteThreshold: setting(environment, "PLWC_MEMORY_WRITE_THRESHOLD"),
    personaWriteThreshold: setting(environment, "PLWC_PERSONA_WRITE_THRESHOLD"),
    temperamentWriteThreshold: setting(environment, "PLWC_TEMPERAMENT_WRITE_THRESHOLD"),
    qdrantEnabled: setting(environment, "PLWC_QDRANT_ENABLED"),
    personaLayerDisabled: setting(environment, "PLWC_PERSONA_LAYER_DISABLED"),
  };
}

export function parseGatewaySettingsUpdate(value: unknown): GatewaySettingsUpdate {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Gateway settings must be an object.");
  }
  const record = value as Record<string, unknown>;
  if (
    Object.keys(record).length !== SETTING_KEYS.length ||
    Object.keys(record).some((key) => !SETTING_KEYS.includes(key as keyof GatewaySettingsUpdate))
  ) {
    throw new Error("Gateway settings must contain exactly the supported fields.");
  }

  const parsed = {} as GatewaySettingsUpdate;
  for (const key of SETTING_KEYS) {
    const raw = record[key];
    if (raw === null) {
      parsed[key] = null;
      continue;
    }
    if (typeof raw !== "string" || raw.trim() === "" || raw.length > 4_096) {
      throw new Error(`Gateway setting ${key} is invalid.`);
    }
    const normalized = raw.trim();
    if (/[\u0000-\u001f\u007f]/u.test(normalized)) {
      throw new Error(`Gateway setting ${key} contains control characters.`);
    }
    if (PATH_SETTING_KEYS.has(key) && !isAbsolute(normalized)) {
      throw new Error(`Gateway setting ${key} must be an absolute path.`);
    }
    if (THRESHOLD_SETTING_KEYS.has(key)) {
      if (!/^(?:0|[1-9][0-9]*)$/u.test(normalized) || Number(normalized) > 1_000_000) {
        throw new Error(`Gateway setting ${key} must be a nonnegative integer.`);
      }
    }
    if (BOOLEAN_SETTING_KEYS.has(key) && normalized !== "true" && normalized !== "false") {
      throw new Error(`Gateway setting ${key} must be true or false.`);
    }
    parsed[key] = normalized;
  }
  return parsed;
}

export function sameGatewaySettings(
  left: GatewaySettingsUpdate | null,
  right: GatewaySettingsUpdate | null,
): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function profileName(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function sameProfile(left: string | null, right: string | null): boolean {
  return left !== null && right !== null && left.localeCompare(right, undefined, { sensitivity: "accent" }) === 0;
}

export function assertActiveProfileStatus(
  value: unknown,
  expectedProfile: string | null,
): void {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("PLwC runtime status did not contain structured profile data.");
  }
  const status = value as Record<string, unknown>;
  const configured = profileName(status.configured_active_profile);
  const resolved = profileName(status.resolved_active_profile);
  const active = profileName(status.active_profile_name);

  if (expectedProfile === null) {
    if (
      configured !== null &&
      (!sameProfile(configured, resolved) || !sameProfile(configured, active))
    ) {
      throw new Error("PLwC runtime reported conflicting active profiles.");
    }
    return;
  }

  const expected = expectedProfile.trim();
  const directory = profileName(status.active_profile_directory);
  const directoryProfile = directory?.split(/[\\/]/u).filter(Boolean).at(-1) ?? null;
  if (
    !sameProfile(configured, expected) ||
    !sameProfile(resolved, expected) ||
    !sameProfile(active, expected) ||
    !sameProfile(directoryProfile, expected) ||
    status.profile_valid !== true
  ) {
    throw new Error(`PLwC runtime did not activate profile '${expected}'.`);
  }
}
