import type { Tool } from "@modelcontextprotocol/sdk/types.js";

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

const canonicalNameSet = new Set<string>(CANONICAL_TOOL_NAMES);

export class ToolContractError extends Error {
  constructor() {
    super("The gateway tool contract does not match the PLwC public facade.");
    this.name = "ToolContractError";
  }
}

export function assertCanonicalTools(tools: readonly Tool[]): void {
  if (tools.length !== CANONICAL_TOOL_NAMES.length) {
    throw new ToolContractError();
  }

  const names = tools.map((tool) => tool.name);
  if (new Set(names).size !== names.length || names.some((name) => !canonicalNameSet.has(name))) {
    throw new ToolContractError();
  }
}

export function isCanonicalToolName(name: string): name is (typeof CANONICAL_TOOL_NAMES)[number] {
  return canonicalNameSet.has(name);
}
