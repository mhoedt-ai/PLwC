# Chat Bridge P1-02 Acceptance Evidence

Date: 2026-07-30

Scope: BRIDGE-P1-02 only. Shared build identity (BRIDGE-P1-03), Windows Setup,
version alignment, and the final release test remain outside this acceptance
pass.

## Outcome

BRIDGE-P1-02 implementation acceptance passes for the generated Primer, Bridge
execution policy, panel, and in-chat result cards.

The Primer now requires a precise `plwc_describe` call whenever an operation
name, schema, required field, or argument shape is unclear. Workspace and
document discovery uses an exact operation filter when the intended operation
is known. Guessed operation names and arguments are explicitly prohibited.

The Bridge presents structured Gateway failures as `Policy denied`,
`Validation failed`, `Not found`, `Unavailable`, `Gateway failed`, or
`Transport failed`. Public `error_category` takes precedence over the separate
`policy_decision`, so an unavailable subsystem is not mislabeled as a policy
denial merely because its technical fallback also denies execution.

Artifact-producing results expose origin and validation metadata in the panel
and in-chat cards. An unvalidated artifact is labeled `Unvalidated artifact`,
uses warning styling, and displays
`UNVALIDATED - do not treat as safe`; it is not presented as an ordinary
successful artifact.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Unclear schemas lead to a precise Describe call | PASS | `describe_guidance_protocol` requires one `plwc_describe` call before the target call and lists the canonical facade scopes. |
| Known workspace/document intent uses an operation filter | PASS | Primer guidance names `scope=document_operation` with `operation=create_pdf` as the model and forbids an unfiltered full schema when the intended operation is known. |
| Operation names and arguments are never guessed | PASS | Primer regressions require the explicit prohibition and require following `next_tool`, `next_operation`, `next_plan_type`, `required_fields`, `supported_operations`, and `example_call`. |
| Unknown operations are not automatic | PASS | Policy tests cover unknown profile, reflection, Governor, workspace, and document operations. Every case is non-read-only, requires individual confirmation, and has no standing-confirmation automation flag. Known profile operations remain read-only. |
| `Policy denied` is distinct | PASS | `POLICY_DENY` and legacy denial-only results map to `Policy denied`. |
| `Validation failed` is distinct | PASS | `INVALID_REQUEST` and artifact `validation_status=validation_failed` map to `Validation failed`. |
| `Not found` is distinct | PASS | `NOT_FOUND` maps to `Not found`. |
| `Unavailable` is distinct | PASS | `UNAVAILABLE` maps to `Unavailable`, including a Safe Mode-style result that also carries `policy_decision=DENY`. |
| `Gateway failed` is distinct | PASS | Gateway conflicts, uncategorized unsuccessful results, and failed calls without a structured result use `Gateway failed`. |
| `Transport failed` is distinct | PASS | Invalid chunk transport results and unknown connection/timeout run states use `Transport failed`. |
| F-01 onboarding guidance remains authoritative | PASS | Primer tests require machine-readable onboarding next-step fields and the governed profile-creation plan/apply path instead of an invented settings action. |
| F-06 requested and active profiles remain separate | PASS | Primer guidance and regressions keep `requested_profile_name`, `active_profile_name`, and `profile_path` semantically separate and state that inspection cannot activate a profile. |
| Provenance and validation status are visible | PASS | Shared metadata rows drive both panel and chat-card output for artifact origin, origin detail, validation, validation detail, and artifact trust. |
| Unvalidated artifacts are not presented as safe | PASS | Unit tests require the exact warning `UNVALIDATED - do not treat as safe`. Visible card state changes from ordinary success to `Unvalidated artifact` with warning styling. |
| Large chunked artifact results retain visible provenance | PASS | A regression creates a large document result, validates and reconstructs its chunk transport, and verifies that origin and trust remain available to the presentation layer. |

## Verification Commands

Executed in
`<REPOSITORY_ROOT>\integrations\plwc-chat-bridge\extension`:

```powershell
npm run typecheck
npm test
npm run build:fixture
```

Result: type checking passed, all 120 extension tests passed, and the browser
fixture build passed.

Executed in `<REPOSITORY_ROOT>\integrations\plwc-chat-bridge`:

```powershell
npm run check
```

Result: loopback Bridge build and all 20 loopback tests passed; extension
production build and all 120 extension tests passed.

Executed from the repository root:

```powershell
git diff --check -- <BRIDGE-P1-02 files>
```

Result: passed with Git LF/CRLF conversion warnings only.

## Browser Smoke

The browser fixture includes a historical `plwc_workspace_operation`
`write_binary` result with `artifact_origin=workspace_binary_write` and
`validation_status=unvalidated`.

The fixture was served over loopback HTTP and inspected in the in-app browser
at a 1280 by 720 viewport. The collapsed and expanded call/result cards showed
`Unvalidated artifact`; the expanded result showed artifact origin,
`Unvalidated`, and `UNVALIDATED - do not treat as safe`. A first visual pass
exposed narrow-header text wrapping caused by redundant warning badges. The
header was corrected to wrap by control group, the duplicate badge was removed,
and the repeated visual pass showed readable text with no panel/card overlap.
The browser console contained no errors or warnings. The temporary browser tab
and HTTP server were closed after verification.

## Implementation Boundary

- `extension/src/primer/build-primer.ts` owns Describe and profile-context
  guidance.
- `extension/src/shared/policy.ts` keeps unknown operations outside automatic
  execution.
- `extension/src/shared/tool-result.ts` owns failure and artifact presentation
  semantics.
- `extension/src/content/chat-renderer.ts` and
  `extension/src/panel/plwc-panel.ts` render the shared semantics.
- `extension/tests/browser/fixture.html` provides the visible unvalidated
  artifact scenario.
- `extension/README.md` documents the user-visible contract in English.

## Non-P1-02 Items

- No version bump to 1.0.0 was performed.
- No Windows Setup changes were made.
- No PLwC Gateway contract changes were made.
- No shared build-identity changes were made.
