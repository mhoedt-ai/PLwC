# Browser Tests

Recorded live-fix evidence:

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

Planned browser coverage:

- PLwC Chat Bridge uses the PLwC Gateway icon and product name;
- terminal-green theme is readable in the panel;
- tabs are `PLwC Tools`, `Primer`, `Policy`, `Status` and `Settings`;
- host chat menu remains reachable while the bridge is open and collapsed;
- host chat menu remains reachable while connected, disconnected and rendering
  tool results;
- reduced-motion settings disable decorative motion effects.
- visible JSONL calls and marked results render as one PLwC card each while raw
  JSON remains available through `Show JSON`;
- read-only execution reaches `SUCCEEDED` and returns one marked result through
  the host composer.
- gateway settings save/restart and restore imported values;
- automatic write and sandbox confirmations remain separately default-off and
  display their own red warnings;
- collapsed calls waiting for individual confirmation display `! CONFIRM` on
  desktop and mobile widths.
