import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { Tool } from "@modelcontextprotocol/sdk/types.js";

import type { BridgeConfig } from "./config.js";
import { assertCanonicalTools, isCanonicalToolName, ToolContractError } from "./contract.js";

export interface BridgeSession {
  start(): Promise<void>;
  listTools(): Promise<Tool[]>;
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>;
  settings(): GatewaySettingsSnapshot;
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

function childEnvironment(overrides: Readonly<Record<string, string>>): Record<string, string> {
  const inherited = Object.fromEntries(
    Object.entries(process.env).filter((entry): entry is [string, string] => entry[1] !== undefined),
  );
  return { ...inherited, ...overrides };
}

export class GatewayClientSession implements BridgeSession {
  private client: Client | undefined;
  private transport: StdioClientTransport | undefined;
  private state: "idle" | "starting" | "ready" | "closed" = "idle";

  constructor(private readonly gateway: BridgeConfig["gateway"]) {}

  async start(): Promise<void> {
    if (this.state !== "idle") {
      throw new Error("Gateway session cannot be started more than once.");
    }
    this.state = "starting";

    const transportOptions = {
      command: this.gateway.command,
      args: this.gateway.args,
      env: childEnvironment(this.gateway.env),
      stderr: "pipe" as const,
      ...(this.gateway.cwd === undefined ? {} : { cwd: this.gateway.cwd }),
    };
    const transport = new StdioClientTransport(transportOptions);
    const client = new Client({ name: "plwc-chat-bridge", version: "0.2.0-rc19.dev4" }, { capabilities: {} });
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
    return gatewaySettingsFromEnvironment({ ...process.env, ...this.gateway.env });
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
