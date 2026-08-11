# Chat Bridge P0-02 Acceptance Evidence

Date: 2026-07-30

Scope: BRIDGE-P0-02 only. Primer workspace rules (BRIDGE-P1-01), Windows Setup,
version alignment, and the final release test remain outside this acceptance
pass.

## Outcome

BRIDGE-P0-02 implementation acceptance passes for the Chat Bridge extension.

Large results use one of two lossless transport protocols:
`plwc_result_chunks.v1` for general tool results and
`plwc_profile_compile_layer_chunks.v1` for profile compile layers. The
extension validates protocol metadata, sequence, counts, Unicode character
counts, per-chunk SHA-256 values, complete-result SHA-256 values, completeness
flags, and reconstructed JSON before a result can be inserted or submitted.

Invalid chunk transports fail closed. The damaged payload is not rewrapped or
forwarded as complete. Instead, the panel enters a visible failed state and
returns a small `chunk_transport_invalid` error result under the original
`call_id`.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| All eight public tools transport 50-100 KB results completely | PASS | A parameterized test covers `plwc_status`, `plwc_describe`, `plwc_profile`, `plwc_reflection`, `plwc_governor`, `plwc_sandbox_run`, `plwc_workspace_operation`, and `plwc_document_operation`. Each UTF-8 JSON payload is between 50 KB and 100 KB and reconstructs to the exact original value. |
| Unicode remains intact across chunk boundaries | PASS | The all-tool test uses repeated non-ASCII and supplementary-plane characters. Existing boundary coverage also verifies general-result Unicode reconstruction. |
| Every chunk has sequence, total, and integrity metadata | PASS | `validateChunkCollection` requires a positive `chunk_index`, matching `total_chunks`, a code-point character count, and a valid SHA-256 value for every chunk. |
| Complete result integrity is independently verified | PASS | General JSON and profile compile transports require matching total counts, character counts, completeness flags, and whole-result SHA-256 values. General results must additionally parse as valid reconstructed JSON. |
| Missing chunks fail visibly and closed | PASS | Unit tests remove a chunk and verify rejection. The formatter refuses invalid transport, while the panel creates a visible failed run with a safe `chunk_transport_invalid` result. |
| Duplicate chunks fail visibly and closed | PASS | A unit test duplicates a chunk index and receives `chunk_index_duplicate`. |
| Reordered chunks fail visibly and closed | PASS | A unit test swaps valid hashed chunks and receives `chunk_order_invalid`; physical array order must be exactly `1..N`. |
| Corrupted chunks fail visibly and closed | PASS | Tests cover a changed chunk body, a bad profile chunk hash, and reconstructed invalid JSON with recomputed chunk and whole-result hashes. |
| Validation occurs before insertion and submission | PASS | `prepareToolResultForChat` validates incoming and generated transports. `PlwcPanel` invokes it before manual or automatic return, and `formatPlwcToolResultMessage` independently asserts validity at the final message boundary. Parsed historical results are also rejected when their transport is invalid. |
| Primer instructions are not the integrity boundary | PASS | Completeness and integrity decisions are enforced in extension code before the generic composer receives a formatted message. Primer guidance remains defense in depth only. |
| F-08 call-ID correlation remains intact | PASS | Regression tests preserve `call_id` through format/parse for both a valid large result and the visible safe error generated for an invalid chunk transport. |

## Verification Commands

Executed in
`<REPOSITORY_ROOT>\integrations\plwc-chat-bridge\extension`:

```powershell
npm run typecheck
npm test
npm run build:fixture
```

Result: type checking passed, all 112 extension tests passed, and the browser
fixture build passed.

Executed in `<REPOSITORY_ROOT>\integrations\plwc-chat-bridge`:

```powershell
npm run check
```

Result: loopback Bridge build and all 20 loopback tests passed; extension
production build and all 112 extension tests passed.

Executed from the repository root:

```powershell
git diff --check -- <BRIDGE-P0-02 files>
```

Result: passed with Git LF/CRLF conversion warnings only.

## Implementation Boundary

- `extension/src/shared/tool-result.ts` owns transport creation, validation,
  reconstruction, and safe transport-failure results.
- `extension/src/content/tool-result-message.ts` enforces validation when
  formatting and parsing result messages.
- `extension/src/panel/plwc-panel.ts` prepares results before manual or
  automatic return and exposes validation failures as failed tool runs.
- The generic composer requires no protocol-specific mutation because it only
  receives the already validated and formatted result message.

## Non-P0-02 Items

- No version bump to 1.0.0 was performed.
- No Windows Setup changes were made.
- No Primer workspace-rule changes were made.
- No PLwC Gateway contract changes were made.
