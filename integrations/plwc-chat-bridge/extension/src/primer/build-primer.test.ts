import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPrimer,
  GUIDED_DOCUMENT_WORKFLOW_EXAMPLE,
  WORKSPACE_GUIDANCE_RULES,
} from "./build-primer";
import { CANONICAL_TOOL_NAMES } from "../shared/contracts";

const tools = CANONICAL_TOOL_NAMES.map((name) => {
  const properties = name === "plwc_status"
    ? { scope: { default: "", type: "string" } }
    : { operation: { type: "string" } };
  return {
    description: `${name} description`,
    inputSchema: { properties, type: "object" },
    name,
  };
});

test("builds the same primer and schema hash for equivalent tool sets", async () => {
  const first = await buildPrimer({ tools });
  const second = await buildPrimer({ tools: [...tools].reverse() });
  assert.equal(first.hash, second.hash);
  assert.equal(first.text, second.text);
  assert.match(first.text, /plwc_governor/);
  assert.match(first.text, /standing write confirmation/);
  assert.match(first.text, /Sandbox execution and unknown operations always require individual confirmation/);
  assert.match(first.text, /fenced json code block/);
  assert.match(first.text, /plwc_tool_call/);
  assert.match(first.text, /Emit at most one tool call at a time/);
  assert.match(first.text, /Never invent, skip, or wait for an unissued call_id/);
  assert.match(first.text, /Never claim that a result is missing for a call you did not emit/);
  assert.match(first.text, /describe_guidance_protocol/u);
  assert.match(first.text, /emit one precise plwc_describe call before the target call/u);
  assert.match(first.text, /scope=document_operation with operation=create_pdf/u);
  assert.match(first.text, /operation filter is valid only for scope=workspace_operation and scope=document_operation/u);
  assert.match(first.text, /Never send operation with plwc_describe scope=status/u);
  assert.match(first.text, /plwc_status is a separate tool, not a Describe operation/u);
  assert.ok(first.text.includes('{"scope":"first_run"}'));
  assert.match(first.text, /Never guess an operation name or operation arguments/u);
  assert.match(first.text, /next_tool, next_operation, next_plan_type, required_fields/u);
  assert.match(first.text, /Do not retry an unsupported operation with another guess/u);
  assert.match(first.text, /Unknown target operations are never eligible for automatic execution/u);
  assert.match(first.text, /large_work_protocol/);
  assert.match(first.text, /Do not serialize large generated files/u);
  assert.match(first.text, /plwc_sandbox_run call that reads workspace files and writes the derived artifacts locally/u);
  assert.match(first.text, /workspace_handling_rules_en/u);
  assert.match(first.text, /workspace_handling_rules_de/u);
  assert.match(first.text, /Temp\/<task-name>\//u);
  assert.match(first.text, /target path requested by the user/u);
  assert.match(first.text, /Bereinige Temp\/ niemals automatisch/u);
  assert.match(first.text, /Lösche keine Dateien oder Verzeichnisse im Workspace/u);
  assert.match(first.text, /explicit deletion request, offer to move the item to Trashcan\//u);
  assert.match(first.text, /Verschiebe niemals automatisch etwas nach Trashcan\//u);
  assert.match(first.text, /Do not create or use Inbox\//u);
  assert.match(first.text, /large_result_chunk_protocol/u);
  assert.match(first.text, /result_transport\.chunked=true/u);
  assert.match(first.text, /plwc_result_chunks\.v1/u);
  assert.match(first.text, /exactly total_chunks unique chunks/u);
  assert.match(first.text, /Recompute every chunk SHA-256/u);
  assert.match(first.text, /recompute the complete SHA-256/u);
  assert.match(first.text, /complete=true and no_omitted_content=true/u);
  assert.match(first.text, /result_summary instead of the reconstructed JSON/u);
  assert.match(first.text, /legacy_large_result_compact_protocol/u);
  assert.match(first.text, /profile_compile_layer_chunk_protocol/u);
  assert.match(first.text, /compile_mode=boot, working, and full/u);
  assert.match(first.text, /profile_compile_layer_chunked=true/u);
  assert.match(first.text, /data\.compiled_layer_transport\.chunks/u);
  assert.match(first.text, /received_chunks == total_chunks/u);
  assert.match(first.text, /sha256 == reconstructed_sha256/u);
  assert.match(first.text, /Do not request a sandbox artifact/u);
  assert.match(first.text, /profile_context_protocol/u);
  assert.match(first.text, /profile_name inspects a requested onboarding target only/u);
  assert.match(first.text, /requested_profile_name, active_profile_name, and profile_path semantically separate/u);
  assert.match(first.text, /do not tell the user to select it in Extension settings first/u);
  assert.match(first.text, /onboarding guidance returns next_tool, next_operation, next_plan_type/u);
  assert.match(first.text, /successful apply creates and activates the new profile/u);
  assert.match(first.text, /profile_activation Governor plan\/apply flow/u);
  assert.match(first.text, /Manual Extension settings changes are not required/u);
  assert.match(first.text, /search scans text contents/);
  assert.match(first.text, /verify the selected path with operation=file_info/);
  assert.match(first.text, /Never report them as found/);
  assert.match(first.text, /mutation succeeded only when its marked result contains ok=true/);
  assert.match(first.text, /summarize it naturally/);
  assert.match(first.text, /onboarding_continuation_protocol/u);
  assert.match(first.text, /plwc_onboarding_continuation\.v1/u);
  assert.match(first.text, /Never replace a continuation Governor call with plwc_describe/u);
  assert.match(first.text, /state=awaiting_user_confirmation does not grant confirmation/u);
  assert.match(first.text, /state=verify_active_profile follows a successful apply/u);
  assert.match(first.text, /tool_call_correction_protocol/u);
  assert.match(first.text, /plwc_tool_call_correction\.v1/u);
  assert.match(first.text, /invalid_onboarding_describe_filter/u);
  assert.match(first.text, /"arguments":\{"scope":"runtime"\}/);
  assert.match(first.text, /call_mask_json/);
  assert.doesNotMatch(first.text, new RegExp(["function", "call", "start"].join("_")));
  assert.doesNotMatch(first.text, new RegExp(["function", "call", "end"].join("_")));
  assert.doesNotMatch(first.text, new RegExp(`call_mask_${"json" + "l"}`));
});

test("renders the same workspace rule set in English and German", async () => {
  const primer = await buildPrimer({ tools });
  const englishIds = sectionRuleIds(
    primer.text,
    "workspace_handling_rules_en:",
    "workspace_handling_rules_de:",
  );
  const germanIds = sectionRuleIds(
    primer.text,
    "workspace_handling_rules_de:",
    "guided_document_workflow_example:",
  );
  const expectedIds = WORKSPACE_GUIDANCE_RULES.map((rule) => rule.id);

  assert.deepEqual(englishIds, expectedIds);
  assert.deepEqual(germanIds, expectedIds);
  for (const rule of WORKSPACE_GUIDANCE_RULES) {
    assert.ok(primer.text.includes(rule.en), `missing English workspace rule ${rule.id}`);
    assert.ok(primer.text.includes(rule.de), `missing German workspace rule ${rule.id}`);
  }
});

test("guided document workflow keeps intermediates under Temp and the final file at the user target", async () => {
  const primer = await buildPrimer({ tools });
  const taskRoot = `Temp/${GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.taskName}/`;

  assert.ok(GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.intermediatePaths.length > 0);
  assert.ok(
    GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.intermediatePaths.every((path) => path.startsWith(taskRoot)),
  );
  assert.ok(
    GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.intermediatePaths.every(
      (path) => !path.startsWith("Inbox/") && !path.startsWith("Trashcan/"),
    ),
  );
  assert.equal(
    GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.userRequestedFinalTarget,
    "Deliverables/document-acceptance.pdf",
  );
  assert.equal(
    GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.userRequestedFinalTarget.startsWith("Temp/"),
    false,
  );
  for (const path of GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.intermediatePaths) {
    assert.match(primer.text, new RegExp(escapeRegExp(path), "u"));
  }
  assert.match(
    primer.text,
    new RegExp(escapeRegExp(GUIDED_DOCUMENT_WORKFLOW_EXAMPLE.userRequestedFinalTarget), "u"),
  );
});

test("fails closed when an extra tool is advertised", async () => {
  await assert.rejects(
    buildPrimer({ tools: [...tools, { inputSchema: { type: "object" }, name: "unsafe_extra" }] }),
    /contract mismatch/,
  );
});

function sectionRuleIds(text: string, startMarker: string, endMarker: string): string[] {
  const start = text.indexOf(startMarker);
  const end = text.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0, `missing section ${startMarker}`);
  assert.ok(end > start, `missing section boundary ${endMarker}`);
  return [...text.slice(start + startMarker.length, end).matchAll(/^- \[([a-z_]+)\]/gmu)]
    .map((match) => match[1] ?? "");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
}
