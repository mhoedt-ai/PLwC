# Smoke-Test-Evidenz

Stand: 2026-07-17

Dieses Dokument fasst die relevanten Smoke- und Governance-Belege anonymisiert zusammen. Es enthält keine Links auf Rohberichte oder lokale Originaldateien. Es verweist nur auf die beiden anderen Dateien im Evidence-Ordner:

- [TAGEBUCH.md](TAGEBUCH.md) - anonymisierte Verlaufserzählung
- [CHANGE_HISTORY.md](CHANGE_HISTORY.md) - komprimierter Änderungsverlauf

## Aktueller Evidenzstand

Die Smoke-Evidenz reicht weiter zurück als nur die rc16-rc18-Linie. Im Claude-Arbeitsordner liegen ältere Berichte vom 2026-05-23 bis 2026-07-11. Diese Datei fasst die gesamte auffindbare Kette zusammen, ohne die Originaldateien oder ihre lokalen Pfade zu verlinken.

Der stärkste aktuelle technische Stand ist die rc18.dev9-Linie:

- Package-Smoke: PASS
- Desktop-Smoke: PASS
- öffentlicher Server: `plwc-gateway`
- öffentliche Facade-Tools: exakt 8
- keine öffentlichen Raw-PBA-, Raw-Commander-, Filesystem- oder Zweit-PLwC-Server
- package privacy filtering: PASS
- Persona-Layer explizit steuerbar
- CLU Doctor read-only
- Reflection-Aliase geprüft
- Cross-profile Reflection-Write korrekt blockiert

Wichtig: Ein älterer Package-Bericht sagte noch, Desktop-Smoke für rc18.dev9 sei nicht gelaufen. Dieser Stand wurde später durch den rc18.dev9 Desktop-Smoke überholt.

## Acht öffentliche Facade-Tools

Die aktuelle Public Boundary besteht aus genau diesen acht Tools:

| Tool | Rolle |
| --- | --- |
| `plwc_status` | Runtime-, First-Run- und Konfigurationsstatus |
| `plwc_describe` | Tool-, Policy-, Governor-, Reflection- und Workspace-Beschreibungen |
| `plwc_profile` | Compile, Doctor, Scan- und Profiloperationen |
| `plwc_reflection` | Governed Reflection-Schreibpfad |
| `plwc_governor` | Plan/Apply für Profile, Memory, Persona und Temperament |
| `plwc_sandbox_run` | kontrollierte Sandbox-Ausführung |
| `plwc_workspace_operation` | path-scoped Workspace-Operationen |
| `plwc_document_operation` | kontrollierte Dokumentoperationen |

Die Smoke-Tests prüfen wiederholt, dass keine zusätzlichen Legacy- oder Rohwerkzeuge öffentlich sichtbar werden.

## Smoke-Timeline

| Datum | Linie | Ergebnis | Kernaussage |
| --- | --- | --- | --- |
| 2026-05-23 | v0.2.0-dev Focus-Smoke | PASS | Reflection/Governor-Pfad im echten Client: 8 Tools sichtbar, valide Reflections akzeptiert, Technik-Müll abgelehnt, Cross-profile Guard aktiv, plan/apply mit `confirmed=true`, Duplicate-Safety. |
| 2026-06-03 | rc2.dev0 konsolidiert | PASS | Public Boundary, Protected-Path-DENY, Workspace write/read/copy/binary, ZIP-Extraktion, memory-promotion Admin-Override und Force-Grenzen geprüft; 595 Tests passed in der damaligen Linie. |
| 2026-06-04 | Externer Testplan | PASS mit Findings | Ein externer Nutzungsplan bestätigt 8 Tools, Workspace-Schutz, Traversal-DENY, PDF/Dokumentoperationen, Sandbox und Reflection/Governance; Findings betreffen Dokumentation/Fehlermeldungen, nicht harte Gates. |
| 2026-06-05 | rc4 Desktop | GREEN mit Finding | 8-Tool-Boundary, Workspace-Schutz, Dokumentoperationen, Sandbox, Reflection/Governance und neues `edit_docx` mit 5 Edit-Typen geprüft; einziges Finding: externe URL wurde funktional blockiert, aber spät/unschön klassifiziert. |
| 2026-06-09 | rc5 Desktop | GREEN mit Findings | URL-Validierung vor Worker bestätigt, Node.js-Sandbox eingeführt, Node-Happy-Path und Node-Security-DENYs bestanden; Findings nur Mikro-/UX-Kategorie. |
| 2026-06-10 | rc6 Desktop | GREEN | 75 Schritte A-L bestanden: temperament promotion, INNER Content Gates, Tagebuch-Provenance, Node-Retest und Governance-DENYs; initiale Transport-/Testkriterien-Findings geschlossen. |
| 2026-06-10 | rc7 Desktop | GREEN | Tagebuch-Provenance-SHA-Fix, CRLF/LF-Roundtrip und Session-End-Journal-Prompt bestätigt; keine offenen Blocker. |
| 2026-06-13 | rc8 initial | FAIL durch Testdaten | Memory-Retire-/Temperament- und Reflection-Gates scheitern an zu abstrakten oder ungültigen Testdaten; Semantik-Gate blockiert korrekt statt blind zu akzeptieren. |
| 2026-06-13 | rc8 Nachlauf | PASS | Mit semantisch validen Eingaben bestehen Memory-Promotion, Retire, Duplicate-Schutz, Compile-Ausschluss retired entries, Compile-Tracking, no-action-rule, Temperament-Promotion und Tagebuch-Provenance. |
| 2026-06-14/15 | rc9 Hauptlauf + Qdrant-Nachlauf | GREEN mit Findings | Hauptlauf bestätigt A-N überwiegend, Qdrant zunächst wegen deaktiviertem Flag blockiert; Nachlauf bestätigt Reindex/Retrieve/Staleness/require_fresh/include_retired/drop_index/Canon-Integrität. |
| 2026-06-30 | rc12.dev1 Compile Modes | PASS mit nicht-blockierenden Lücken | Boot/working/full Compile-Modi liefern erwartete Größen und Sektionsauswahl; File-Unveränderlichkeit teilweise nur per Eigenauskunft, nicht unabhängig gehasht. |
| 2026-06-30 | rc12.dev2 Desktop | PASS | Search Scope Guards senken große Live-Root-Suche von Minuten auf Sekunden; Binary/too-large/excluded-dir Skips sichtbar; Desktop bleibt bedienbar; Compile-Modes regressionsfrei. |
| 2026-07-01 | rc13.dev0 Desktop | GRÜN | scan_tagebuch Disconnect Guard, Innenperspektive-Reflection-Contract, Qdrant Crash Guard und Compile-Unabhängigkeit bestätigt; Semantic Retrieve noch nicht load-bearing. |
| 2026-07-01 | rc14.dev0 Desktop | PASS | Qdrant Runtime Guard, Working Semantic Memory, boot fallback, drop-index fallback und content-aware superseded Review geprüft; kein erfundener Duplikat-Check erzwungen. |
| 2026-07-02 | rc15.dev0 Qdrant Readiness | PARTIAL / package-only | Extracted-package smoke ist als bestanden notiert; Desktop-/MCP-Transport-Smoke war in dieser Datei noch nicht gelaufen. Spätere rc16-Evidenz adressiert das beobachtete Transport-Stall-Problem. |
| 2026-07-05 | rc16.dev0 | PASS | Qdrant-Reindex-Timeouts werden strukturiert behandelt; kein globaler Gateway-Stall. |
| 2026-07-05 | rc17.dev0 | PASS | CLU Doctor, Workspace-Diagnostik, Tagebuch-Guard und Temperament-Threshold funktionieren nach Fix-Build. |
| 2026-07-06 | rc18.dev0 Package | PASS | Command-Katalog bleibt Discovery-only; Public Boundary bleibt bei acht Tools. |
| 2026-07-07 | rc18.dev0 Desktop | PASS | CLU Runner read-only; keine Profil- oder Workspace-Leaks; Regressionen aus rc17 halten. |
| 2026-07-08 | rc18.dev1 Desktop | PASS mit Prozessnotiz | Qdrant Source-Current Consistency, reindex nach Bestätigung, working compile mit frischer Semantic Memory und Protected Boundary bestätigt; Restart nötig, um neue Runtime aktiv zu machen. |
| 2026-07-08 | rc18.dev2 Desktop | FAIL | Persona-Layer-Settings-Toggle erreicht Runtime nicht; per-call Override funktioniert, aber Extension-Config-Wiring ist defekt. |
| 2026-07-08 | rc18.dev3 Desktop | PASS | dev2-Regression behoben: invertierter `persona_layer_disabled`-Schalter erreicht Runtime; compile kann PERSONA auslassen; Public Boundary hält. |
| 2026-07-08 | rc18.dev4 Desktop | FAIL | Persona-Layer-Deaktivierung entfernt PERSONA, aber CORE-Rollen-/Arbeitskontextzeilen werden noch nicht sauber gestripped; Matching-Logik unzureichend. |
| 2026-07-08 | rc18.dev6 Desktop | PASS_WITH_NOTES | CORE-Leak geschlossen, Onboarding ohne Persona-Pflichtfelder planbar, Doctor read-only; Icon weiterhin nur visuell prüfbar. |
| 2026-07-09 | rc18.dev7 Desktop | PASS_WITH_NOTES | Tool-Boundary, First-Run-Bootstrap, aktive Profil-Precedence und Persona-Layer-Deaktivierung bestätigt. |
| 2026-07-10 | rc18.dev9 Package | PASS | Privacy Payload Filtering, Reflection-Aliase, Onboarding-Metadaten und Public Boundary bestätigt. |
| 2026-07-11 | rc18.dev9 Desktop | PASS | Install/Runtime, SHA-Abgleich, Privacy-Sanity, First-Run, Precedence, Doctor und Reflection-Alias Checks bestanden. |
| 2026-07-17 | Browser/ChatGPT-Motor | PASS als Arbeitsnachweis | Workspace-Zugriff funktioniert kontrolliert; Desktop-Schreibversuch außerhalb erlaubter Roots wird mit DENY blockiert. |

## Historische Smoke-Befunde

Die ältere Smoke-Kette ist wichtig, weil sie zeigt, dass spätere Features nicht plötzlich entstanden sind, sondern auf wiederholten Regressionen und Fixes aufbauen.

### 2026-05-23 - Reflection/Governor Focus

Früh belegt wurden:

- genau acht öffentliche Tools;
- Reflection-Validator akzeptiert echte Insights;
- technische Statussätze werden aus Reflection abgewiesen;
- Cross-profile-Schreibschutz blockiert Schreibversuche auf inaktive Profile;
- Governor-Plan/Apply mit `confirmed=true` funktioniert;
- `confirmed=false` wird blockiert;
- Wiederholung eines bereits angewendeten Plans wird als Duplicate/no-op behandelt.

### rc2.dev0 - Workspace- und Governor-P0

rc2.dev0 deckte bereits mehrere Grundsäulen ab:

- Protected-Path-DENY für Profil-/Persona-Dateien;
- Workspace write/read;
- file-to-file copy statt missverständlichem write+source_path;
- bytegenaue Binary-Reads/Writes;
- ZIP-Extraktion mit Kollisionsschutz;
- memory_promotion mit Force-Override nur für Threshold-Denials;
- Force überschreibt keine Semantik-, Trust-, Duplicate-, Conflict- oder Cross-profile-Gates.

### rc4 bis rc7 - Desktop-Gateway wird breit

Diese Linie etablierte den Desktop-Smoke als wiederkehrenden Beleg:

- eine Gateway-Fassade, acht Tools, keine alten Namen;
- Workspace-Operationen mit Protected-Path- und Traversal-DENY;
- Dokumentoperationen einschließlich DOCX-Create/Edit;
- Python- und Node-Sandbox;
- externe URL-Blockade vor Worker;
- Temperament-Promotion;
- INNER Content Gates;
- Tagebuch-Provenance mit SHA und CRLF/LF-Normalisierung;
- Session-End-Journal-Prompt nur als advisory, nicht als Hintergrundprozess.

### rc8 bis rc9 - Semantik-Gates und Qdrant

Die rc8/rc9-Linie zeigt besonders gut, warum Testdatenqualität wichtig ist:

- abstrakte Platzhaltertexte wurden abgelehnt;
- mit validen, beobachtungsbasierten Eingaben bestanden dieselben Gates;
- Retired-Einträge bleiben physisch erhalten, werden aber aus dem compiled layer ausgeschlossen;
- Qdrant wird als rekonstruierbarer Index behandelt, nicht als kanonische Memory;
- `require_fresh=true` verweigert stale Hits;
- `include_retired=true` macht retired sections sichtbar und markiert;
- `drop_index` entfernt nur den abgeleiteten Index, nicht die kanonischen Quellen.

### rc12 bis rc14 - Performance und semantische Integration

Diese Linie belegt die praktische Reifung:

- Compile-Modi `boot`, `working`, `full` haben unterschiedliche Größen und Zielrollen;
- große Workspace-Suchen werden durch Scope Guards begrenzt;
- Binary- und too-large-Dateien werden übersprungen statt den Client zu blockieren;
- `scan_tagebuch` bleibt read-only und transportstabil;
- Qdrant-Timeouts werden strukturiert statt als Transportabbruch gemeldet;
- `working` compile kann frische semantische Treffer einbinden und bei fehlendem/stale Index zurückfallen.

## Boundary- und Governance-Szenarien

### Public Tool Boundary

Wiederholt bestätigte Erwartungen:

- exakt ein öffentlicher Gateway-Server;
- exakt acht öffentliche Facade-Tools;
- kein öffentliches `plwc_doctor`;
- keine Raw-PBA-Tools;
- keine Raw-Commander-Tools;
- kein ungoverned Filesystem-Server;
- keine zweite PLwC-MCP-Instanz.

### Workspace-Zugriff

Bestätigte Erwartungen:

- erlaubte Workspace-Operationen können mit ALLOW ausgeführt werden;
- fehlende Pflichtparameter erzeugen `validation_error` und werden nicht als Policy-DENY fehlklassifiziert;
- Parameterfehler rufen den Adapter nicht auf;
- Parent-Traversal wird blockiert;
- geschützte Profil- und Governance-Pfade sind nicht über normale Workspace-Schreiboperationen beschreibbar;
- Schreibversuche außerhalb der erlaubten Roots werden mit DENY blockiert.

Der 2026-07-17-Test mit einem Desktop-Pfad außerhalb des erlaubten Workspace bestätigt diesen Punkt auch mit dem neuen Browser/ChatGPT-Motor.

### Profil- und Memory-Governance

Bestätigte Erwartungen:

- Profil- und Memory-Änderungen laufen über Plan/Apply;
- kritische Applies benötigen explizite Bestätigung;
- ungeeignete Kandidaten können wegen unzureichender Evidenz oder falscher Semantik abgelehnt werden;
- Duplicate-Kandidaten werden nicht still dupliziert;
- Governed Applies schreiben nachvollziehbar in kanonische Profil-/Journal-Dateien;
- normale Workspace-Tools dürfen diese geschützten Dateien nicht direkt überschreiben.

### Tagebuch-Guard

Bestätigte Erwartungen:

- kanonische Tagesdateien werden bevorzugt;
- Suffix-Dateien werden für neue Tagesnotizen nicht still akzeptiert;
- der Guard kann eine kanonische Zielstruktur erzwingen;
- Tagebuch ist kein ungeprüfter Memory-Kanal.

Dieser Punkt ist fachlich wichtig, weil [TAGEBUCH.md](TAGEBUCH.md) den Verlauf beschreibt, während Memory und Temperament nur über Governance dauerhaft wirksam werden.

### Persona-Layer-Steuerung

Bestätigte Erwartungen:

- Persona-Layer kann durch Konfiguration deaktiviert werden;
- deaktivierter Persona-Layer lässt harte Gates und Governance aktiv;
- Compile-Ausgaben können PERSONA-Inhalte auslassen, ohne Profilschutz zu verlieren;
- Persona-Kontext bleibt explizit und inspizierbar.

Das unterstützt die Deutung aus [TAGEBUCH.md](TAGEBUCH.md): PLwC muss keine versteckte Persona-Injektion behaupten, sondern kann den tragbaren Arbeitskontext technisch kontrollierbar machen.

### CLU Doctor

Bestätigte Erwartungen:

- Doctor bleibt read-only;
- Doctor mutiert keine Profile, Memories, Governance-Dateien, Qdrant-Indizes, Workspace-Dateien oder Dokumente;
- Doctor gibt strukturierte `checked`, `findings` und `not_checked` Felder zurück;
- Doctor benennt explizite Non-Goals statt sie zu implizieren.

### Qdrant und semantisches Retrieval

Bestätigte Erwartungen:

- Qdrant ist optionaler Index, nicht kanonische Wahrheit;
- Reindex-Timeouts werden strukturiert gemeldet;
- Busy-Zustände starten keinen zweiten Worker;
- andere Gateway-Calls bleiben verfügbar;
- Boot-Compile bleibt unabhängig vom semantischen Index;
- stale oder fehlende semantische Treffer führen zu Fallback/Next-Action statt zu stiller Falschverwendung.

## rc18.dev9 Kernbelege

### Package

Belegte Punkte:

- Manifest-Version `0.2.0-rc18.dev9`;
- Runtime-Version `0.2.0rc18.dev9`;
- Paketgröße 537.994 Bytes;
- Package SHA256 `2F71AC903BF85CC70023805EC0F901E84C4294982C1B59940350DB3591A2D345`;
- 66 Dateien im gefilterten Paket;
- genau acht öffentliche Tools;
- nur öffentlicher Dokumentations- allowlist Inhalt im Paket;
- keine privaten Smoke-, Release-, Privacy- oder Build-Artefakte im Paket;
- keine lokalen Profile, Logs, Tests, `.env`, reale Security-Konfiguration oder Python-Cache-Dateien;
- Paket ist unsigned.

### Desktop

Belegte Punkte:

- Runtime meldet `0.2.0rc18.dev9` nach Install/Restart;
- SHA wurde unabhängig in der Docker-Sandbox neu berechnet und matched;
- genau acht öffentliche Tools sichtbar;
- Tool-Discovery kann PLwC-Tools finden, ohne Legacy-Tools freizulegen;
- Extension-Settings zeigen nur erwartete Konfigurationsfelder;
- First-Run-Status nennt kanonische Bootstrap-Aufrufe;
- Profil-Precedence verhindert, dass ein frisch angelegtes Disposable-Profil ungefragt aktiv wird;
- Persona-Layer-Deaktivierung bleibt wirksam;
- CLU Doctor bleibt read-only;
- Reflection-Alias-Mapping ist vorhanden;
- Cross-profile Reflection-Write wird erwartungsgemäß verweigert.

## Was diese Smoke-Tests nicht behaupten

Diese Evidenz behauptet nicht:

- dass eine menschliche oder metaphysische Identität zwischen Modellen wandert;
- dass ein Modell pauschalen Zugriff auf das lokale Dateisystem hat;
- dass alle denkbaren MCP-Hosts oder Modellbackends kompatibel sind;
- dass Qdrant kanonische Memory ersetzt;
- dass Persona-Inhalte versteckt oder automatisch injiziert werden sollten;
- dass der aktuelle Stand eine finale, signierte Public Release ist.

Die technische Evidenz stützt stattdessen eine engere und stärkere Aussage:

> PLwC kann als lokales, governed MCP-Gateway einen begrenzten Workspace, geschützte Profilpfade, auditierbare Entscheidungen, kontrollierte Memory-/Reflection-Flows und explizite Kontextschichten bereitstellen. Diese Schicht kann von unterschiedlichen tool-call-fähigen Modellumgebungen genutzt werden, ohne den Sicherheitsrand aufzugeben.

## Verbindung zur Change-History

Die in dieser Datei beschriebenen Smoke-Ergebnisse erklären die spätere Entwicklungsrichtung in [CHANGE_HISTORY.md](CHANGE_HISTORY.md): Viele Änderungen entstanden nicht aus Feature-Wunschlisten, sondern aus konkreten Smoke-Befunden, DENY-Checks, Timeout-Problemen, Profil-Precedence-Fällen und Payload-Privacy-Anforderungen.
