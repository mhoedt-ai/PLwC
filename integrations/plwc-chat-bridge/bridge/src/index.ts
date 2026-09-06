import { loadConfig, ConfigurationError } from "./config.js";
import { GatewayClientSession } from "./gateway-session.js";
import { LoopbackBridgeServer } from "./server.js";

function configArgument(args: readonly string[]): string {
  const index = args.indexOf("--config");
  const value = index === -1 ? undefined : args[index + 1];
  if (value === undefined || value.trim() === "") {
    throw new ConfigurationError("A bridge configuration file must be provided with --config.");
  }
  return value;
}

async function main(): Promise<void> {
  const config = await loadConfig(configArgument(process.argv.slice(2)));
  const session = new GatewayClientSession(config.gateway);
  const bridge = new LoopbackBridgeServer(config.bridge, session);
  await bridge.start();

  process.stdout.write(`PLwC Chat Bridge listening on ws://127.0.0.1:${config.bridge.port}${config.bridge.path}\n`);

  let shuttingDown = false;
  const shutdown = async (): Promise<void> => {
    if (shuttingDown) {
      return;
    }
    shuttingDown = true;
    await bridge.stop();
  };

  process.once("SIGINT", () => void shutdown());
  process.once("SIGTERM", () => void shutdown());
}

void main().catch((error: unknown) => {
  const message = error instanceof ConfigurationError ? error.message : "PLwC Chat Bridge could not be started.";
  process.stderr.write(`${message}\n`);
  process.exitCode = 1;
});
