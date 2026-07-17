import assert from "node:assert/strict";
import test from "node:test";
import type { Tool } from "@modelcontextprotocol/sdk/types.js";

import { assertCanonicalTools, CANONICAL_TOOL_NAMES, ToolContractError } from "../src/contract.js";

const tool = (name: string): Tool => ({ name, inputSchema: { type: "object" } });

test("accepts exactly the eight canonical facade tools", () => {
  assert.doesNotThrow(() => assertCanonicalTools(CANONICAL_TOOL_NAMES.map(tool)));
});

test("fails closed for missing, extra and duplicate tools", () => {
  const exact = CANONICAL_TOOL_NAMES.map(tool);
  assert.throws(() => assertCanonicalTools(exact.slice(0, -1)), ToolContractError);
  assert.throws(() => assertCanonicalTools([...exact, tool("plwc_extra")]), ToolContractError);
  assert.throws(() => assertCanonicalTools([...exact.slice(0, -1), tool(CANONICAL_TOOL_NAMES[0])]), ToolContractError);
});
