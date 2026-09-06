# PLwC 1.0 / Installer r26 – Phase 3 Extension-Handshake

Stand: 3. September 2026

## Umfang und Freigabegrenze

Phase 3 ändert ausschließlich den lokalen Extension-, Bridge-, Launcher- und
Konfigurationsvertrag. Es wurde weder ein Browser-Store-Paket erzeugt oder
hochgeladen noch eine Store-Einstellung gespeichert oder eine Veröffentlichung
ausgelöst. Der endgültige r26-Produktionsbuild bleibt ebenfalls ausstehend.

## Atomarer Bereitschaftszustand

Die Extension veröffentlicht nun einen generationsgebundenen Zustand mit den
Stufen `disconnected`, `connecting`, `checking_build`, `loading_tools`, `ready`,
`incompatible` und `error`. `ready` wird erst gesetzt, nachdem Transport,
Buildidentität, gespeicherte Gatewayeinstellungen und der exakte 8/8-Toolvertrag
bestätigt wurden.

Reconnect und Disconnect verwerfen Build- und Tool-Caches. Auch eine Änderung
oder Rücksetzung der Gatewayeinstellungen nimmt den Zustand aus `ready`, bis der
Toolvertrag erneut geladen wurde. Ergebnisse einer älteren Verbindungsgeneration
können einen neueren Zustand nicht überschreiben. Ein älteres Statusobjekt mit
`connection=connected`, aber ohne geprüfte Buildidentität und Toolset wird als
`checking_build` normalisiert und nicht als stabiler Zustand „verbunden, 0/8“
ausgegeben.

## Paketversion und Protokoll

- Browser-Paket und Browsermanifest: `1.0.1`
- Bridge-/Native-Messaging-Protokoll: `1.0.0`
- gemeinsamer lokaler Buildvertrag: `plwc-chat-bridge@1.0.0`
- gemeinsamer Browser-Komponentenvertrag: `1.0.0`

Die Buildprüfung erzwingt die Gleichheit von Paket- und Manifestversion, erlaubt
innerhalb des 1.0-Protokollvertrags aber Paketversionen `1.0.x`. Der isolierte
Installer-Prüfbuild führte deshalb das Browserpaket als `1.0.1`, während
Node-Bridge, Native Launcher und gemeinsamer Buildvertrag `1.0.0` blieben.

Die erhaltene r25-Buildidentität belegt Browserpaket `1.0.0` und lokalen
Bridgevertrag `1.0.0`. Die alte 1.0.0-Extension sendet den Native-Messaging-Befehl
`command:start` ohne die neuen Kontaktfelder. Der r26-Launcher behandelt die
optionale Kontaktpersistenz bei diesem alten Startformat best-effort und führt
den Start weiterhin aus. Automatisierte Inventartests prüfen zusätzlich die
Kombinationen Extension 1.0.0/1.0.1 mit Installerrevision r25/r26 und Protokoll
1.0.0. Ein echter Windows-Systemtest mit dem späteren r26-Kandidaten bleibt Teil
der Phase-8-Testmatrix; hier wurde kein finaler r26-Installer gebaut.

## Tatsächliche Browseridentität und Updatehinweis

Die Extension liest Paketversion und ID zur Laufzeit aus dem Browser, erkennt die
Browserfamilie und übermittelt Paketversion, Extension-ID, Browserfamilie,
Protokollversion, Zeitstempel und 8/8-Status an den Native Launcher. Dieser prüft
die erlaubte Extension-ID und schreibt den letzten Kontakt atomar nach
`browser-extension-last-contact.json`. Die Konfigurationsseite zeigt diese Werte
und markiert Kontakte nach 24 Stunden als veraltet; ohne Kontakt bleibt der
Zustand korrekt `unbekannt`.

Der Updatehinweis reagiert ausschließlich auf das Browserereignis
`runtime.onUpdateAvailable` und setzt ein dezentes `UP`-Badge. Es gibt keinen
aggressiven Polling- oder Store-Bypass-Pfad.

## Prüfnachweise

- Python-Integration und Repro-Fälle: `33 passed`
- Extension-Typecheck: `PASS`
- Extension-Tests: `177 passed`
- Extension-Build: `PASS`, Manifest/Paket `1.0.1`
- Python- und JavaScript-Syntax: `PASS`
- PowerShell-Parser für `build.ps1`: `PASS`
- isoliertes `build.ps1 -ValidateOnly`: `PASS`
- Native Launcher kompiliert: `PASS`, Prüfartefakt SHA-256
  `8596a5fd7712bf73d566ea5e6d8864700aeadd9058d8039466b8276400944fdb`
- ISCC/Produktions-Setup: nicht aufgerufen
- kanonischer Stage-Baum vorher/nachher:
  `710f354cc98da63e7181e1e2a94e0063257dd7afb62108bb1b7d879476f00a8d`
- kanonischer Dist-Baum vorher/nachher:
  `87256ea50404143c2cded93c507befa937796f9bd42148b021a84720b11cd735`

## Phase-3-Gate

**PASS.** Der widersprüchliche 0/8-Endzustand ist durch das atomare
Readiness-Modell ausgeschlossen und durch positive sowie negative
Generationstests belegt. Paketversion 1.0.1 wird tatsächlich gebaut und lokal
erkannt, während 1.0.0 über denselben Protokollvertrag und das alte Startformat
kompatibel bleibt. Die abschließenden realen Windows-11-Installationsfälle
werden mit dem unveränderlich gesicherten r26-Kandidaten in Phase 8 ausgeführt.
