# Chat Bridge P0-02 Fix 02 Acceptance Evidence

Date: 2026-08-07

Scope: BRIDGE-P0-02-FIX-02 only. This pass covers ChatGPT composer-state
integration, verified result insertion and submission, a complete-result copy
fallback, correction of the invalid onboarding Describe entry, Primer rules,
aligned Bridge component identity, browser fixture coverage, production builds,
and the Windows native launcher build.

Windows Setup payload integration, Browser Store packaging or publication, and
a post-fix live ChatGPT onboarding run remain outside this pass.

## Observed Failure

ChatGPT changed its controlled composer implementation. The extension wrote a
marked result directly to `contenteditable.textContent`, so the text appeared
visually without entering ChatGPT's internal editor state. Focusing the composer
caused ChatGPT to reconcile the DOM back to its empty state. The send control
therefore remained the audio control and the result was never submitted.

The submission loop also treated an empty composer as successful before any
send activation. This could misclassify editor reconciliation as a completed
result return.

The bounded Status preview truncated large chunked results at 5,000 characters.
`Show JSON` exposed the same bounded display, so manual copying could contain
only the first chunk even though the transport itself was complete.

The model also emitted the invalid onboarding entry
`plwc_describe(scope=status, operation=onboarding)`. The Gateway correctly
rejected it because Describe operation filters are supported only for
`workspace_operation` and `document_operation` scopes.

## Outcome

BRIDGE-P0-02-FIX-02 passes automated, production-build, native-build, and local
browser fixture acceptance on this host.

Contenteditable insertion now uses the browser editing command after placing the
caret at the editor end. Text controls use their native value setter and an input
event. The extension then blurs and refocuses the composer and verifies the
normalized complete content over multiple stabilization ticks. A disappearing
or changed insertion returns `composer-rejected-insertion` and is never reported
as submitted.

Submission success now requires at least one send activation before an empty
composer can prove acceptance. A pre-submit empty state is classified as editor
rejection.

Every terminal run in the Status queue now exposes `Copy Complete Result`. It
copies the exact marked result message created from the complete validated chat
transport, including every chunk and any continuation or correction contract.
It never uses the bounded visual preview. Clipboard API failure falls back to a
user-gesture `copy` command.

Invalid onboarding Describe results now carry a strictly validated
`plwc_tool_call_correction.v1` contract with the exact next call
`plwc_status({scope: first_run})`. Chain recovery preserves that call. The Primer
now states that Describe operation filters are valid only for workspace and
document scopes and that `plwc_status` is a separate tool.

The common build, Node Bridge, browser extension, and native launcher all report
`0.2.0-rc19.dev20`.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Enter text through the controlled editor path | PASS | Contenteditable uses browser `insertText`; text controls use the native value setter and input event. |
| Detect focus reconciliation | PASS | Verified insertion performs a blur/refocus cycle and stabilization checks; a simulated controlled-editor wipe returns rejection. |
| Never mistake reconciliation for submission | PASS | Empty composer state proves success only after at least one send activation. |
| Preserve complete large results | PASS | A result over 90 KB retained its final `browser-result-899` value after browser insertion and refocus. |
| Provide a complete manual fallback | PASS | `Copy Complete Result` receives the exact marked message; tests verify length over 12,000, final content, and absence of the preview truncation marker. |
| Keep previews bounded | PASS | Status result rendering remains bounded and separate from the complete copy source. |
| Correct invalid onboarding entry | PASS | The observed invalid Describe shape produces one exact `plwc_status` call with `{scope: first_run}` and a correlated bounded call ID. |
| Reject unrelated corrections | PASS | Unrelated Describe validation failures produce no correction contract. |
| Validate correction transport | PASS | Result formatting and parsing accept only the versioned correction protocol, exact keys, canonical next tool, bounded call ID, and exact arguments. |
| Preserve governance | PASS | The correction is model-facing guidance only; it does not execute a tool or bypass confirmation. |
| Align all Bridge component versions | PASS | Source metadata, manifests, compiled bundles, and the native launcher contain `0.2.0-rc19.dev20`. |

## Verification Commands

The pre-change Extension baseline passed 132 tests:

```powershell
npm --prefix integrations/plwc-chat-bridge/extension test
```

Regression tests were added first and failed because the new complete-copy and
onboarding-correction modules did not yet exist:

```text
ERROR: Could not resolve "./complete-result-copy"
```

The complete Bridge gate was executed from `integrations/plwc-chat-bridge`:

```powershell
npm run check
```

Final result:

```text
Loopback Bridge: 23 passed, 0 failed
Extension:       140 passed, 0 failed
TypeScript:      passed
Bridge build:    passed
Extension build: passed
```

The browser fixture and Windows native launcher were built separately:

```powershell
npm --prefix extension run build:fixture
npm run build:native:windows
```

The final built fixture was served from loopback and inspected in a real
browser. Its document state was:

```text
data-plwc-p0-01-acceptance=pass
data-plwc-p0-02-fix-01-acceptance=pass
data-plwc-p0-02-fix-02-acceptance=pass
composerLength=0
panelMounted=true
horizontalOverflow=false
```

## Final Build Identity And Artifacts

```text
Build ID
plwc-chat-bridge@0.2.0-rc19.dev20

integrations/plwc-chat-bridge/build-identity.json
Bytes  402
SHA256 b364902839a88ffc71f6ba6c4e44a2ef897a7a56bf421d69f4aef773a9dda9c1

integrations/plwc-chat-bridge/bridge/dist/src/index.js
Bytes  1415
SHA256 33848b6a436db9be7ace2debe472e260db84e4684bb552fa0eb5039ea6cccb4e

integrations/plwc-chat-bridge/extension/dist/manifest.json
Bytes  1546
SHA256 f1740376b7c17eca51e5c35b41746976c7df6e1d147f6f841771cc4de76b583b

integrations/plwc-chat-bridge/extension/dist/background.js
Bytes  44687
SHA256 889f8e39d2fda87dd59d0f3cce6970468285787b298c9da5f7632637ec502c50

integrations/plwc-chat-bridge/extension/dist/content.js
Bytes  195944
SHA256 0e84f14204878acaac2f44a6ac9d9dd485e0add83ddfc830a610437fb0ab3a9d

integrations/plwc-chat-bridge/extension/.browser-fixture/fixture.js
Bytes  206049
SHA256 8cb42e931c08282ad63757eb3455dd48a35215cefb923497a68bcc292628dca0

integrations/plwc-chat-bridge/native/bin/plwc-chat-bridge-launcher.exe
Bytes  32256
SHA256 fc6e4ab59412d561fde42a637ec9068b79d8472f1d9c2b3f886af2e82ee09db5
```

## Implementation Boundary

- `extension/src/content/composer.ts` owns editor-compatible insertion,
  stabilization verification, and submit acceptance.
- `extension/src/content/complete-result-copy.ts` owns complete clipboard output
  and the browser copy fallback.
- `extension/src/content/onboarding-correction.ts` owns strict onboarding entry
  correction creation and validation.
- `extension/src/content/tool-result-message.ts` carries the optional correction
  in the correlated marked result.
- `extension/src/content/chain-recovery.ts` repeats verified continuation or
  correction contracts without executing them.
- `extension/src/panel/plwc-panel.ts` exposes verified insertion and complete
  copy actions for terminal runs.
- `extension/src/primer/build-primer.ts` defines the model-facing Describe,
  status, and correction rules.
- `build-identity.json` and component metadata own the aligned `dev20` identity.

## Outside This Fix

- `PLwC-Setup-0.2.0-rc18.dev9-installer-r12.exe` still contains the earlier
  Chat Bridge build. No Setup source, staging, or installer artifact was changed
  in this package.
- No Browser Store package, publisher identity, listing, or submission was
  created.
- No live ChatGPT onboarding flow was executed after this fix; the acceptance
  used the isolated browser fixture and does not mutate PLwC profile state.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
