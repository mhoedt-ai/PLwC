import { closeSync, mkdirSync, openSync, readFileSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

import { loadConfig } from "../dist/src/config.js";
import { verifyBridgeHealth } from "../dist/src/healthcheck.js";

function requiredArgument(name) {
  const index = process.argv.indexOf(name);
  const value = index >= 0 ? process.argv[index + 1] : undefined;
  if (!value) throw new Error(`Missing required launcher argument: ${name}`);
  return resolve(value);
}

function acquireLaunchLock(lockPath) {
  try {
    return openSync(lockPath, "wx");
  } catch (error) {
    if (error?.code !== "EEXIST") throw error;
    try {
      if (Date.now() - statSync(lockPath).mtimeMs > 60_000) {
        unlinkSync(lockPath);
        return openSync(lockPath, "wx");
      }
    } catch (staleError) {
      if (staleError?.code !== "ENOENT") throw staleError;
      return openSync(lockPath, "wx");
    }
    return undefined;
  }
}

const entry = requiredArgument("--entry");
const config = requiredArgument("--config");
const stdoutPath = requiredArgument("--stdout");
const stderrPath = requiredArgument("--stderr");
const pidPath = requiredArgument("--pid");
const scriptRoot = dirname(fileURLToPath(import.meta.url));
const identity = JSON.parse(
  readFileSync(resolve(scriptRoot, "../../native/extension-identity.json"), "utf8"),
);
const origin = identity.identities.development.webSocketOrigin;
const bridgeConfig = await loadConfig(config);
const endpoint =
  `ws://${bridgeConfig.bridge.host}:${bridgeConfig.bridge.port}${bridgeConfig.bridge.path}`;

const [nodeMajor, nodeMinor] = process.versions.node.split(".").map(Number);
if (nodeMajor < 22 || (nodeMajor === 22 && nodeMinor < 12)) {
  throw new Error("Node.js 22.12 or newer is required.");
}

mkdirSync(dirname(stdoutPath), { recursive: true });
mkdirSync(dirname(stderrPath), { recursive: true });
mkdirSync(dirname(pidPath), { recursive: true });
const launchLockPath = `${pidPath}.launch.lock`;
const launchLock = acquireLaunchLock(launchLockPath);

try {
  if (launchLock === undefined) {
    process.stdout.write(`${JSON.stringify({ launchInProgress: true })}\n`);
    process.exitCode = 0;
  } else {
    try {
      const health = await verifyBridgeHealth(endpoint, origin, 2_500);
      process.stdout.write(
        `${JSON.stringify({ alreadyRunning: true, toolCount: health.toolCount })}\n`,
      );
    } catch {
      const stdout = openSync(stdoutPath, "a");
      const stderr = openSync(stderrPath, "a");
      let child;
      try {
        child = spawn(process.execPath, [entry, "--config", config], {
          cwd: resolve(dirname(entry), "../../.."),
          detached: true,
          stdio: ["ignore", stdout, stderr],
          windowsHide: true,
        });
        await new Promise((resolveSpawn, rejectSpawn) => {
          child.once("spawn", resolveSpawn);
          child.once("error", rejectSpawn);
        });
        writeFileSync(pidPath, `${child.pid}\n`, "utf8");
        child.unref();
      } finally {
        closeSync(stdout);
        closeSync(stderr);
      }

      const deadline = Date.now() + 30_000;
      let healthError;
      while (Date.now() < deadline) {
        try {
          const health = await verifyBridgeHealth(endpoint, origin, 2_500);
          process.stdout.write(
            `${JSON.stringify({
              alreadyRunning: false,
              pid: child.pid,
              toolCount: health.toolCount,
            })}\n`,
          );
          healthError = undefined;
          break;
        } catch (error) {
          healthError = error;
          await new Promise((resolveDelay) => setTimeout(resolveDelay, 400));
        }
      }
      if (healthError !== undefined) {
        try {
          process.kill(child.pid);
        } catch {
          // The child may already have exited after logging its startup error.
        }
        try {
          unlinkSync(pidPath);
        } catch (error) {
          if (error?.code !== "ENOENT") throw error;
        }
        throw healthError;
      }
    }
  }
} finally {
  if (launchLock !== undefined) {
    closeSync(launchLock);
    try {
      unlinkSync(launchLockPath);
    } catch (error) {
      if (error?.code !== "ENOENT") throw error;
    }
  }
}
