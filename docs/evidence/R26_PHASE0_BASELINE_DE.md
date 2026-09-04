# PLwC 1.0 / Installer r26 – Phase-0-Bestand und Reproduktionen

Stand: 2. September 2026

## Repositorybasis

- Branch: `codex/plwc-chat-bridge-rc19`
- HEAD: `3f02b54e648486ce3a5a4c071080ae10440f1716`
- Titel: `Harden Windows r25 bridge startup verification`
- Tracking: synchron mit `origin/codex/plwc-chat-bridge-rc19`
- Fremde/unversionierte Dateien: `docs/BRIEFING_R26_NEUER_CHAT.md` sowie
  `screen1.png` bis `screen5.png`

Die Screenshots wurden nicht verändert oder committed. Ihre exakten Namen wurden
in `.gitignore` aufgenommen, damit sie nicht versehentlich in einen Commit geraten.
Die Hashes liegen zusammen mit der lokalen Artefaktsicherung unter
`private_evidence/r26-phase0/baseline-hashes.json`.

## Gesicherte Installerartefakte

Die vollständigen `dist`-Inhalte von `.unsigned-build-r24` und
`.unsigned-build-r25` wurden bytegleich nach
`private_evidence/r26-phase0/r24-artifacts` beziehungsweise
`private_evidence/r26-phase0/r25-artifacts` kopiert. Dieser Bereich ist
git-ignoriert und liegt außerhalb aller Buildausgaben.

Der r25-Setupkandidat hat folgende Identität:

- Datei: `PLwC-Setup-1.0.0-installer-r25.exe`
- Größe: `5221208` Byte
- SHA-256: `e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c`

Der historische r21-Kandidat wurde nicht rekonstruiert. Die vorhandenen r24-/r25-
Dateien werden nicht als Ersatz für r21 ausgegeben.

## Belegte r25-Befunde

1. `build.ps1 -ValidateOnly` wählte ohne `-GeneratedOutputRoot` die kanonischen
   Verzeichnisse `installer/windows/stage` und `installer/windows/dist` und setzte
   beide zurück. r26 leitet den Standardlauf deshalb nach
   `installer/windows/.validate-build` um und verweigert den kanonischen Root für
   `ValidateOnly` ausdrücklich.
2. Die Konfigurations-API liefert für einen leeren Profilordner einen fachlich
   strukturierten Plan mit `ok:false`, `valid:false`, `reason` und
   `missing_files`. Die r25-Oberfläche führt den Ordner zugleich als einfachen
   auswählbaren Namen und verwirft beim Fehler die `reason` zugunsten von
   `HTTP 200`.
3. Das Panelstatusmodell akzeptiert den stabilen Widerspruch
   `connection=connected`, `buildIdentityValidation=null`, `toolSet=null`. Damit
   ist die Anzeige `verbunden`, `0/8`, Build ungeprüft im aktuellen Code
   reproduzierbar.
4. Die maschinenlesbaren Fixtures `r26-clean-install.json` und
   `r26-dirty-r25-install.json` trennen Clean- und Dirty/Migrationszustand. Der
   Dirty-Fall enthält belegbar PLwC-zuordenbare Legacy-Pfade sowie einen fremden
   Port-3007-Inhaber, der niemals beendet werden darf.

## Chrome-Web-Store-Status (erneut geprüft)

Der Entwurf wurde am 2. September 2026 im Chrome Web Store Developer Dashboard
schreibgeschützt geprüft:

- Artikel: `PLwC Chat Bridge`, Version `1.0.0`
- Extension-ID: `feceodobnhefdbfgmbinkndhogpfkicb`
- Status: `Bereit zur Veröffentlichung`
- angezeigte Frist: `vor dem 01.10.2026`
- aktive Sichtbarkeit: `Privat`
- Sichtbarkeit `Nicht gelistet`: nicht ausgewählt
- Trusted-Tester-Gruppe: `Keine`

Der Entwurf ist damit nicht als nutzbare Linkveröffentlichung zu behandeln. Das
beabsichtigte Vertriebsmodell bleibt `Nicht gelistet`. Vor einer späteren
Veröffentlichung muss die aktive Sichtbarkeit erneut geprüft werden; ein durch
die Änderung ausgelöster Review ist abzuwarten. Bei dieser Prüfung wurden weder
`Speichern` noch `Senden` oder eine Veröffentlichungsaktion ausgelöst.

## Phase-0-Gate

Das Gate ist erfüllt, wenn die gezielten Python-, TypeScript- und Pester-Tests
grün sind, der Pester-Build den Standardpfad von `ValidateOnly` verwendet und
der Vorher-/Nachher-Snapshot von `installer/windows/stage` und
`installer/windows/dist` bytegleich bleibt.

Lokaler Nachweis:

- Python: `17 passed`
- Extension: `174 passed`
- `ValidateOnly`: vollständig erfolgreich, ISCC nicht aufgerufen
- Stage/Dist-Snapshot vorher und nachher:
  `6b0103bd39c4f372817bbab57d139a9d315ed073ccae2a63341962b1d72318f4`
- Pester war auf dem Prüfcomputer nicht installiert; die Pester-Datei wurde als
  PowerShell-Scriptblock erfolgreich geparst, und der entscheidende Buildlauf
  samt Hashvergleich wurde direkt ausgeführt.
