# PLwC 1.0 / Windows Installer r26 Test Matrix

Stand: 2026-09-04

Freigegebener, ausdrücklich unsignierter r26-Releasekandidat:

- Datei: `PLwC-Setup-1.0.0-installer-r26.exe`
- Größe: `5.494.996` Bytes
- SHA-256: `d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
- Authenticode: `NotSigned`
- Build-ID:
  `plwc-windows-setup@1.0.0/installer-r26#sha256:d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
- Abnahmehost: Windows 11 Pro 64 Bit, Build 22631

Zuletzt in der sauberen VM ausgeführter Vorgängerkandidat (durch die
nachfolgenden Korrekturen nicht mehr freigabefähig):

- Datei: `PLwC-Setup-1.0.0-installer-r26.exe`
- Größe: `5.493.306` Bytes
- SHA-256: `55e10b6193ddf0bb88efc2e02e5ad5d587f3c54b48b48b2f58795e4a6b6feab6`
- Authenticode: `NotSigned` (ausdrücklich freigegebener Unsigned-Build)
- Host des vorhandenen Systemlaufs: Windows 11 Pro 64 Bit, Build 22631

Neu gebauter und in der sauberen VM erfolgreich ausgeführter Testkandidat:

- Datei: `PLwC-Setup-1.0.0-installer-r26-VMTEST-f30a2795.exe`
- Größe: `5.495.024` Bytes
- SHA-256: `f30a2795e6144882e824bb8ca69ebf5466e831d9415cc9ae597d58250519dfa8`
- Authenticode: `NotSigned` (isolierter VM-Testbuild, kein Produktionsbuild)

Statuslegende:

- **AUTOMATED PASS**: deterministische Vertrags-, Fixture- oder
  Integrationsprüfung auf dem aktuellen r26-Quellstand bestanden.
- **SYSTEM PASS**: gegen den jeweils ausdrücklich genannten Kandidaten auf Windows 11
  bestanden.
- **SYSTEM PARTIAL**: ein wesentlicher Teil ist gegen den Kandidaten belegt,
  aber nicht die vollständige benannte Variante.
- **SYSTEM PENDING**: für den exakten Kandidaten noch nicht in einer geeigneten
  isolierten Windows-Umgebung ausgeführt.
- **SYSTEM FAIL**: der benannte Systemfall ist real fehlgeschlagen; das Gate
  bleibt bis zum erfolgreichen Nachtest einer korrigierten Version geschlossen.

| # | Pflichtfall | Automatisierter Nachweis | Kandidatengebundener Systemstatus |
|---:|---|---|---|
| 1 | Saubere Windows-11-Installation ohne Setup als Administrator | Clean-Fixture, Preflight und gemeinsamer harter Postflight PASS | **SYSTEM PASS** für `f30a2795…9dfa8` – Setup auf sauberem Windows 11 abgeschlossen; Gateway `1.0.0`, vollständiger Arbeitsbereich und exakt 8 öffentliche Tools anschließend im Browser belegt. Der Vorgänger `55e10b61…feab6` bleibt wegen der dokumentierten Timeout-/Snapshotfehler verworfen. |
| 2 | Direkte Aktualisierung r25 auf r26 | r25-Fixture nutzt eine unveränderliche Migration und denselben Postflight | **SYSTEM PASS** für `d604e771…97dc65` – der unveränderte r25-Kandidat `e0fdcc54…1fa7c` wurde mit Gateway, Codex und Chat Bridge installiert und anschließend direkt auf den freigegebenen r26-Kandidaten aktualisiert. Setup endete mit Code 0, Transaktion `postflight_succeeded`, 12/12 Checks und regulär geschlossenem Log. |
| 3 | Gespeicherter alter Pfad `chat-bridge` | Legacy-Pfad-Fixture und Migration auf `app\bridge` PASS | **SYSTEM PENDING** – muss mit exaktem Kandidaten aus r25 wiederholt werden |
| 4 | Parallele alte und neue PLwC-Pfade | Mixed-Install-Klassifizierung und Dirty-Fixture PASS | **SYSTEM PENDING** – isolierte Dirty-Windows-Instanz erforderlich |
| 5 | Alte geplante Aufgabe plus alter Autostart-Link | Backup-, Allowlist- und Rollback-Fixture PASS | **SYSTEM PENDING** – isolierte Altinstallation erforderlich |
| 6 | Nachweisbarer alter PLwC-Node-Prozess besitzt Port 3007 | PID-/Identitäts-Revalidierung und atomarer Austausch PASS | **SYSTEM PASS** – PID 824 wurde als PLwC belegt und beendet; neuer eindeutiger Besitzer ist PID 4832 unter `app\bridge` |
| 7 | Fremder Prozess besitzt Port 3007 und muss überleben | Fremdbesitzer blockiert Migration; Prozess wird nicht beendet | **SYSTEM PENDING** – absichtliche Portkollision nur isoliert ausführen |
| 8 | Fehlendes Konfigurationssymbol oder falsches Shortcut-Ziel | Doctor- und Hard-Postflight-Negativtests PASS | **SYSTEM PENDING** – installierter Gutpfad ist korrekt, Defektinjektion fehlt |
| 9 | Leeres Profilverzeichnis | Konfigurationsoberfläche liefert Grund, Meldung und fehlende Dateien | **SYSTEM PENDING** – nur Fixture, keine Benutzerdaten manipuliert |
| 10 | Unvollständiges Profil | Inventur- und Aktivierungsblocker PASS | **SYSTEM PENDING** – nur Fixture |
| 11 | Gültiges Profil und vorhandener Arbeitsbereich | Konfigurations-/Profilintegration PASS | **SYSTEM PASS** – Profil `Sororitas`, F:-Arbeitsbereich und Schwellen 2/3/2 erhalten; Vollhashvergleich unverändert |
| 12 | Spätere Änderung des Arbeitsbereichspfads | Unveränderlicher Plan, Bestätigung und Synchronisierung PASS | **SYSTEM PENDING** – reale Benutzerkonfiguration nicht ohne Einzelbestätigung geändert |
| 13 | Extension 1.0.0 mit r26 | Kompatibilitätsmatrix und Bridge-Buildidentität PASS | **SYSTEM PARTIAL** – Live-Health für die 1.0.0-Bridge-Identität PASS, kein Browser-Panel-Lauf |
| 14 | Extension 1.0.1 mit r26 | Extension-1.0.1-Build, Identität und Vertrag PASS | **SYSTEM PASS** für `f30a2795…9dfa8` – installierte Entwicklungserweiterung `1.0.1`, stabile ID `nlogfcafjdfdoknpkbehjgihpafpipdb`, passender gemeinsamer Build und 8/8 im Chrome-Panel. Eine Store-Veröffentlichung ist davon ausdrücklich nicht abgeleitet. |
| 15 | Browser-Neustart, Disconnect, Reconnect | Generation-Invalidierung, No-Resend, lokales Cache-Recovery und deterministische Panel-Inhaberschaft PASS | **SYSTEM PASS** – auf der sauberen VM blieb PLwC nach vollständigem Chrome-Neustart installiert und meldete wieder Extension `1.0.1`, passende Buildidentität und 8/8. Zusätzlich bestand auf dem Abnahmehost der vollständige Brave-Neustart nach einmaligem Wechsel vom Repository-Netzpfad auf `%APPDATA%\PLwC\app\bridge\extension`. |
| 16 | Bridge 8/8, während Panel noch nicht geladen ist | Atomare Readiness-State-Tests PASS | **SYSTEM PASS** für `d604e771…97dc65` – Live-Health liefert ohne Panel exakt 8/8 für Development-, Chrome- und Edge-Origin. |
| 17 | Inkompatible Buildidentität | Fail-closed-Buildidentitätstests PASS | **SYSTEM PENDING** – Defektinjektion nur isoliert |
| 18 | Docker, Qdrant und Document Worker: vorhanden, fehlend oder nicht prüfbar | Echte CLI-/Daemon-, Python-Distributions- und Docker-Image-Probes samt Positiv-, Fehlend- und Nicht-erreichbar-Regressionen PASS | **SYSTEM PASS (positiver Pfad)** für `d604e771…97dc65` – Docker `29.3.1`, Qdrant-Client `1.18.0` und Document Worker `0.1.0` mit Image-ID `sha256:c81b8c2…9470344`; `blocking=none`, `unknown=none`. Der isolierte Negativpfad bleibt automatisiert belegt. |
| 19 | Doctor-Diagnose verändert nichts | Dateisystem-/Registry-/Prozess-Snapshot-Test PASS | **SYSTEM PASS** für `d604e771…97dc65` – installierter Doctor read-only, 7 PASS, 1 Hinweis, 0 Fehler; Profile und Arbeitsbereich bytegleich, Bridge blieb aktiv, Reparaturplan leer. |
| 20 | Doctor-Reparatur erfolgreich und zweiter Lauf idempotent | Plan/Apply/Postflight/Idempotenz-Tests PASS | **SYSTEM PARTIAL** – zwei installierte Diagnosen erzeugten jeweils einen leeren Plan; kein Apply ohne planspezifische Bestätigung |
| 21 | Doctor-Reparaturfehler rollt zurück | Injizierter Fehler und Rollback-Test PASS | **SYSTEM PENDING** – Defektinjektion nur isoliert |
| 22 | Updateprüfung offline | Intervall-, Cache- und Offline-Test PASS | **SYSTEM PENDING** – kein externer Releasekanal konfiguriert |
| 23 | Ungültige Manifest-Signatur | RSA-Signatur-Negativtest PASS | **SYSTEM PENDING** – isolierte Update-Defektinjektion fehlt |
| 24 | Gültiges Manifest mit falschem Artefakthash | Download-Hash-Negativtest PASS | **SYSTEM PENDING** – isolierte Update-Defektinjektion fehlt |
| 25 | Unterbrochener Download oder Installerfehler | Kurzer Download, Rückgabecode und Rollbackreport PASS | **SYSTEM PENDING** – isolierte Fehlerumgebung erforderlich |
| 26 | Installer-Postflight-Fehler darf keinen Erfolg melden | Hard-Postflight-, Rollback- und Custom-Exitcode-Vertrag PASS | **SYSTEM PASS** für `55e10b61…feab6` – Setup meldete bei zwei fehlgeschlagenen Postflight-Checks keinen Erfolg, endete mit Code 30, stoppte PID 776 und quarantänisierte die neue Anwendung fehlerfrei unter `app-r26-failed-b51c226c85b6`. Die Auslösung war falsch-positiv und ist separat korrigiert. |
| 27 | Build/ValidateOnly erhält bestehende Artefakte | Pester-Bytesnapshot und isoliertes ValidateOnly PASS | Nicht auf installiertes System anwendbar |

## Aktuelle automatisierte Gesamtstände

- Python: **112 bestanden, 6 übersprungen** in 44,28 s. Die Skips sind
  optionale Docker-/Symlink-Capability-Gates und keine umgedeuteten Erfolge.
- Chat-Bridge-Extension: **190/190 bestanden**, Typecheck und Build PASS. Darin
  enthalten sind sechs neue Regressionstests für Cache-Recovery und
  konkurrierende alte/neue Panel-Instanzen.
- Windows-Installer-Pester: **72/72 bestanden**, 0 übersprungen, 0 ausstehend,
  Laufzeit 620,12 s. Der bereits archivierte NUnit-Nachweis desselben
  Vertragsstands hat SHA-256
  `22bc69dc445050eb627e34915b30f57365fde363f84044d33f323fbef35d8068`.
- Isoliertes `ValidateOnly`: PASS ohne ISCC; geschützte kanonische Ausgaben
  blieben bytegleich.

## Finaler direkter r25→r26-Systemlauf

Der unveränderte r25-Kandidat mit SHA-256 `e0fdcc54…1fa7c` wurde ohne dauerhaft
erhöhten Setup-Prozess mit `gateway,codex,chatbridge` installiert. Die
gesicherte r25-Auswahl bindet Revision `installer-r25`, den vollständigen
r25-Setuphash, Browser-Extension `1.0.0` und genau diese Komponenten. Direkt
danach wurde der freigegebene Kandidat `d604e771…97dc65` mit derselben Auswahl
installiert. Beide Setups endeten mit Code 0 und regulär geschlossenem Log.

Die r26-Transaktion endete mit `postflight_succeeded`; alle 12 harten Checks
bestanden. `selection.ini` bindet danach Revision, vollständigen Setuphash und
Extension `1.0.1`. Genau ein Node-Prozess unter
`%APPDATA%\PLwC\app\bridge\bridge\dist\src\index.js` besitzt Port 3007. Der
Live-Healthcheck bestand für Development-, Chrome- und Edge-Store-Origin mit
exakt acht Werkzeugen.

Vorher/Nachher blieben unverändert:

- Profile: 83 Dateien; Baumhash vor/nachher
  `8d57e1f4af69e8d2cdd21314786279ae7d9b7f75ebd5c564c339d5c6f7cd7544`;
- Arbeitsbereich: 955 Dateien; Baumhash vor/nachher
  `b4280ed5437576620030525714a0a8ec89905615059adb7da01e64e235ef2736`;
- `active_profile.json`: SHA-256 weiterhin
  `24ee97780a92a4e67eefa9bd2982e89dc3b832c9f79d8998d39df61b036c39ec`.

`gateway-settings.json` änderte ausschließlich das installerverwaltete Feld
`updated_at`; Profil, Pfade, Schwellen und Aktivierungsschalter blieben
inhaltlich gleich.

## Reales Brave-Neustartproblem

Am 4. September 2026 blieb das PLwC-Panel nach einem Brave-Neustart sichtbar,
zeigte jedoch gleichzeitig `Bereit 8/8` und `Tool contract locked`. Extension-
Version, Extension-ID und letzter Extension-Kontakt waren `unknown`; der Doctor
meldete 6 PASS, 2 WARN und 0 FAIL. Der Launcher selbst war `ready` mit 8/8.

Die sichtbare Extension `1.0.1` und ihre Dateien stammten aus der neuen
Installation. Braves interne Präferenzen enthielten daneben zwar noch einen
nicht sichtbaren historischen Datensatz für die alte ID
`cjammbahoiopfjibogoofeamileannae` und Version `0.2.0`; eine aktive zweite
Extension ist damit jedoch nicht belegt. Nachweisbar war stattdessen ein
Versionsversatz: Für die stabile Entwicklungs-ID
`nlogfcafjdfdoknpkbehjgihpafpipdb` war der Service Worker noch als `1.0.0`
registriert, obwohl im gemeinsamen `extension\dist` bereits die neue Version
`1.0.1` lag. Zusätzlich verlor das Panel bei einem transienten Nicht-Bereit-
Ereignis seinen lokal verifizierten Toolcache, lud ihn nach Rückkehr zu 8/8 aber
nicht neu.

Der Quellstand lädt den verifizierten Toolvertrag nun nach einem Ready-Recovery
erneut und priorisiert Store- beziehungsweise stabile Entwicklungsinstanzen vor
unmarkierten oder veralteten entpackten Panels. Die gebaute Extension ist
`1.0.1`. Nach dem manuellen Neuladen der stabilen Entwicklungserweiterung und
des ChatGPT-Tabs bestand der Live-Nachtest: `8 / 8 tools verified`, Extension-ID
`nlogfcafjdfdoknpkbehjgihpafpipdb`, Browser `brave`, Build-Abgleich passend und
keine Fehler. Der Native Launcher speicherte den Extension-Kontakt mit Version
`1.0.1` und Toolzahl 8. Die alte `0.2.0`-Registrierung war in der Brave-Oberfläche
nicht mehr sichtbar und wurde nicht verändert.

Der anschließend tatsächlich ausgeführte vollständige Brave-Prozessneustart
um 14:38 Uhr deckte einen getrennten Installationszustand auf: Die PLwC-Karte
fehlte danach vollständig auf `brave://extensions`, und der fertig geladene
ChatGPT-Tab enthielt kein `plwc-chat-bridge-host`-Element. Gleichzeitig blieb
der Listener auf `127.0.0.1:3007` aktiv. Braves gespeicherter Restdatensatz für
die Entwicklungs-ID zeigt als bisherigen Ladepfad den Repository-Netzpfad
`T:\CODEX_PROJEKTE\PLwC\integrations\plwc-chat-bridge\extension\dist`, nicht
den vom Setup installierten lokalen Ordner
`%APPDATA%\PLwC\app\bridge\extension`. Der Installer kann einen bereits manuell
geladenen entpackten Browserpfad aus Sicherheitsgründen nicht stillschweigend
umhängen. Die Entwicklungsinstanz wurde anschließend einmalig aus dem lokalen
Installationsordner geladen. Der weitere vollständige Brave-Neustart bestand:
PLwC blieb geladen, das Panel erschien wieder, Extension `1.0.1` und Build
stimmten überein, die Bridge meldete `8/8` und `plwc_status` wurde erfolgreich
ausgeführt. Der A/B-Nachweis bindet den Ausfall damit an den zuvor verwendeten
Repository-Netzpfad; ob Brave ihn wegen des Startzeitpunkts der Laufwerks-
Einbindung oder einer internen Einschränkung für entpackte Erweiterungen
verwarf, ist ohne Browser-Fehlerlog nicht weiter unterscheidbar.

Die Updatezentrale zeigte
mangels veröffentlichtem Release-Manifest erwartungsgemäß `offline`/HTTP 404;
das ist nicht die Ursache des Browserfehlers.

## Nachträglich geschlossene Inventurlücke

Die erste r26-Konfigurationsimplementierung führte Docker, Qdrant und Document
Worker zwar als von der Kompatibilitätsmatrix verlangte Zeilen, ermittelte sie
aber nicht vollständig: Docker beruhte nur auf CLI-/Installer-Erkennung,
Qdrant wurde mit dem Aktivierungsschalter gleichgesetzt und der Document Worker
war fest als `unknown`/`unavailable` eingetragen. Damit war das Phase-2-Gate
entgegen dem damaligen Nachweis nicht vollständig erfüllt und wurde am
4. September 2026 wieder geöffnet.

Der aktuelle Quellstand prüft Docker-CLI und -Daemon begrenzt und read-only,
liest die tatsächliche `qdrant-client`-Distribution aus der aktiven
Python-Laufzeit und inspiziert das fest gepinnte lokale Worker-Image ohne Pull.
Fehlende Komponenten werden als `nicht installiert` statt als bloßes
`unbekannt` dargestellt; ein nicht erreichbarer Daemon bleibt korrekt
fail-closed `unknown`. Der reale Host-Snapshot liefert Docker `29.3.1`,
Qdrant-Client `1.18.0` und Document Worker `0.1.0` mit der lokalen Image-ID
`sha256:c81b8c2bd3a4b697453e8d31585ffad2e1540e10fb6941dd2ea02ba5a9470344`.
Die vollständige Python-Suite (`112 passed, 6 skipped`), Syntaxprüfungen und
der isolierte Installer-Pester-Lauf (`72/72`) bestanden; die gestagte
Konfigurationsdatei ist bytegleich mit der Quelle.

## Sauberer VM-Lauf des Vorgängerkandidaten

Der erstmalige Lauf von `55e10b61…feab6` in einer sauberen Windows-11-VM
belegte zwei weitere reale Grenzfälle. Python 3.13.14, Visual C++ Runtime und
alle fest gepinnten Python-Module wurden erfolgreich installiert. `pip` endete
mit Code 0 und der abschließende Diagnoseabschnitt meldete alle vier Importe
sowie `runtime_probe=ok`. Der kalte Importlauf benötigte laut Dateizeit jedoch
rund 32 Sekunden und überschritt damit die damalige Grenze von 30 Sekunden;
Setup zeigte deshalb fälschlich einen Voraussetzungenfehler. Die Grenze beträgt
im aktuellen Quellstand 120 Sekunden und ist vertraglich gebunden.

Nach Fortsetzung installierten Node und Docker Desktop ebenfalls erfolgreich.
Bridge, Gateway, Payload-Hashes, Native Messaging, Buildidentität und exakt
8/8 Werkzeuge bestanden den harten Postflight. Nur
`shortcuts.autostart` und `configuration.ui_icon` scheiterten: Der gemeinsame
PowerShell-Snapshot lief nach acht Sekunden ab und hinterließ für nachweislich
vorhandene `.lnk`-Dateien keine Felder `target` und `arguments`. Setup meldete
korrekt keinen Erfolg und der Rollback quarantänisierte die neue Anwendung ohne
Fehler. Der aktuelle Doctor erhebt Links, Prozesse, Port und geplante Aufgaben
in vier voneinander unabhängigen, jeweils begrenzten Probes und wertet fehlende
Sicherheitsprobes nicht mehr als leere Erfolgsliste. Der lokale Windows-Nachweis
lieferte alle vier Probe-Statuswerte `true` und vollständige Linkziele.

Für den VM-Nachtest wurde ausschließlich im isolierten Unsigned-Pfad der
Kandidat `f30a2795…9dfa8` gebaut und unter eindeutigem `VMTEST`-Namen in den
Downloadordner kopiert. Quell- und Stagingversion von `doctor.py` und
`installer_state.py` sind bytegleich. Das ist kein endgültiger
Produktionsbuild. Der anschließende saubere Windows-11-Lauf bestand: Nach
abgeschlossener Installation liefen Gateway `1.0.0` und 8/8 Tools. Auch nach
vollständigem Chrome-Neustart blieb die Erweiterung geladen; das Panel zeigte
Version `1.0.1`, die stabile Entwicklungs-ID, passenden Build und erneut 8/8.

## Gate-Ergebnis

Die automatisierte Matrix, der saubere VM-Lauf des aktuellen
Implementierungsstands und die direkte hashgebundene r25→r26-Aktualisierung
sind grün. Der Product Owner hat den endgültigen, ausdrücklich unsignierten
r26-Build freigegeben. Phase 8 ist für den Windows-Installer deshalb **PASS**.

Diese Entscheidung veröffentlicht nichts. Chrome `1.0.1` bleibt in Prüfung
mit Sichtbarkeit **Nicht gelistet** und deaktivierter automatischer
Veröffentlichung. Edge `1.0.1` bleibt **In draft**. Eine Store- oder
GitHub-Release-Veröffentlichung benötigt weiterhin eine getrennte ausdrückliche
Freigabe.
