import {
  mkdir,
  readFile,
  rename,
  rm,
  stat,
  unlink,
  writeFile,
} from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { randomUUID } from "node:crypto";

import {
  parseGatewaySettingsUpdate,
  type GatewaySettingsUpdate,
} from "./gateway-settings.js";

const SHARED_SETTINGS_SCHEMA_VERSION = 1;

const SHARED_SETTING_NAMES = {
  activeProfileName: "active_profile_name",
  memoryWriteThreshold: "memory_write_threshold",
  personaLayerDisabled: "persona_layer_disabled",
  personaWriteThreshold: "persona_write_threshold",
  profilesPath: "profiles_path",
  qdrantEnabled: "qdrant_enabled",
  securityConfig: "security_config",
  temperamentWriteThreshold: "temperament_write_threshold",
  workspacePath: "workspace_path",
} as const satisfies Record<keyof GatewaySettingsUpdate, string>;

export interface GatewaySettingsStore {
  load(): Promise<GatewaySettingsUpdate | null>;
  save(settings: GatewaySettingsUpdate): Promise<void>;
  clear(): Promise<void>;
}

export interface GatewaySettingsPaths {
  sharedSettings: string;
  activeProfileState: string;
  claudeMcpbSettings: string;
}

interface FileChange {
  path: string;
  content: string | null;
}

interface PreviousFile {
  path: string;
  content: Buffer | null;
}

function appDataRoot(environment: NodeJS.ProcessEnv): string {
  const base = environment.APPDATA?.trim() || environment.LOCALAPPDATA?.trim();
  return base ? join(base, "PLwC") : join(homedir(), ".plwc");
}

export function defaultGatewaySettingsPaths(
  environment: NodeJS.ProcessEnv = process.env,
): GatewaySettingsPaths {
  const plwcRoot = appDataRoot(environment);
  const appData = environment.APPDATA?.trim() || environment.LOCALAPPDATA?.trim() || homedir();
  return {
    sharedSettings: join(plwcRoot, "config", "gateway-settings.json"),
    activeProfileState: join(plwcRoot, "config", "active_profile.json"),
    claudeMcpbSettings: join(
      appData,
      "Claude",
      "Claude Extensions Settings",
      "local.mcpb.plwc.plwc-gateway.json",
    ),
  };
}

function typedSetting(key: keyof GatewaySettingsUpdate, value: string | null): string | number | boolean | null {
  if (value === null) return null;
  if (
    key === "memoryWriteThreshold" ||
    key === "personaWriteThreshold" ||
    key === "temperamentWriteThreshold"
  ) {
    return Number(value);
  }
  if (key === "qdrantEnabled" || key === "personaLayerDisabled") {
    return value === "true";
  }
  return value;
}

function sharedSettingsRecord(settings: GatewaySettingsUpdate): Record<string, string | number | boolean | null> {
  return Object.fromEntries(
    Object.entries(SHARED_SETTING_NAMES).map(([key, name]) => [
      name,
      typedSetting(key as keyof GatewaySettingsUpdate, settings[key as keyof GatewaySettingsUpdate]),
    ]),
  );
}

function bridgeSettingsRecord(value: unknown): GatewaySettingsUpdate {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("Shared PLwC settings must be a JSON object.");
  }
  const payload = value as Record<string, unknown>;
  if (payload.schema_version !== SHARED_SETTINGS_SCHEMA_VERSION) {
    throw new Error("Shared PLwC settings use an unsupported schema version.");
  }
  if (typeof payload.settings !== "object" || payload.settings === null || Array.isArray(payload.settings)) {
    throw new Error("Shared PLwC settings do not contain a settings object.");
  }
  const stored = payload.settings as Record<string, unknown>;
  const update = {} as GatewaySettingsUpdate;
  for (const [key, storedName] of Object.entries(SHARED_SETTING_NAMES)) {
    const raw = stored[storedName];
    const target = key as keyof GatewaySettingsUpdate;
    if (raw === null) {
      update[target] = null;
    } else if (typeof raw === "boolean" || typeof raw === "number") {
      update[target] = String(raw);
    } else {
      update[target] = typeof raw === "string" ? raw : null;
    }
  }
  return parseGatewaySettingsUpdate(update);
}

function jsonText(value: unknown): string {
  return `${JSON.stringify(value, null, 2)}\n`;
}

async function fileExists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

async function readPrevious(path: string): Promise<PreviousFile> {
  try {
    return { path, content: await readFile(path) };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { path, content: null };
    }
    throw error;
  }
}

async function replaceFile(path: string, content: string | Buffer | null): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  if (content === null) {
    await unlink(path).catch((error: NodeJS.ErrnoException) => {
      if (error.code !== "ENOENT") throw error;
    });
    return;
  }

  const suffix = `${process.pid}-${randomUUID()}`;
  const temporary = `${path}.${suffix}.tmp`;
  const backup = `${path}.${suffix}.bak`;
  await writeFile(temporary, content, { flag: "wx" });
  const hadTarget = await fileExists(path);
  try {
    if (hadTarget) await rename(path, backup);
    await rename(temporary, path);
    if (hadTarget) await rm(backup, { force: true });
  } catch (error) {
    await rm(temporary, { force: true });
    if (hadTarget && await fileExists(backup)) {
      await rm(path, { force: true });
      await rename(backup, path);
    }
    throw error;
  }
}

async function applyChanges(changes: readonly FileChange[]): Promise<void> {
  const previous = await Promise.all(changes.map((change) => readPrevious(change.path)));
  const applied: PreviousFile[] = [];
  try {
    for (let index = 0; index < changes.length; index += 1) {
      const change = changes[index]!;
      await replaceFile(change.path, change.content);
      applied.push(previous[index]!);
    }
  } catch (error) {
    for (const file of applied.reverse()) {
      await replaceFile(file.path, file.content).catch(() => undefined);
    }
    throw error;
  }
}

async function claudeSettingsUpdate(
  path: string,
  settings: GatewaySettingsUpdate,
): Promise<string | null> {
  if (!await fileExists(path)) return null;
  const payload = JSON.parse(await readFile(path, "utf8")) as Record<string, unknown>;
  const currentUserConfig =
    typeof payload.userConfig === "object" && payload.userConfig !== null && !Array.isArray(payload.userConfig)
      ? payload.userConfig as Record<string, unknown>
      : {};
  const userConfig = { ...currentUserConfig };
  for (const [key, storedName] of Object.entries(SHARED_SETTING_NAMES)) {
    const setting = settings[key as keyof GatewaySettingsUpdate];
    if (setting === null) {
      delete userConfig[storedName];
    } else {
      userConfig[storedName] = typedSetting(key as keyof GatewaySettingsUpdate, setting);
    }
  }
  return jsonText({ ...payload, userConfig });
}

export class FileSystemGatewaySettingsStore implements GatewaySettingsStore {
  constructor(private readonly paths: GatewaySettingsPaths = defaultGatewaySettingsPaths()) {}

  async load(): Promise<GatewaySettingsUpdate | null> {
    try {
      const payload = JSON.parse(await readFile(this.paths.sharedSettings, "utf8"));
      return bridgeSettingsRecord(payload);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw new Error("Shared PLwC settings could not be loaded.");
    }
  }

  async save(settings: GatewaySettingsUpdate): Promise<void> {
    const normalized = parseGatewaySettingsUpdate(settings);
    const claudeSettings = await claudeSettingsUpdate(this.paths.claudeMcpbSettings, normalized);
    const changes: FileChange[] = [
      {
        path: this.paths.sharedSettings,
        content: jsonText({
          schema_version: SHARED_SETTINGS_SCHEMA_VERSION,
          settings: sharedSettingsRecord(normalized),
          updated_at: new Date().toISOString(),
          updated_by: "plwc-chat-bridge-settings",
        }),
      },
    ];
    if (claudeSettings !== null) {
      changes.push({ path: this.paths.claudeMcpbSettings, content: claudeSettings });
    }
    await applyChanges(changes);
  }

  async clear(): Promise<void> {
    await applyChanges([{ path: this.paths.sharedSettings, content: null }]);
  }
}
