export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: number;
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcErrorBody {
  code: number;
  message: string;
}

export class RpcFault extends Error {
  constructor(
    readonly code: number,
    message: string,
  ) {
    super(message);
    this.name = "RpcFault";
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseRequest(source: string): JsonRpcRequest {
  let value: unknown;
  try {
    value = JSON.parse(source) as unknown;
  } catch {
    throw new RpcFault(-32700, "Invalid JSON.");
  }

  if (
    !isObject(value) ||
    value.jsonrpc !== "2.0" ||
    typeof value.method !== "string" ||
    value.method.trim() === ""
  ) {
    throw new RpcFault(-32600, "Invalid JSON-RPC request.");
  }
  if (!Number.isSafeInteger(value.id) || (value.id as number) < 0) {
    throw new RpcFault(-32600, "JSON-RPC id must be a non-negative integer.");
  }
  if (value.params !== undefined && !isObject(value.params)) {
    throw new RpcFault(-32602, "JSON-RPC params must be an object.");
  }

  return value.params === undefined
    ? { jsonrpc: "2.0", id: value.id as number, method: value.method }
    : { jsonrpc: "2.0", id: value.id as number, method: value.method, params: value.params };
}

export function success(id: number, result: unknown): string {
  return JSON.stringify({ jsonrpc: "2.0", id, result });
}

export function failure(id: number | null, error: JsonRpcErrorBody): string {
  return JSON.stringify({ jsonrpc: "2.0", id, error });
}
