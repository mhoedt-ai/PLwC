import assert from "node:assert/strict";
import test from "node:test";

import { classifyToolResult, normalizeToolResult, presentToolResult } from "./tool-result";

test("prefers structured MCP content and keeps the error flag", () => {
  assert.deepEqual(
    normalizeToolResult({
      content: [{ type: "text", text: "{\"ok\":false}" }],
      structuredContent: { ok: true, value: 42 },
      isError: true,
    }),
    { isError: true, result: { ok: true, value: 42 } },
  );
});

test("parses a single JSON text result when structured content is unavailable", () => {
  assert.deepEqual(
    normalizeToolResult({ content: [{ type: "text", text: "{\"ok\":true}" }], isError: false }),
    { isError: false, result: { ok: true } },
  );
});

test("classifies structured domain failures instead of trusting only the MCP error flag", () => {
  assert.equal(classifyToolResult(false, { ok: true, policy_decision: "ALLOW" }), "succeeded");
  assert.equal(
    classifyToolResult(false, {
      error: "Path is outside the allowed roots.",
      ok: false,
      policy_decision: "DENY",
    }),
    "denied",
  );
  assert.equal(
    classifyToolResult(false, { error: "Source file does not exist.", ok: false, policy_decision: "ALLOW" }),
    "failed",
  );
  assert.equal(classifyToolResult(true, { error: "Transport failed." }), "failed");
});

test("presents runtime status without repeated profile diagnostics", () => {
  const result = presentToolResult("plwc_status", {
    ok: true,
    scope: "runtime",
    workspace_root: "C:\\workspace",
    active_profile_name: "WasIstDas",
    expected_public_tool_count: 8,
    registered_public_tool_count: 8,
    available_profiles: [{ name: "large repeated payload" }],
    governance_thresholds: { memory_write_threshold: 2 },
    profile_compile: { persona_layer_enabled: false },
  });

  assert.deepEqual(result, {
    ok: true,
    server: undefined,
    version: undefined,
    scope: "runtime",
    workspace_root: "C:\\workspace",
    profile_root: undefined,
    active_profile_name: "WasIstDas",
    active_profile_source: undefined,
    profile_exists: undefined,
    profile_valid: undefined,
    policy_config_source: undefined,
    security_config_path: undefined,
    tools: { expected: 8, registered: 8 },
    governance_thresholds: { memory_write_threshold: 2 },
    persona_layer_enabled: false,
    setup_warnings: undefined,
  });
  assert.equal(JSON.stringify(result).includes("available_profiles"), false);
});
