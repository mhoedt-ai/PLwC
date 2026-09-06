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

## Nachtrag 2026-07-21 - ChatGPT-Bridge-Protokoll

Der ChatGPT-Bridge-Transport wurde auf `0.2.0-rc19.dev11` angehoben. Tool-Calls werden im Primer nicht mehr als intern wirkende Event-Sequenzen beschrieben, sondern als eigenes `plwc_tool_call`-Wrapper-JSON. Zudem werden grosse Tool-Resultate fuer den Chat-Transport kompakt gehalten. Technische Detailnotiz: `integrations/plwc-chat-bridge/SESSION_NOTES_2026-07-21.md`.

Nachtrag `0.2.0-rc19.dev12`: Fuer `plwc_profile compile_mode=full` erzwingt der Chat-Bridge-Primer jetzt: "Full" gilt erst als vollstaendig verarbeitet, wenn ein lokales Sandbox-/Chunk-Verfahren alle Chunks bestaetigt hat. Bei Fehlschlag soll GPT den Fehler nennen und `compile_mode=working` mit praezisem `task_context` als Arbeitsmodus anbieten. Gateway-Code wurde dafuer nicht geaendert.

Nachtrag `0.2.0-rc19.dev13`: Die Full-Regel wurde verallgemeinert. Nicht nur `full`, sondern jeder `plwc_profile operation=compile`-Layer (`boot`, `working`, `full`) gilt als vollstaendigkeitskritisch. Die alte 1.800-Zeichen-Kappe bleibt fuer generische lange Strings, wird aber nicht mehr auf `data.compiled_layer` angewendet. Grosse Compile-Layer werden vollstaendig als `plwc_profile_compile_layer_chunks.v1` mit Chunk-Zaehlern und SHA-256-Metadaten transportiert. Der Sandbox-Artefaktweg ist nicht mehr der Sollweg fuer diese Resultate.

Nachtrag `0.2.0-rc19.dev16`: Die Chunk-Transportregel gilt nun allgemein fuer grosse Tool-Resultate. Uebergrosse Governor-, Workspace- und andere Result-JSONs werden als `plwc_result_json_chunks.v1` mit vollstaendigen Chunks, Chunk-Zaehlern und SHA-256-Pruefung an den Chat uebergeben, statt relevante Felder nur als `omitted_keys` zusammenzufassen. Profile-Compile-Layer behalten ihr spezialisiertes Layer-Protokoll; Sandbox-Resultate werden weiterhin vor dem Chunking um redundante Docker-Details bereinigt.

Nachtrag `2026-07-25 Windows-Installer`: Die optionale Chat Bridge wird nun
vollständig vom Setup integriert. Das Setup führt die mitgelieferten
Native-Messaging- und Autostart-Skripte intern aus, registriert Chrome und Edge
für die stabile Extension-ID und erstellt eine eingeschränkte benutzerbezogene
Aufgabe mit 20 Sekunden Anmeldeverzögerung. Start und `Reconnect` prüfen den
konfigurierten Loopback-Endpunkt auf genau `8/8` Werkzeuge. Reparatur-/Upgrade-
Fehler stellen die vorherige Aufgabe und Launcher-Konfiguration wieder her;
die Deinstallation entfernt Aufgabe, Prozess, Registry-Einträge und Manifest.

Nachtrag `2026-07-25 Windows-Installer UI`: Die Voraussetzungsliste reagiert
nun über Inno Setups `OnClickCheck` unmittelbar auf Python-, Node- und
Docker-Auswahl. `Weiter` wird nur für einen vollständigen Pflichtplan aktiv;
auf der Bereit-Seite verwendet Inno wieder `Installieren` beziehungsweise
`Install`. Abgesicherte deutsche und englische UI-Läufe, Gateway- und
Chat-Bridge-Auswahltests sowie ein lokaler SHA-256-geprüfter Downloadtest
decken die Regression ab. Der neue Kandidat bleibt bis zum exakten
Clean-Windows-VM-Lauf G5 `HOLD`.

Nachtrag `2026-07-27 Windows-Installer installer-r2`: Importierte WinAPI-
Funktionen verwenden nun Windows `BOOL` statt Pascal `Boolean`; der
Prozessstart-Record wird vollständig initialisiert. Unerwartete Fehler bei
Auswahl, Prüfung oder Installation werden mit genauer Phase dauerhaft unter
`%LOCALAPPDATA%\PLwC\logs\setup\installer-diagnostic.log` protokolliert.
Der eindeutige Dateiname `PLwC-Setup-0.2.0-rc18.dev9-installer-r2.exe`
verhindert die Verwechslung mit älteren VM-Kopien. Native API-, Auswahl-,
Weiter-, Sprach-, Bereit-Seiten- und SHA-256-Download-Fixtures bestanden;
echte Fremdinstaller und Neustart bleiben G5.

Nachtrag `2026-07-27 Chat-Bridge Altverlauf`: Beim Start und nach einem
ChatGPT-Konversationswechsel wird nun eine ruhige Bestandsaufnahme aufgebaut.
Bereits vorhandene Tool-Call-JSONs und alte Chain-Recovery-Texte werden damit
nicht mehr als neue automatische Arbeit ausgefuehrt. Die Extension-Suite
deckt Start waehrend einer laufenden Antwort und den Wechsel in einen alten
Chat ab (`88/88`).

Nachtrag `2026-07-27 Windows-Installer installer-r3`: Der auszuliefernde
Kandidat traegt bewusst eine neue Revision, damit bereits kopierte
`installer-r2`-Zwischenstaende nicht mit dem finalen Payload verwechselt
werden. Nur die `installer-r3`-EXE mit dem in den G3-Evidenzen genannten
SHA-256 ist der aktuelle G5-Testkandidat.

Nachtrag `2026-08-08 Gateway dev10 / Windows-Installer r14`: Ein in der
erhaltenen Windows-VM reproduzierter Timeout von `docker.exe info` brach den
optionalen First-Run-Status vollstaendig ab. Gateway `0.2.0-rc18.dev10` faengt
Daemon- und Image-Probe-Timeouts nun als Safe Mode ab, sodass das geregelte
Profil-Onboarding ohne laufendes Docker fortgesetzt werden kann. Setup
`installer-r14` integriert dev10 und behaelt die akzeptierte Chat Bridge
`0.2.0-rc19.dev20`. Gateway-, Bridge-, Extension- und Setup-Vertraege sowie
geschuetzte deutsche und englische Produktions-UI-Laeufe sind lokal `PASS`;
die erneute VM-Endabnahme bleibt der naechste manuelle Schritt.

Nachtrag `2026-08-08 Windows-VM-Endabnahme r14`: Der exakte r14-Pfad wurde auf
der erhaltenen Windows-VM end-to-end bestaetigt. Gateway dev10, acht Werkzeuge,
Profil-Onboarding und -Aktivierung, Persona-Schalter, Full-Compile,
Reflection/Governor, Tagebuch-Write sowie Trashcan- und Loeschschutzregeln
bestanden. Der manuelle Windows-System-Gate fuer `SETUP-P0-02-FIX-04` ist
geschlossen. Das öffentliche englische Protokoll liegt unter
`docs/evidence/SETUP_P0_02_FIX_04_VM_ACCEPTANCE_EN.md`; die zehn
SHA-256-erfassten Screenshots bleiben wegen Browser- und VM-Metadaten privat.

Nachtrag `2026-08-08 Windows-Installer r15 / SETUP-P1-02`: Setup installiert
nun eine lokale englische oder deutsche Bedienungsanleitung, oeffnet sie auf
der Abschlussseite standardmaessig und stellt sie dauerhaft im Startmenue
bereit. Die Anleitung beschreibt insbesondere Bridge-Status `8/8`, Primer
`Generate` und `Insert Bridge Primer`, das anschliessende manuelle Absenden
sowie natuerlich formulierte Aufgaben, aus denen die KI nach Schema-Pruefung
die korrekten PLwC-Aufrufe ableitet. Compile, Reflection, Governor, Tagebuch,
Trashcan, Persona-Promotion, Force und Neustartpfade sind abgedeckt. Gateway
dev10 und Chat Bridge dev20 bleiben unveraendert; alle automatisierten
Vertraege und beide geschuetzten Produktions-UI-Laeufe bestehen. Der letzte
manuelle Gate ist das Oeffnen der lokalisierten Anleitung auf der erhaltenen
Windows-VM.

Nachtrag `2026-08-08 Windows-Installer r16 / SETUP-P1-02-FIX-01`: Die lokale
Bedienungsanleitung beginnt nun mit getrennten Wegen fuer Gateway-only, Claude
Desktop MCPB, Codex STDIO, Odysseus STDIO und Chat Bridge. Der Primer ist
ausdruecklich nur fuer die Bridge erforderlich; native MCP-Clients erhalten
ihre Werkzeugschemas direkt. Status, Describe, Onboarding, Compile, Reflection,
Governor, Tagebuch, Trashcan, Persona-Promotion und Force erklaeren jetzt in
normaler Sprache Zweck, Einsatzzeitpunkt und moegliche Aenderungen. Compile
wird eindeutig als lesendes Laden des aktiven Profils in eine geregelte
Kontextschicht beschrieben und nicht als Kompilieren von Programmcode. Gateway
dev10 und Bridge dev20 bleiben unveraendert. Alle `45` fokussierten und `64`
vollstaendigen Installer-Vertraege sowie beide geschuetzten Produktions-UI-
Laeufe bestehen; die r16-EXE ist an `SETUP-P1-02-FIX-01` gebunden.

Nachtrag `2026-08-08 Windows-Installer r17 / SETUP-P1-03`: Setup installiert
nun eine eigenstaendige lokale PLwC-Konfiguration fuer Gateway-only, Claude
Desktop, Codex, Odysseus und Chat Bridge. Aktives Profil, Memory-, Persona-
und Temperament-Schwellen sowie Persona Layer und Qdrant lassen sich damit
clientunabhaengig verwalten. Die gemeinsamen Werte werden atomar in
`gateway-settings.json` gespeichert; Profilwechsel bleiben durch Governor
Plan, Vorschau und ausdrueckliches Apply geschuetzt. Die Seite bindet nur an
`127.0.0.1`, verwendet eine zufaellige Sitzung, strikte Browser-Header und
keine externen Inhalte. Deutsch und Englisch, Desktop und schmale Ansicht
sowie die echte Governor-Vorschau wurden lokal geprueft. Gateway dev10 und
Chat Bridge dev20 bleiben unveraendert; die finale r17-Artefaktbindung steht
in `SETUP_P1_03_ACCEPTANCE_EN.md`.

Nachtrag `2026-08-09 Windows-Installer r18 / SETUP-P1-04`: Die lokale
Konfigurationsseite bietet nun ein gefuehrtes, durch Governor Plan und Apply
geschuetztes Profil-Onboarding. Antworten werden erst nach einer
Digest-gebundenen Vorschau und ausdruecklichen Bestaetigung in die sieben
Profildateien uebernommen; das neue Profil wird anschliessend geregelt aktiv.
Konfiguration und Einstiegshilfe verlinken sich innerhalb derselben lokalen
Loopback-Sitzung. Setup legt die PLwC-Konfiguration zusaetzlich direkt auf dem
Benutzer-Desktop ab. Gateway dev10 und Chat Bridge dev20 bleiben unveraendert;
die finale Artefaktbindung steht in `SETUP_P1_04_ACCEPTANCE_EN.md`.

Nachtrag `2026-08-09 Windows-Installer r19 / SETUP-P1-04-FIX-01`: Die
Pflichtfeldpruefung des neuen Profil-Onboardings blockierte in r18 auch
`Abbrechen` und das Schliessen-Symbol. Alle Dialog-Abbrueche umgehen nun nur
die Formularvalidierung; `Erstellungsplan pruefen` validiert weiterhin alle
aktiven Pflichtfelder. Der leere Dialog wurde im Browser ueber beide Wege
erfolgreich geschlossen. Gateway dev10 und Chat Bridge dev20 bleiben
unveraendert.

Nachtrag `2026-08-09 Windows-Installer r20 / SETUP-P1-04-FIX-02`: Der Kopf
der Einstiegshilfe entspricht nun der lokalen Konfigurationsseite.
`Konfiguration oeffnen` steht oben rechts neben dem Status fuer lokale
Dokumentation; die horizontale Abschnittsleiste beginnt wieder vollstaendig
mit `Installationswege`. Desktop- und 390-x-844-Ansicht wurden ohne
horizontales Seiten-Overflow geprueft. Gateway dev10 und Chat Bridge dev20
bleiben unveraendert.

Nachtrag `2026-08-09 STORE-G0-01 interne Vorbereitung`: Die aktuellen Chrome-
und Edge-Anforderungen wurden ausschliesslich gegen offizielle Google- und
Microsoft-Quellen abgeglichen. Fuer die Chat Bridge liegen nun englische
Listing-, Permission-, Datenschutz-, Reviewer- und Screenshot-Unterlagen,
statische Datenschutz- und Support-Seiten fuer die bestehende `plwc.de`-Basis,
ein oeffentlicher Store-ID-Vertrag sowie eine sichere Product-Owner-Checkliste
vor. Ein key-loser, als nicht einreichbar markierter Draft-Seed trennt die
spaeteren Store-Identitaeten von der Development-/Sideload-ID
`nlogfcafjdfdoknpkbehjgihpafpipdb`. Die Extension-Gesamtpruefung besteht mit
`148/148`. Datenschutz, Support, gemeinsames Stylesheet und die Links von der
PLwC-Startseite sind inzwischen live ueber HTTPS verifiziert. Publisher-Konten
und die Edge-Draft-ID bleiben extern `PENDING`. Chrome-Publisher-Name,
Kontakt-/2FA-Pflicht, Dashboard-Berechtigung und die Kontrolle ueber `plwc.de`
wurden extern bestaetigt. Der key-lose Chrome-Upload hat die oeffentliche
Store-ID `feceodobnhefdbfgmbinkndhogpfkicb` erzeugt; sie ist vom Development-
und Sideload-Vertrag getrennt und der Artikel blieb unveroeffentlicht.
STORE-G0-01 bleibt bis zum Edge-Abschluss weiterhin ausdruecklich `HOLD` und
nicht `PASS`.

Nachtrag `2026-08-09 STORE-G0-01 Abschluss`: Der bestehende individuelle
Microsoft-Partner-Center-Zugang, die Edge-Workspace-Berechtigung und der
erfolgreiche key-lose Draft-Upload wurden extern bestaetigt. Der unveroeffentlichte
Edge-Entwurf besitzt die oeffentliche CRX-ID
`nncomjknhhlgcmkmlaljhkiojcnpmflb`; sie unterscheidet sich sowohl von der
Chrome- als auch von der Development-/Sideload-ID. Partner Center stellt die
tatsaechliche Listing-URL erst nach einer Veroeffentlichung bereit, daher ist
vorerst nur der aus der CRX-ID abgeleitete zukuenftige Add-ons-Pfad dokumentiert.
STORE-G0-01 ist damit `PASS`; Einreichung, Zertifizierung, Veroeffentlichung,
finale Listing-URL und identity-aware Packaging bleiben spaeteren Gates
vorbehalten.

Nachtrag `2026-08-10 BRIDGE-P0-03 interne Umsetzung`: Der kanonische
Extension-Vertrag unterscheidet nun Development/Sideload, Chrome Web Store und
Microsoft Edge Add-ons mit exakt drei Native-Messaging- und WebSocket-Origins.
Bridge und Native Launcher lehnen fremde IDs und Wildcards ab; der Launcher
prueft den Acht-Werkzeug-Vertrag ueber alle drei genehmigten Origins. Getrennte,
deterministische Chrome/Brave- und Edge-ZIPs enthalten nur `manifest.json`,
`background.js`, `content.js` und das PLwC-Icon. Development-Key, Source Maps,
Repository-Dateien und hochkonfidente Secret-Muster sind ausgeschlossen; je
Ziel bindet eine externe Buildidentitaet den ZIP-Hash an die echte Store-ID.
Bridge `26/26`, Extension `173/173`, Store-Reproduzierbarkeit und Windows Native
Build bestehen lokal. Das Gate bleibt dennoch `HOLD`, bis echte Store-ID-
Browser-/Launcher-Laeufe, die fuenf finalen Screenshots, ein versionierter
oeffentlicher Setup-Download und die erneuerte H2-Abnahme vorliegen.
