import assert from "node:assert/strict";
import test from "node:test";
import type { Tool } from "@modelcontextprotocol/sdk/types.js";

import { assertCanonicalTools, CANONICAL_TOOL_NAMES, ToolContractError } from "../src/contract.js";

const tool = (name: string): Tool => ({
  name,
  inputSchema: {
    type: "object",
    ...(name === "plwc_status"
      ? { properties: { profile_name: { default: "", type: "string" }, scope: { default: "", type: "string" } } }
      : {}),
  },
});

test("accepts exactly the eight canonical facade tools", () => {
  assert.doesNotThrow(() => assertCanonicalTools(CANONICAL_TOOL_NAMES.map(tool)));
});

test("fails closed for missing, extra and duplicate tools", () => {
  const exact = CANONICAL_TOOL_NAMES.map(tool);
  assert.throws(() => assertCanonicalTools(exact.slice(0, -1)), ToolContractError);
  assert.throws(() => assertCanonicalTools([...exact, tool("plwc_extra")]), ToolContractError);
  assert.throws(() => assertCanonicalTools([...exact.slice(0, -1), tool(CANONICAL_TOOL_NAMES[0])]), ToolContractError);
});

test("fails closed for a gateway that silently ignores requested profile status", () => {
  const tools = CANONICAL_TOOL_NAMES.map(tool);
  const legacyStatus = tools.find((candidate) => candidate.name === "plwc_status")!;
  legacyStatus.inputSchema = { properties: { scope: { type: "string" } }, type: "object" };

  assert.throws(() => assertCanonicalTools(tools), ToolContractError);
});
