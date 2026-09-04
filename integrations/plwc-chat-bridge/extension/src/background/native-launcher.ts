import type { LauncherStatus, LauncherState } from "../shared/messages";
import {
  EXTENSION_BUILD_IDENTITY,
  parseBuildIdentity,
  validateBuildIdentity,
} from "../shared/build-identity";
import { RpcRequestError } from "./transport";

export const NATIVE_LAUNCHER_HOST = "plwc.chat_bridge.launcher";
export const NATIVE_LAUNCHER_PORT = 3007;
export const NATIVE_STARTUP_TIMEOUT_MS = 40_000;
export const NATIVE_STARTUP_RETRY_MS = 500;

const LAUNCHER_STATES = new Set<LauncherState>([
  "not_requested",
  "starting",
  "started",
  "already_running",
  "unavailable",
  "failed",
]);

export const INITIAL_LAUNCHER_STATUS: LauncherStatus = {
  code: "not_requested",
  message: "Native launcher has not been requested.",
  state: "not_requested",
};

export class NativeLauncherError extends RpcRequestError {
  constructor(
    message: string,
    code: string,
    readonly status: LauncherStatus,
  ) {
    super(message, code);
    this.name = "NativeLauncherError";
  }
}

export function parseNativeLauncherResponse(value: unknown): LauncherStatus {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    const status: LauncherStatus = {
      code: "native_launcher_invalid_response",
      message: "Native launcher returned an invalid response.",
      state: "failed",
    };
    throw new NativeLauncherError(status.message, status.code!, status);
  }

  const response = value as Record<string, unknown>;
  const message = typeof response.message === "string" ? response.message : "";
  const code = typeof response.code === "string" ? response.code : "native_launcher_failed";
  const logPath = typeof response.logPath === "string" ? response.logPath : undefined;
  const toolCount =
    typeof response.toolCount === "number" && Number.isSafeInteger(response.toolCount)
      ? response.toolCount
      : undefined;
  const rawState = response.state;
  const state =
    typeof rawState === "string" && LAUNCHER_STATES.has(rawState as LauncherState)
      ? rawState as LauncherState
      : "failed";
  let buildIdentity;
  let buildIdentityValidation;
  try {
    buildIdentity = parseBuildIdentity(response.buildIdentity);
    buildIdentityValidation = validateBuildIdentity(buildIdentity);
  } catch {
    buildIdentity = undefined;
    buildIdentityValidation = undefined;
  }
  const status: LauncherStatus = {
    ...(buildIdentity === undefined ? {} : { buildIdentity }),
    ...(buildIdentityValidation === undefined ? {} : { buildIdentityValidation }),
    code,
    ...(logPath === undefined ? {} : { logPath }),
    message: message || "Native launcher request completed.",
    state,
    ...(toolCount === undefined ? {} : { toolCount }),
  };

  if (response.ok !== true) {
    throw new NativeLauncherError(
      message || "Native launcher could not start PLwC Chat Bridge.",
      code,
      status,
    );
  }

  if (buildIdentityValidation?.valid !== true) {
    const invalidStatus: LauncherStatus = {
      ...status,
      code: "build_identity_mismatch",
      message: buildIdentity === undefined
        ? "Native launcher did not return a valid PLwC Chat Bridge build identity."
        : `Native launcher build identity mismatch: expected ${EXTENSION_BUILD_IDENTITY.buildId}, received ${buildIdentity.buildId}.`,
      state: "failed",
    };
    throw new NativeLauncherError(
      invalidStatus.message,
      invalidStatus.code!,
      invalidStatus,
    );
  }

  if (
    (state !== "started" && state !== "already_running") ||
    code !== "ready" ||
    toolCount !== 8
  ) {
    const invalidStatus: LauncherStatus = {
      ...status,
      code: "native_launcher_invalid_response",
      message: "Native launcher did not verify the eight-tool bridge contract.",
      state: "failed",
    };
    throw new NativeLauncherError(
      invalidStatus.message,
      invalidStatus.code!,
      invalidStatus,
    );
  }

  return status;
}

export function isRecoverableConnectionError(error: unknown): boolean {
  if (!(error instanceof RpcRequestError)) return false;
  return error.code === "connection_closed" || error.code === "not_connected";
}

export async function connectAfterNativeStart(
  connect: () => Promise<void>,
  start: () => Promise<LauncherStatus>,
  wait: (milliseconds: number) => Promise<void>,
  timeoutMs = NATIVE_STARTUP_TIMEOUT_MS,
  retryMs = NATIVE_STARTUP_RETRY_MS,
): Promise<LauncherStatus> {
  const launchStatus = await start();
  const deadline = Date.now() + timeoutMs;
  let lastError = "";

  while (Date.now() < deadline) {
    await wait(retryMs);
    try {
      await connect();
      return launchStatus;
    } catch (error) {
      lastError = error instanceof Error ? error.message : "";
    }
  }

  throw new RpcRequestError(
    `Native launcher verified the bridge, but the browser connection did not become ready within ${timeoutMs} ms.${
      lastError ? ` Last error: ${lastError}` : ""
    }`,
    "native_launcher_timeout",
  );
}
