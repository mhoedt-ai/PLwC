export const BRIDGE_VERSION = "0.2.0-rc19.dev0";
export const BRIDGE_ENDPOINT = "ws://127.0.0.1:3007/message";

export const CANONICAL_TOOL_NAMES = [
  "plwc_status",
  "plwc_describe",
  "plwc_profile",
  "plwc_reflection",
  "plwc_governor",
  "plwc_sandbox_run",
  "plwc_workspace_operation",
  "plwc_document_operation",
] as const;

export type CanonicalToolName = (typeof CANONICAL_TOOL_NAMES)[number];
export type JsonObject = Record<string, unknown>;

export interface McpTool {
  name: string;
  description?: string;
  inputSchema: JsonObject;
}

export interface ToolSetValidation {
  valid: boolean;
  tools: McpTool[];
  missing: string[];
  extra: string[];
  duplicates: string[];
  invalidSchemas: string[];
}

export function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function validateToolSet(value: unknown): ToolSetValidation {
  const source = isJsonObject(value) && Array.isArray(value.tools) ? value.tools : value;
  const candidates = Array.isArray(source) ? source : [];
  const parsed = candidates.filter(isJsonObject).map((item) => ({
    description: typeof item.description === "string" ? item.description : undefined,
    inputSchema: isJsonObject(item.inputSchema) ? item.inputSchema : {},
    name: typeof item.name === "string" ? item.name : "",
  }));

  const counts = new Map<string, number>();
  for (const tool of parsed) {
    counts.set(tool.name, (counts.get(tool.name) ?? 0) + 1);
  }

  const expected = new Set<string>(CANONICAL_TOOL_NAMES);
  const received = new Set(parsed.map((tool) => tool.name).filter(Boolean));
  const missing = CANONICAL_TOOL_NAMES.filter((name) => !received.has(name));
  const extra = [...received].filter((name) => !expected.has(name)).sort();
  const duplicates = [...counts.entries()]
    .filter(([, count]) => count > 1)
    .map(([name]) => name)
    .sort();
  const invalidSchemas = parsed
    .filter((tool) => Object.keys(tool.inputSchema).length === 0)
    .map((tool) => tool.name || "<unnamed>")
    .sort();

  const byName = new Map(parsed.map((tool) => [tool.name, tool]));
  const tools = CANONICAL_TOOL_NAMES.flatMap((name) => {
    const tool = byName.get(name);
    return tool ? [tool] : [];
  });
  const valid =
    candidates.length === CANONICAL_TOOL_NAMES.length &&
    parsed.length === candidates.length &&
    missing.length === 0 &&
    extra.length === 0 &&
    duplicates.length === 0 &&
    invalidSchemas.length === 0;

  return { duplicates, extra, invalidSchemas, missing, tools, valid };
}

export function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  if (isJsonObject(value)) {
    const entries = Object.keys(value)
      .filter((key) => value[key] !== undefined)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

export async function sha256(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
