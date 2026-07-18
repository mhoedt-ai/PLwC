import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { Tool } from "@modelcontextprotocol/sdk/types.js";
import { isAbsolute } from "node:path";

import type { BridgeConfig } from "./config.js";
import { assertCanonicalTools, isCanonicalToolName, ToolContractError } from "./contract.js";

export interface BridgeSession {
  start(): Promise<void>;
  listTools(): Promise<Tool[]>;
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>;
  settings(): GatewaySettingsSnapshot;
  updateSettings(settings: GatewaySettingsUpdate): Promise<GatewaySettingsSnapshot>;
  resetSettings(): Promise<GatewaySettingsSnapshot>;
  close(): Promise<void>;
}

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

const SETTINGS_ENVIRONMENT = {
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

const SETTING_KEYS = Object.keys(SETTINGS_ENVIRONMENT) as Array<keyof GatewaySettingsUpdate>;
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

function childEnvironment(overrides: Readonly<Record<string, string>>): Record<string, string> {
  const inherited = Object.fromEntries(
    Object.entries(process.env).filter((entry): entry is [string, string] => entry[1] !== undefined),
  );
  return { ...inherited, ...overrides };
}

export class GatewayClientSession implements BridgeSession {
  private client: Client | undefined;
  private transport: StdioClientTransport | undefined;
  private state: "idle" | "starting" | "ready" | "restarting" | "closed" = "idle";
  private runtimeSettings: GatewaySettingsUpdate | null = null;
  private settingsUpdate: Promise<GatewaySettingsSnapshot> | null = null;

  constructor(private readonly gateway: BridgeConfig["gateway"]) {}

  async start(): Promise<void> {
    if (this.state !== "idle") {
      throw new Error("Gateway session cannot be started more than once.");
    }
    this.state = "starting";

    const transportOptions = {
      command: this.gateway.command,
      args: this.gateway.args,
      env: this.effectiveEnvironment(),
      stderr: "pipe" as const,
      ...(this.gateway.cwd === undefined ? {} : { cwd: this.gateway.cwd }),
    };
    const transport = new StdioClientTransport(transportOptions);
    const client = new Client({ name: "plwc-chat-bridge", version: "0.2.0-rc19.dev7" }, { capabilities: {} });
    this.transport = transport;
    this.client = client;

    try {
      await client.connect(transport);
      await this.fetchCanonicalTools();
      this.state = "ready";
    } catch (error) {
      await this.closeResources();
      this.state = "closed";
      if (error instanceof ToolContractError) {
        throw error;
      }
      throw new Error("The PLwC gateway could not be started.");
    }
  }

  async listTools(): Promise<Tool[]> {
    this.assertReady();
    return this.fetchCanonicalTools();
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    this.assertReady();
    if (!isCanonicalToolName(name)) {
      throw new ToolContractError();
    }

    // Revalidate immediately before execution. callTool itself is invoked once;
    // an ambiguous mutating failure is returned and is never retried here.
    await this.fetchCanonicalTools();
    return this.client!.callTool({ name, arguments: args });
  }

  settings(): GatewaySettingsSnapshot {
    const settings = gatewaySettingsFromEnvironment(this.effectiveEnvironment());
    if (this.runtimeSettings !== null) {
      settings.source = "PLwC Chat Bridge saved settings";
    }
    return settings;
  }

  async updateSettings(settings: GatewaySettingsUpdate): Promise<GatewaySettingsSnapshot> {
    const normalized = parseGatewaySettingsUpdate(settings);
    return this.runSettingsUpdate(normalized);
  }

  async resetSettings(): Promise<GatewaySettingsSnapshot> {
    return this.runSettingsUpdate(null);
  }

  async close(): Promise<void> {
    if (this.state === "closed") {
      return;
    }
    this.state = "closed";
    await this.closeResources();
  }

  private assertReady(): void {
    if (this.state !== "ready" || this.client === undefined) {
      throw new Error("The PLwC gateway session is not available.");
    }
  }

  private effectiveEnvironment(): Record<string, string> {
    const environment = childEnvironment(this.gateway.env);
    if (this.runtimeSettings === null) return environment;
    for (const key of SETTING_KEYS) {
      const environmentName = SETTINGS_ENVIRONMENT[key];
      const value = this.runtimeSettings[key];
      if (value === null) {
        delete environment[environmentName];
      } else {
        environment[environmentName] = value;
      }
    }
    environment.PLWC_CHAT_BRIDGE_SETTINGS_SOURCE = "PLwC Chat Bridge saved settings";
    return environment;
  }

  private runSettingsUpdate(next: GatewaySettingsUpdate | null): Promise<GatewaySettingsSnapshot> {
    if (this.settingsUpdate !== null) {
      throw new Error("A gateway settings update is already in progress.");
    }
    if (JSON.stringify(next) === JSON.stringify(this.runtimeSettings)) {
      return Promise.resolve(this.settings());
    }
    const operation = this.restartWithSettings(next);
    this.settingsUpdate = operation;
    operation.then(
      () => {
        this.settingsUpdate = null;
      },
      () => {
        this.settingsUpdate = null;
      },
    );
    return operation;
  }

  private async restartWithSettings(next: GatewaySettingsUpdate | null): Promise<GatewaySettingsSnapshot> {
    const previous = this.runtimeSettings;
    this.state = "restarting";
    await this.closeResources();
    this.runtimeSettings = next;
    this.state = "idle";
    try {
      await this.start();
      return this.settings();
    } catch {
      this.runtimeSettings = previous;
      this.state = "idle";
      try {
        await this.start();
      } catch {
        // The public error remains generic even when rollback cannot restore the child.
      }
      throw new Error("Updated PLwC settings could not be applied.");
    }
  }

  private async fetchCanonicalTools(): Promise<Tool[]> {
    if (this.client === undefined) {
      throw new Error("The PLwC gateway session is not available.");
    }

    const tools: Tool[] = [];
    let cursor: string | undefined;
    do {
      const page = await this.client.listTools(cursor === undefined ? {} : { cursor });
      tools.push(...page.tools);
      cursor = page.nextCursor;
    } while (cursor !== undefined);

    assertCanonicalTools(tools);
    return tools;
  }

  private async closeResources(): Promise<void> {
    const client = this.client;
    const transport = this.transport;
    this.client = undefined;
    this.transport = undefined;

    if (client !== undefined) {
      try {
        await client.close();
        return;
      } catch {
        // Fall through and close the transport directly.
      }
    }
    if (transport !== undefined) {
      try {
        await transport.close();
      } catch {
        // Shutdown remains best-effort and never exposes child-process details.
      }
    }
  }
}
