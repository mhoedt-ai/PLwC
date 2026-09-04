# Briefing für neuen Chat: PLwC 1.0 – Windows-Installer r26

Stand: 2. September 2026

## Startauftrag für den neuen Chat

Wir setzen die Entwicklung von PLwC 1.0 mit dem Windows-Installer r26 fort.
Lies dieses Briefing vollständig, prüfe anschließend den tatsächlichen
Quellstand und arbeite die beschriebenen Pakete in der angegebenen Reihenfolge
ab. Trenne belegte Fehler von Vermutungen, erhalte Benutzerdaten und bestehende
Git-Historie und führe keine Veröffentlichung in einem Browser-Store ohne eine
erneute ausdrückliche Freigabe des Benutzers aus.

Das Ziel ist nicht nur ein neuer Installer. r26 soll PLwC auf sauberen und auf
bereits benutzten Windows-11-Systemen zuverlässig installieren, aktualisieren,
diagnostizieren und – nach einem verständlichen Plan und ausdrücklicher
Bestätigung – sicher reparieren können.

## 1. Verbindlicher Projektstand

- Repository: `\\fearun\Tausch\CODEX_PROJEKTE\PLwC`
- Branch zu Beginn dieses Briefings: `codex/plwc-chat-bridge-rc19`
- HEAD zu Beginn dieses Briefings:
  `3f02b54e648486ce3a5a4c071080ae10440f1716`
- Commit-Titel: `Harden Windows r25 bridge startup verification`
- Der Branch war zu diesem Zeitpunkt mit dem gleichnamigen Remote-Branch
  synchron.
- Im Repository lagen fünf unversionierte Benutzerdateien `screen1.png` bis
  `screen5.png`. Diese Dateien gehören dem Benutzer und dürfen nicht gelöscht,
  überschrieben oder ungefragt committed werden.
- Produktbezeichnung: PLwC 1.0
- Produkt-/Vertragsversion: `1.0.0`
- Nächste Installerrevision: `installer-r26`
- Vorgesehener Setupname: `PLwC-Setup-1.0.0-installer-r26.exe`
- Gateway-Vertrag: `1.0.0`
- Bridge-Protokoll: `1.0.0`
- Vorgesehene nächste Browser-Store-Paketversion: `1.0.1`
- Die Paketversion `1.0.1` der Erweiterung muss mit dem lokalen
  PLwC-/Bridge-Protokoll `1.0.0` kompatibel bleiben.
- Zusätzlich zur semantischen Version muss jedes neu gebaute Artefakt über eine
  unverwechselbare Buildrevision und einen SHA-256-Nachweis identifizierbar
  sein. Zwei verschiedene Binärdateien dürfen nicht als bytegleich behandelt
  werden, nur weil beide `1.0.0` anzeigen.

Vor jeder Arbeit sind `git status`, HEAD, Branch und vorhandene Artefakte erneut
zu prüfen. Abweichungen sind zu erklären; fremde Änderungen bleiben erhalten.

## 2. Bereits getroffene Produktentscheidungen

### 2.1 Versionslose Installationspfade

Die normalen Laufzeitpfade tragen keine Versionsnummer:

```text
%APPDATA%\PLwC\app
%APPDATA%\PLwC\app\gateway
%APPDATA%\PLwC\app\bridge
```

Insbesondere sind Pfade wie `gateway-1.0.0`, `chat-bridge-1.0.0` oder andere
versionsabhängige Laufzeitnamen unerwünscht. Frühere `chat-bridge`-Pfade müssen
als Altbestand erkannt und kontrolliert nach `bridge` migriert werden.

PLwC ist eine Installation pro Benutzer. Es soll weder nach `System32` noch in
andere geschützte Windows-Systemverzeichnisse schreiben. Der automatische Start
erfolgt über eine Verknüpfung im Autostartordner des aktuellen Benutzers.

### 2.2 Kein kostenpflichtiges Authenticode-Zertifikat

Für r26 ist kein gekauftes Windows-Code-Signing-Zertifikat vorgesehen. Der
Installer bleibt daher gegebenenfalls von Windows als unbekannter Herausgeber
gekennzeichnet. Das darf nicht verschleiert werden.

Für den eigenen Updatekanal ist trotzdem ein kostenlos realisierbarer
Integritätsschutz vorgesehen: signiertes Release-Manifest, fest eingebetteter
öffentlicher Projektschlüssel, SHA-256-Prüfung und exakte Buildidentität. Der
private Signaturschlüssel darf niemals ins Repository gelangen.

### 2.3 Nur ein sichtbarer Doktor

Es gibt für den Benutzer genau einen **PLwC-Doktor auf Basis von CLU**. Kein
zweites Doktorprogramm und keine konkurrierenden Diagnoseoberflächen.

Der Ablauf dieses einen Doktors besteht aus:

1. Diagnose ausführen – garantiert read-only.
2. Reparaturplan anzeigen – jede geplante Änderung wird einzeln erklärt.
3. Reparatur bestätigen und anwenden – mit Sicherung, Auditprotokoll,
   möglichem Rollback und anschließendem Postflight.

Intern bleibt die Sicherheitsgrenze erhalten: CLU diagnostiziert, bewertet und
erklärt. Eine deterministische, allowlist-basierte Reparatur-Engine führt nach
Bestätigung ausschließlich bekannte Reparaturaktionen aus. Ein Sprachmodell
darf keine freien Systemänderungen erzeugen oder unmittelbar ausführen.

Der bisherige CLU-Doctor-Vertrag ist read-only. Diese Eigenschaft bleibt für
Diagnoseaufrufe und öffentliche MCP-Aufrufe erhalten. Reparaturen laufen nur
über explizite Plan-/Bestätigungsoperationen mit Auditnachweis.

### 2.4 Browser-Stores

- Die Edge-Erweiterung `PLwC Chat Bridge` Version `1.0.0` wurde bereits als live
  gemeldet.
- Der Chrome-Entwurf mit der ID `feceodobnhefdbfgmbinkndhogpfkicb` war am
  2. September 2026 akzeptiert und `Bereit zur Veröffentlichung`. Google zeigte
  als spätesten Veröffentlichungstermin den 1. Oktober 2026. Die genehmigte
  Sichtbarkeit stand jedoch auf `Privat`, ohne ausgewählte
  Trusted-Tester-Gruppe. Dieser private Entwurf darf nicht versehentlich als
  nutzbare Linkveröffentlichung betrachtet werden.
- Das beabsichtigte Chrome-Vertriebsmodell entspricht Edge: `Nicht gelistet`
  beziehungsweise nur über den offiziellen Store-Link erreichbar. Vor dem
  Veröffentlichungsschritt ist die tatsächlich aktive Sichtbarkeit erneut zu
  bestätigen; falls der Wechsel einen neuen Review auslöst, ist dieser sauber
  abzuwarten.
- Store-Pakete dürfen vorbereitet und als Entwurf hochgeladen werden, aber
  `Zur Überprüfung einreichen`, `Publish` oder eine vergleichbare endgültige
  Aktion benötigt eine neue ausdrückliche Benutzerfreigabe.
- Die Konfigurationsseite darf eine veraltete Browser-Erweiterung anzeigen und
  zum offiziellen Store-Eintrag führen. Sie darf eine Store-Erweiterung nicht
  am Store vorbei ersetzen.

### 2.5 OpenWebUI

Die betreffende OpenWebUI-Installation ist so konfiguriert, dass dort keine MCPs
laufen. Eine OpenWebUI-Integration ist daher kein r26-Pflichtumfang und darf die
Abnahme nicht erweitern.

## 3. Wichtiger historischer Buildvorfall

Ein in die Pester-Suite eingebetteter Aufruf von `build.ps1 -ValidateOnly` hat
in der Vergangenheit `installer/windows/stage` und `dist` zurückgesetzt. Dabei
wurden die übergebene r21-EXE, ihre externe Buildidentität und der damalige
Dist-Nachweis entfernt oder überschrieben. Eine bytegleiche Kopie mit dem
historischen Hash wurde nicht gefunden. Die Git-Historie wurde nicht
umgeschrieben; der heutige Dist-Inhalt ist ausdrücklich kein Ersatz für r21.

Daraus folgen verbindliche Regeln:

- `-ValidateOnly` darf nicht als harmlos angenommen werden.
- Vor dem ersten r26-Build ist der Build-/Testpfad zu prüfen und so zu ändern,
  dass Validierung keine bestehenden Artefakte löscht oder überschreibt.
- Builds verwenden isolierte temporäre Stage-/Dist-Verzeichnisse oder eine
  explizit gesicherte Ausgabe.
- Bestehende r24-/r25-Artefakte werden als unveränderliche Eingaben behandelt
  und vor destruktiven Buildschritten außerhalb der Buildausgabe gesichert.
- Der Benutzer ist vor einem unvermeidbar destruktiven Artefaktschritt zu
  informieren. Git-Historie darf nicht neu geschrieben werden.

## 4. Belegte aktuelle Befunde

### 4.1 Launcher-Lebensdauer

`plwc-chat-bridge-launcher.exe --start --delay-seconds 20 --lang de` wartet,
startet oder prüft die eigentliche Bridge, führt den Healthcheck durch und
beendet sich danach. Dass das Launcherfenster nach ungefähr 20 Sekunden
verschwindet, ist beabsichtigt. Der Launcher soll nicht zu einem dauerhaften
Daemon umgebaut werden.

r26 soll stattdessen das letzte Launcher-Ergebnis persistent erfassen:

- Zeitstempel
- ausgeführte Aktion
- Exitcode und Statuscode
- verwendeter Bridgepfad
- Buildidentität
- Werkzeuganzahl
- Logpfad

Diese Informationen erscheinen auf der Konfigurationsseite und im PLwC-Doktor.

### 4.2 Bridge und Gateway waren auf dem Problemrechner gesund

Ein direkter Healthcheck lieferte:

```text
ok: true
buildId: plwc-chat-bridge@1.0.0
toolCount: 8
```

Damit waren Node Bridge, Gateway und der öffentliche 8-Tool-Vertrag zu diesem
Zeitpunkt funktionsfähig. Die Browser-Erweiterung zeigte trotzdem zeitweise
`verbunden`, `0/8` und `Build-Abgleich nicht geprüft`. Dieser Widerspruch ist ein
Extension-seitiger Zustands-/Handshakefehler und nicht durch einen kaputten
Gateway-Toolvertrag erklärt.

### 4.3 Leerer Profilordner

Der Ordner `%APPDATA%\PLwC\profiles\FAUN` war leer. Der Governor lehnte die
Aktivierung daher korrekt ab und meldete folgende fehlende Dateien:

```text
CORE.md
TEMPERAMENT.md
PERSONA.md
memory.md
reflection.md
governance/config.yaml
```

Die Konfigurationsseite führte den bloßen Ordnernamen trotzdem als normales
verfügbares Profil auf. Das ist ein UI-/Inventarisierungsfehler. Ein leerer oder
unvollständiger Ordner darf nicht als aktivierbares Profil erscheinen.

### 4.4 Irreführende Meldung „HTTP 200“

`POST /api/profile/plan` lieferte valides JSON mit `ok:false`, `valid:false`,
`reason` und `missing_files`. Die JavaScript-Funktion warf jedoch nur
`payload.error || HTTP 200`, obwohl kein `error`, aber eine aussagekräftige
`reason` vorhanden war.

Die Konfigurationsseite muss fachliche Ablehnungen von Transportfehlern trennen
und strukturierte Informationen in dieser Art ausgeben:

```text
Profil FAUN kann nicht aktiviert werden.
Erforderliche Profildateien fehlen: ...
```

### 4.5 Schmutziger Upgradezustand

Auf einem benutzten Rechner gab es mindestens einen störenden alten
Node-Prozess sowie Hinweise auf alte Pfade oder Verknüpfungen. Eine vollständige
r24/r25-Mischinstallation ist dadurch plausibel, aber noch nicht allein durch
diese Hinweise bewiesen. r26 muss diesen Fall diagnostisch belegen, bevor es
etwas entfernt.

Der Problemrechner ist als „dirty/migrated installation“-Regressionstest zu
erhalten. Er soll nicht vollständig bereinigt werden, bevor die r26-Diagnose
den Zustand erfasst hat. Ein funktionierender privater Rechner dient als
Gegenprobe für eine saubere Installation.

## 5. Zielbild der Konfigurationsseite

Die lokale PLwC-Konfigurationsseite wird zur zentralen, verständlichen
Systemübersicht. Sie enthält mindestens folgende Bereiche.

### 5.1 Komponenten und Kompatibilität

Für jeden Bestandteil werden tatsächliche installierte Werte angezeigt:

- PLwC-Produktversion und Buildrevision
- Windows-Installerrevision und Setup-Hash
- Gateway-Version
- Node-Bridge-Version und Buildidentität
- Native-Launcher-Version und Buildidentität
- Konfigurationsoberflächen-Version
- Browser-Erweiterung: Browser, Extension-ID, tatsächliche Store-Paketversion,
  letzter Kontakt
- Python-Laufzeit
- Node-Laufzeit
- optionale Komponenten wie Docker, Qdrant und Document Worker
- vorbereitete optionale Clients, soweit zuverlässig ermittelbar

Die Tabelle zeigt nicht nur `installiert` und `neueste Version`, sondern:

| Feld | Bedeutung |
|---|---|
| Installiert | tatsächlich lokal erkannte Version/Buildrevision |
| Vertrag | unterstützte Protokoll-/Schemaversion |
| Verfügbar | letzte vertrauenswürdig ermittelte Releaseversion |
| Zustand | bereit, kompatibel, empfohlenes Update, Pflichtupdate, fehlt, optional, unbekannt oder Mischinstallation |
| Aktion | Details, Diagnose, Reparatur oder offizieller Updateweg |

`Unbekannt` ist korrekt, wenn beispielsweise noch keine Erweiterung Kontakt
hatte. Eine fehlende Onlineverbindung bedeutet nicht automatisch inkompatibel.

### 5.2 Zentrale Kompatibilitätsmatrix

Kompatibilität darf nicht ausschließlich durch Gleichheit aller
Versionsnummern bestimmt werden. Ein versioniertes, maschinenlesbares
Kompatibilitätsmodell prüft mindestens:

- Produkt-/Releasefamilie
- Bridge-Protokollversion
- Build-Identity-Schemaversion
- Gateway-Fassade und 8/8-Werkzeugvertrag
- unterstützte Browser-Erweiterungs-Paketbereiche
- Native-Messaging-Vertrag
- Launcher-/Bridge-Kompatibilität
- notwendige Python-/Node-Versionen
- optionale Komponenten und deren Status

Die Browser-Erweiterung `1.0.1` muss deshalb als kompatibel zum lokalen Vertrag
`1.0.0` ausweisbar sein. Paketversion, Protokollversion und konkrete
Buildidentität sind getrennte Felder.

### 5.3 Profile

Die API liefert für jedes Profilobjekt mindestens:

```text
name
path
exists
valid
status
missing_files
active
activatable
```

Ungültige Profile bleiben sichtbar, werden aber als `unvollständig` oder
`ungültig` markiert. Aktivierung ist deaktiviert, und die fehlenden Dateien
werden angezeigt. Nichts wird automatisch gelöscht oder mit erfundenem Inhalt
gefüllt.

### 5.4 Arbeitsbereich nachträglich ändern

Der Workspacepfad soll nach der Installation über die Konfigurationsseite
änderbar sein. Der Ablauf benötigt:

1. neuen Pfad auswählen,
2. Pfad und Schreibbarkeit prüfen,
3. Änderungsplan anzeigen,
4. ausdrückliche Bestätigung,
5. Standardordner idempotent anlegen,
6. Einstellungen atomar speichern,
7. Status erneut prüfen.

Eine Datenmigration ist von einer reinen Pfadumschaltung zu trennen. Vorhandene
Dateien werden nicht still verschoben oder überschrieben.

### 5.5 Updatebereich

Die Seite prüft in angemessenen Abständen und auf manuellen Wunsch:

- neue PLwC-/Installer-Version
- neue Gateway-/Bridge-Kompatibilität
- neue Browser-Erweiterung
- Pflichtupdate gegenüber empfohlenem Update
- Releasehinweise und Bezugsquelle

Automatische Prüfung ist zulässig; Download und Installation benötigen eine
verständliche Anzeige und eine ausdrückliche Bestätigung. Es gibt keine stille
Installation. Offline- und Fehlerzustände werden nachvollziehbar angezeigt.

## 6. Ein PLwC-Doktor auf Basis von CLU

### 6.1 Benutzeroberfläche

Auf der Konfigurationsseite gibt es genau einen Bereich `PLwC-Doktor` mit:

- `Diagnose ausführen`
- `Reparaturplan anzeigen`
- `Reparatur durchführen`
- `Diagnosebericht exportieren`

Der Bericht verwendet verständliche Statuswerte und enthält Beleg, Risiko,
Empfehlung und gegebenenfalls eine erlaubte Reparaturaktion.

### 6.2 Diagnosen

Der Doktor prüft read-only mindestens:

- Buildidentitäten und Hashnachweise
- installierte Versionen und Kompatibilitätsmatrix
- Gateway-, Bridge- und Launcherdateien
- Bridge-Healthcheck und exakt 8/8 Werkzeuge
- Native-Messaging-Registrierung für unterstützte Browser
- Autostart-Verknüpfung und Zielkommando
- alte geplante Windows-Aufgaben
- laufende PLwC-Prozesse samt ausführbarem Pfad und Kommandozeile
- Eigentümer von Port 3007
- parallele Pfade `bridge`, `chat-bridge` und frühere Versionspfade
- Konfigurationsverknüpfung und Icon
- Konfiguration, aktives Profil und alle Profilordner
- Workspacepfad und notwendige Standardordner
- letzte Launcher-/Installer-/Bridge-Protokolle
- Updatezustand, soweit vertrauenswürdig verfügbar

### 6.3 Erlaubte Reparaturen

Nach Plananzeige und Bestätigung darf die deterministische Engine unter anderem:

- fehlende oder falsche PLwC-Verknüpfungen neu erzeugen,
- das PLwC-Icon aus einem verifizierten Payload wiederherstellen,
- Native Messaging neu registrieren,
- genau eine korrekte Benutzer-Autostartverknüpfung herstellen,
- obsolete PLwC-Windows-Aufgaben entfernen,
- eindeutig als PLwC erkannte alte Prozesse beenden,
- die aktuelle Bridge starten oder neu starten,
- bekannte Altpfade kontrolliert nach `app\bridge` migrieren,
- ersetzte Laufzeitdateien vor der Änderung sichern,
- fehlende Programmdateien aus einem hashgeprüften lokalen oder zuvor
  bestätigten Download-Payload wiederherstellen,
- idempotent fehlende Standardordner ergänzen,
- anschließend den vollständigen Postflight ausführen.

Ein fehlender Binärpayload darf nicht aus beliebigen Quellen rekonstruiert
werden. Ohne vertrauenswürdigen lokalen Payload oder bestätigten Download bleibt
die Aktion als `nicht ausführbar` im Reparaturplan.

### 6.4 Verbotene automatische Reparaturen

Der Doktor darf nicht automatisch:

- Profil-, Persona-, Memory- oder Governance-Inhalte erfinden oder
  überschreiben,
- Workspace-Dokumente verschieben, löschen oder verändern,
- fremde Prozesse nur wegen Port 3007 beenden,
- unbekannte Verzeichnisse löschen,
- die aktive Profilauswahl ändern,
- Schutzschwellen absenken,
- eine Browser-Erweiterung am Store vorbei ersetzen,
- ein Produktupdate ohne Bestätigung installieren.

Für eine gewünschte Profilreparatur ist der bestehende regierte
Onboarding-/Governor-Plan-und-Apply-Weg mit eigener ausdrücklicher Bestätigung zu
verwenden.

### 6.5 Reparaturtransaktion

Jeder Reparaturlauf benötigt:

1. unveränderlichen Diagnose-Snapshot,
2. maschinenlesbaren Reparaturplan mit Plan-ID,
3. Benutzerbestätigung genau dieser Plan-ID,
4. Sicherung aller ersetzten lokalen Laufzeitdateien und Verknüpfungen,
5. schrittweises Auditprotokoll,
6. Abbruch bei unerwartetem Zustand,
7. Rollback, soweit die bereits ausgeführten Schritte reversibel sind,
8. vollständigen Postflight,
9. eindeutiges Endergebnis: erfolgreich, teilweise zurückgerollt oder
   fehlgeschlagen.

Ein zweiter identischer Reparaturlauf soll nach erfolgreicher Reparatur keine
weiteren Änderungen erzeugen.

## 7. Installer r26: Upgrade, Migration und Postflight

### 7.1 Preflight-Inventar

Vor Änderungen erfasst der Installer:

- vorhandene App-, Gateway- und Bridgepfade,
- gespeicherte Pfade aus `selection.ini`,
- installierte Buildidentitäten,
- laufende PLwC-Prozesse,
- Port-3007-Eigentümer,
- Autostartverknüpfungen,
- geplante Aufgaben,
- Native-Messaging-Registrierungen,
- Konfigurationsverknüpfung und Icon,
- vorhandene Profile und Workspacepfad.

Der Bericht unterscheidet `belegt`, `vermutet` und `unbekannt`. Ein Prozess darf
nur anhand eines eindeutigen PLwC-Pfads, einer passenden Kommandozeile oder einer
validierten Buildidentität PLwC zugeordnet werden.

### 7.2 Updateerkennung

Ein bestehender vollständiger PLwC-Zustand schaltet den Installer auf Update.
Bei einem Update werden bekannte Verzeichnisse übernommen und nicht erneut
abgefragt. Unvollständige oder widersprüchliche Zustände führen zu einer klaren
Migrations-/Reparaturübersicht, nicht zu einer stillen Neuinstallation.

Benutzerdaten, Profile, Konfigurationen, Logs und Workspaceinhalte bleiben
erhalten. Fehlende Standardordner dürfen idempotent ergänzt werden.

### 7.3 Pfadmigration

Ziel ist genau ein aktiver Laufzeitpfad `app\bridge`. Ein alter
`app\chat-bridge`-Pfad wird nicht sofort gelöscht:

1. Quelle und Ziel inventarisieren,
2. laufende zugehörige Prozesse kontrolliert stoppen,
3. Ziel sichern,
4. r26-Payload installieren,
5. Registrierung und Verknüpfungen auf das Ziel umstellen,
6. Bridge starten und Build-ID plus 8/8 prüfen,
7. Altpfad nur bei Erfolg als Recoverybestand archivieren oder nach einer
   ausdrücklichen Regel entfernen,
8. bei Fehler zurückrollen.

### 7.4 Verbindlicher Postflight

Der Installer darf `Installation abgeschlossen` nur melden, wenn mindestens
Folgendes bestätigt wurde:

1. erwartete Gateway-, Bridge-, Launcher- und Konfigurationsdateien vorhanden,
2. Hash-/Buildidentitäten passen zum r26-Payload,
3. Native Messaging ist für die vorgesehenen Browser korrekt registriert,
4. genau eine korrekte Autostartverknüpfung ist vorhanden,
5. Konfigurationsverknüpfung und Icon funktionieren,
6. Launcher kann die aktuelle Bridge starten,
7. Gateway antwortet,
8. Bridge meldet exakt 8/8 kanonische Werkzeuge,
9. kein eindeutig alter PLwC-Prozess aus einem Legacy-Pfad ist aktiv,
10. Konfigurations- und Profildaten wurden erhalten,
11. Diagnosebericht und Installationsidentität wurden erfolgreich geschrieben.

Ein fremder Portinhaber wird nicht beendet. Der Installer scheitert dann mit
einer konkreten, handlungsfähigen Diagnose. Bei fehlgeschlagenem Postflight darf
keine Erfolgsmeldung erscheinen.

## 8. Browser-Erweiterung 1.0.1

### 8.1 Atomarer Bereitschaftszustand

`Verbunden` darf erst als vollständig bereit angezeigt werden, wenn atomar
bestätigt sind:

1. Transport verbunden,
2. Buildidentität gelesen,
3. Kompatibilität validiert,
4. gespeicherte Gatewayeinstellungen angewandt,
5. `tools/list` geladen,
6. exakt 8/8 Werkzeuge validiert.

Die UI unterscheidet mindestens:

```text
Getrennt
Verbindung wird aufgebaut
Build wird geprüft
Werkzeuge werden geladen
Bereit – 8/8
Inkompatibel – Update erforderlich
Fehler – konkrete Ursache
```

Nach Trennung, Browserneustart oder erneutem Verbinden werden zwischengespeicherte
Build- und Werkzeugdaten verworfen und neu geladen. Der Zustand
`verbunden, 0/8, Build nicht geprüft` darf nicht als stabiler Endzustand
erscheinen.

### 8.2 Tatsächliche Erweiterungsversion

Die Erweiterung übermittelt bei Native-Messaging-Kontakt mindestens:

- tatsächliche Paketversion aus dem Browsermanifest,
- Extension-ID,
- Browserfamilie,
- Protokoll-/Kompatibilitätsversion,
- Zeitstempel.

Der Launcher bzw. lokale Statusdienst speichert den letzten Kontakt für die
Konfigurationsseite. Veraltete Informationen werden als solche markiert.

### 8.3 Store-Updatehinweis

Version 1.0.1 soll zusätzlich einen verständlichen Hinweis/Bage anbieten, wenn
der Browser ein verfügbares Store-Update meldet. Wiederholte aggressive
Updateprüfungen sind zu vermeiden. Die lokale Konfigurationsseite bleibt der
Ort, an dem alle PLwC-Komponentenversionen gemeinsam bewertet werden.

## 9. Noch offene Bridge-/Protokollkorrekturen

Die bereits besprochenen Sicherheits- und Konsistenzkorrekturen bleiben im
r26-Umfang:

1. Mutierende oder möglicherweise bereits ausgeführte Aufrufe werden bei
   unklarem Transportergebnis nicht automatisch wiederholt.
2. Der Primer-/Schemahash wird von Bridge beziehungsweise Erweiterung berechnet
   und mit einem klaren `integrity_verified`-Zustand transportiert.
3. Bestätigungspflichtige Vorgänge erhalten einen eindeutigen
   `awaiting_confirmation`-Zustand statt eines mehrdeutigen Fehlers.
4. `first_run` akzeptiert einen optionalen Profilnamen, ohne den öffentlichen
   Vertrag unnötig zu erweitern.
5. Notwendige read-only Hilfsaufrufe für einen regierten Ablauf bleiben erlaubt.
6. Profilerstellung und Profilaktivierung werden niemals von einer allgemeinen
   Dauerfreigabe abgedeckt; sie benötigen eine eigene Bestätigung.

Alle Änderungen benötigen positive und negative Vertragstests. Die öffentliche
Fassade bleibt bei exakt acht kanonischen Werkzeugen.

## 10. Updatearchitektur

### 10.1 Release-Manifest

Ein maschinenlesbares Release-Manifest enthält mindestens:

- Manifest-Schemaversion,
- Produktversion und Installerrevision,
- Komponentenversionen und Kompatibilitätsbereiche,
- Artefakt-URLs,
- Artefaktgrößen und SHA-256-Werte,
- Veröffentlichungszeitpunkt,
- Pflichtupdate/empfohlenes Update,
- Releasehinweise,
- Signatur über die kanonische Manifestdarstellung.

Die Signatur wird vor jeder Verwendung geprüft. Erst danach dürfen Hash und
Downloadziel als vertrauenswürdig gelten.

### 10.2 Verhalten

- Automatische Prüfung in einem begrenzten Intervall, nicht bei jeder
  UI-Aktion.
- Manuelle Prüfung jederzeit möglich.
- Letztes gültiges Ergebnis wird lokal mit Zeitpunkt gespeichert.
- Offlinezustand bleibt nutzbar und wird als `zuletzt geprüft` angezeigt.
- Download und Installation nur nach Bestätigung.
- Vor Ausführung: Signatur, Größe, SHA-256 und Buildidentität prüfen.
- Nach Ausführung: r26-Postflight und Rollback-/Fehlerbericht.
- Keine Telemetrie und keine Übertragung von Profil- oder Workspaceinhalten.

Die gemeinsame Updatelogik darf nicht ausschließlich in der Bridge liegen,
weil PLwC auch ohne Browser-Bridge installiert sein kann.

## 11. Arbeitspakete und Reihenfolge

### Phase 0 – Bestand schützen und Fehler reproduzieren

- aktuellen Git-/Artefaktstand dokumentieren,
- unversionierte Benutzerdateien schützen,
- r25-Artefakte außerhalb mutierender Buildausgaben sichern,
- destruktiven `ValidateOnly`-Pfad beseitigen oder isolieren,
- reproduzierende Tests für `HTTP 200`, leeres Profil, 0/8-Panel und
  Legacy-Pfade hinzufügen,
- Dirty- und Clean-System als getrennte Testfälle beschreiben.

**Gate:** Validierung kann keine vorhandenen Dist-Artefakte mehr zerstören; die
bekannten Fehler sind durch Tests oder reproduzierbare Diagnosen erfasst.

### Phase 1 – Identität, Inventar und Kompatibilitätsmodell

- zentrales Komponenteninventar entwerfen,
- semantische Version, Protokollversion, Buildrevision und Hash trennen,
- maschinenlesbare Kompatibilitätsmatrix implementieren,
- lokale und Live-Quellen mit Vertrauensstatus versehen,
- Statusmodell für bereit/kompatibel/Update/fehlt/unbekannt definieren.

**Gate:** Ein Testinventar kann gemischte, kompatible, veraltete und unbekannte
Komponenten eindeutig klassifizieren.

### Phase 2 – Konfigurationsseite und Profilfehler

- `reason`, `message`, `validation_error` und `missing_files` korrekt anzeigen,
- Profilinventar auf Gültigkeit erweitern,
- Aktivierung ungültiger Profile sperren,
- Komponenten-/Kompatibilitätstabelle einbauen,
- Workspaceänderung als Plan-/Bestätigungsablauf ergänzen,
- Launcher-Letztergebnis anzeigen.

**Gate:** Der leere FAUN-Fall wird verständlich erklärt; kein `HTTP 200` als
fachliche Fehlermeldung; tatsächliche Komponentenwerte sind sichtbar.

### Phase 3 – Extension-Handshake und Versionsentkopplung

- atomaren Bereitschaftszustand implementieren,
- Caches bei Reconnect korrekt invalidieren,
- Paketversion `1.0.1` vom Protokollvertrag `1.0.0` entkoppeln,
- tatsächliche Browser-/Erweiterungsversion lokal melden,
- Store-Updatehinweis ergänzen,
- Kompatibilität mit lokaler r25/r26-Laufzeit testen.

**Gate:** Kein stabiler widersprüchlicher `verbunden/0 von 8`-Zustand;
Erweiterung 1.0.0 bleibt mit r26 nutzbar und 1.0.1 wird korrekt erkannt.

### Phase 4 – Ein CLU-basierter PLwC-Doktor

- Diagnosemodell um Installations- und Kompatibilitätschecks erweitern,
- Plan-ID und erlaubte Reparaturaktionen definieren,
- deterministische Reparatur-Engine implementieren,
- Sicherung, Audit, Rollback und Idempotenz sicherstellen,
- Diagnose/Plan/Bestätigung in die eine Konfigurationsoberfläche integrieren,
- MCP-Doctor-Diagnose weiterhin read-only halten.

**Gate:** Diagnose verändert nichts; Plan erklärt jede Änderung; Apply akzeptiert
nur denselben bestätigten Plan und bekannte Aktionen; zweiter Lauf ist
änderungsfrei.

### Phase 5 – Installer-Migration und harter Postflight

- Preflight-Inventar implementieren,
- Updateerkennung und Seitensprung ohne erneute Verzeichnisabfrage,
- sichere `chat-bridge`-zu-`bridge`-Migration,
- alte Aufgaben/Verknüpfungen kontrolliert behandeln,
- fremde Portinhaber schützen,
- Postflight und verständliche Fehleroberfläche fertigstellen,
- Reparaturfunktionen zwischen Installer und Doktor wiederverwenden.

**Gate:** Clean-Install, r25-Update und Dirty-Migration bestehen denselben
Postflight; kein falsches Erfolgssignal.

### Phase 6 – Protokollsicherheit

- sechs in Abschnitt 9 genannten Korrekturen implementieren,
- positive, negative, Timeout-, Reconnect- und Bestätigungstests ergänzen,
- 8-Tool-Fassade unverändert halten.

**Gate:** Kein doppelter mutierender Aufruf, korrekte Integritätsanzeige und
eindeutige Bestätigungszustände.

### Phase 7 – Updatezentrale

- signiertes Manifestformat und Verifikation implementieren,
- sichere Abfrage und lokales Cachemodell,
- UI für empfohlenes/Pflichtupdate,
- bestätigten Download-/Installationsweg,
- Offline-, Manipulations- und Rollbacktests.

**Gate:** Manipuliertes Manifest oder falscher Hash wird abgelehnt; ohne
Bestätigung wird nichts installiert.

### Phase 8 – Abnahme, Dokumentation und Release

- vollständige Windows-11-Testmatrix ausführen,
- Softwarebeschreibung, Installation, Konfiguration, Troubleshooting,
  Sicherheitsmodell, Update- und Doctor-Dokumentation aktualisieren,
- Buildidentität, Hashes und Akzeptanzprotokoll erzeugen,
- exakten r26-Kandidaten unveränderlich sichern,
- Git-Änderungen nachvollziehbar committen und ohne Force-Push hochladen,
- Storepaket 1.0.1 erst nach separater Freigabe final einreichen.

**Gate:** Definition of Done erfüllt und Nachweise referenzieren exakt dieselben
Artefakthashes.

## 12. Verbindliche Testmatrix

Mindestens folgende Fälle müssen automatisiert oder als nachvollziehbarer
Systemtest abgedeckt werden:

1. saubere Windows-11-Neuinstallation ohne Administratorrechte,
2. direktes Update r25 auf r26,
3. alter `chat-bridge`-Pfad mit gespeicherter Pfadauswahl,
4. parallele alte und neue PLwC-Pfade,
5. alte geplante Aufgabe plus alter Autostartlink,
6. eindeutig alter PLwC-Node-Prozess auf Port 3007,
7. fremder Prozess auf Port 3007 – darf nicht beendet werden,
8. fehlendes Konfigurationsicon oder falsches Shortcutziel,
9. leerer Profilordner,
10. unvollständiges Profil,
11. gültiges vorhandenes Profil und bestehender Workspace,
12. nachträgliche Workspacepfadänderung,
13. Extension 1.0.0 mit r26,
14. Extension 1.0.1 mit r26,
15. Browserneustart, Disconnect und Reconnect,
16. Bridge gesund 8/8, Panelzustand noch nicht geladen,
17. inkompatible Buildidentität,
18. fehlende optionale Docker-/Qdrant-Komponente,
19. Doctor-Diagnose garantiert ohne Mutation,
20. Doctor-Reparatur erfolgreich und zweiter Lauf idempotent,
21. Reparaturfehler mit Rollback,
22. Updateprüfung offline,
23. ungültige Manifest-Signatur,
24. gültiges Manifest mit falschem Artefakthash,
25. abgebrochener Download oder Installationsfehler,
26. Installer-Postflightfehler – keine Erfolgsmeldung,
27. Build-/ValidateOnly-Lauf erhält bestehende Artefakte.

## 13. Definition of Done für r26

r26 ist erst fertig, wenn:

- der Installer auf Clean-, Update- und Dirty-Systemen zuverlässig arbeitet,
- ausschließlich versionslose aktive Laufzeitpfade verwendet werden,
- kein Schreiben nach `System32` erforderlich ist,
- die Konfigurationsseite tatsächliche Versionen und Kompatibilität aller
  relevanten Komponenten anzeigt,
- empfohlene und notwendige Updates unterschieden werden,
- ungültige Profile verständlich dargestellt werden,
- Workspacepfade sicher nachträglich änderbar sind,
- die Extension keinen widersprüchlichen Verbindungszustand zeigt,
- die alte Store-Erweiterung 1.0.0 kompatibel bleibt,
- genau ein sichtbarer PLwC-/CLU-Doktor Diagnose, Plan und bestätigte Reparatur
  anbietet,
- Reparaturen allowlist-basiert, auditierbar, möglichst rückrollbar und
  idempotent sind,
- Installer und Doktor denselben harten 8/8-Postflight verwenden,
- keine fremden Prozesse oder Benutzerdaten beschädigt werden,
- Updateinformationen signiert und Artefakte hashgeprüft sind,
- kein Update still installiert wird,
- alle relevanten automatischen Tests und Windows-Systemtests bestanden sind,
- Dokumentation und Akzeptanzprotokoll den tatsächlichen Stand beschreiben,
- der veröffentlichungsfähige Kandidat mit exakten Hashes gesichert und auf
  GitHub nachvollziehbar versioniert ist.

## 14. Konkreter Beginn im neuen Chat

Der neue Chat soll nicht sofort einen Produktionsbuild starten. Zuerst:

1. dieses Briefing vollständig lesen,
2. `git status`, Branch und HEAD erneut prüfen,
3. relevante Quellstellen für Installer, Konfigurationsseite, CLU Doctor,
   Extension-Handshake und Buildskript lokalisieren,
4. bestätigen, welche Befunde im aktuellen Code tatsächlich reproduzierbar
   sind,
5. Phase 0 umsetzen: Buildausgaben schützen und Regressionstests für die
   bekannten Fehler anlegen,
6. danach Phase für Phase implementieren und jedes Gate mit Tests belegen.

Keine Store-Veröffentlichung, kein Löschen alter Installationszustände auf dem
Problemrechner und kein endgültiger r26-Build, bevor die entsprechenden Gates
erfüllt sind.
