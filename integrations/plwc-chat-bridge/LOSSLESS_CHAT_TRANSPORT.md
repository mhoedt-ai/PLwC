# Lossless Chat Transport and Recovery

This document defines the runtime invariants for large PLwC results in the
ChatGPT web client. It is intentionally stricter than a preview or retrieval
scheme: Wandorra data and compiled profile layers must remain available to the
model without bridge-side summarization.

## Non-negotiable invariants

1. `plwc_result_chunks.v1` and
   `plwc_profile_compile_layer_chunks.v1` remain lossless transports.
2. A result is complete only when every contiguous chunk is present, every
   per-chunk SHA-256 value matches, the reconstructed SHA-256 value matches,
   and the explicit completeness flags are true.
3. Persona, Primer, Policy, compiled profile layers and Wandorra tool data are
   never replaced by `result_summary`, a local-only reference or omitted keys.
4. Compact JSON serialization may remove formatting whitespace only. It must
   round-trip to the exact same envelope and reconstructed result.
5. A bridge display card may bound its visual preview, but `Copy Complete
   Result`, insertion and automatic submission always use the complete marked
   result message.
6. When a payload exceeds the model's real context capacity, the bridge must
   fail visibly. It must not silently claim that a partial result is complete.

## Tool-call detection

ChatGPT can defer mounting output below a collapsed reasoning disclosure. The
bridge therefore treats tool-call discovery as reconciliation rather than a
single mutation event:

- only controls in the newest assistant turn whose label identifies a
  reasoning disclosure are revealed automatically;
- each concrete disclosure control is revealed at most once;
- the observer continues a low-frequency reconciliation scan even when no DOM
  mutation arrives;
- exact PLwC wrapper parsing, canonical tool-name validation, conversation and
  call identity checks, startup baselining and policy confirmation remain
  mandatory;
- raw PLwC call markers or an unopened reasoning disclosure suppress chain
  recovery until the normal call observer has had a chance to reconcile the
  turn.

## Recovery state

For one conversation and `call_id`, the effective state progression is:

`observed -> scheduled -> running -> result_validated -> result_submitted`

Recovery is allowed only when ChatGPT has finished responding, no executable
call wrapper or pending reasoning disclosure exists, no tool is running and no
recovery has already been emitted since the latest observed tool call. A DOM
expansion or delayed render must never create a second execution because the
conversation/call registry remains authoritative.

## Current web-client boundary

The Chat Bridge intentionally stays on the signed-in ChatGPT web surface. It
does not have a native structured-tool-result channel into ChatGPT. Therefore
large results are submitted as complete marked chat messages. Compact JSON and
collapsed visual cards reduce browser work, but neither changes the semantic
payload. Any future attachment or reference transport must prove that the
model consumed the complete data before it can replace this path.
