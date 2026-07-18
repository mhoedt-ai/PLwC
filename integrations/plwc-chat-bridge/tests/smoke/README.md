# Smoke Tests

Recorded execution evidence:

- [rc19.dev0 test evidence, 2026-07-18](../RC19_DEV0_TEST_EVIDENCE_2026-07-18.md)
- [rc19.dev1 live-fix evidence, 2026-07-18](../RC19_DEV1_LIVE_FIX_EVIDENCE_2026-07-18.md)
- [rc19.dev2 settings and composer evidence, 2026-07-18](../RC19_DEV2_SETTINGS_AND_COMPOSER_EVIDENCE_2026-07-18.md)
- [rc19.dev3 connection and result evidence, 2026-07-18](../RC19_DEV3_CONNECTION_AND_RESULT_EVIDENCE_2026-07-18.md)
- [rc19.dev4 chat automation evidence, 2026-07-18](../RC19_DEV4_CHAT_AUTOMATION_EVIDENCE_2026-07-18.md)

First rc19 smoke matrix:

1. Start bridge on loopback.
2. Open a fresh signed-in ChatGPT conversation.
3. Insert the versioned PLwC Bridge Primer.
4. Verify ChatGPT lists exactly eight PLwC tools.
5. Run one `plwc_status(scope="runtime")` call.
6. Confirm one workspace write and verify exactly one file was created.
7. Read the file back and verify the expected content.
8. Attempt a protected-path write and verify denial with no file created.
9. Verify Governor `apply` requires explicit confirmation.
10. Reload the extension and page and verify stale mutating calls do not run.
11. Verify the left host chat menu remains reachable throughout.
