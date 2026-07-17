import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

export interface BridgeConfig {
  bridge: {
    host: "127.0.0.1";
    port: number;
    path: string;
  };
  gateway: {
    command: string;
    args: string[];
    cwd?: string;
    env: Record<string, string>;
  };
}

export class ConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ConfigurationError";
  }
}

type JsonRecord = Record<string, unknown>;

function asObject(value: unknown, field: string): JsonRecord {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ConfigurationError(`Configuration field ${field} must be an object.`);
  }
  return value as JsonRecord;
}

function asString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new ConfigurationError(`Configuration field ${field} must be a non-empty string.`);
  }
  return value;
}

function expand(
  value: string,
  field: string,
  variables: Readonly<Record<string, string | undefined>>,
): string {
  return value.replace(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_match, name: string) => {
    const replacement = variables[name];
    if (replacement === undefined) {
      throw new ConfigurationError(`Configuration field ${field} contains an unresolved placeholder.`);
    }
    return replacement;
  });
}

function parseConfig(value: unknown, configPath: string): BridgeConfig {
  const root = asObject(value, "root");
  const bridge = asObject(root.bridge, "bridge");
  const gateway = asObject(root.gateway, "gateway");

  if (bridge.host !== "127.0.0.1") {
    throw new ConfigurationError("Configuration field bridge.host must be 127.0.0.1.");
  }

  if (!Number.isSafeInteger(bridge.port) || (bridge.port as number) < 1 || (bridge.port as number) > 65535) {
    throw new ConfigurationError("Configuration field bridge.port must be an integer from 1 through 65535.");
  }

  const socketPath = asString(bridge.path, "bridge.path");
  if (!/^\/[A-Za-z0-9._~!$&'()*+,;=:@/-]*$/.test(socketPath) || socketPath.includes("//")) {
    throw new ConfigurationError("Configuration field bridge.path must be a normalized absolute URL path.");
  }

  const configDir = dirname(resolve(configPath));
  const variables: Record<string, string | undefined> = {
    ...process.env,
    configDir,
    repoRoot: resolve(configDir, "../../.."),
  };

  const command = expand(asString(gateway.command, "gateway.command"), "gateway.command", variables);
  const rawArgs = gateway.args ?? [];
  if (!Array.isArray(rawArgs) || rawArgs.some((item) => typeof item !== "string")) {
    throw new ConfigurationError("Configuration field gateway.args must be an array of strings.");
  }
  const args = rawArgs.map((item, index) => expand(item as string, `gateway.args[${index}]`, variables));

  let cwd: string | undefined;
  if (gateway.cwd !== undefined) {
    cwd = expand(asString(gateway.cwd, "gateway.cwd"), "gateway.cwd", variables);
  }

  const rawEnv = gateway.env === undefined ? {} : asObject(gateway.env, "gateway.env");
  const env: Record<string, string> = {};
  for (const [name, rawValue] of Object.entries(rawEnv)) {
    env[name] = expand(asString(rawValue, `gateway.env.${name}`), `gateway.env.${name}`, variables);
  }

  return {
    bridge: { host: "127.0.0.1", port: bridge.port as number, path: socketPath },
    gateway: cwd === undefined ? { command, args, env } : { command, args, cwd, env },
  };
}

export async function loadConfig(configPath: string): Promise<BridgeConfig> {
  let source: string;
  try {
    source = await readFile(configPath, "utf8");
  } catch {
    throw new ConfigurationError("The bridge configuration file could not be read.");
  }

  let value: unknown;
  try {
    value = JSON.parse(source) as unknown;
  } catch {
    throw new ConfigurationError("The bridge configuration file is not valid JSON.");
  }

  return parseConfig(value, configPath);
}
