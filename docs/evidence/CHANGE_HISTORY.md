# Change-History Evidence

Stand: 2026-07-17

Dieses Dokument fasst den Entwicklungsverlauf von PLwC anonymisiert und evidenzorientiert zusammen. Es enthält keine Links auf Originaldateien oder lokale Rohberichte. Für Kontext siehe:

- [TAGEBUCH.md](TAGEBUCH.md) - anonymisierte Verlaufserzählung
- [SMOKE_TESTS.md](SMOKE_TESTS.md) - technische Smoke- und Governance-Belege

## Kurzüberblick

PLwC entwickelte sich in drei größeren Bewegungen:

1. Sicherheits- und Gateway-Fundament: lokales MCP-Gateway, feste Public Boundary, Workspace- und Profilschutz.
2. Kontinuitäts- und Governance-Schicht: Profile, Memory, Reflection, Tagebuch, Governor, auditierbare Promotions.
3. Modell- und Host-Unabhängigkeit: Persona-Layer-Steuerung, Privacy-Packaging, Browser/ChatGPT-Adapter und Wiederaufnahme des Arbeitskontexts außerhalb der ursprünglichen Modellumgebung.

## April bis Anfang Mai 2026 - Fundament

| Datum | Abschnitt | Inhalt |
| --- | --- | --- |
| 2026-04-30 | Projektstruktur | Initiale PLwC-Gateway-Struktur entsteht. |
| 2026-04-30 | Source Intake | Quellmaterial und Migrationspfad werden analysiert. |
| 2026-04-30 | Requirements | Traceability und Verifikationsplan werden angelegt. |
| 2026-04-30 | Policy Core | Grundlegende Policy- und Boundary-Tests entstehen. |
| 2026-04-30 | MVP Gateway | MVP-Gateway-Fundament wird abgeschlossen. |
| 2026-04-30 | Security Review | Erste Sicherheitsreview benennt Release-Blocker. |
| 2026-05-01 | Root-/Path-Hardening | Konfigurationsroots und geschützte Pfade werden gehärtet. |
| 2026-05-01 | Audit-Redaction | Audit-Logging wird gegen sensitive Daten gehärtet. |
| 2026-05-01 | Docker-Policy | Docker-Sandbox wird mit dem Sicherheitsmodell abgeglichen. |
| 2026-05-01 | Governor/PBA | Governor- und PBA-Integration werden abgesichert. |
| 2026-05-01 | Preflight | Release-Preflight-Gates werden dokumentiert. |

Leitmotiv dieser Phase: Erst Sicherheitsrand und überprüfbare Grenzen, dann Komfort.

## Mai 2026 - Erste Release Candidates und reale Workflows

| Datum | Version/Stand | Inhalt |
| --- | --- | --- |
| 2026-05-02 | v0.1.0-rc1/rc2 | Erste v0.1 Release Candidates nach Packaging-, Registry-, Docker- und Symlink-Validierungen. |
| 2026-05-07 | v0.1.0-rc3 bis rc5 | Stabilisierung der frühen Gateway- und Packaging-Linie. |
| 2026-05-23 | v0.2.0-rc1 | Start der v0.2-Linie mit stärkerem Profil-, Persona- und Governance-Fokus. |
| 2026-05-24 | Tagebuch-Beginn als Kontinuitätsmedium | Tagebuch wird als leichter Session-Kontinuitätsanker genutzt. |
| 2026-05-25 | Dokument-Workflow | Reale Dokumentarbeit zeigt Nutzen und Grenzen vorhandener Document-Operationen. |

In dieser Phase zeigt sich, dass PLwC nicht nur Smoke-Test-Infrastruktur ist. Es wird in längeren Arbeitsabläufen benutzt, wobei Fehler und Workarounds direkt in Backlog und Governance zurückfließen.

## Juni 2026 - Memory, Tagebuch und Governor werden zentral

| Datum | Version/Stand | Inhalt |
| --- | --- | --- |
| 2026-06-03 | v0.2.0-rc2 | Write-/Wrapper-Probleme werden sichtbar und behoben; Kontinuität zwischen Diagnose, Fix und erneutem Test wird praktisch erfahrbar. |
| 2026-06-04 | v0.2.0-rc3 | Stabilisierung und Private-Beta-Readiness. Leere Profile werden gegen gewachsene Profile verglichen. |
| 2026-06-05 | v0.2.0-rc4 | Dokumenteditierung und Governance-DENYs werden erfolgreich geprüft. |
| 2026-06-09 | v0.2.0-rc5 | Node.js-Sandbox und Image-Path-Validation werden ergänzt. |
| 2026-06-10 | v0.2.0-rc6 | Größerer Smoke-Durchlauf, erneute Verifikation statt Vertrauen auf Vorzustand. |
| 2026-06-10 | v0.2.0-rc7 | Session-End-Journal-Prompt und Provenance-/SHA-Fixes. |
| 2026-06-13 | v0.2.0-rc8 | Memory Governance wird stärker. Suite: 947 passed / 4 skipped in der damaligen Linie. |
| 2026-06-19 | v0.2.0-rc10 | INNER-Hardening, Qdrant-Konfigurationsfenster, weitere P1-P4-Fixes. Suite: 939 passed / 4 skipped in der damaligen Linie. |
| 2026-06-19 | v0.2.0-rc11 | Read-only Tagebuch-Pattern-Scanner wird eingeführt. Suite: 947 passed / 4 skipped in der damaligen Linie. |
| 2026-06-30 | v0.2.0-rc12 | Performance- und Retrieval-Reibung werden stärker sichtbar. |

Leitmotiv dieser Phase: Das System beginnt, aus seinen eigenen Spuren zu lernen, aber nur über Prüfpfade. Scanner liefern Hinweise, nicht Wahrheit.

## Ende Juni bis Anfang Juli 2026 - Reibung wird Produktarbeit

| Datum | Version/Stand | Inhalt |
| --- | --- | --- |
| 2026-06-30 | Performance-/Qdrant-Reibung | Semantisches Retrieval und lange Compiles zeigen Grenzen im Alltag. |
| 2026-07-01 | v0.2.0-rc13 | Crash-Guard verbessert Timeout-Verhalten; Retrieval bleibt noch nicht tragender Arbeitskern. |
| 2026-07-01 | Evidenz vor Autorität | Ein Profil-/Namensdetail wird erst nach Belegen korrigiert, nicht aufgrund bloßer Behauptung. |
| 2026-07-02 | Tagebuch vs. Reflection | Tagebuch und Reflection werden als getrennte Pfade verstanden: ungefilterte Spur vs. governed Kandidat. |
| 2026-07-03/04 | Arbeitsstil-Kalibrierung | Bei Serienarbeit zeigt sich das Muster: erst Beispiel kalibrieren, dann breit anwenden. |
| 2026-07-05 | rc16.dev0 | Qdrant Maintenance Guard behebt globalen Stall durch strukturierte Timeout-/Busy-Zustände. |
| 2026-07-05 | rc17.dev0 | CLU Doctor, Workspace-Diagnostik, Tagebuch-Guard und Temperament-Threshold werden geprüft. |

Diese Phase ist wichtig, weil sie zeigt, dass Fehler nicht nur repariert, sondern in Regeln, Tests und Arbeitsmuster übersetzt werden.

## Juli 2026 - rc18, Packaging, Persona-Layer und Public Boundary

| Datum | Version/Stand | Inhalt |
| --- | --- | --- |
| 2026-07-06 | rc18.dev0 Package | Command-Katalog wird Discovery-only; kein Tool-Expansion-Effekt. |
| 2026-07-07 | rc18.dev0 Desktop | CLU Runner wird im Desktop-Kontext geprüft; read-only und no-leak Verhalten bestätigt. |
| 2026-07-08 | rc18.dev1-dev6 | Mehrere schnelle Entwicklungsstände verbessern Desktop- und Package-Verhalten. |
| 2026-07-09 | rc18.dev7 Desktop | First-Run-Bootstrap, aktive Profil-Precedence und Persona-Layer-Deaktivierung werden bestätigt. |
| 2026-07-10 | rc18.dev9 Package | Privacy Payload Filtering, Alias-Metadaten und Onboarding-Baseline werden paketiert. |
| 2026-07-11 | rc18.dev9 Desktop | Install/Runtime, SHA-Abgleich, Privacy-Sanity, First-Run, Precedence, Doctor und Reflection-Aliase bestehen. |
| 2026-07-12 | Open-Beta-Publikationsstand | Public Snapshot und Open-Beta-Unterlagen werden normalisiert. |
| 2026-07-13 | Registry-/Kontakt-Dokumentation | Gateway-Positionierung, Registry-Metadaten und Projektkontakt werden dokumentiert. |

Der wichtigste technische Shift: Persona und Arbeitskontext werden explizit kontrollierbar. Der Persona-Layer kann deaktiviert werden, ohne Governance oder Hard Gates zu verlieren.

## 2026-07-13 bis 2026-07-17 - Modellübergreifender Anschluss

| Datum | Ereignis | Bedeutung |
| --- | --- | --- |
| 2026-07-13 | Erstes Laden des gewachsenen Profils in Codex/GPT | Boot- und Full-Compile funktionieren nach anfänglicher Korrektur. Die Arbeitsgeschichte beginnt nicht bei null. |
| 2026-07-17 | Browser/ChatGPT-Motor mit lokalem Gateway | Workspace-Zugriff, Tagebuch-Arbeit, Reflection, Governor und Memory-Übernahme funktionieren im neuen Modellkontext. |
| 2026-07-17 | Desktop-DENY-Test | Schreibversuch außerhalb erlaubter Roots wird blockiert. Governance hält auch mit neuem Motor. |
| 2026-07-17 | Temperament Version 17.0 | "Kalibrierung vor Serienarbeit" wird nach Tagebuchanalyse, Governor-Prüfung und Bestätigung übernommen. |

Diese Phase ist der stärkste Werdegangsbeleg für die These aus [TAGEBUCH.md](TAGEBUCH.md): PLwC transportiert keine fortlaufende Instanz, aber eine dokumentierte Kontinuitätsschicht.

## Verdichtete technische Entwicklungslinie

| Thema | Früher Stand | Späterer Stand |
| --- | --- | --- |
| Public Boundary | Gateway-Fassade entsteht | genau acht öffentliche Tools, keine Raw-Server |
| Dateizugriff | Workspace-Root und Protected Paths | Deny-by-default, Parent-Traversal-Block, Desktop-DENY außerhalb erlaubter Roots |
| Audit | Metadaten-Audit | No-content/No-secret-Logging, High-risk Fail-Closed |
| Profile | Profiltexte und Memory | Governor-Plan/Apply, Profile-Precedence, Persona-Layer-Steuerung |
| Tagebuch | Kontinuitätsnotiz | Scanner-Quelle, aber nicht automatisch Memory |
| Reflection | Beobachtungsablage | governed Kandidatenpfad |
| Qdrant | hilfreicher semantischer Index | optional, stale-aware, nicht kanonisch |
| Doctor | Einzelne Diagnostik | read-only CLU Runner mit checked/findings/not_checked |
| Packaging | MCPB-Artefakte | Privacy-gefilterte Pakete mit öffentlicher Allowlist |
| Modellumgebung | primär eine Desktop-App | anschlussfähig in Codex/GPT und Browser/ChatGPT-Kontext |

## Evidenzorientierte Schlussfolgerung

Der Änderungsverlauf spricht für eine Architektur, die aus realen Fehlern gelernt hat:

- Ein falsch klassifizierter Parameterfehler führte zu saubererer Workspace-Diagnostik.
- Qdrant-Stalls führten zu Timeout-/Busy-Guards.
- Scanner-Echo führte zu stärkerem Misstrauen gegenüber automatisch gefundenen Mustern.
- Persona-Reibung führte zu expliziter Persona-Layer-Steuerung.
- Packaging-Risiken führten zu Privacy Payload Filtering.
- Modellwechsel führte zur klareren Formulierung von "dokumentierter Kontinuität" statt Instanzbehauptung.

Die Smoke-Test-Belege zu diesen Punkten stehen zusammengefasst in [SMOKE_TESTS.md](SMOKE_TESTS.md). Die erzählerische Einordnung steht in [TAGEBUCH.md](TAGEBUCH.md).
