# PLwC Windows Setup Guide

This guide covers the selectable PLwC Windows setup executable. It is written
for end users. PowerShell scripts and repository commands are not part of the
normal installation flow.

## Deutsch

### Vor dem Start

Das PLwC-Setup installiert den Gateway-Kern und auf Wunsch eine oder mehrere
Integrationen:

- Claude Desktop MCPB
- STDIO-Konfigurationsvorlage für Codex
- STDIO-Konfigurationsvorlage für Odysseus
- PLwC Chat Bridge für Chrome, Edge oder Brave

Python, Node.js und Docker Desktop sind eigenständige Programme. Das Setup
prüft zuerst, welche Programme und Zielanwendungen bereits vorhanden sind.
Fehlende Programme werden nur nach Ihrer ausdrücklichen Auswahl
heruntergeladen und installiert.

### Setup und Administratorrechte

Starten Sie die `PLwC-Setup-<Version>.exe` normal per Doppelklick. Dadurch
werden Native Messaging, der automatische Bridge-Start und `%APPDATA%\PLwC`
dem aktuell angemeldeten Windows-Benutzer zugeordnet.

Für Node.js, Docker Desktop und bestimmte Windows-Komponenten ist eine
Windows-Administratorbestätigung erforderlich. Das Setup öffnet die
Windows-Sicherheitsabfrage gezielt, sobald eine ausgewählte Installation diese
Rechte benötigt. Starten Sie das gesamte Setup nicht mit den Zugangsdaten eines
anderen Administratorkontos, weil dessen Benutzerprofil sonst die
benutzerbezogenen Einträge erhalten kann.

Während das Setup installierte Komponenten erkennt, sind die Auswahl und die
Vor-/Zurücknavigation gesperrt. Nach „Weiter“ bleibt der gewählte
Installationsplan bis zur abschließenden Nachprüfung unverändert. Eine
durchgehende Fortschrittsseite bleibt während Downloads, Herstellerprogrammen
und Nachprüfungen sichtbar; die Auswahlseite erscheint nicht zwischen den
einzelnen Installationsschritten.

### Sprache auswählen

Der erste Setup-Dialog bietet:

- Deutsch
- English

Die Windows-Anzeigesprache ist vorausgewählt. Die Auswahl kann vor dem Start
des Assistenten geändert werden und gilt für alle Setup-Seiten, Meldungen,
Protokollhinweise und den Installationsbericht.

### Größen und Speicherplatz

Das Setup zeigt die aktuellen Werte für die verwendeten Paketversionen an.
Die folgenden Werte dienen nur als Größenordnung:

| Bestandteil | Ungefährer Download | Zusätzlicher Speicher |
| --- | ---: | --- |
| PLwC Gateway und Chat Bridge | etwa 20 MB | abhängig von der Auswahl |
| Python und PLwC-Laufzeit | etwa 95 MB | einschließlich Qdrant-Modulen etwa 400 bis 1000 MB |
| Qdrant-Embedding-Modell | etwa 100 bis 500 MB bei der ersten Nutzung | abhängig vom Modellcache |
| Node.js-Installer | etwa 31 MB | installiert ungefähr 100 MB oder mehr |
| Docker Desktop | etwa 610 MB | Anwendung und WSL benötigen mehrere GB |
| Docker-Images und weitere Modelldaten | variabel | bei späterer Nutzung mehrere zusätzliche GB möglich |

Docker-Images werden nicht stillschweigend heruntergeladen. Vor dem Download
zeigt das Setup die bekannten Einzelgrößen, die bekannte Gesamtdownloadgröße,
den Mindest-Speicherbedarf und einen gesonderten Hinweis für variable
Docker-, WSL-, Image- und Modelldaten.

### Installation

1. Wählen Sie die Sprache.
2. Prüfen Sie den Sicherheits- und Administratorhinweis.
3. Wählen Sie die gewünschten Integrationen.
4. Prüfen Sie den erkannten Status von Python, Node.js, Docker, Browsern und
   Zielanwendungen.
5. Wählen Sie bei fehlendem Python, Node.js oder Docker entweder die
   automatische Einrichtung oder öffnen Sie die offizielle Herstellerseite.
6. Prüfen Sie Downloadgröße und freien Speicherplatz.
7. Übernehmen oder ändern Sie die vorgeschlagenen PLwC-Verzeichnisse.
8. Legen Sie Profil und Laufzeitwerte fest oder verwenden Sie die sicheren
   Vorgaben.
9. Prüfen Sie die vollständige Vorschau.
10. Starten Sie die Installation.

Bei einer Neuinstallation verwendet das Setup stabile Laufzeitverzeichnisse:

```text
%APPDATA%\PLwC\app\gateway
%APPDATA%\PLwC\app\bridge
```

Die Produktversion steht in den Build- und Installationsnachweisen, nicht im
Ordnernamen. Dadurch muss ein Update keinen neuen Laufzeitordner nur wegen
einer Versionsänderung anlegen.

Findet das Setup eine vollständige vorhandene PLwC-Installation, wechselt es
automatisch in den Update-Modus. Es übernimmt die gespeicherten App-, Gateway-,
Bridge-, Arbeits-, Profil-, Konfigurations-, Status-, Protokoll- und
Sicherungsverzeichnisse sowie die vorhandenen Laufzeiteinstellungen. Die
entsprechenden Seiten werden nicht erneut abgefragt. Auch ältere, bereits
verwendete versionsgebundene Gateway- oder Bridge-Pfade bleiben erhalten; das
Update verschiebt oder löscht keine Benutzerdaten.

Ein fehlendes Claude Desktop blockiert nur die ausgewählte Claude-Integration.
Ein fehlender Chrome-, Edge- oder Brave-Browser blockiert nur die ausgewählte
Chat Bridge. Fehlendes Codex oder Odysseus erzeugt eine klar als vorbereitet
gekennzeichnete Konfigurationsvorlage. Fehlendes Docker verhindert die
PLwC-Kerninstallation nicht, schränkt aber Sandbox- und Dokumentfunktionen ein.

### Browser-Erweiterung einrichten

Der normale Veröffentlichungsweg ist die zum Browser passende Store-Version.
Chrome wurde am 30.08.2026 privat für den genehmigten Trusted Tester zur
Prüfung eingereicht; die automatische Veröffentlichung ist deaktiviert. Edge
wurde am selben Tag verborgen und nur über den späteren Link auffindbar zur
Zertifizierung eingereicht. Beide enthalten Version 1.0.0 und sind während der
Prüfung noch nicht als Store-signierte Erweiterung installierbar.

Eine entpackt geladene Erweiterung verwendet die getrennte
Entwicklungsidentität. Sie darf nicht als Nachweis für die Chrome- oder
Edge-Store-ID bezeichnet werden.

Nur für Entwicklung und lokale Vorabnahme öffnet das Setup nach der
Installation den vorbereiteten Erweiterungsordner. Verwenden Sie dabei genau
den installierten `extension`-Ordner und keine Repository-Kopie.

Für Chrome:

1. Öffnen Sie `chrome://extensions`.
2. Aktivieren Sie **Entwicklermodus**.
3. Wählen Sie **Entpackte Erweiterung laden**.
4. Wählen Sie den vom PLwC-Setup geöffneten Erweiterungsordner.
5. Laden Sie die Erweiterung neu, wenn der Browser nach einer geänderten
   Berechtigung fragt.

Für Edge:

1. Öffnen Sie `edge://extensions`.
2. Aktivieren Sie **Entwicklermodus**.
3. Wählen Sie **Entpackte Erweiterung laden**.
4. Wählen Sie den vom PLwC-Setup geöffneten Erweiterungsordner.
5. Laden Sie die Erweiterung neu, wenn der Browser nach einer geänderten
   Berechtigung fragt.

Für Brave:

1. Öffnen Sie `brave://extensions`.
2. Aktivieren Sie **Entwicklermodus**.
3. Wählen Sie **Entpackte Erweiterung laden**.
4. Wählen Sie den vom PLwC-Setup geöffneten Erweiterungsordner.
5. Laden Sie die Erweiterung nach Reparaturen oder Updates neu.

Die Native-Messaging-Registrierung erlaubt getrennt die Entwicklungs-, Chrome-
Store- und Edge-Store-ID, aber keine Wildcard. Die benutzerbezogene Windows-
Autostart-Aufgabe wird vom PLwC-Setup beziehungsweise dessen Reparaturfunktion
übernommen. Im normalen Ablauf ist kein Terminalbefehl erforderlich.

### Bridge prüfen

Öffnen Sie in der PLwC Chat Bridge den Bereich **Status** und wählen Sie
**Reconnect**. Der betriebsbereite Zustand lautet:

```text
Bridge    connected
Launcher  available
Tools     8 / 8
```

Nach jeder Windows-Anmeldung startet das Setup die lokale Bridge automatisch
und prüft den Zustand `8 / 8`. Danach genügt es, den Browser zu öffnen und bei
Bedarf **Reconnect** zu wählen. Der Native Launcher darf nicht noch einmal
installiert werden müssen.

Falls die Verbindung nicht hergestellt wird, verwenden Sie die
PLwC-Reparaturfunktion. Die Fehlermeldung und der Installationsbericht nennen
den genauen Protokollpfad. Führen Sie keine Skripte aus einem
Entwicklungs-Repository aus.

### Arbeitsordner nachträglich ändern

Öffnen Sie die installierte **PLwC-Konfiguration** und tragen Sie unter
**Arbeitsordner ändern** den gewünschten absoluten Pfad ein. Nach
**Einstellungen speichern** legt PLwC dort bei Bedarf ausschließlich die
Standardordner `Tagebuch`, `Temp` und `Trashcan` an. Vorhandene Dateien werden
nicht verschoben, überschrieben oder gelöscht.

Der neue Pfad wird als gemeinsamer Arbeitsordner für Gateway, Chat Bridge,
Codex und Odysseus gespeichert und vom Setup bei späteren Updates wieder
verwendet. Bereits laufende Clients müssen nur dann neu gestartet werden, wenn
sie noch den alten Pfad anzeigen.

### Erste Schritte nach der Installation

Das Setup installiert eine lokale Einführung unter
`%APPDATA%\PLwC\app\docs` und öffnet auf der Abschlussseite standardmäßig die
zur gewählten Setup-Sprache passende Fassung. Sie bleibt über den
Startmenüeintrag **Erste Schritte mit PLwC** erreichbar. Die technische
Installationsübersicht ist weiterhin verfügbar, wird aber nicht zusätzlich
ungefragt geöffnet.

Die Einführung beginnt mit getrennten Abschlusswegen für **Nur Gateway**,
**Claude Desktop MCPB**, **Codex STDIO**, **Odysseus STDIO** und **Chat
Bridge**. Sie nennt die vom Setup erzeugten Dateien und erklärt, welche
Aktivierung noch im jeweiligen Client vorgenommen werden muss. Nur bei der Chat
Bridge beginnt jedes neue Gespräch mit dem versionierten Primer: Unter
**Status** müssen Verbindung, Buildabgleich und `8 / 8` Werkzeuge bestätigt
sein. Danach unter **Primer** zuerst **Generate** und anschließend **Insert
Bridge Primer** wählen. Der Primer wird in das ChatGPT-Eingabefeld eingefügt
und muss manuell gesendet werden. Native MCP-Clients erhalten ihre Schemas
direkt und verwenden keinen Bridge Primer.

In allen Clients können Aufgaben normal beschrieben werden. Für normale
Benutzer erklärt die Einführung bei jedem zentralen Ablauf den Zweck, den
sinnvollen Einsatzzeitpunkt und mögliche Änderungen. Compile bedeutet dabei
nicht das Übersetzen von Programmcode, sondern das lesende Laden des aktiven
Profils als kontrollierte Kontextschicht für die aktuelle Sitzung. Entsprechend
werden auch Status, Describe, Onboarding, Reflection, Governor, Tagebuch,
Trashcan, Persona-Erweiterung, Force-Grenzen und Neustartverhalten erklärt.

## English

### Before you start

The PLwC setup installs the Gateway core and any selected integrations:

- Claude Desktop MCPB
- STDIO configuration snippet for Codex
- STDIO configuration snippet for Odysseus
- PLwC Chat Bridge for Chrome, Edge or Brave

Python, Node.js and Docker Desktop are separate applications. Setup first
checks which applications and target clients are already available. Missing
software is downloaded and installed only after you explicitly select it.

### Setup and administrator approval

Start `PLwC-Setup-<version>.exe` normally with a double-click. This keeps
Native Messaging, automatic Bridge startup and `%APPDATA%\PLwC` assigned to
the signed-in Windows user.

Node.js, Docker Desktop and some Windows components require Windows
administrator approval. Setup opens the Windows security prompt only when a
selected installation needs those rights. Do not start the whole setup with
credentials for a different administrator account, because per-user entries
could then be written to that administrator's profile.

While Setup detects installed components, prerequisite choices and Back/Next
navigation are disabled. After Next is clicked, the selected acquisition plan
remains locked until the final postflight check. One continuous progress page
stays visible across downloads, vendor installers and checks; the selection
page does not reappear between child installations.

### Choose a language

The first setup dialog offers:

- Deutsch
- English

The Windows display language is preselected. You can change it before the
wizard starts. The selection applies to every setup page, message, log hint and
the installation report.

### Download and storage size

Setup displays current values for the pinned package versions. The following
values are only a guide:

| Item | Approximate download | Additional storage |
| --- | ---: | --- |
| PLwC payload | included in Setup | calculated from the staged payload for each build |
| Python and PLwC runtime | about 115 MB | including Qdrant modules, about 450 to 1050 MB |
| Node.js installer | about 32 MB | installed runtime is about 100 MB or more |
| Docker Desktop | about 610 MB | the application and WSL require multiple GB |
| WSL runtime and Docker images | unknown until enabled or pulled | unknown; can require several additional GB |
| First-use model cache | default embedding model about 100 to 500 MB | additional model caches are unknown |

Docker images are not downloaded implicitly. Before acquisition, setup shows
the PLwC payload, Python, Node.js, Docker Desktop, WSL/image storage, and
variable first-use caches separately. It labels every unavailable value as
`unknown`, never as null or zero, and excludes unknown later downloads from the
selected known-download total.

### Installation

1. Choose the language.
2. Review the security and administrator notice.
3. Select the required integrations.
4. Review the detected status of Python, Node.js, Docker, browsers and target
   applications.
5. For missing Python, Node.js or Docker, choose automatic setup or open the
   official vendor page.
6. Review download size and available storage.
7. Accept or change the proposed PLwC directories.
8. Configure the profile and runtime values or keep the safe defaults.
9. Review the complete write preview.
10. Start installation.

On a new installation, Setup uses stable runtime directories:

```text
%APPDATA%\PLwC\app\gateway
%APPDATA%\PLwC\app\bridge
```

The product version belongs in build and installation evidence, not in the
directory name. An update therefore does not create a new runtime directory
only because the version changed.

When Setup finds a complete existing PLwC installation, it automatically
switches to update mode. It reuses the stored app, Gateway, Bridge, workspace,
profiles, config, state, log and backup directories together with the existing
runtime settings. Those pages are not requested again. Older versioned Gateway
or Bridge paths that are already in use are preserved; an update does not move
or delete user data.

A missing Claude Desktop application blocks only the selected Claude
integration. A missing Chrome, Edge or Brave browser blocks only the selected
Chat Bridge. Missing Codex or Odysseus creates a clearly marked prepared
configuration snippet. Missing Docker does not block the PLwC core, but
sandbox and document operations remain unavailable.

### Build identity and support records

Every completed installation records the identity of the exact setup executable
that performed the installation. By default, the installation summary is stored
at:

```text
%APPDATA%\PLwC\config\installer\installation-summary.txt
```

By default, the machine-readable selection and identity state is stored at:

```text
%APPDATA%\PLwC\config\installer\selection.ini
```

If a different configuration directory was selected in the wizard, both files
are below its `installer` subdirectory. The append-only setup diagnostic record
is stored at:

```text
%LOCALAPPDATA%\PLwC\logs\setup\installer-diagnostic.log
```

These records contain the installer revision, setup EXE SHA-256, Gateway
version, Node Bridge version, Browser Extension version, Native Launcher
version, installation mode and selected components. When reporting a setup
problem, provide the installation summary and diagnostic record together. Their
build ID and EXE hash identify the exact generated installer and its acceptance
evidence.

### Workspace structure

On a new installation, upgrade, or repair, setup ensures that the selected
workspace contains these directories:

```text
Tagebuch/
Temp/
Trashcan/
```

Existing directories and their contents are preserved. Repair adds a missing
standard directory but does not rewrite data on later runs. Setup does not
create `Inbox/` or any other workspace directory, and it performs no workspace
cleanup or deletion.

The directories are created by the non-elevated setup process and belong to
the signed-in Windows user. Administrator approval for a prerequisite installer
does not change workspace ownership.

### Change the workspace later

Open the installed **PLwC Configuration** page and enter the required absolute
path under **Change workspace folder**. After **Save settings**, PLwC creates
only the standard `Tagebuch`, `Temp` and `Trashcan` directories when they are
missing. Existing files are not moved, overwritten or deleted.

The new path is stored as the shared workspace for Gateway, Chat Bridge, Codex
and Odysseus and is reused by later Setup updates. Restart a running client only
if it still displays the previous path.

### Chat Bridge browser extension

The normal release path is the matching browser Store package. On 2026-08-30,
Chrome was submitted as private for the approved trusted tester with automatic
publication disabled, and Edge was submitted as hidden/link-only. Both contain
version 1.0.0 and remain under review, so neither Store-signed package is
installable yet.

An unpacked extension uses the separate development identity. It must not be
reported as Chrome or Edge Store-ID acceptance evidence.

For development and local pre-release acceptance only, Setup opens the
installed extension folder. Use that exact folder. For a default installation,
the folder is:

```text
%APPDATA%\PLwC\app\bridge\extension
```

If you changed the Chat Bridge directory during setup, use:

```text
<selected Chat Bridge directory>\extension
```

Do not load `extension\src`, `extension\dist`, a repository checkout, or any
folder under a development workspace. End users do not need scripts from the
development repository.

For Chrome:

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Select the installed `extension` folder shown above.
5. After a PLwC repair or update, return to `chrome://extensions` and select
   **Reload** on the PLwC Chat Bridge extension card.

For Brave:

1. Open `brave://extensions`.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Select the installed `extension` folder shown above.
5. After a PLwC repair or update, return to `brave://extensions` and select
   **Reload** on the PLwC Chat Bridge extension card.

For Edge development acceptance:

1. Open `edge://extensions`.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Select the installed `extension` folder shown above.
5. After a PLwC repair or update, select **Reload** on the extension card.

PLwC setup and repair register the Native Launcher for Chrome, Edge and Brave
under the signed-in Windows user. The generated manifest allows the distinct
development, Chrome Store and Edge Store origins and no wildcard. The expected
registration points are the browser Native Messaging host entries for
`plwc.chat_bridge.launcher`, pointing to the PLwC-generated manifest in:

```text
%APPDATA%\PLwC\config\native-messaging\plwc.chat_bridge.launcher.json
```

The manifest points to the installed launcher executable below the selected
Chat Bridge directory:

```text
<selected Chat Bridge directory>\native\bin\plwc-chat-bridge-launcher.exe
```

If Chrome or Brave reports that the native host is missing, run PLwC setup
again and choose **Repair**. Repair re-registers the Native Launcher and the
per-user Bridge autostart task. Do not run repository scripts manually.

### Verify the Bridge

Open **Status** in PLwC Chat Bridge and select **Reconnect**. A ready
installation reports:

```text
Bridge    connected
Launcher  available
Tools     8 / 8
```

After every Windows sign-in, the local Bridge starts automatically and verifies
the `8 / 8` state. Open Chrome or Brave, open the PLwC Chat Bridge panel and
select **Reconnect** if the panel does not connect immediately. The Native
Launcher must not require another installation.

If the launcher is missing, use PLwC **Repair** and then reload the extension
on `chrome://extensions` or `brave://extensions`.

If the wrong extension directory was loaded, remove that unpacked extension
entry, select **Load unpacked** again and choose the installed PLwC
`extension` folder under `%APPDATA%\PLwC\app\bridge`.

If the Bridge is unavailable while the launcher is available, select
**Reconnect**. If the status still does not reach `Tools 8 / 8`, use PLwC
**Repair**. The error and installation report identify the exact log path.

### Getting started after installation

Setup installs a local guide below `%APPDATA%\PLwC\app\docs` and selects the
page matching the chosen Setup language on the Finish page. It remains
available through the localized **PLwC Getting Started** Start menu entry. The
technical installation summary remains available as a separate, default-off
Finish action.

The guide begins with separate completion paths for **Gateway only**, **Claude
Desktop MCPB**, **Codex STDIO**, **Odysseus STDIO**, and **Chat Bridge**. It
names the files prepared by Setup and the remaining client-owned activation
step. Only Chat Bridge begins each new conversation with the versioned Primer:
verify the connection, matching build identity, and `8 / 8` tools under
**Status**, then select **Generate**, **Insert Bridge Primer**, and manually
send the inserted Primer. Native MCP clients receive their schemas directly and
do not use the Bridge Primer.

Tasks can be described in normal language in every client. For nontechnical
users, the guide explains the purpose, appropriate time to use, and possible
changes for each core workflow. Compile does not build program code; it reads
the active profile and returns a controlled context layer for the current
session. Status, Describe, onboarding, Reflection, Governor, diary, Trashcan,
Persona growth, the narrow Force boundary, and restart behavior receive the
same plain-language treatment.
