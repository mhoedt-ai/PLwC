# r26 Phase 2 – Konfigurationsseite und Profilfehler

Stand: 4. September 2026

## Ergebnis und nachträgliche Korrektur

Das Phase-2-Gate wurde am 4. September erneut geöffnet, weil die ursprüngliche
Abnahme die fest eingetragene `unknown`-Beobachtung für den Document Worker und
die unvollständige Docker-/Qdrant-Erkennung nicht beanstandet hatte. Dieser
Status war mit der Briefing-Forderung nach tatsächlich lokal erkannten Werten
nicht vereinbar. Nach Implementierung der fehlenden Probes und Regressionstests
ist das Gate erneut erfüllt. Die lokale Konfigurationsseite behandelt
fachliche Ablehnungen getrennt vom HTTP-Transport, zeigt ungültige Profile mit
konkretem Grund und fehlenden Dateien an und lässt deren Aktivierung nicht zu.
Workspaceänderungen sind aus dem allgemeinen Speichervorgang entfernt und
verwenden einen eigenen Plan-/Bestätigungsablauf.

## Profil- und Fehlervertrag

- `runtime.available_profiles` enthält strukturierte Einträge mit `name`,
  `path`, `exists`, `valid`, `status`, `reason`, `missing_files`, `active` und
  `activatable`.
- Ein leerer Ordner `FAUN` bleibt sichtbar, wird aber als
  `missing_required_files` klassifiziert und nicht als aktivierbar behandelt.
- Der Browserclient wertet `error`, `reason`, `message`, `validation_error` und
  `missing_files` aus.
- Ein fachlich abgelehnter Plan mit HTTP 200 wird als strukturierter Plan
  dargestellt. Der Text `HTTP 200` ist nicht länger der Ersatz für den
  vorhandenen Fachgrund.
- Profilanlage und Profilaktivierung bleiben Plan-/Bestätigungsoperationen;
  ungültige Pläne können nicht angewandt werden.

## Workspaceänderung

- Allgemeine Governance-/Featureeinstellungen ändern den Workspace nicht mehr.
- `POST /api/workspace/plan` prüft den absoluten Zielpfad und Schreibbarkeit,
  listet die anzulegenden Standardordner und alle vorhandenen zu
  synchronisierenden Konfigurationsverweise auf und verändert nichts.
- `POST /api/workspace/apply` verlangt `confirmed=true` und den unveränderten
  SHA-256-Plandigest.
- Vorhandene Workspaceinhalte werden weder verschoben noch kopiert noch
  gelöscht. Dieser Umstand ist im Plan und im Bestätigungsdialog sichtbar.

## Tatsächliches Komponenteninventar

Die Konfigurationsseite baut die Tabelle aus lokalen Beobachtungen und der in
Phase 1 eingeführten Kompatibilitätsmatrix auf. Angezeigt werden unter anderem:

- Installer-Build-ID, Installerrevision und Setup-SHA-256 aus `selection.ini`,
- Gatewayversion und der tatsächliche kanonische 8-Tool-Vertrag,
- Node-Bridge-/Launcher-Versionen, Build-ID und lokale Dateihashes,
- Konfigurationsoberflächen-Version und Hash,
- laufende Python- und Node-Version,
- Docker-CLI-Version und tatsächliche Erreichbarkeit des lokalen Daemons,
- installierte `qdrant-client`-Version unabhängig vom Aktivierungsschalter,
- gepinnte Document-Worker-Imageversion und lokale Image-ID,
- Vertrauensquelle und eindeutiger Status pro Komponente.

Die geladene Browser-Erweiterung wird in Phase 2 bewusst als `unknown`
angezeigt. Die paketierte Sollversion aus der Bridge ist kein Beleg für die im
Browser tatsächlich laufende Version; dieser Nachweis folgt erst mit dem
Handshake in Phase 3.

Für optionale lokale Komponenten gilt jetzt explizit: Ein erfolgreicher
read-only-Probe liefert Version beziehungsweise Build-ID; ein sicher
festgestelltes Fehlen wird als `nicht installiert` angezeigt; nur ein technisch
nicht entscheidbarer Zustand bleibt `unknown`. Die Worker-Prüfung verwendet
`docker image inspect` mit `--pull never`-äquivalenter Semantik und lädt nichts
aus dem Netz.

## Persistiertes Launcher-Letztergebnis

Der native Launcher schreibt atomar nach
`%APPDATA%\PLwC\state\chat-bridge\launcher-last-result.json`. Enthalten sind
Schema, UTC-Zeitpunkt, Aktion, Erfolg, Zustand, Statuscode,
Operation-Exitcode, Meldung, Bridgepfad, Toolanzahl, Logpfad und die gemeinsame
Buildidentität. Die Konfigurationsseite zeigt das letzte vorhandene Ergebnis,
führt bei fehlender Datei aber keinen Start aus.

## Abnahmen

Nach der Inventarkorrektur am 4. September 2026:

- vollständige Python-Suite: `112 passed, 6 skipped`;
- neue Regressionen: installierter Worker samt Version und Image-ID, fehlendes
  Image, nicht erreichbarer Docker-Daemon sowie Qdrant-Version bei
  deaktiviertem Feature;
- tatsächlicher lokaler Snapshot: Docker `29.3.1`, Qdrant-Client `1.18.0`,
  Document Worker `0.1.0`, Image-ID
  `sha256:c81b8c2bd3a4b697453e8d31585ffad2e1540e10fb6941dd2ea02ba5a9470344`;
- Python- und JavaScript-Syntax: PASS;
- Installer-Pester samt isoliertem `ValidateOnly`: `72/72` PASS; gestagte
  Konfigurationsdatei bytegleich mit der Quelle; ISCC nicht aufgerufen.

Ursprüngliche Phase-2-Nachweise vor dieser Korrektur:

- `python -m pytest tests/integration/test_plwc_configuration_ui.py tests/integration/test_component_inventory.py -q`
  – 27 bestanden.
- Zusammen mit den Phase-0-Fixtures – 29 bestanden.
- `npm test --prefix integrations/plwc-chat-bridge/extension` – 174 bestanden.
- `python -m py_compile installer/windows/assets/configuration/plwc-config.py`
  – bestanden.
- `node --check installer/windows/assets/configuration/plwc-config.js` –
  bestanden.
- `installer/windows/build.ps1 -ValidateOnly` – erfolgreich; Node Bridge und
  Extension gebaut, der geänderte C#-Launcher kompiliert, Matrixdateien
  gestaged, Payload geprüft und ISCC nicht aufgerufen. Ausgabe ausschließlich
  unter `installer/windows/.validate-build`.
- `git diff --check` – keine Whitespacefehler.

Es wurde kein Installer-Endbuild erzeugt und keine Storeaktion ausgeführt.

## Gate

**PASS NACH ERNEUTER PRÜFUNG:** Der leere FAUN-Fall wird mit allen sechs fehlenden Dateien erklärt;
kein `HTTP 200` ersetzt mehr den Fachgrund; ungültige Aktivierung ist gesperrt;
Docker, Qdrant und Document Worker werden tatsächlich lokal geprüft; lokal
beobachtete Komponentenwerte und das letzte Launcher-Ergebnis sind sichtbar.
