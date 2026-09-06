# r26 Phase 6 – Protokollsicherheit

Stand: 2026-09-03

## Ergebnis

Phase 6 ist **PASS**. Die öffentliche MCP-Fassade bleibt bei exakt acht
kanonischen Werkzeugen. Es wurde weder eine Store-Veröffentlichung ausgelöst
noch ein r26-Produktionsinstaller gebaut.

## Umsetzung der sechs Korrekturen

1. Mutierende Tool-Calls benötigen für die Ausführung `conversation_id` und
   `call_id`. Die Identität wird vor dem Versand persistent beansprucht. Timeout
   oder Verbindungsabbruch nach dem Versand ergeben `outcome_unknown` mit
   `mutation_may_have_executed=true` und `retry_allowed=false`; der Transport
   sendet nicht automatisch erneut.
2. Die Extension berechnet SHA-256 über die kanonisch sortierten acht Live-
   Schemas. `ToolListResponse`, Primertext und Primeranzeige transportieren
   `schema_sha256` und den expliziten Zustand `integrity_verified=true`.
   Unbestätigte oder abweichende Integritätsangaben sperren den Primer.
3. Eine noch nicht bestätigte Mutation liefert die reguläre Protokollantwort
   `state=awaiting_confirmation` statt eines RPC-Fehlers.
4. `plwc_status(scope="first_run", profile_name="…")` akzeptiert den optionalen
   Profilnamen ausschließlich zur Inspektion. Es wird kein zusätzliches
   öffentliches Werkzeug eingeführt und das aktive Profil wird nicht geändert.
5. Read-only Status-, Describe-, Profil-, Governor-Plan- und anerkannte
   Inspektionsaufrufe bleiben zulässig und automatisch ausführbar, sofern die
   lokale read-only Einstellung dies erlaubt.
6. `profile_creation` und `profile_activation` bei Governor `apply` sind nicht
   für die stehende Schreibbestätigung freigegeben. Beide benötigen eine eigene
   Bestätigung; ihre read-only Planaufrufe bleiben möglich.

## Wesentliche Nachweise

- `integrations/plwc-chat-bridge/extension/src/background/transport.ts`
  unterscheidet `not_sent`, `outcome_unknown` und `response_received`.
- `integrations/plwc-chat-bridge/extension/src/shared/tool-call-protocol.ts`
  bildet die eindeutigen Bestätigungs- und Transportzustände ab.
- `integrations/plwc-chat-bridge/extension/src/shared/policy.ts` schließt
  Profilanlage und -aktivierung von stehender Bestätigung aus.
- `integrations/plwc-chat-bridge/extension/src/shared/contracts.ts` berechnet
  die Schema-Integrität; `src/primer/build-primer.ts` prüft und transportiert
  sie.
- `tests/integration/test_requested_profile_status.py` belegt den optionalen
  `first_run`-Profilnamen sowie dessen rein inspizierende Wirkung.

## Ausgeführte Gates

- Extension `npm run check`: **PASS**
  - TypeScript: PASS
  - Tests: **184/184 PASS**
  - Extension-Build: PASS
- Timeout-Negativtest: genau ein WebSocket-Versand, anschließend
  `outcome_unknown`: PASS
- Disconnect-Negativtest: genau ein WebSocket-Versand, kein Resend: PASS
- Reconnect-/Cachetest: veraltete Verifikation wird nach Disconnect verworfen:
  PASS
- Bestätigungs-/Policytests einschließlich Profilanlage/-aktivierung: PASS
- Primer-Integrität positiv sowie unbestätigt/falscher Hash negativ: PASS
- Gateway-Zieltests: **12/12 PASS**
- Vollständige Python-Suite: **94 PASS, 6 SKIPPED**
- Öffentlicher Werkzeugvertrag: exakt acht kanonische Werkzeuge: PASS

## Gate-Entscheidung

**PASS:** Kein automatischer doppelter mutierender Aufruf bei unklarem
Transportergebnis, korrekte Integritätsanzeige und eindeutige
Bestätigungszustände sind durch positive und negative Vertragstests belegt.
