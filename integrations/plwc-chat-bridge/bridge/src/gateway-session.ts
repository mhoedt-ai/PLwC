import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { Tool } from "@modelcontextprotocol/sdk/types.js";

import type { BridgeConfig } from "./config.js";
import { assertCanonicalTools, isCanonicalToolName, ToolContractError } from "./contract.js";
import {
  assertActiveProfileStatus,
  gatewaySettingsFromEnvironment,
  parseGatewaySettingsUpdate,
  sameGatewaySettings,
  SETTINGS_ENVIRONMENT,
  SETTING_KEYS,
  type GatewaySettingsSnapshot,
  type GatewaySettingsUpdate,
} from "./gateway-settings.js";
import {
  FileSystemGatewaySettingsStore,
  type GatewaySettingsStore,
} from "./gateway-settings-store.js";

export {
  gatewaySettingsFromEnvironment,
  parseGatewaySettingsUpdate,
  type GatewaySettingsSnapshot,
  type GatewaySettingsUpdate,
} from "./gateway-settings.js";

export interface BridgeSession {
  start(): Promise<void>;
  listTools(): Promise<Tool[]>;
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>;
  settings(): GatewaySettingsSnapshot;
  updateSettings(settings: GatewaySettingsUpdate): Promise<GatewaySettingsSnapshot>;
  resetSettings(): Promise<GatewaySettingsSnapshot>;
  close(): Promise<void>;
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
  private persistedSettingsLoaded = false;

  constructor(
    private readonly gateway: BridgeConfig["gateway"],
    private readonly settingsStore: GatewaySettingsStore = new FileSystemGatewaySettingsStore(),
  ) {}

  async start(): Promise<void> {
    if (this.state !== "idle") {
      throw new Error("Gateway session cannot be started more than once.");
    }
    this.state = "starting";
    if (!this.persistedSettingsLoaded) {
      this.runtimeSettings = await this.settingsStore.load();
      this.persistedSettingsLoaded = true;
    }

    const transportOptions = {
      command: this.gateway.command,
      args: this.gateway.args,
      env: this.effectiveEnvironment(),
      stderr: "pipe" as const,
      ...(this.gateway.cwd === undefined ? {} : { cwd: this.gateway.cwd }),
    };
    const transport = new StdioClientTransport(transportOptions);
    const client = new Client({ name: "plwc-chat-bridge", version: "1.0.0" }, { capabilities: {} });
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
      settings.source = "PLwC shared settings";
    }
    return settings;
  }

  async updateSettings(settings: GatewaySettingsUpdate): Promise<GatewaySettingsSnapshot> {
    const normalized = parseGatewaySettingsUpdate(settings);
    const persisted = await this.settingsStore.load();
    if (sameGatewaySettings(normalized, this.runtimeSettings) && sameGatewaySettings(normalized, persisted)) {
      return this.settings();
    }
    await this.settingsStore.save(normalized);
    try {
      return await this.runSettingsUpdate(normalized);
    } catch (error) {
      if (persisted === null) {
        await this.settingsStore.clear();
      } else {
        await this.settingsStore.save(persisted);
      }
      throw error;
    }
  }

  async resetSettings(): Promise<GatewaySettingsSnapshot> {
    const persisted = await this.settingsStore.load();
    await this.settingsStore.clear();
    try {
      return await this.runSettingsUpdate(null);
    } catch (error) {
      if (persisted !== null) await this.settingsStore.save(persisted);
      throw error;
    }
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
    environment.PLWC_CHAT_BRIDGE_SETTINGS_SOURCE = "PLwC shared settings";
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
      await this.verifyActiveProfile(null);
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

  private async verifyActiveProfile(expectedProfile: string | null): Promise<void> {
    if (this.client === undefined) {
      throw new Error("The PLwC gateway session is not available.");
    }
    const response = await this.client.callTool({
      name: "plwc_status",
      arguments: { scope: "runtime" },
    });
    assertActiveProfileStatus(response.structuredContent, expectedProfile);
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
