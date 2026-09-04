# Chat Bridge P0-02 Fix 01 Acceptance Evidence

Date: 2026-08-06

Scope: BRIDGE-P0-02-FIX-01 only. This pass covers the governed browser-chat
continuation from an approved profile-creation plan to confirmed apply and
read-only active-profile verification, execution-refusal recovery, correlated
result transport, aligned Bridge component identity, browser fixture coverage,
production builds, and focused Gateway contract verification.

Windows Setup payload integration, Browser Store packaging or publication,
clean-machine installation, and a post-fix live ChatGPT onboarding run remain
outside this pass.

## Observed Failure

The clean-VM screenshots showed a healthy local path: the Bridge was connected,
all eight tools were available, the profile-creation plan succeeded, and its
result was returned to ChatGPT. The dependent apply did not run. ChatGPT instead
stated that it could not execute the PLwC apply step and later emitted
`plwc_describe(scope=governor, operation=plan)`. Governor operation filters are
not valid Describe filters, so the Gateway correctly returned a visible
validation failure.

The Status view also displayed a matched common `dev18` build while separately
showing Node Bridge `dev12`. Its `Setup`/`Einrichtung` row referred to native
launcher startup, but could be mistaken for profile-onboarding state.

## Outcome

BRIDGE-P0-02-FIX-01 passes automated, production-build, and local browser
fixture acceptance on this host.

An approved `profile_creation` plan now adds a strictly validated
`plwc_onboarding_continuation.v1` object to the marked result. It contains one
exact correlated `plwc_governor` apply wrapper, preserves the complete reviewed
onboarding arguments, changes `operation` to `apply`, and sets `confirmed=true`.
The extension does not execute this wrapper by itself and does not treat it as
user confirmation; the existing individual or standing write-confirmation
boundary remains authoritative.

A successful profile-creation apply supplies one exact read-only
`plwc_status(scope=runtime)` continuation. Chain recovery now recognizes the
German and English execution-refusal forms observed in the screenshots. When a
verified onboarding continuation exists, the recovery message repeats its
exact wrapper and explicitly forbids replacing Governor apply with Describe.

The common build, Node Bridge, browser extension, and native launcher now all
report `0.2.0-rc19.dev19`. The status row is labeled `Native start` / `Nativer
Start`, keeping launcher startup distinct from profile onboarding.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Carry the complete reviewed onboarding data from plan to apply | PASS | The continuation copies the successful plan arguments without mutation, then changes only `operation=apply` and `confirmed=true`. Unit and browser acceptance tests compare the complete object. |
| Route the continuation through Governor | PASS | `next_call.name` is exactly `plwc_governor`; recovery explicitly forbids substitution with `plwc_describe`. |
| Preserve call correlation | PASS | The apply and status IDs are deterministically derived from the source call ID, remain within the 256-character parser limit, and pass the canonical wrapper parser. |
| Create no apply continuation for denied or incomplete plans | PASS | Plans require `ok=true`, `operation=plan`, `data.plan_type=profile_creation`, and an apply-approved decision. Negative tests return no continuation. |
| Preserve confirmation governance | PASS | The continuation state is `awaiting_user_confirmation`; no execution occurs from the result itself, and Governor apply remains classified as a mutating confirmation-required operation. |
| Verify the active profile after apply | PASS | A successful confirmed profile-creation apply yields exactly one `plwc_status` call with `{scope: runtime}`. |
| Recover the observed execution refusal | PASS | German `Ich kann ... nicht direkt ausfuehren` and English `I cannot directly execute` responses with a PLwC call reference are recoverable when no real wrapper is present. |
| Never duplicate a real call | PASS | Existing recovery and observer gates still reject recovery when `plwc_tool_call` is already present and preserve `(conversation_id, call_id)` exactly-once behavior. |
| Validate the continuation before result return | PASS | Result formatting and parsing accept only the versioned protocol, exact object shape, canonical next tool, bounded call ID, and state-specific arguments. Manipulated continuation objects fail closed. |
| Align all Bridge component versions | PASS | Common build, Node Bridge, extension, launcher, package metadata, manifest, config track, and compiled bundles report `0.2.0-rc19.dev19`. |
| Separate native startup from onboarding status | PASS | The visible row is `Native start` / `Nativer Start`; its not-requested message does not mention profile onboarding. |
| Verify desktop and mobile browser layout | PASS | The local browser fixture reported the new acceptance marker as `pass`, no horizontal overflow at default desktop or 390x844, and a 366-pixel panel inside the 390-pixel viewport. |

## Verification Commands

The pre-change extension baseline passed 123 tests. Regression tests were then
added first and failed because the continuation module did not yet exist:

```text
ERROR: Could not resolve "./onboarding-continuation"
```

The complete Windows Bridge gate was executed from
`integrations/plwc-chat-bridge`:

```powershell
npm run check:windows
```

Result:

```text
Loopback Bridge: 23 passed, 0 failed
Extension:       131 passed, 0 failed
Native launcher: built successfully
```

After the final Primer and malformed-continuation contracts were added, the
authoritative final Extension gate and browser fixture build were executed:

```powershell
npm --prefix extension run check
npm --prefix extension run build:fixture
```

Final result:

```text
Extension: 132 passed, 0 failed
TypeScript: passed
Production extension build: passed
Browser fixture build: passed
```

Focused Gateway contracts were executed from the repository root:

```powershell
python -m pytest -q `
  tests/integration/test_chat_bridge_contract.py `
  tests/integration/test_requested_profile_status.py `
  tests/integration/test_shared_gateway_settings.py `
  tests/integration/test_describe_contract.py
```

Result:

```text
19 passed in 5.91s
```

The built fixture was served from loopback and inspected in a real browser.
Its document markers and visible Status values were:

```text
data-plwc-p0-01-acceptance=pass
data-plwc-p0-02-fix-01-acceptance=pass
Node Bridge     0.2.0-rc19.dev19
Extension       0.2.0-rc19.dev19
Launcher        0.2.0-rc19.dev19
Desktop horizontal overflow: false
390x844 horizontal overflow: false
390px panel: left 12.4px, right 378.4px, width 366px
```

## Final Build Identity And Artifacts

```text
Build ID
plwc-chat-bridge@0.2.0-rc19.dev19

integrations/plwc-chat-bridge/build-identity.json
Bytes  402
SHA256 93a116cc44a59dd640b4a49f5dc73b975756a733bf4ab7a21df6c42e29f1016a

integrations/plwc-chat-bridge/bridge/dist/src/index.js
Bytes  1415
SHA256 33848b6a436db9be7ace2debe472e260db84e4684bb552fa0eb5039ea6cccb4e

integrations/plwc-chat-bridge/extension/dist/manifest.json
Bytes  1546
SHA256 d8b6fe778de88515395334525ea27c60eeaa4bdcebd304468d58e35d0dfa83b7

integrations/plwc-chat-bridge/extension/dist/background.js
Bytes  44687
SHA256 ae91c49b46fb4b0a888aedf15ed1ed582255ab620698a9210fa653c694560867

integrations/plwc-chat-bridge/extension/dist/content.js
Bytes  186276
SHA256 ea6ed31ad03435b1fa24e38f36a042983f97c44df4b917c167114753bba73731

integrations/plwc-chat-bridge/native/bin/plwc-chat-bridge-launcher.exe
Bytes  32256
SHA256 7a31dc119b8543eb53b9ee8543a4ebe0fad0882351f9f868aee707338bcf44d7
```

## Non-Final Diagnostic Notes

The first focused Gateway run passed 18 tests and found one stale contract that
explicitly required Node Bridge and extension versions to differ. The contract
was updated to require all three components to equal the common release, and
the accepted rerun passed 19 of 19.

Visual fixture inspection exposed a damaged non-ASCII character in the new
German native-start sentence. The sentence was changed to an ASCII-safe German
form, the fixture was rebuilt and reloaded, and the corrected text was verified
at desktop and mobile widths.

## Implementation Boundary

- `extension/src/content/onboarding-continuation.ts` owns strict continuation
  creation and validation.
- `extension/src/content/tool-result-message.ts` carries the optional validated
  continuation inside the correlated marked result.
- `extension/src/content/chain-recovery.ts` recognizes execution refusals and
  repeats a verified exact continuation without executing it.
- `extension/src/panel/plwc-panel.ts` binds continuations to successful tool-run
  records and supplies the latest verified onboarding context to recovery.
- `extension/src/primer/build-primer.ts` defines model-facing continuation and
  confirmation rules.
- Unit and browser acceptance tests cover plan, apply, verification, malformed
  continuation, refusal recovery, call IDs, and desktop/mobile fixture state.
- `build-identity.json` and component package metadata own the aligned `dev19`
  identity.

## Outside This Fix

- The accepted `PLwC-Setup-0.2.0-rc18.dev9-installer-r11.exe` still contains
  the earlier Chat Bridge build. No Setup source, manifest, staging, or installer
  artifact was changed in this package.
- No Browser Store package, publisher identity, listing, or submission was
  created.
- No live ChatGPT apply wrote a profile during automated acceptance.
- A new installer integration package and then a preserved-VM live
  `plan -> confirmation -> apply -> runtime status` run are still required
  before end-user acceptance of this Bridge fix.
- No unrelated dirty work was reset, reverted, deleted, staged, or committed.
