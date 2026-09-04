# Smoke Tests

Recorded execution evidence:

- [rc19.dev0 test evidence, 2026-07-18](../RC19_DEV0_TEST_EVIDENCE_2026-07-18.md)
- [rc19.dev1 live-fix evidence, 2026-07-18](../RC19_DEV1_LIVE_FIX_EVIDENCE_2026-07-18.md)
- [rc19.dev2 settings and composer evidence, 2026-07-18](../RC19_DEV2_SETTINGS_AND_COMPOSER_EVIDENCE_2026-07-18.md)
- [rc19.dev3 connection and result evidence, 2026-07-18](../RC19_DEV3_CONNECTION_AND_RESULT_EVIDENCE_2026-07-18.md)
- [rc19.dev4 chat automation evidence, 2026-07-18](../RC19_DEV4_CHAT_AUTOMATION_EVIDENCE_2026-07-18.md)
- [rc19.dev5 editable settings and compact UI evidence, 2026-07-18](../RC19_DEV5_EDITABLE_SETTINGS_AND_COMPACT_UI_EVIDENCE_2026-07-18.md)
- [rc19.dev6 native auto-submit evidence, 2026-07-18](../RC19_DEV6_NATIVE_AUTO_SUBMIT_EVIDENCE_2026-07-18.md)
- [rc19.dev7 automation timing and retry evidence, 2026-07-18](../RC19_DEV7_AUTOMATION_TIMING_AND_RETRY_EVIDENCE_2026-07-18.md)
- [rc19.dev8 complete result transport evidence, 2026-07-18](../RC19_DEV8_COMPLETE_RESULT_TRANSPORT_EVIDENCE_2026-07-18.md)
- [rc19.dev9 workspace evidence and sequencing evidence, 2026-07-18](../RC19_DEV9_WORKSPACE_EVIDENCE_AND_SEQUENCING_2026-07-18.md)
- [rc19.dev10 sandbox automation and confirmation evidence, 2026-07-18](../RC19_DEV10_SANDBOX_AUTOMATION_AND_CONFIRMATION_EVIDENCE_2026-07-18.md)

First rc19 smoke matrix:

1. Start bridge on loopback.
2. Open a fresh signed-in ChatGPT conversation.
3. Insert the versioned PLwC Bridge Primer.
4. Verify ChatGPT lists exactly eight PLwC tools.
5. Run one `plwc_status(scope="runtime")` call.
6. Confirm one workspace write and verify exactly one file was created.
7. Read the file back and verify the expected content.
8. Attempt a protected-path write and verify denial with no file created.
9. With automatic write confirmation disabled, verify Governor `apply`
   requires explicit confirmation.
10. With automatic sandbox confirmation disabled, verify sandbox calls show
    `! CONFIRM`; enable the separate warned setting and verify one new sandbox
    call runs automatically.
11. Reload the extension and page and verify stale mutating calls do not run.
12. Verify the left host chat menu remains reachable throughout.
