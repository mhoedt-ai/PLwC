; PLwC Windows installer
; Payload contract (all directories are optional for development builds):
;   stage\common\*       -> shared application files
;   stage\gateway\*      -> PLwC Gateway runtime, including server.py
;   stage\claude\*       -> Claude Desktop MCPB artifacts
;   stage\codex\*        -> optional Codex support artifacts
;   stage\odysseus\*     -> optional Odysseus support artifacts
;   stage\chat-bridge\*  -> bridge, extension and native launcher payload

#define MyAppName "PLwC"
#define MyAppPublisher "PLwC"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#ifndef InstallerRevision
#define InstallerRevision "installer-r26"
#endif
#ifndef GatewayVersion
#define GatewayVersion "1.0.0"
#endif
#ifndef NodeBridgeVersion
#define NodeBridgeVersion "1.0.0"
#endif
#ifndef BrowserExtensionVersion
#define BrowserExtensionVersion "1.0.1"
#endif
#ifndef NativeLauncherVersion
#define NativeLauncherVersion "1.0.0"
#endif
#ifndef StageDir
#define StageDir "stage"
#endif
#ifndef BridgeDirectoryName
#define BridgeDirectoryName "bridge"
#endif
#ifndef McpbAvailable
#define McpbAvailable "0"
#endif
#ifndef StableChatBridgeExtensionId
#define StableChatBridgeExtensionId "nlogfcafjdfdoknpkbehjgihpafpipdb"
#endif
#include "assets\prerequisite-sizes.iss"

[Setup]
AppId={{9B40478C-3B55-4E2D-A0F9-BAFF0AE6672A}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion} ({#InstallerRevision})
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\PLwC\app
DefaultGroupName=PLwC
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
MinVersion=10.0
WizardStyle=modern
WizardSizePercent=110
Compression=lzma2/max
SolidCompression=yes
SetupLogging=yes
CloseApplications=no
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousSetupType=no
Uninstallable=yes
UninstallDisplayName=PLwC
UninstallDisplayIcon={uninstallexe}
SetupIconFile=assets\plwc.ico
WizardSmallImageFile=..\..\plwc-icon-512.png
ShowLanguageDialog=yes
UsePreviousLanguage=no
LanguageDetectionMethod=uilanguage
OutputDir=output
OutputBaseFilename=PLwC-Setup-{#AppVersion}-{#InstallerRevision}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[CustomMessages]
english.TypeGatewayOnly=PLwC Gateway only
german.TypeGatewayOnly=Nur PLwC Gateway
english.TypeFull=All integrations
german.TypeFull=Alle Integrationen
english.TypeCustom=Custom selection
german.TypeCustom=Benutzerdefinierte Auswahl
english.ComponentGateway=PLwC Gateway (required)
german.ComponentGateway=PLwC Gateway (erforderlich)
english.ComponentClaude=Claude Desktop MCPB
german.ComponentClaude=Claude Desktop MCPB
english.ComponentCodex=Codex STDIO snippet
german.ComponentCodex=Codex STDIO-Konfigurationsvorlage
english.ComponentOdysseus=Odysseus STDIO snippet
german.ComponentOdysseus=Odysseus STDIO-Konfigurationsvorlage
english.ComponentChatBridge=PLwC Chat Bridge
german.ComponentChatBridge=PLwC Chat Bridge
english.IconSummary=PLwC installation summary
german.IconSummary=PLwC-Installationsübersicht
english.IconGettingStarted=PLwC Getting Started
german.IconGettingStarted=Erste Schritte mit PLwC
english.IconConfig=PLwC configuration
german.IconConfig=PLwC-Konfiguration
english.IconDesktopConfig=PLwC-Konfiguration
german.IconDesktopConfig=PLwC-Konfiguration
english.IconConfigFolder=Open PLwC configuration folder
german.IconConfigFolder=PLwC-Konfigurationsordner öffnen
english.IconUninstall=Uninstall PLwC
german.IconUninstall=PLwC deinstallieren
english.RunOpenSummary=Open installation summary
german.RunOpenSummary=Installationsübersicht öffnen
english.RunOpenGettingStarted=Open PLwC Getting Started
german.RunOpenGettingStarted=Erste Schritte mit PLwC öffnen
english.RunOpenConfiguration=Open shared PLwC configuration
german.RunOpenConfiguration=Gemeinsame PLwC-Konfiguration öffnen
english.RunOpenClaude=Open Claude MCPB folder
german.RunOpenClaude=Claude-MCPB-Ordner öffnen
english.RunOpenCodex=Open Codex STDIO snippet
german.RunOpenCodex=Codex-STDIO-Konfigurationsvorlage öffnen
english.RunOpenOdysseus=Open Odysseus STDIO snippet
german.RunOpenOdysseus=Odysseus-STDIO-Konfigurationsvorlage öffnen
english.RunOpenExtension=Open browser extension folder
german.RunOpenExtension=Browser-Erweiterung zum Laden öffnen
english.PagePrereqTitle=PLwC prerequisites
german.PagePrereqTitle=PLwC-Voraussetzungen
english.PagePrereqDescription=Check required software and selected target applications
german.PagePrereqDescription=Pflichtsoftware und ausgewählte Zielanwendungen prüfen
english.PagePrereqSubCaption=The checks run again whenever this page is shown and immediately before installation.
german.PagePrereqSubCaption=Die Prüfungen laufen bei jedem Anzeigen und unmittelbar vor der Installation erneut.
english.PagePrereqActionTitle=Resolve prerequisites
german.PagePrereqActionTitle=Voraussetzungen einrichten
english.PagePrereqActionDescription=Choose automatic setup or use the official download pages
german.PagePrereqActionDescription=Automatische Einrichtung wählen oder die offiziellen Downloadseiten verwenden
english.PagePrereqActionSubCaption=All options start disabled. Setup requests Windows administrator approval only for the Visual C++ runtime, Node.js and Docker/WSL when needed.
german.PagePrereqActionSubCaption=Alle Optionen sind zunächst aus. Setup fordert die Windows-Administratorbestätigung nur bei Bedarf für die Visual-C++-Laufzeit, Node.js und Docker/WSL an.
english.OptionInstallPython=Install Python 3.13, Visual C++ and PLwC runtime
german.OptionInstallPython=Python 3.13, Visual C++ und PLwC-Laufzeit installieren
english.OptionInstallNode=Install Node.js 24 LTS
german.OptionInstallNode=Node.js 24 LTS installieren
english.OptionInstallDocker=Install Docker Desktop
german.OptionInstallDocker=Docker Desktop installieren
english.ButtonPythonDownload=Official Python / VC++ pages
german.ButtonPythonDownload=Offizielle Python-/VC++-Seiten
english.ButtonNodeDownload=Official Node.js page
german.ButtonNodeDownload=Offizielle Node.js-Seite
english.ButtonDockerDownload=Official Docker page
german.ButtonDockerDownload=Offizielle Docker-Seite
english.ButtonRecheckPrerequisites=Check again
german.ButtonRecheckPrerequisites=Erneut prüfen
english.ActionSelectRequired=Select automatic setup for every missing required component.
german.ActionSelectRequired=Wählen Sie die automatische Einrichtung für jede fehlende Pflichtkomponente.
english.ActionInstallSelected=Click Next to install the selected prerequisites.
german.ActionInstallSelected=Mit „Weiter“ werden die ausgewählten Voraussetzungen installiert.
english.ActionRetrySelected=The previous attempt was incomplete. Review the log and click Next to retry.
german.ActionRetrySelected=Der vorherige Versuch war unvollständig. Prüfen Sie das Protokoll und klicken Sie zum Wiederholen auf „Weiter“.
english.ActionNothingSelected=No automatic prerequisite installation is selected.
german.ActionNothingSelected=Es ist keine automatische Installation von Voraussetzungen ausgewählt.
english.SizeHeading=Estimated download and installed storage:
german.SizeHeading=Geschätzter Download- und installierter Speicherbedarf:
english.SizePlwc=PLwC payload: included in Setup; approx. {#PlwcPayloadMiB} MB installed
german.SizePlwc=PLwC-Payload: im Setup enthalten; ca. {#PlwcPayloadMiB} MB installiert
english.SizePython=Python, Visual C++ and PLwC runtime: approx. {#PythonDownloadMiB} MB download; {#PythonDiskMinMiB}-{#PythonDiskMaxMiB} MB installed
german.SizePython=Python, Visual C++ und PLwC-Laufzeit: ca. {#PythonDownloadMiB} MB Download; {#PythonDiskMinMiB}-{#PythonDiskMaxMiB} MB installiert
english.SizeNode=Node.js: approx. {#NodeDownloadMiB} MB download; {#NodeDiskMiB} MB installed
german.SizeNode=Node.js: ca. {#NodeDownloadMiB} MB Download; {#NodeDiskMiB} MB installiert
english.SizeDocker=Docker Desktop: approx. {#DockerDownloadMiB} MB download; at least {#DockerDiskMinMiB} MB installed
german.SizeDocker=Docker Desktop: ca. {#DockerDownloadMiB} MB Download; mindestens {#DockerDiskMinMiB} MB installiert
english.SizeWslImages=WSL runtime and Docker image storage: 
german.SizeWslImages=WSL-Laufzeit und Docker-Image-Speicher: 
english.SizeWslImagesNote=; can require several additional GB after enablement or image pulls
german.SizeWslImagesNote=; kann nach Aktivierung oder Image-Downloads mehrere zusätzliche GB benötigen
english.SizeFirstUse=Variable first use: default embedding model approx. {#QdrantModelMinMiB}-{#QdrantModelMaxMiB} MB; additional model caches 
german.SizeFirstUse=Variable erste Nutzung: Standard-Embedding-Modell ca. {#QdrantModelMinMiB}-{#QdrantModelMaxMiB} MB; weitere Modell-Caches 
english.SizeUnknown=unknown
german.SizeUnknown=unbekannt
english.SizeSelected=Selected known external downloads: approx. 
german.SizeSelected=Ausgewählte bekannte externe Downloads: ca. 
english.SizeSelectedVariable=Later WSL, image and model downloads: 
german.SizeSelectedVariable=Spätere WSL-, Image- und Modell-Downloads: 
english.SizeEstimateAsOf=Estimate as of {#SizeEstimateDate}; vendor packages and actual disk usage may change.
german.SizeEstimateAsOf=Schätzung vom {#SizeEstimateDate}; Herstellerpakete und tatsächlicher Speicherbedarf können abweichen.
english.SizeLogLocation=Failure diagnostics: 
german.SizeLogLocation=Fehlerdiagnose: 
english.PageDownloadTitle=Download prerequisites
german.PageDownloadTitle=Voraussetzungen herunterladen
english.PageDownloadDescription=Downloading a verified official installer
german.PageDownloadDescription=Ein geprüftes offizielles Installationsprogramm wird heruntergeladen
english.PageDownloadSubCaption=The package is verified against its pinned SHA-256 value before it can run.
german.PageDownloadSubCaption=Das Paket wird vor der Ausführung anhand des festgelegten SHA-256-Werts geprüft.
english.PageInstallProgressTitle=Installing prerequisites
german.PageInstallProgressTitle=Voraussetzungen werden installiert
english.PageInstallProgressDescription=Please wait while the selected software is installed
german.PageInstallProgressDescription=Bitte warten Sie, während die ausgewählte Software installiert wird
english.PrereqProgressPython=Installing Python 3.13...
german.PrereqProgressPython=Python 3.13 wird installiert...
english.PrereqProgressVCRuntime=Installing the Microsoft Visual C++ runtime...
german.PrereqProgressVCRuntime=Die Microsoft-Visual-C++-Laufzeit wird installiert...
english.PrereqProgressMcp=Installing the PLwC Python runtime...
german.PrereqProgressMcp=Die PLwC-Pythonlaufzeit wird eingerichtet...
english.PrereqProgressNode=Installing Node.js 24 LTS...
german.PrereqProgressNode=Node.js 24 LTS wird installiert...
english.PrereqProgressDocker=Installing Docker Desktop...
german.PrereqProgressDocker=Docker Desktop wird installiert...
english.PrereqProgressFallbackDownload=Retrying the verified download with Windows curl...
german.PrereqProgressFallbackDownload=Der geprüfte Download wird mit Windows-curl erneut versucht...
english.PrereqProgressRecheck=Checking prerequisites again...
german.PrereqProgressRecheck=Voraussetzungen werden erneut geprüft...
english.PrereqProgressBatch=Preparing the selected prerequisite plan...
german.PrereqProgressBatch=Der ausgewählte Voraussetzungenplan wird vorbereitet...
english.PrereqProgressWait=This may take several minutes. Setup checks the result again when this step finishes.
german.PrereqProgressWait=Dies kann mehrere Minuten dauern. Anschließend prüft Setup das Ergebnis erneut.
english.PrereqProgressPlanLocked=The selection is locked until all selected downloads, installations and final checks finish. Selected plan: 
german.PrereqProgressPlanLocked=Die Auswahl bleibt gesperrt, bis alle gewählten Downloads, Installationen und Abschlussprüfungen beendet sind. Ausgewählter Plan: 
english.PrereqProgressCheckingLocked=Setup is detecting installed components. Selection and navigation remain disabled until this check finishes.
german.PrereqProgressCheckingLocked=Setup erkennt die installierten Komponenten. Auswahl und Navigation bleiben bis zum Abschluss dieser Prüfung deaktiviert.
english.PageRuntimeDirsTitle=PLwC runtime directories
german.PageRuntimeDirsTitle=PLwC-Laufzeitverzeichnisse
english.PageRuntimeDirsDescription=Set application, Gateway and Chat Bridge directories
german.PageRuntimeDirsDescription=App-, Gateway- und Chat-Bridge-Verzeichnisse festlegen
english.PageRuntimeDirsSubCaption=Gateway and Bridge must remain separate subdirectories of the application directory.
german.PageRuntimeDirsSubCaption=Gateway und Bridge bleiben getrennte Unterverzeichnisse des App-Verzeichnisses.
english.FieldApp=Application:
german.FieldApp=App:
english.FieldGateway=Gateway:
german.FieldGateway=Gateway:
english.FieldChatBridge=Chat Bridge:
german.FieldChatBridge=Chat Bridge:
english.PageCoreDirsTitle=PLwC core data directories
german.PageCoreDirsTitle=PLwC-Kerndatenverzeichnisse
english.PageCoreDirsDescription=Set workspace, profiles and configuration directories
german.PageCoreDirsDescription=Arbeitsbereichs-, Profil- und Konfigurationsverzeichnisse festlegen
english.PageCoreDirsSubCaption=These data areas must be separate. Safe defaults are located below your user profile.
german.PageCoreDirsSubCaption=Diese Datenbereiche müssen getrennt sein. Die sicheren Vorgaben liegen unter Ihrem Benutzerprofil.
english.FieldWorkspace=Workspace:
german.FieldWorkspace=Arbeitsbereich:
english.FieldProfiles=Profiles:
german.FieldProfiles=Profile:
english.FieldConfig=Configuration:
german.FieldConfig=Konfiguration:
english.PageOpsDirsTitle=PLwC operating data directories
german.PageOpsDirsTitle=PLwC-Betriebsdatenverzeichnisse
english.PageOpsDirsDescription=Set state, logs and backup directories
german.PageOpsDirsDescription=Status-, Log- und Backup-Verzeichnisse festlegen
english.PageOpsDirsSubCaption=Runtime state, logs and profile backups are stored separately.
german.PageOpsDirsSubCaption=Laufzeitstatus, Protokolle und Profilsicherungen werden getrennt gespeichert.
english.FieldState=State:
german.FieldState=Status:
english.FieldLogs=Logs:
german.FieldLogs=Protokolle:
english.FieldBackups=Backups:
german.FieldBackups=Sicherungen:
english.PageProfileTitle=PLwC initial setup
german.PageProfileTitle=PLwC-Ersteinrichtung
english.PageProfileDescription=Set profile and security configuration
german.PageProfileDescription=Profil und Sicherheitskonfiguration festlegen
english.PageProfileSubCaption=The security path is optional. Governed onboarding is completed later through PLwC.
german.PageProfileSubCaption=Der Sicherheitspfad ist optional. Die gesteuerte Ersteinrichtung erfolgt später über PLwC.
english.FieldProfileName=Profile name:
german.FieldProfileName=Profilname:
english.FieldSecurityConfig=Security configuration path (optional):
german.FieldSecurityConfig=Pfad zur Sicherheitskonfiguration (optional):
english.PageThresholdTitle=PLwC write thresholds
german.PageThresholdTitle=PLwC-Schreibschwellen
english.PageThresholdDescription=Set governance thresholds
german.PageThresholdDescription=Governance-Schwellwerte festlegen
english.PageThresholdSubCaption=The safe defaults apply to all generated integrations.
german.PageThresholdSubCaption=Die sicheren Standardwerte gelten für alle erzeugten Integrationen.
english.FieldMemoryThreshold=Memory write threshold:
german.FieldMemoryThreshold=Speicher-Schreibschwelle:
english.FieldPersonaThreshold=Persona write threshold:
german.FieldPersonaThreshold=Persona-Schreibschwelle:
english.FieldTemperamentThreshold=Temperament write threshold:
german.FieldTemperamentThreshold=Temperament-Schreibschwelle:
english.PageFeatureTitle=PLwC runtime options
german.PageFeatureTitle=PLwC-Laufzeitoptionen
english.PageFeatureDescription=Enable optional runtime behavior
german.PageFeatureDescription=Optionale Laufzeitfunktionen aktivieren
english.PageFeatureSubCaption=Docker remains optional; Qdrant is disabled by default.
german.PageFeatureSubCaption=Docker bleibt optional; Qdrant ist standardmäßig deaktiviert.
english.OptionQdrant=Enable Qdrant indexing
german.OptionQdrant=Qdrant-Indexierung aktivieren
english.OptionPersonaDisabled=Disable persona layer
german.OptionPersonaDisabled=Persona-Layer deaktivieren
english.PrereqChecking=Checking this computer...
german.PrereqChecking=Dieser Computer wird geprüft...
english.PrereqIntro=Status for the current component selection:
german.PrereqIntro=Status für die aktuelle Komponentenauswahl:
english.PrereqAdminElevated=Administrator status: Setup is running with elevated rights. PLwC data remains in the current user profile.
german.PrereqAdminElevated=Administratorstatus: Setup wird mit erhöhten Rechten ausgeführt. Die PLwC-Daten bleiben im aktuellen Benutzerprofil.
english.PrereqAdminStandard=Administrator status: Setup is running for the current user. Windows will ask for approval before a system-wide Node.js or required Windows component is installed.
german.PrereqAdminStandard=Administratorstatus: Setup wird für den aktuellen Benutzer ausgeführt. Windows fragt vor einer systemweiten Node.js- oder erforderlichen Windows-Komponente nach einer Bestätigung.
english.PrereqOK=[OK]
german.PrereqOK=[OK]
english.PrereqActionRequired=[ACTION REQUIRED]
german.PrereqActionRequired=[AKTION ERFORDERLICH]
english.PrereqWarning=[WARNING]
german.PrereqWarning=[WARNUNG]
english.PrereqSafeMode=[SAFE MODE]
german.PrereqSafeMode=[ABGESICHERTER MODUS]
english.PrereqNotSelected=[NOT SELECTED]
german.PrereqNotSelected=[NICHT GEWÄHLT]
english.PrereqPrepared=[PREPARED]
german.PrereqPrepared=[VORBEREITET]
english.PrereqPath=Path: 
german.PrereqPath=Pfad: 
english.PrereqVersion=Version: 
german.PrereqVersion=Version: 
english.PrereqPythonOK=PLwC Gateway: Python 3.11 or newer is usable.
german.PrereqPythonOK=PLwC Gateway: Python 3.11 oder neuer ist verwendbar.
english.PrereqPythonMissing=PLwC Gateway: Python 3.11 or newer was not found.
german.PrereqPythonMissing=PLwC Gateway: Python 3.11 oder neuer wurde nicht gefunden.
english.PrereqVCRuntimeOK=PLwC Gateway: Microsoft Visual C++ runtime x64 is available.
german.PrereqVCRuntimeOK=PLwC Gateway: Die Microsoft-Visual-C++-Laufzeit x64 ist verfügbar.
english.PrereqVCRuntimeMissing=PLwC Gateway: Microsoft Visual C++ runtime x64 is missing; ONNX Runtime requires it on Windows.
german.PrereqVCRuntimeMissing=PLwC Gateway: Die Microsoft-Visual-C++-Laufzeit x64 fehlt; ONNX Runtime benötigt sie unter Windows.
english.PrereqMcpMissing=PLwC Gateway: required Python modules (mcp, qdrant-client, onnxruntime, fastembed) are missing or cannot be loaded.
german.PrereqMcpMissing=PLwC Gateway: Erforderliche Python-Module (mcp, qdrant-client, onnxruntime, fastembed) fehlen oder können nicht geladen werden.
english.PrereqMcpOK=PLwC Gateway: all required Python modules can be imported.
german.PrereqMcpOK=PLwC Gateway: Alle erforderlichen Python-Module können importiert werden.
english.PrereqDockerDesktopOK=Docker Desktop: installed.
german.PrereqDockerDesktopOK=Docker Desktop: installiert.
english.PrereqDockerDesktopMissing=Docker Desktop: not installed. PLwC can continue in Safe Mode.
german.PrereqDockerDesktopMissing=Docker Desktop: nicht installiert. PLwC kann im abgesicherten Modus fortfahren.
english.PrereqDockerOK=Docker: CLI, daemon and required images are available.
german.PrereqDockerOK=Docker: Kommandozeilenprogramm, Docker-Dienst und erforderliche Images sind verfügbar.
english.PrereqDockerCliMissing=Docker: CLI not found. PLwC will use Safe Mode; sandbox and document-worker operations are unavailable.
german.PrereqDockerCliMissing=Docker: Das Kommandozeilenprogramm fehlt. PLwC verwendet den abgesicherten Modus; Sandbox- und Dokument-Worker-Funktionen sind nicht verfügbar.
english.PrereqDockerDaemonMissing=Docker: CLI found, but the local daemon is not reachable. Installed Docker Desktop alone is not a running daemon. PLwC will use Safe Mode.
german.PrereqDockerDaemonMissing=Docker: Das Kommandozeilenprogramm wurde gefunden, aber der lokale Docker-Dienst ist nicht erreichbar. Ein installiertes Docker Desktop ist noch kein laufender Docker-Dienst. PLwC verwendet den abgesicherten Modus.
english.PrereqDockerFirstStart=Setup will start Docker Desktop after copying the PLwC files. Complete Docker's visible first-run terms and WSL setup; PLwC detects readiness without a restart.
german.PrereqDockerFirstStart=Setup startet Docker Desktop nach dem Kopieren der PLwC-Dateien. Schließen Sie die sichtbare Ersteinrichtung mit Docker-Lizenz und WSL ab; PLwC erkennt die Bereitschaft ohne Neustart.
english.PrereqDockerImagesMissing=Docker: required local images are missing. PLwC will use Safe Mode; sandbox and document-worker operations remain unavailable.
german.PrereqDockerImagesMissing=Docker: Erforderliche lokale Images fehlen. PLwC verwendet den abgesicherten Modus; Sandbox- und Dokument-Worker-Funktionen bleiben nicht verfügbar.
english.PrereqWsl2OK=WSL2: available for Docker Desktop.
german.PrereqWsl2OK=WSL2: für Docker Desktop verfügbar.
english.PrereqWsl2Missing=WSL2: not available or not configured yet. Docker Desktop may need Windows WSL setup; PLwC can continue in Safe Mode.
german.PrereqWsl2Missing=WSL2: nicht verfügbar oder noch nicht eingerichtet. Docker Desktop benötigt möglicherweise die Windows-WSL-Einrichtung; PLwC kann im abgesicherten Modus fortfahren.
english.PrereqVirtualizationOK=Virtualization: firmware capability is available.
german.PrereqVirtualizationOK=Virtualisierung: Firmware-Fähigkeit ist verfügbar.
english.PrereqVirtualizationMissing=Virtualization: firmware capability was not detected. Docker Desktop may not be usable; PLwC can continue in Safe Mode.
german.PrereqVirtualizationMissing=Virtualisierung: Firmware-Fähigkeit wurde nicht erkannt. Docker Desktop ist möglicherweise nicht nutzbar; PLwC kann im abgesicherten Modus fortfahren.
english.PrereqVmHostPhysical=Virtual machine: no VM host was detected.
german.PrereqVmHostPhysical=Virtuelle Maschine: kein VM-Host erkannt.
english.PrereqVmNestedOK=Virtual machine: nested virtualization appears available.
german.PrereqVmNestedOK=Virtuelle Maschine: Nested Virtualization scheint verfügbar zu sein.
english.PrereqVmNestedMissing=Virtual machine detected without nested virtualization. Enable nested virtualization in the host VM settings or use Safe Mode; Docker-backed sandbox and document-worker operations cannot run here.
german.PrereqVmNestedMissing=Virtuelle Maschine ohne Nested Virtualization erkannt. Aktivieren Sie Nested Virtualization in den VM-Einstellungen des Hosts oder verwenden Sie den abgesicherten Modus; Docker-basierte Sandbox- und Dokument-Worker-Funktionen können hier nicht laufen.
english.PrereqSafeModeExplanation=Safe Mode is installable: PLwC Gateway and STDIO snippets remain available; sandbox and document-worker operations stay disabled until Docker CLI, daemon, WSL2 and virtualization are ready.
german.PrereqSafeModeExplanation=Der abgesicherte Modus ist installierbar: PLwC Gateway und STDIO-Konfigurationsvorlagen bleiben verfügbar; Sandbox- und Dokument-Worker-Funktionen bleiben deaktiviert, bis Docker-Kommandozeile, Docker-Dienst, WSL2 und Virtualisierung bereit sind.
english.PrereqClaudeOK=Claude Desktop MCPB: Claude Desktop was detected.
german.PrereqClaudeOK=Claude Desktop MCPB: Claude Desktop wurde erkannt.
english.PrereqClaudeMissing=Claude Desktop MCPB: Claude Desktop was not found.
german.PrereqClaudeMissing=Claude Desktop MCPB: Claude Desktop wurde nicht gefunden.
english.PrereqClaudeNotSelected=Claude Desktop MCPB is not selected.
german.PrereqClaudeNotSelected=Claude Desktop MCPB ist nicht ausgewählt.
english.PrereqNodeOK=PLwC Chat Bridge: Node.js 22.12 or newer is usable.
german.PrereqNodeOK=PLwC Chat Bridge: Node.js 22.12 oder neuer ist verwendbar.
english.PrereqNodeMissing=PLwC Chat Bridge: Node.js 22.12 or newer was not found.
german.PrereqNodeMissing=PLwC Chat Bridge: Node.js 22.12 oder neuer wurde nicht gefunden.
english.PrereqBrowserOK=PLwC Chat Bridge: Chrome, Edge or Brave was detected.
german.PrereqBrowserOK=PLwC Chat Bridge: Chrome, Edge oder Brave wurde erkannt.
english.PrereqBrowserMissing=PLwC Chat Bridge: neither Chrome, Edge nor Brave was found.
german.PrereqBrowserMissing=PLwC Chat Bridge: Weder Chrome, Edge noch Brave wurde gefunden.
english.PrereqBridgeNotSelected=PLwC Chat Bridge is not selected.
german.PrereqBridgeNotSelected=PLwC Chat Bridge ist nicht ausgewählt.
english.PrereqCodexOK=Codex STDIO: Codex was detected; a snippet will be prepared without changing host configuration.
german.PrereqCodexOK=Codex STDIO: Codex wurde erkannt; eine Konfigurationsvorlage wird ohne Änderung der Zielanwendung vorbereitet.
english.PrereqCodexMissing=Codex STDIO: Codex was not found; only a prepared snippet will be created.
german.PrereqCodexMissing=Codex STDIO: Codex wurde nicht gefunden; es wird nur eine vorbereitete Konfigurationsvorlage erzeugt.
english.PrereqCodexNotSelected=Codex STDIO is not selected.
german.PrereqCodexNotSelected=Codex STDIO ist nicht ausgewählt.
english.PrereqOdysseusOK=Odysseus STDIO: Odysseus was detected; a snippet will be prepared without changing host configuration.
german.PrereqOdysseusOK=Odysseus STDIO: Odysseus wurde erkannt; eine Konfigurationsvorlage wird ohne Änderung der Zielanwendung vorbereitet.
english.PrereqOdysseusMissing=Odysseus STDIO: Odysseus was not found; only a prepared snippet will be created.
german.PrereqOdysseusMissing=Odysseus STDIO: Odysseus wurde nicht gefunden; es wird nur eine vorbereitete Konfigurationsvorlage erzeugt.
english.PrereqOdysseusNotSelected=Odysseus STDIO is not selected.
german.PrereqOdysseusNotSelected=Odysseus STDIO ist nicht ausgewählt.
english.PrereqGatePassed=All prerequisites are satisfied. You can continue with directory and profile setup.
german.PrereqGatePassed=Alle Voraussetzungen sind erfüllt. Die Verzeichnis- und Profileinrichtung kann fortgesetzt werden.
english.PrereqGateFailed=Setup needs attention. Install the missing software or go back and deselect the affected optional component.
german.PrereqGateFailed=Für die ausgewählten Komponenten fehlt noch erforderliche Software. Installieren Sie diese oder wählen Sie die betreffende optionale Komponente ab.
english.PrereqManualGateFailed=Before anything is downloaded or installed, resolve these selected-component requirements. Install the software, or click Back and deselect the affected component.
german.PrereqManualGateFailed=Bevor etwas heruntergeladen oder installiert wird, müssen diese Voraussetzungen der ausgewählten Komponenten erfüllt sein. Installieren Sie die Software oder gehen Sie zurück und wählen Sie die betreffende Komponente ab.
english.PrereqAcquisitionPlanIncomplete=Select automatic setup for every missing required prerequisite, install it through the official page and click Check again, or go back and deselect the affected optional component.
german.PrereqAcquisitionPlanIncomplete=Wählen Sie für jede fehlende Pflichtvoraussetzung die automatische Einrichtung, installieren Sie sie über die offizielle Seite und klicken Sie auf Erneut prüfen oder gehen Sie zurück und wählen Sie die betroffene optionale Komponente ab.
english.PrereqInstallFailed=Automatic prerequisite setup did not complete successfully. The status has been checked again.
german.PrereqInstallFailed=Die automatische Einrichtung der Voraussetzung wurde nicht erfolgreich abgeschlossen. Der Status wurde erneut geprüft.
english.PrereqUnexpectedFailure=An unexpected error occurred while checking or installing prerequisites. Setup has stopped this step without continuing.
german.PrereqUnexpectedFailure=Beim Prüfen oder Installieren der Voraussetzungen ist ein unerwarteter Fehler aufgetreten. Setup hat diesen Schritt beendet und nicht fortgesetzt.
english.PrereqUnexpectedPhase=Phase: 
german.PrereqUnexpectedPhase=Phase: 
english.PrereqUnexpectedDetails=Technical details: 
german.PrereqUnexpectedDetails=Technische Details: 
english.PrereqUnexpectedLog=Diagnostic log: 
german.PrereqUnexpectedLog=Diagnoseprotokoll: 
english.PrereqPhaseSelection=Update prerequisite selection
german.PrereqPhaseSelection=Voraussetzungsauswahl aktualisieren
english.PrereqPhaseRecheck=Check prerequisites again
german.PrereqPhaseRecheck=Voraussetzungen erneut prüfen
english.PrereqPhasePageCheck=Check prerequisites
german.PrereqPhasePageCheck=Voraussetzungen prüfen
english.PrereqPhaseInstall=Install selected prerequisites
german.PrereqPhaseInstall=Ausgewählte Voraussetzungen installieren
english.PrereqPhasePythonDownload=Download Python
german.PrereqPhasePythonDownload=Python herunterladen
english.PrereqPhasePythonPrepare=Prepare Python installation
german.PrereqPhasePythonPrepare=Python-Installation vorbereiten
english.PrereqPhasePythonInstall=Install Python
german.PrereqPhasePythonInstall=Python installieren
english.PrereqPhaseVCRuntimeDownload=Download Microsoft Visual C++ runtime
german.PrereqPhaseVCRuntimeDownload=Microsoft-Visual-C++-Laufzeit herunterladen
english.PrereqPhaseVCRuntimePrepare=Prepare Microsoft Visual C++ runtime installation
german.PrereqPhaseVCRuntimePrepare=Installation der Microsoft-Visual-C++-Laufzeit vorbereiten
english.PrereqPhaseVCRuntimeInstall=Install Microsoft Visual C++ runtime
german.PrereqPhaseVCRuntimeInstall=Microsoft-Visual-C++-Laufzeit installieren
english.PrereqPhasePythonModules=Install PLwC Python modules
german.PrereqPhasePythonModules=PLwC-Pythonmodule installieren
english.PrereqPhaseNodeDownload=Download Node.js
german.PrereqPhaseNodeDownload=Node.js herunterladen
english.PrereqPhaseNodePrepare=Prepare Node.js installation
german.PrereqPhaseNodePrepare=Node.js-Installation vorbereiten
english.PrereqPhaseNodeInstall=Install Node.js
german.PrereqPhaseNodeInstall=Node.js installieren
english.PrereqPhaseDockerDownload=Download Docker Desktop
german.PrereqPhaseDockerDownload=Docker Desktop herunterladen
english.PrereqPhaseDockerPrepare=Prepare Docker Desktop installation
german.PrereqPhaseDockerPrepare=Docker-Desktop-Installation vorbereiten
english.PrereqPhaseDockerInstall=Install Docker Desktop
german.PrereqPhaseDockerInstall=Docker Desktop installieren
english.PrereqPhaseFinalCheck=Final prerequisite check
german.PrereqPhaseFinalCheck=Abschließende Prüfung der Voraussetzungen
english.PrereqDownloadFailed=The verified download could not be completed for: 
german.PrereqDownloadFailed=Der geprüfte Download konnte für folgende Datei nicht abgeschlossen werden: 
english.PrereqDownloadDnsHint=Windows could not resolve the server name. Check the VM network, DNS and proxy settings.
german.PrereqDownloadDnsHint=Windows konnte den Servernamen nicht auflösen. Prüfen Sie Netzwerk, DNS und Proxy der VM.
english.PrereqDownloadRetryHint=The selection remains enabled. Correct the connection and click Next to retry, or use the corresponding official page.
german.PrereqDownloadRetryHint=Die Auswahl bleibt aktiviert. Korrigieren Sie die Verbindung und klicken Sie zum Wiederholen auf „Weiter“ oder verwenden Sie die entsprechende offizielle Seite.
english.PrereqCurlUnavailable=The Windows curl fallback is unavailable.
german.PrereqCurlUnavailable=Der Windows-curl-Ersatzdownload ist nicht verfügbar.
english.PrereqCurlFailed=The Windows curl fallback ended with code: 
german.PrereqCurlFailed=Der Windows-curl-Ersatzdownload endete mit Code: 
english.PrereqDownloadHashMismatch=The fallback download did not match the pinned SHA-256 value.
german.PrereqDownloadHashMismatch=Der Ersatzdownload entspricht nicht dem festgelegten SHA-256-Wert.
english.PrereqOpenPageFailed=The official download page could not be opened.
german.PrereqOpenPageFailed=Die offizielle Downloadseite konnte nicht geöffnet werden.
english.PrereqPythonInstallFailed=Python or the PLwC Python modules could not be installed.
german.PrereqPythonInstallFailed=Python oder die PLwC-Pythonmodule konnten nicht installiert werden.
english.PrereqVCRuntimeInstallFailed=The Microsoft Visual C++ runtime could not be installed.
german.PrereqVCRuntimeInstallFailed=Die Microsoft-Visual-C++-Laufzeit konnte nicht installiert werden.
english.PrereqNodeInstallFailed=Node.js could not be installed.
german.PrereqNodeInstallFailed=Node.js konnte nicht installiert werden.
english.PrereqDockerInstallFailed=Docker Desktop could not be installed. PLwC can continue in Safe Mode.
german.PrereqDockerInstallFailed=Docker Desktop konnte nicht installiert werden. PLwC kann im abgesicherten Modus fortfahren.
english.PrereqFailureComponent=Component: 
german.PrereqFailureComponent=Komponente: 
english.PrereqFailureExitCode=Exit code: 
german.PrereqFailureExitCode=Exitcode: 
english.PrereqFailureLog=Diagnostic log: 
german.PrereqFailureLog=Diagnoseprotokoll: 
english.PrereqComponentPython=Python 3.13
german.PrereqComponentPython=Python 3.13
english.PrereqComponentPythonModules=PLwC Python modules
german.PrereqComponentPythonModules=PLwC-Pythonmodule
english.PrereqComponentPythonBundle=Python 3.13 / PLwC Python modules
german.PrereqComponentPythonBundle=Python 3.13 / PLwC-Pythonmodule
english.PrereqComponentVCRuntime=Microsoft Visual C++ runtime x64 14.51.36247
german.PrereqComponentVCRuntime=Microsoft-Visual-C++-Laufzeit x64 14.51.36247
english.PrereqComponentNode=Node.js 24 LTS
german.PrereqComponentNode=Node.js 24 LTS
english.PrereqComponentDocker=Docker Desktop
german.PrereqComponentDocker=Docker Desktop
english.PrereqFailureUacCancelled=The administrator confirmation or installation was cancelled.
german.PrereqFailureUacCancelled=Die Administratorbestätigung oder Installation wurde abgebrochen.
english.PrereqFailurePath=Windows could not resolve the elevated installer path. The prerequisite was not started.
german.PrereqFailurePath=Windows konnte den erhöhten Installationspfad nicht auflösen. Die Voraussetzung wurde nicht gestartet.
english.PrereqFailureBusy=Another Windows Installer operation is running. Wait until it finishes and then retry.
german.PrereqFailureBusy=Eine andere Windows-Installer-Aktion wird ausgeführt. Warten Sie, bis sie beendet ist, und versuchen Sie es erneut.
english.PrereqFailureFatal=The vendor installer reported a fatal error. Review the diagnostic log for details.
german.PrereqFailureFatal=Das Herstellerprogramm meldete einen schwerwiegenden Fehler. Prüfen Sie das Diagnoseprotokoll.
english.PrereqFailureLaunch=The vendor installer could not be started.
german.PrereqFailureLaunch=Das Herstellerprogramm konnte nicht gestartet werden.
english.PrereqFailureNotDetected=The installer returned success, but the prerequisite is still not available.
german.PrereqFailureNotDetected=Das Installationsprogramm meldete Erfolg, aber die Voraussetzung ist weiterhin nicht verfügbar.
english.PrereqFailureNextPython=Retry with Next or open the official Python and Microsoft Visual C++ download pages.
german.PrereqFailureNextPython=Versuchen Sie es mit „Weiter“ erneut oder öffnen Sie die offiziellen Downloadseiten für Python und Microsoft Visual C++.
english.PrereqFailureNextVCRuntime=Retry with Next or open the official Microsoft Visual C++ download page.
german.PrereqFailureNextVCRuntime=Versuchen Sie es mit „Weiter“ erneut oder öffnen Sie die offizielle Microsoft-Seite für Visual C++.
english.PrereqFailureNextNode=Approve the Windows administrator prompt, then retry with Next, or open the official Node.js page.
german.PrereqFailureNextNode=Bestätigen Sie die Windows-Administratorabfrage und versuchen Sie es mit „Weiter“ erneut oder öffnen Sie die offizielle Node.js-Seite.
english.PrereqFailureNextDocker=Retry with Next, use Safe Mode, or open the official Docker page.
german.PrereqFailureNextDocker=Versuchen Sie es mit „Weiter“ erneut, verwenden Sie den abgesicherten Modus oder öffnen Sie die offizielle Docker-Seite.
english.PrereqRestartRequired=A Windows restart is required to finish prerequisite setup. No further prerequisites or PLwC files will be installed now. Close Setup and restart Windows before trying again.
german.PrereqRestartRequired=Zum Abschließen der Einrichtung ist ein Windows-Neustart erforderlich. Es werden jetzt keine weiteren Voraussetzungen oder PLwC-Dateien installiert. Schließen Sie den Assistenten und starten Sie Windows neu, bevor Sie es erneut versuchen.
english.ErrorPathsRequired=Application, Gateway and Chat Bridge directories must be specified.
german.ErrorPathsRequired=App-, Gateway- und Chat-Bridge-Verzeichnisse müssen angegeben werden.
english.ErrorRuntimeChildren=Gateway and Chat Bridge must be separate subdirectories of the application directory.
german.ErrorRuntimeChildren=Gateway und Chat Bridge müssen getrennte Unterverzeichnisse des App-Verzeichnisses sein.
english.ErrorRuntimeOverlap=Gateway and Chat Bridge must not be identical or nested.
german.ErrorRuntimeOverlap=Gateway und Chat Bridge dürfen nicht identisch sein oder ineinander liegen.
english.ErrorDataRequired=This directory must be specified: 
german.ErrorDataRequired=Dieses Verzeichnis muss angegeben werden: 
english.ErrorDataInApp=This data directory must not be inside the application directory or contain it: 
german.ErrorDataInApp=Dieses Datenverzeichnis darf nicht im App-Verzeichnis liegen oder dieses enthalten: 
english.ErrorDataOverlap=These directories must be separate and not nested: 
german.ErrorDataOverlap=Diese Verzeichnisse müssen getrennt sein und dürfen nicht ineinander liegen: 
english.ErrorProfileName=The profile name may contain only letters, digits, dots, hyphens and underscores.
german.ErrorProfileName=Der Profilname darf nur Buchstaben, Ziffern, Punkt, Bindestrich und Unterstrich enthalten.
english.ErrorSecurityFile=The specified security configuration file was not found.
german.ErrorSecurityFile=Der angegebene Pfad zur Sicherheitskonfiguration wurde nicht als Datei gefunden.
english.ErrorThresholds=All three thresholds must be integers between 0 and 100.
german.ErrorThresholds=Die drei Schreibschwellen müssen ganze Zahlen zwischen 0 und 100 sein.
english.ErrorCreateDir=Directory could not be created: 
german.ErrorCreateDir=Verzeichnis konnte nicht erstellt werden: 
english.ErrorStoreDirs=The selected installer directories could not be stored.
german.ErrorStoreDirs=Die ausgewählten Installer-Verzeichnisse konnten nicht gespeichert werden.
english.ErrorCodexSnippet=The Codex snippet could not be written.
german.ErrorCodexSnippet=Die Codex-Konfigurationsvorlage konnte nicht geschrieben werden.
english.ErrorOdysseusSnippet=The Odysseus snippet could not be written.
german.ErrorOdysseusSnippet=Die Odysseus-Konfigurationsvorlage konnte nicht geschrieben werden.
english.ErrorBridgeConfig=The Chat Bridge configuration could not be written.
german.ErrorBridgeConfig=Die Chat-Bridge-Konfiguration konnte nicht geschrieben werden.
english.ErrorSummary=The installation summary could not be written.
english.ErrorSetupHash=The SHA-256 identity of the running setup executable could not be determined.
german.ErrorSetupHash=Die SHA-256-Identität der laufenden Setup-Datei konnte nicht ermittelt werden.
english.ErrorDiagnostic=The installer diagnostic record could not be written.
german.ErrorDiagnostic=Der Installer-Diagnoseeintrag konnte nicht geschrieben werden.
german.ErrorSummary=Die Installationsübersicht konnte nicht geschrieben werden.
english.ErrorNativeManifest=The Native Messaging manifest could not be written.
german.ErrorNativeManifest=Das Native-Messaging-Manifest konnte nicht geschrieben werden.
english.ErrorChromeNative=Chrome Native Messaging could not be registered.
german.ErrorChromeNative=Chrome Native Messaging konnte nicht registriert werden.
english.ErrorEdgeNative=Edge Native Messaging could not be registered.
german.ErrorEdgeNative=Edge Native Messaging konnte nicht registriert werden.
english.ErrorNativeHostMissing=The Native Messaging launcher is missing from the installed Chat Bridge: 
german.ErrorNativeHostMissing=Der Native-Messaging-Launcher fehlt in der installierten Chat Bridge: 
english.LogNativeHostMissing=Native Messaging was not registered because the host executable is missing: 
german.LogNativeHostMissing=Native Messaging wurde nicht registriert, weil die Host-EXE fehlt: 
english.BridgeIntegrationStatus=Registering Native Messaging and starting the Chat Bridge...
german.BridgeIntegrationStatus=Native Messaging wird registriert und die Chat Bridge wird gestartet...
english.ErrorBridgeIntegration=Chat Bridge postflight did not confirm the native launcher, startup shortcut, exact build identity and 8 of 8 tools. Setup was not completed. Review %LOCALAPPDATA%\PLwC\logs\setup\installer-diagnostic.log and %APPDATA%\PLwC\logs\chat-bridge\native-launcher.log. Exit code:
german.ErrorBridgeIntegration=Der Chat-Bridge-Abschlusstest hat Native Launcher, Autostart-Verknüpfung, exakte Buildidentität und 8 von 8 Werkzeugen nicht bestätigt. Setup wurde nicht abgeschlossen. Prüfen Sie %LOCALAPPDATA%\PLwC\logs\setup\installer-diagnostic.log und %APPDATA%\PLwC\logs\chat-bridge\native-launcher.log. Exitcode:
english.ReadyBridgeAutostart=Chat Bridge: start automatically at every Windows sign-in
german.ReadyBridgeAutostart=Chat Bridge: automatischer Start bei jeder Windows-Anmeldung
english.ReadyRuntime=PLwC runtime:
german.ReadyRuntime=PLwC-Laufzeit:
english.ReadyData=PLwC data:
german.ReadyData=PLwC-Daten:
english.ReadyProfile=Active profile: 
german.ReadyProfile=Aktives Profil: 
english.ReadySecurity=Security configuration: 
german.ReadySecurity=Sicherheitskonfiguration: 
english.ReadyThresholds=Thresholds Memory/Persona/Temperament: 
german.ReadyThresholds=Schreibschwellen Speicher/Persona/Temperament: 
english.ReadyQdrant=Qdrant enabled: 
german.ReadyQdrant=Qdrant aktiviert: 
english.ReadyPersona=Persona layer disabled: 
german.ReadyPersona=Persona-Layer deaktiviert: 
english.ReadySafeMode=Safe Mode expected: 
german.ReadySafeMode=Abgesicherter Modus erwartet: 
english.ValueYes=Yes
german.ValueYes=Ja
english.ValueNo=No
german.ValueNo=Nein
english.ReadyHostConfig=Host configurations:
german.ReadyHostConfig=Konfigurationen der Zielanwendungen:
english.ReadySnippets=Codex/Odysseus: prepared snippets only
german.ReadySnippets=Codex/Odysseus: nur vorbereitete Konfigurationsvorlagen
english.ReadyClaude=Claude Desktop: existing configuration remains unchanged
german.ReadyClaude=Claude Desktop: vorhandene Konfiguration bleibt unangetastet
english.ReadyNativeStable=Native Messaging: automatic Chrome, Edge and Brave registration for stable extension ID 
german.ReadyNativeStable=Native Messaging: automatische Chrome-, Edge- und Brave-Registrierung für die stabile Erweiterungs-ID 
english.SummaryTitle=PLwC installation
german.SummaryTitle=PLwC Installation
english.SummaryBuildIdentity=Build identity:
german.SummaryBuildIdentity=Buildidentität:
english.SummaryBuildId=Build ID: 
german.SummaryBuildId=Build-ID: 
english.SummaryInstallerRevision=Installer revision: 
german.SummaryInstallerRevision=Installer-Revision: 
english.SummarySetupSha256=Setup EXE SHA-256: 
german.SummarySetupSha256=SHA-256 der Setup-EXE: 
english.SummaryGatewayVersion=Gateway version: 
german.SummaryGatewayVersion=Gateway-Version: 
english.SummaryNodeBridgeVersion=Node Bridge version: 
german.SummaryNodeBridgeVersion=Node-Bridge-Version: 
english.SummaryBrowserExtensionVersion=Browser Extension version: 
german.SummaryBrowserExtensionVersion=Browser-Extension-Version: 
english.SummaryNativeLauncherVersion=Native Launcher version: 
german.SummaryNativeLauncherVersion=Native-Launcher-Version: 
english.SummaryInstallationMode=Installation mode: 
german.SummaryInstallationMode=Installationsmodus: 
english.SummarySelectedComponentIds=Selected component IDs: 
german.SummarySelectedComponentIds=Ausgewählte Komponenten-IDs: 
english.SummaryApp=Application: 
german.SummaryApp=App: 
english.SummaryGateway=Gateway: 
german.SummaryGateway=Gateway: 
english.SummaryChatBridge=Chat Bridge: 
german.SummaryChatBridge=Chat Bridge: 
english.SummaryWorkspace=Workspace: 
german.SummaryWorkspace=Arbeitsbereich: 
english.SummaryProfiles=Profiles: 
german.SummaryProfiles=Profile: 
english.SummaryConfig=Configuration: 
german.SummaryConfig=Konfiguration: 
english.SummaryState=State: 
german.SummaryState=Status: 
english.SummaryLogs=Logs: 
german.SummaryLogs=Protokolle: 
english.SummaryBackups=Backups: 
german.SummaryBackups=Sicherungen: 
english.SummaryMemoryThreshold=Memory threshold: 
german.SummaryMemoryThreshold=Speicher-Schreibschwelle: 
english.SummaryPersonaThreshold=Persona threshold: 
german.SummaryPersonaThreshold=Persona-Schreibschwelle: 
english.SummaryTemperamentThreshold=Temperament threshold: 
german.SummaryTemperamentThreshold=Temperament-Schreibschwelle: 
english.SummaryQdrant=Qdrant enabled: 
german.SummaryQdrant=Qdrant aktiviert: 
english.SummaryPersonaDisabled=Persona layer disabled: 
german.SummaryPersonaDisabled=Persona-Layer deaktiviert: 
english.SummarySafeMode=Safe Mode expected: 
german.SummarySafeMode=Abgesicherter Modus erwartet: 
english.SummaryPrerequisites=Prerequisite check:
german.SummaryPrerequisites=Voraussetzungsprüfung:
english.SummaryComponents=Components:
german.SummaryComponents=Komponenten:
english.SummaryActiveProfile=Active profile: 
german.SummaryActiveProfile=Aktives Profil: 
english.SummarySecurity=Security configuration: 
german.SummarySecurity=Sicherheitskonfiguration: 
english.SummaryCodexSnippet=Codex snippet: 
german.SummaryCodexSnippet=Codex-Konfigurationsvorlage: 
english.SummaryOdysseusSnippet=Odysseus snippet: 
german.SummaryOdysseusSnippet=Odysseus-Konfigurationsvorlage: 
english.SummaryClaudeFolder=Claude MCPB folder: 
german.SummaryClaudeFolder=Claude-MCPB-Ordner: 
english.SummaryBridgeFolder=Chat Bridge folder: 
german.SummaryBridgeFolder=Chat-Bridge-Ordner: 
english.SummaryBridgeConfig=Chat Bridge configuration: 
german.SummaryBridgeConfig=Chat-Bridge-Konfiguration: 
english.SummaryNativeStable=Chrome, Edge and Brave Native Messaging: registered for stable extension ID 
german.SummaryNativeStable=Chrome, Edge und Brave Native Messaging: registriert für die stabile Erweiterungs-ID 
english.SummaryBridgeAutostart=Chat Bridge autostart: enabled for the current Windows user
german.SummaryBridgeAutostart=Chat-Bridge-Autostart: für den aktuellen Windows-Benutzer aktiviert
english.SummaryHostUnchanged=Note: Existing Claude, Codex and Odysseus configurations were not changed.
german.SummaryHostUnchanged=Hinweis: Bestehende Claude-, Codex- und Odysseus-Konfigurationen wurden nicht verändert.
english.SummaryDataRemain=Workspace and profile data remain after uninstall.
german.SummaryDataRemain=Arbeitsbereichs- und Profildaten bleiben bei einer Deinstallation erhalten.
english.SummaryDevPayload=Development build: stage\gateway\server.py was not present in the payload.
german.SummaryDevPayload=Entwicklungsversion: stage\gateway\server.py war nicht im Installationspaket vorhanden.
english.SummaryPythonPlaceholder=Python 3.11+ was not found; STDIO snippets contain a visible placeholder.
german.SummaryPythonPlaceholder=Python 3.11+ wurde nicht gefunden; die STDIO-Snippets enthalten einen sichtbaren Platzhalter.
english.SnippetPreparedComment=Prepared by PLwC Setup. Existing host configuration was not changed.
german.SnippetPreparedComment=Vom PLwC-Installationsprogramm vorbereitet. Die bestehende Konfiguration der Zielanwendung wurde nicht verändert.
english.ReadyUpdateMode=Existing PLwC installation detected. Stored folders and settings are reused for this update.
german.ReadyUpdateMode=Vorhandene PLwC-Installation erkannt. Gespeicherte Ordner und Einstellungen werden für dieses Update wiederverwendet.
english.ErrorSharedSync=Setup could not synchronize the shared PLwC settings. Exit code:
german.ErrorSharedSync=Setup konnte die gemeinsamen PLwC-Einstellungen nicht synchronisieren. Rückgabecode:
english.InstallerMigrationStatus=Securing the existing PLwC runtime and checking the migration plan...
german.InstallerMigrationStatus=Vorhandene PLwC-Laufzeit wird gesichert und der Migrationsplan geprüft...
english.InstallerPostflightStatus=Verifying the complete r26 installation...
german.InstallerPostflightStatus=Die vollständige r26-Installation wird geprüft...
english.ErrorInstallerPreflight=The r26 preflight or migration preparation failed. No foreign process was stopped. Review the diagnostic report:
german.ErrorInstallerPreflight=Der r26-Preflight oder die Migrationsvorbereitung ist fehlgeschlagen. Es wurde kein fremder Prozess beendet. Prüfen Sie den Diagnosebericht:
english.ErrorInstallerPostflight=The mandatory r26 postflight failed; Setup will not report success and attempted to restore the previous application runtime. Review the diagnostic report:
german.ErrorInstallerPostflight=Der verbindliche r26-Postflight ist fehlgeschlagen; Setup meldet keinen Erfolg und hat versucht, die vorherige Anwendungslaufzeit wiederherzustellen. Prüfen Sie den Diagnosebericht:

[Types]
Name: "compact"; Description: "{cm:TypeGatewayOnly}"
Name: "full"; Description: "{cm:TypeFull}"
Name: "custom"; Description: "{cm:TypeCustom}"; Flags: iscustom

[Components]
Name: "gateway"; Description: "{cm:ComponentGateway}"; Types: full compact custom; Flags: fixed
#if McpbAvailable == "1"
Name: "claude"; Description: "{cm:ComponentClaude}"; Types: full
#endif
Name: "codex"; Description: "{cm:ComponentCodex}"; Types: full
Name: "odysseus"; Description: "{cm:ComponentOdysseus}"; Types: full
Name: "chatbridge"; Description: "{cm:ComponentChatBridge}"; Types: full

[Files]
Source: "assets\mcp-runtime-lock.txt"; Flags: dontcopy
Source: "assets\python-runtime-probe.py"; Flags: dontcopy
Source: "assets\installer-maintenance.py"; Flags: dontcopy
Source: "..\..\src\plwc_gateway\installation\installer_state.py"; Flags: dontcopy
Source: "..\..\src\plwc_gateway\installation\doctor.py"; Flags: dontcopy
Source: "{#StageDir}\common\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: gateway
Source: "{#StageDir}\gateway\*"; DestDir: "{code:GetGatewayPath}"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: gateway
#if McpbAvailable == "1"
Source: "{#StageDir}\claude\*"; DestDir: "{app}\packages"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: claude
#endif
Source: "{#StageDir}\codex\*"; DestDir: "{app}\clients\codex"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: codex
Source: "{#StageDir}\odysseus\*"; DestDir: "{app}\clients\odysseus"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: odysseus
Source: "{#StageDir}\chat-bridge\*"; DestDir: "{code:GetBridgePath}"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: chatbridge
Source: "{#StageDir}\payload-manifest.json"; DestDir: "{app}\installation"; Flags: ignoreversion

[Dirs]
Name: "{code:GetWorkspacePath}"; Flags: uninsneveruninstall
Name: "{code:GetProfilesPath}"; Flags: uninsneveruninstall
Name: "{code:GetConfigPath}"; Flags: uninsneveruninstall
Name: "{code:GetStatePath}"; Flags: uninsneveruninstall
Name: "{code:GetLogsPath}"; Flags: uninsneveruninstall
Name: "{code:GetBackupsPath}"; Flags: uninsneveruninstall

[InstallDelete]
Type: files; Name: "{userdesktop}\PLwC Konfiguration.lnk"
Type: files; Name: "{userdesktop}\PLwC configuration.lnk"
Type: files; Name: "{userdesktop}\PLwC-Konfiguration.lnk"
Type: files; Name: "{userstartup}\PLwC Chat Bridge.lnk"

[Icons]
Name: "{group}\{cm:IconGettingStarted}"; Filename: "{code:GetConfigurationPythonPath}"; Parameters: "{code:GetGettingStartedArguments}"; WorkingDir: "{app}\configuration"; IconFilename: "{app}\configuration\plwc.ico"; Check: GettingStartedUiExists
Name: "{group}\{cm:IconSummary}"; Filename: "{sys}\notepad.exe"; Parameters: """{code:GetInstallSummaryPath}"""
Name: "{group}\{cm:IconConfig}"; Filename: "{code:GetConfigurationPythonPath}"; Parameters: "{code:GetConfigurationArguments}"; WorkingDir: "{app}\configuration"; IconFilename: "{app}\configuration\plwc.ico"
Name: "{userdesktop}\{cm:IconDesktopConfig}"; Filename: "{code:GetConfigurationPythonPath}"; Parameters: "{code:GetConfigurationArguments}"; WorkingDir: "{app}\configuration"; IconFilename: "{app}\configuration\plwc.ico"; Check: ConfigurationUiExists
Name: "{group}\{cm:IconConfigFolder}"; Filename: "{sys}\explorer.exe"; Parameters: """{code:GetConfigPath}"""
Name: "{group}\{cm:IconUninstall}"; Filename: "{uninstallexe}"
Name: "{userstartup}\PLwC Chat Bridge"; Filename: "{code:GetNativeHostExePathConstant}"; Parameters: "{code:GetBridgeAutostartArguments}"; WorkingDir: "{code:GetBridgePath}"; IconFilename: "{app}\configuration\plwc.ico"; Flags: runminimized; Components: chatbridge

[Run]
Filename: "{code:GetConfigurationPythonPath}"; Parameters: "{code:GetGettingStartedArguments}"; WorkingDir: "{app}\configuration"; Description: "{cm:RunOpenGettingStarted}"; Flags: postinstall nowait skipifsilent; Check: GettingStartedUiExists
Filename: "{code:GetConfigurationPythonPath}"; Parameters: "{code:GetConfigurationArguments}"; WorkingDir: "{app}\configuration"; Description: "{cm:RunOpenConfiguration}"; Flags: postinstall nowait skipifsilent unchecked; Check: ConfigurationUiExists
Filename: "{sys}\notepad.exe"; Parameters: """{code:GetInstallSummaryPath}"""; Description: "{cm:RunOpenSummary}"; Flags: postinstall nowait skipifsilent unchecked; Check: InstallSummaryExists
Filename: "{sys}\explorer.exe"; Parameters: """{code:GetClaudeFolder}"""; Description: "{cm:RunOpenClaude}"; Flags: postinstall nowait skipifsilent unchecked; Check: ShouldOfferClaudeFolder
Filename: "{sys}\notepad.exe"; Parameters: """{code:GetCodexSnippetPath}"""; Description: "{cm:RunOpenCodex}"; Flags: postinstall nowait skipifsilent unchecked; Check: ShouldOfferCodexSnippet
Filename: "{sys}\notepad.exe"; Parameters: """{code:GetOdysseusSnippetPath}"""; Description: "{cm:RunOpenOdysseus}"; Flags: postinstall nowait skipifsilent unchecked; Check: ShouldOfferOdysseusSnippet
Filename: "{sys}\explorer.exe"; Parameters: """{code:GetExtensionFolder}"""; Description: "{cm:RunOpenExtension}"; Flags: postinstall nowait skipifsilent unchecked; Check: ShouldOfferExtensionFolder

[Code]
const
  ChatBridgeExtensionId = '{#StableChatBridgeExtensionId}';
  InstallerSettingsKey = 'Software\PLwC\Installer';
  AppModelPackagesKey = 'Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages';
  WaitObject0 = 0;
  WaitTimeout = 258;
  SeeMaskNoCloseProcess = 64;
  { Cold imports of onnxruntime/fastembed exceeded 30 seconds in the clean-VM gate. }
  PythonRuntimeProbeTimeoutMilliseconds = 120000;
#ifdef UiSmokeDownloadFixture
  PythonInstallerUrl = '{#UiSmokeDownloadUrl}';
  PythonInstallerFileName = '{#UiSmokeDownloadFileName}';
  PythonInstallerSha256 = '{#UiSmokeDownloadSha256}';
#else
  PythonInstallerUrl = 'https://www.python.org/ftp/python/3.13.14/python-3.13.14-amd64.exe';
  PythonInstallerFileName = 'python-3.13.14-amd64.exe';
  PythonInstallerSha256 = 'c54d9b9bbb8a36e6489363ddd01139707fd781d72f1f9e90c7ec65d0061368e0';
#endif
  PythonDownloadPageUrl = 'https://www.python.org/downloads/windows/';
  VCRuntimeInstallerUrl = 'https://aka.ms/vs/18/release/14.51.36247/VC_redist.x64.exe';
  VCRuntimeInstallerFileName = 'VC_redist.x64-14.51.36247.exe';
  VCRuntimeInstallerSha256 = '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c';
  VCRuntimeDownloadPageUrl = 'https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist';
  NodeInstallerUrl = 'https://nodejs.org/dist/v24.18.0/node-v24.18.0-x64.msi';
  NodeInstallerFileName = 'node-v24.18.0-x64.msi';
  NodeInstallerSha256 = 'e30cd4ca15529583afe0efc978f1ae3ab3a93c2400c222d0752d17900552ebb3';
  NodeDownloadPageUrl = 'https://nodejs.org/en/download';
  DockerInstallerUrl = 'https://desktop.docker.com/win/main/amd64/233772/Docker%20Desktop%20Installer.exe';
  DockerInstallerFileName = 'Docker Desktop Installer-4.82.0.exe';
  DockerInstallerSha256 = 'a5b5837542f2f57fadbb09db90a60c84f8efc0a65f8d6dcd2e5b9fca3a2b87e6';
  DockerDownloadPageUrl = 'https://docs.docker.com/desktop/setup/install/windows-install/';
type
  TShellExecuteInfo = record
    cbSize: LongWord;
    fMask: LongWord;
    Wnd: HWND;
    lpVerb: String;
    lpFile: String;
    lpParameters: String;
    lpDirectory: String;
    nShow: Integer;
    hInstApp: THandle;
    lpIDList: LongWord;
    lpClass: String;
    hkeyClass: THandle;
    dwHotKey: LongWord;
    hMonitor: THandle;
    hProcess: THandle;
  end;

function WaitNamedPipe(
  PipeName: String; TimeoutMilliseconds: LongWord): BOOL;
  external 'WaitNamedPipeW@kernel32.dll stdcall';
function ShellExecuteEx(var ExecInfo: TShellExecuteInfo): BOOL;
  external 'ShellExecuteExW@shell32.dll stdcall';
function WaitForSingleObject(Handle: THandle; Milliseconds: LongWord): LongWord;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function GetExitCodeProcess(Handle: THandle; var ExitCode: LongWord): BOOL;
  external 'GetExitCodeProcess@kernel32.dll stdcall';
function TerminateProcess(Handle: THandle; ExitCode: LongWord): BOOL;
  external 'TerminateProcess@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): BOOL;
  external 'CloseHandle@kernel32.dll stdcall';

var
  PrerequisitesPage: TOutputMsgMemoWizardPage;
  PrerequisiteActionsPage: TInputOptionWizardPage;
  DependencyDownloadPage: TDownloadWizardPage;
  DependencyInstallPage: TOutputMarqueeProgressWizardPage;
  PythonDownloadButton: TNewButton;
  NodeDownloadButton: TNewButton;
  DockerDownloadButton: TNewButton;
  RecheckPrerequisitesButton: TNewButton;
  PrerequisiteActionStatusLabel: TNewStaticText;
  PrerequisiteSizeMemo: TNewMemo;
  RuntimeDirsPage: TInputDirWizardPage;
  DataDirsPage: TInputDirWizardPage;
  OperatingDirsPage: TInputDirWizardPage;
  ProfilePage: TInputQueryWizardPage;
  RuntimeSettingsPage: TInputQueryWizardPage;
  RuntimeOptionsPage: TInputOptionWizardPage;
  LastAppRoot: String;
  PrerequisiteReport: String;
  PrerequisiteBlockers: String;
  PrerequisiteManualBlockers: String;
  DetectedPythonPath: String;
  DetectedDockerPath: String;
  DetectedDockerDesktopPath: String;
  DetectedNodePath: String;
  DetectedClaudePath: String;
  DetectedBrowserPath: String;
  DetectedChromePath: String;
  DetectedEdgePath: String;
  DetectedBravePath: String;
  DetectedCodexPath: String;
  DetectedOdysseusPath: String;
  PythonDetected: Boolean;
  PythonVersionOK: Boolean;
  PythonRuntimeOK: Boolean;
  VCRuntimeOK: Boolean;
  DetectedVCRuntimeVersion: String;
  DockerDesktopInstalled: Boolean;
  DockerCliOK: Boolean;
  DockerDaemonOK: Boolean;
  DockerImagesOK: Boolean;
  DockerInstalledBySetup: Boolean;
  Wsl2OK: Boolean;
  VirtualizationCapabilityOK: Boolean;
  VirtualMachineDetected: Boolean;
  NestedVirtualizationOK: Boolean;
  NodeVersionOK: Boolean;
  ClaudeDetected: Boolean;
  BrowserDetected: Boolean;
  ChromeDetected: Boolean;
  EdgeDetected: Boolean;
  BraveDetected: Boolean;
  CodexDetected: Boolean;
  OdysseusDetected: Boolean;
  DependencyRestartRequired: Boolean;
  VCRuntimeRepairAttempted: Boolean;
  PrerequisiteAcquisitionFailed: Boolean;
  PrerequisiteOperationBusy: Boolean;
  PrerequisiteBatchActive: Boolean;
  PrerequisiteBatchPlan: String;
  CurrentPrerequisitePhase: String;
  DefaultNextButtonCaption: String;
  SetupExeSha256: String;
  ExistingInstallDetected: Boolean;
  ExistingSettingsComplete: Boolean;
  LegacyBridgePath: String;
  InstallerMigrationTransactionPath: String;
  InstallerPreflightReportPath: String;
  InstallerPostflightReportPath: String;
  InstallerRollbackReportPath: String;
  InstallerMigrationPrepared: Boolean;
  InstallerRollbackAttempted: Boolean;
  InstallerInstallationCompleted: Boolean;
  InstallerFailureExitCode: Integer;

function GetDataRoot: String;
begin
  Result := ExpandConstant('{userappdata}\PLwC');
end;

function GetAppPath: String;
begin
  if RuntimeDirsPage <> nil then
    Result := RuntimeDirsPage.Values[0]
  else
    Result := ExpandConstant('{app}');
end;

function ReadStoredPath(ValueName, DefaultValue: String): String;
var
  StoredValue: String;
  StoredConfigPath: String;
  SelectionPath: String;
begin
  StoredConfigPath := '';
  RegQueryStringValue(HKCU, InstallerSettingsKey, 'ConfigPath', StoredConfigPath);
  if Trim(StoredConfigPath) <> '' then
    SelectionPath := RemoveBackslashUnlessRoot(StoredConfigPath) + '\installer\selection.ini'
  else
    SelectionPath := GetDataRoot + '\config\installer\selection.ini';
  if not FileExists(SelectionPath) then
    SelectionPath := GetDataRoot + '\config\installer\selection.ini';

  StoredValue := GetIniString('PLwC', ValueName, '', SelectionPath);
  if Trim(StoredValue) <> '' then
    Result := StoredValue
  else if RegQueryStringValue(HKCU, InstallerSettingsKey, ValueName, StoredValue) and
          (Trim(StoredValue) <> '') then
    Result := StoredValue
  else
    Result := DefaultValue;
end;

function GetStoredSelectionPath: String;
var
  StoredConfigPath: String;
begin
  StoredConfigPath := '';
  RegQueryStringValue(HKCU, InstallerSettingsKey, 'ConfigPath', StoredConfigPath);
  if Trim(StoredConfigPath) = '' then
    StoredConfigPath := GetDataRoot + '\config';
  Result := RemoveBackslashUnlessRoot(StoredConfigPath) + '\installer\selection.ini';
end;

function ReadStoredSetting(ValueName, DefaultValue: String): String;
var
  StoredValue: String;
begin
  StoredValue := GetIniString('PLwC', ValueName, '', GetStoredSelectionPath);
  if Trim(StoredValue) <> '' then
    Result := StoredValue
  else
    Result := DefaultValue;
end;

function ReadStoredBoolean(ValueName: String; DefaultValue: Boolean): Boolean;
var
  StoredValue: String;
begin
  StoredValue := Lowercase(Trim(ReadStoredSetting(ValueName, '')));
  if StoredValue = 'true' then
    Result := True
  else if StoredValue = 'false' then
    Result := False
  else
    Result := DefaultValue;
end;

function DetectExistingInstall: Boolean;
var
  StoredAppPath: String;
begin
  StoredAppPath := ReadStoredPath('AppPath', '');
  Result := FileExists(GetStoredSelectionPath) or
    ((StoredAppPath <> '') and DirExists(StoredAppPath));
end;

function HasCompleteExistingSettings: Boolean;
begin
  Result :=
    (ReadStoredPath('AppPath', '') <> '') and
    (ReadStoredPath('GatewayPath', '') <> '') and
    (ReadStoredPath('BridgePath', '') <> '') and
    (ReadStoredPath('WorkspacePath', '') <> '') and
    (ReadStoredPath('ProfilesPath', '') <> '') and
    (ReadStoredPath('ConfigPath', '') <> '') and
    (ReadStoredPath('StatePath', '') <> '') and
    (ReadStoredPath('LogsPath', '') <> '') and
    (ReadStoredPath('BackupsPath', '') <> '');
end;

function GetGatewayPath(Param: String): String;
begin
  if RuntimeDirsPage <> nil then
    Result := RuntimeDirsPage.Values[1]
  else
    Result := ReadStoredPath('GatewayPath', ExpandConstant('{app}\gateway'));
end;

function GetBridgePath(Param: String): String;
begin
  Result := RemoveBackslashUnlessRoot(GetAppPath) + '\{#BridgeDirectoryName}';
end;

function GetWorkspacePath(Param: String): String;
begin
  if DataDirsPage <> nil then
    Result := DataDirsPage.Values[0]
  else
    Result := ReadStoredPath('WorkspacePath', GetDataRoot + '\workspace');
end;

function GetProfilesPath(Param: String): String;
begin
  if DataDirsPage <> nil then
    Result := DataDirsPage.Values[1]
  else
    Result := ReadStoredPath('ProfilesPath', GetDataRoot + '\profiles');
end;

function GetConfigPath(Param: String): String;
begin
  if DataDirsPage <> nil then
    Result := DataDirsPage.Values[2]
  else
    Result := ReadStoredPath('ConfigPath', GetDataRoot + '\config');
end;

function GetStatePath(Param: String): String;
begin
  if OperatingDirsPage <> nil then
    Result := OperatingDirsPage.Values[0]
  else
    Result := ReadStoredPath('StatePath', GetDataRoot + '\state');
end;

function GetLogsPath(Param: String): String;
begin
  if OperatingDirsPage <> nil then
    Result := OperatingDirsPage.Values[1]
  else
    Result := ReadStoredPath('LogsPath', GetDataRoot + '\logs');
end;

function GetBackupsPath(Param: String): String;
begin
  if OperatingDirsPage <> nil then
    Result := OperatingDirsPage.Values[2]
  else
    Result := ReadStoredPath('BackupsPath', GetDataRoot + '\profile_backups');
end;

function GetProfileName: String;
begin
  Result := Trim(ProfilePage.Values[0]);
end;

function GetSecurityConfigPath: String;
begin
  Result := Trim(ProfilePage.Values[1]);
  if Result <> '' then
    Result := RemoveBackslashUnlessRoot(ExpandFileName(Result));
end;

function GetMemoryThreshold: String;
begin
  Result := Trim(RuntimeSettingsPage.Values[0]);
end;

function GetPersonaThreshold: String;
begin
  Result := Trim(RuntimeSettingsPage.Values[1]);
end;

function GetTemperamentThreshold: String;
begin
  Result := Trim(RuntimeSettingsPage.Values[2]);
end;

function GetQdrantEnabled: String;
begin
  if RuntimeOptionsPage.Values[0] then
    Result := 'true'
  else
    Result := 'false';
end;

function GetPersonaLayerDisabled: String;
begin
  if RuntimeOptionsPage.Values[1] then
    Result := 'true'
  else
    Result := 'false';
end;

function GetInstallSummaryPath(Param: String): String;
begin
  Result := GetConfigPath('') + '\installer\installation-summary.txt';
end;

function GetGettingStartedPath(Param: String): String;
begin
  if CompareText(ActiveLanguage, 'german') = 0 then
    Result := GetAppPath + '\docs\getting-started-de.html'
  else
    Result := GetAppPath + '\docs\getting-started-en.html';
end;

function GetConfigurationScriptPath: String;
begin
  Result := GetAppPath + '\configuration\plwc-config.py';
end;

function GetCodexSnippetPath(Param: String): String;
begin
  Result := GetConfigPath('') + '\clients\codex\plwc-gateway.generated.toml';
end;

function GetOdysseusSnippetPath(Param: String): String;
begin
  Result := GetConfigPath('') + '\clients\odysseus\plwc-gateway.generated.json';
end;

function GetClaudeFolder(Param: String): String;
begin
  Result := GetAppPath + '\packages';
end;

function GetGatewayServerPath: String;
begin
  Result := GetGatewayPath('') + '\server.py';
end;

function GetNativeHostExePath: String;
begin
  Result := GetBridgePath('') + '\native\bin\plwc-chat-bridge-launcher.exe';
end;

function GetNativeHostExePathConstant(Param: String): String;
begin
  Result := GetNativeHostExePath;
end;

function GetBridgeAutostartShortcutPath: String;
begin
  Result := ExpandConstant('{userstartup}\PLwC Chat Bridge.lnk');
end;

function GetBridgeConfigPath: String;
begin
  Result := GetBridgePath('') + '\config\plwc.example.json';
end;

function GetExtensionFolder(Param: String): String;
var
  Candidate: String;
begin
  Candidate := GetBridgePath('') + '\extension\dist';
  if DirExists(Candidate) then
    Result := Candidate
  else
  begin
    Candidate := GetBridgePath('') + '\extension';
    if DirExists(Candidate) then
      Result := Candidate
    else
      Result := GetBridgePath('');
  end;
end;

function NormalizePath(Value: String): String;
begin
  Result := RemoveBackslashUnlessRoot(ExpandFileName(Trim(Value)));
end;

function IsSameOrChildPath(ChildPath, ParentPath: String): Boolean;
var
  ChildWithSlash: String;
  ParentWithSlash: String;
begin
  ChildWithSlash := Lowercase(AddBackslash(NormalizePath(ChildPath)));
  ParentWithSlash := Lowercase(AddBackslash(NormalizePath(ParentPath)));
  Result := Pos(ParentWithSlash, ChildWithSlash) = 1;
end;

function PathsOverlap(FirstPath, SecondPath: String): Boolean;
begin
  Result := IsSameOrChildPath(FirstPath, SecondPath) or
    IsSameOrChildPath(SecondPath, FirstPath);
end;

function BooleanIniValue(Value: Boolean): String;
begin
  if Value then
    Result := 'true'
  else
    Result := 'false';
end;

function LocalizedBoolean(Value: Boolean): String;
begin
  if Value then
    Result := CustomMessage('ValueYes')
  else
    Result := CustomMessage('ValueNo');
end;

function IsSafeModeExpected: Boolean;
begin
  Result := not (DockerCliOK and DockerDaemonOK and DockerImagesOK);
end;

function RunProbe(Executable, Parameters: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := (Executable <> '') and FileExists(Executable) and
    Exec(Executable, Parameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and
    (ResultCode = 0);
end;

function RunProbeWithTimeout(
  Executable, Parameters: String; TimeoutMilliseconds: LongWord): Boolean;
var
  ExecInfo: TShellExecuteInfo;
  ExitCode: LongWord;
  WaitResult: LongWord;
begin
  Result := False;
  if (Executable = '') or (not FileExists(Executable)) then
    Exit;

  ExecInfo.cbSize := SizeOf(ExecInfo);
  ExecInfo.fMask := SeeMaskNoCloseProcess;
  ExecInfo.Wnd := 0;
  ExecInfo.lpVerb := '';
  ExecInfo.lpFile := Executable;
  ExecInfo.lpParameters := Parameters;
  ExecInfo.lpDirectory := '';
  ExecInfo.nShow := SW_HIDE;
  ExecInfo.hInstApp := 0;
  ExecInfo.lpIDList := 0;
  ExecInfo.lpClass := '';
  ExecInfo.hkeyClass := 0;
  ExecInfo.dwHotKey := 0;
  ExecInfo.hMonitor := 0;
  ExecInfo.hProcess := 0;

  if not ShellExecuteEx(ExecInfo) then
    Exit;
  try
    WaitResult := WaitForSingleObject(ExecInfo.hProcess, TimeoutMilliseconds);
    if WaitResult = WaitObject0 then
    begin
      ExitCode := 1;
      if GetExitCodeProcess(ExecInfo.hProcess, ExitCode) then
        Result := ExitCode = 0;
    end
    else if WaitResult = WaitTimeout then
    begin
      TerminateProcess(ExecInfo.hProcess, 124);
      WaitForSingleObject(ExecInfo.hProcess, 1000);
    end;
  finally
    CloseHandle(ExecInfo.hProcess);
  end;
end;

function IsWindowsStoreAlias(Path: String): Boolean;
begin
  Result := Pos('\microsoft\windowsapps\', Lowercase(Path)) > 0;
end;

function QueryAppPath(RootKey: Integer; FileName: String): String;
var
  Candidate: String;
begin
  Result := '';
  if RegQueryStringValue(
       RootKey,
       'Software\Microsoft\Windows\CurrentVersion\App Paths\' + FileName,
       '',
       Candidate) and FileExists(Candidate) then
    Result := Candidate;
end;

function FindExecutable(FileName: String): String;
begin
  Result := FileSearch(FileName, GetEnv('PATH'));
  if (Result <> '') and IsWindowsStoreAlias(Result) then
    Result := '';
  if Result = '' then
    Result := QueryAppPath(HKCU, FileName);
  if Result = '' then
    Result := QueryAppPath(HKLM32, FileName);
  if (Result = '') and IsWin64 then
    Result := QueryAppPath(HKLM64, FileName);
end;

function FindKnownProgramFile(RelativePath: String): String;
var
  Candidate: String;
begin
  Result := '';
  Candidate := AddBackslash(GetEnv('ProgramW6432')) + RelativePath;
  if (GetEnv('ProgramW6432') <> '') and FileExists(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;
  Candidate := AddBackslash(GetEnv('ProgramFiles')) + RelativePath;
  if (GetEnv('ProgramFiles') <> '') and FileExists(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;
  Candidate := AddBackslash(GetEnv('ProgramFiles(x86)')) + RelativePath;
  if (GetEnv('ProgramFiles(x86)') <> '') and FileExists(Candidate) then
    Result := Candidate;
end;

function RunPowerShellProbe(
  CommandText: String; TimeoutMilliseconds: LongWord): Boolean;
var
  PowerShellPath: String;
begin
  PowerShellPath := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Result := RunProbeWithTimeout(
    PowerShellPath,
    '-NoLogo -NoProfile -ExecutionPolicy Bypass -Command "' +
      CommandText + '"',
    TimeoutMilliseconds);
end;

function FindDockerCliExecutable: String;
begin
  Result := FindExecutable('docker.exe');
  if Result = '' then
    if FileExists(ExpandConstant(
         '{localappdata}\Programs\DockerDesktop\resources\bin\docker.exe')) then
      Result := ExpandConstant(
        '{localappdata}\Programs\DockerDesktop\resources\bin\docker.exe');
  if Result = '' then
    Result := FindKnownProgramFile('Docker\Docker\resources\bin\docker.exe');
end;

function FindDockerDesktopApplicationPath: String;
begin
  Result := '';
  if FileExists(ExpandConstant(
       '{localappdata}\Programs\DockerDesktop\Docker Desktop.exe')) then
    Result := ExpandConstant(
      '{localappdata}\Programs\DockerDesktop\Docker Desktop.exe');
  if Result = '' then
    Result := FindKnownProgramFile('Docker\Docker\Docker Desktop.exe');
end;

function RegistryHasUninstallNameAtRoot(RootKey: Integer; Needle: String): Boolean;
var
  Names: TArrayOfString;
  DisplayName: String;
  I: Integer;
  Key: String;
begin
  Result := False;
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall';
  if not RegGetSubkeyNames(RootKey, Key, Names) then
    Exit;
  for I := 0 to GetArrayLength(Names) - 1 do
  begin
    if RegQueryStringValue(RootKey, Key + '\' + Names[I], 'DisplayName', DisplayName) and
       (Pos(Lowercase(Needle), Lowercase(DisplayName)) > 0) then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function RegistryHasUninstallName(Needle: String): Boolean;
begin
  Result := RegistryHasUninstallNameAtRoot(HKCU, Needle) or
    RegistryHasUninstallNameAtRoot(HKLM32, Needle);
  if (not Result) and IsWin64 then
    Result := RegistryHasUninstallNameAtRoot(HKLM64, Needle);
end;

function FindRegisteredPackageExecutable(
  PackagePrefix, RelativeExecutable: String): String;
var
  PackageNames: TArrayOfString;
  PackageRoot: String;
  Candidate: String;
  I: Integer;
begin
  Result := '';
  if not RegGetSubkeyNames(HKCU, AppModelPackagesKey, PackageNames) then
    Exit;

  PackagePrefix := Lowercase(PackagePrefix);
  for I := 0 to GetArrayLength(PackageNames) - 1 do
  begin
    if Pos(PackagePrefix, Lowercase(PackageNames[I])) = 1 then
    begin
      PackageRoot := '';
      if RegQueryStringValue(
           HKCU,
           AppModelPackagesKey + '\' + PackageNames[I],
           'PackageRootFolder',
           PackageRoot) then
      begin
        Candidate := AddBackslash(PackageRoot) + RelativeExecutable;
        if FileExists(Candidate) then
        begin
          Result := Candidate;
          Exit;
        end;
      end;
    end;
  end;
end;

procedure CheckVCRuntimeRegistryRoot(RootKey: Integer);
var
  Installed: Cardinal;
  VersionValue: String;
begin
  if VCRuntimeOK then
    Exit;

  Installed := 0;
  if RegQueryDWordValue(
       RootKey,
       'Software\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
       'Installed',
       Installed) and
     (Installed = 1) then
  begin
    VCRuntimeOK := True;
    VersionValue := '';
    if RegQueryStringValue(
         RootKey,
         'Software\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
         'Version',
         VersionValue) then
      DetectedVCRuntimeVersion := VersionValue;
  end;
end;

procedure ProbeVCRuntime;
begin
  VCRuntimeOK := False;
  DetectedVCRuntimeVersion := '';
  if IsWin64 then
    CheckVCRuntimeRegistryRoot(HKLM64);
  CheckVCRuntimeRegistryRoot(HKLM32);
end;

function PythonPrerequisitesOK: Boolean;
begin
  Result := PythonVersionOK and PythonRuntimeOK and VCRuntimeOK;
end;

function RunPythonRuntimeProbe(PythonPath, LogPath: String): Boolean;
var
  ProbeScriptPath: String;
  Parameters: String;
begin
  Result := False;
  if (PythonPath = '') or (not FileExists(PythonPath)) then
    Exit;

  ExtractTemporaryFile('python-runtime-probe.py');
  ProbeScriptPath := ExpandConstant('{tmp}\python-runtime-probe.py');
  Parameters := '-u "' + ProbeScriptPath + '" "' + LogPath + '"';
  Log('Running PLwC Python runtime probe with interpreter=' + PythonPath +
    ' diagnostic_log=' + LogPath);
  Result := RunProbeWithTimeout(
    PythonPath, Parameters, PythonRuntimeProbeTimeoutMilliseconds);
  Log('PLwC Python runtime probe result=' + BooleanIniValue(Result));
  if not Result then
    Log(
      'PLwC Python runtime probe failed or timed out after ' +
      IntToStr(PythonRuntimeProbeTimeoutMilliseconds) + ' ms; ' +
      'see diagnostic_log=' + LogPath);
end;

procedure CheckPythonCandidate(Candidate: String);
begin
  if PythonVersionOK then
    Exit;
  if (Candidate = '') or (not FileExists(Candidate)) or IsWindowsStoreAlias(Candidate) then
    Exit;

  PythonDetected := True;
  if DetectedPythonPath = '' then
    DetectedPythonPath := Candidate;

  if RunProbeWithTimeout(
       Candidate,
       '-c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"',
       5000) then
  begin
    PythonVersionOK := True;
    DetectedPythonPath := Candidate;
    if RunProbeWithTimeout(
         Candidate,
         '-c "import mcp, qdrant_client, onnxruntime, fastembed"',
         PythonRuntimeProbeTimeoutMilliseconds) then
      PythonRuntimeOK := True;
  end;
end;

procedure CheckPythonRegistryRoot(RootKey: Integer);
var
  Versions: TArrayOfString;
  Candidate: String;
  InstallPath: String;
  I: Integer;
  VersionKey: String;
begin
  if not RegGetSubkeyNames(RootKey, 'Software\Python\PythonCore', Versions) then
    Exit;
  for I := 0 to GetArrayLength(Versions) - 1 do
  begin
    VersionKey := 'Software\Python\PythonCore\' + Versions[I] + '\InstallPath';
    Candidate := '';
    if RegQueryStringValue(RootKey, VersionKey, 'ExecutablePath', Candidate) then
      CheckPythonCandidate(Candidate);
    InstallPath := '';
    if RegQueryStringValue(RootKey, VersionKey, '', InstallPath) then
      CheckPythonCandidate(AddBackslash(InstallPath) + 'python.exe');
  end;
end;

procedure ProbePython;
var
  Candidate: String;
  Version: Integer;
begin
  DetectedPythonPath := '';
  PythonDetected := False;
  PythonVersionOK := False;
  PythonRuntimeOK := False;

  CheckPythonCandidate(FindExecutable('python.exe'));
  for Version := 15 downto 11 do
  begin
    Candidate := ExpandConstant('{localappdata}\Programs\Python\Python3' +
      IntToStr(Version) + '\python.exe');
    CheckPythonCandidate(Candidate);
    CheckPythonCandidate(FindKnownProgramFile('Python3' + IntToStr(Version) + '\python.exe'));
  end;
  CheckPythonRegistryRoot(HKCU);
  CheckPythonRegistryRoot(HKLM32);
  if IsWin64 then
    CheckPythonRegistryRoot(HKLM64);
end;

procedure CheckNodeCandidate(Candidate: String);
begin
  if NodeVersionOK or (Candidate = '') or (not FileExists(Candidate)) then
    Exit;
  if DetectedNodePath = '' then
    DetectedNodePath := Candidate;
  if RunProbeWithTimeout(
       Candidate,
       '-e "const v=process.versions.node.split(''.'').map(Number); process.exit(v[0]>22 || (v[0]===22 && v[1]>=12) ? 0 : 1)"',
       5000) then
  begin
    NodeVersionOK := True;
    DetectedNodePath := Candidate;
  end;
end;

procedure ProbeNode;
begin
  DetectedNodePath := '';
  NodeVersionOK := False;
  CheckNodeCandidate(FindExecutable('node.exe'));
  CheckNodeCandidate(FindKnownProgramFile('nodejs\node.exe'));
  CheckNodeCandidate(ExpandConstant('{localappdata}\Programs\nodejs\node.exe'));
end;

procedure ProbeDocker;
begin
  DetectedDockerDesktopPath := FindDockerDesktopApplicationPath;
  DockerDesktopInstalled := (DetectedDockerDesktopPath <> '') or
    RegistryHasUninstallName('Docker Desktop');
  DetectedDockerPath := FindDockerCliExecutable;
  DockerCliOK := DetectedDockerPath <> '';
  DockerDaemonOK := False;
  if DockerCliOK then
    if WaitNamedPipe('\\.\pipe\docker_engine', 2000) then
      DockerDaemonOK := RunProbeWithTimeout(
        DetectedDockerPath,
        '-H npipe:////./pipe/docker_engine info',
        8000);
  DockerImagesOK := DockerDaemonOK and RunProbeWithTimeout(
    DetectedDockerPath,
    '-H npipe:////./pipe/docker_engine image inspect ' +
      'python:3.12-slim plwc-node-runner:0.1.0 plwc-document-worker:0.1.0',
    8000);
end;

procedure ProbeWsl2;
begin
  Wsl2OK := RunPowerShellProbe(
    'if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { exit 1 }; ' +
    '$status = & wsl.exe --status 2>$null; ' +
    'if ($LASTEXITCODE -eq 0) { exit 0 } else { exit 1 }',
    10000);
end;

procedure ProbeVirtualization;
begin
  VirtualizationCapabilityOK := RunPowerShellProbe(
    '$ErrorActionPreference=''Stop''; ' +
    '$processors = @(Get-CimInstance Win32_Processor); ' +
    'if (@($processors | Where-Object { $_.VirtualizationFirmwareEnabled }).Count -gt 0) { exit 0 } else { exit 1 }',
    10000);
  VirtualMachineDetected := RunPowerShellProbe(
    '$ErrorActionPreference=''Stop''; ' +
    '$cs = Get-CimInstance Win32_ComputerSystem; ' +
    '$hostText = (($cs.Manufacturer + '' '' + $cs.Model).ToLowerInvariant()); ' +
    'if ($hostText -match ''virtual|vmware|virtualbox|qemu|kvm|hyper-v|parallels'') { exit 0 } else { exit 1 }',
    10000);
  NestedVirtualizationOK := (not VirtualMachineDetected) or
    VirtualizationCapabilityOK;
end;

procedure ProbeClaude;
begin
  DetectedClaudePath := '';
  if FileExists(ExpandConstant('{localappdata}\AnthropicClaude\claude.exe')) then
    DetectedClaudePath := ExpandConstant('{localappdata}\AnthropicClaude\claude.exe');
  if DetectedClaudePath = '' then
    if FileExists(ExpandConstant('{localappdata}\Programs\Claude\Claude.exe')) then
      DetectedClaudePath := ExpandConstant('{localappdata}\Programs\Claude\Claude.exe');
  if DetectedClaudePath = '' then
    DetectedClaudePath := FindKnownProgramFile('Claude\Claude.exe');
  if DetectedClaudePath = '' then
    DetectedClaudePath := FindRegisteredPackageExecutable('claude_', 'app\claude.exe');
  ClaudeDetected := DetectedClaudePath <> '';
end;

procedure ProbeBrowser;
begin
  DetectedBrowserPath := '';
  DetectedChromePath := FindExecutable('chrome.exe');
  if DetectedChromePath = '' then
    if FileExists(ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe')) then
      DetectedChromePath := ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe');
  if DetectedChromePath = '' then
    DetectedChromePath := FindKnownProgramFile('Google\Chrome\Application\chrome.exe');

  DetectedEdgePath := FindExecutable('msedge.exe');
  if DetectedEdgePath = '' then
    DetectedEdgePath := FindKnownProgramFile('Microsoft\Edge\Application\msedge.exe');

  DetectedBravePath := FindExecutable('brave.exe');
  if DetectedBravePath = '' then
    if FileExists(ExpandConstant('{localappdata}\BraveSoftware\Brave-Browser\Application\brave.exe')) then
      DetectedBravePath := ExpandConstant('{localappdata}\BraveSoftware\Brave-Browser\Application\brave.exe');
  if DetectedBravePath = '' then
    DetectedBravePath := FindKnownProgramFile('BraveSoftware\Brave-Browser\Application\brave.exe');

  ChromeDetected := DetectedChromePath <> '';
  EdgeDetected := DetectedEdgePath <> '';
  BraveDetected := DetectedBravePath <> '';
  BrowserDetected := ChromeDetected or EdgeDetected or BraveDetected;
  if ChromeDetected then
    DetectedBrowserPath := DetectedChromePath
  else if BraveDetected then
    DetectedBrowserPath := DetectedBravePath
  else
    DetectedBrowserPath := DetectedEdgePath;
end;

procedure ProbeCodex;
begin
  DetectedCodexPath := FindExecutable('codex.exe');
  if DetectedCodexPath = '' then
    DetectedCodexPath := FileSearch('codex.cmd', GetEnv('PATH'));
  if DetectedCodexPath = '' then
    if FileExists(ExpandConstant('{localappdata}\Programs\Codex\Codex.exe')) then
      DetectedCodexPath := ExpandConstant('{localappdata}\Programs\Codex\Codex.exe');
  if DetectedCodexPath = '' then
    DetectedCodexPath := FindKnownProgramFile('Codex\Codex.exe');
  if DetectedCodexPath = '' then
    DetectedCodexPath := FindRegisteredPackageExecutable('openai.codex_', 'app\Codex.exe');
  CodexDetected := (DetectedCodexPath <> '') or RegistryHasUninstallName('Codex');
end;

procedure ProbeOdysseus;
begin
  DetectedOdysseusPath := FindExecutable('odysseus.exe');
  if DetectedOdysseusPath = '' then
    if FileExists(ExpandConstant('{localappdata}\Programs\Odysseus\Odysseus.exe')) then
      DetectedOdysseusPath := ExpandConstant('{localappdata}\Programs\Odysseus\Odysseus.exe');
  if DetectedOdysseusPath = '' then
    DetectedOdysseusPath := FindKnownProgramFile('Odysseus\Odysseus.exe');
  OdysseusDetected := (DetectedOdysseusPath <> '') or
    RegistryHasUninstallName('Odysseus');
end;

procedure AppendPrerequisiteLine(StatusText, MessageText, DetailPath: String);
begin
  PrerequisiteReport := PrerequisiteReport + StatusText + ' ' + MessageText + #13#10;
  if DetailPath <> '' then
    PrerequisiteReport := PrerequisiteReport + '    ' +
      CustomMessage('PrereqPath') + DetailPath + #13#10;
end;

procedure AppendPrerequisiteBlocker(MessageText: String);
begin
  if PrerequisiteBlockers <> '' then
    PrerequisiteBlockers := PrerequisiteBlockers + #13#10;
  PrerequisiteBlockers := PrerequisiteBlockers + '- ' + MessageText;
end;

procedure AppendManualPrerequisiteBlocker(MessageText: String);
begin
  AppendPrerequisiteBlocker(MessageText);
  if PrerequisiteManualBlockers <> '' then
    PrerequisiteManualBlockers := PrerequisiteManualBlockers + #13#10;
  PrerequisiteManualBlockers := PrerequisiteManualBlockers + '- ' + MessageText;
end;

procedure RunPrerequisiteChecks;
var
  VCRuntimeStatusText: String;
begin
  PrerequisiteReport := CustomMessage('PrereqIntro') + #13#10 + #13#10;
  if IsAdmin then
    PrerequisiteReport := PrerequisiteReport +
      CustomMessage('PrereqAdminElevated') + #13#10 + #13#10
  else
    PrerequisiteReport := PrerequisiteReport +
      CustomMessage('PrereqAdminStandard') + #13#10 + #13#10;
  PrerequisiteBlockers := '';
  PrerequisiteManualBlockers := '';

  ProbeVCRuntime;
  ProbePython;
  ProbeDocker;
  ProbeWsl2;
  ProbeVirtualization;
  ProbeClaude;
  ProbeNode;
  ProbeBrowser;
  ProbeCodex;
  ProbeOdysseus;

#ifdef UiSmokeMissingPrerequisites
  VCRuntimeOK := False;
  DetectedVCRuntimeVersion := '';
  DetectedPythonPath := '';
  PythonDetected := False;
  PythonVersionOK := False;
  PythonRuntimeOK := False;
  DetectedNodePath := '';
  NodeVersionOK := False;
  DetectedDockerPath := '';
  DetectedDockerDesktopPath := '';
  DockerDesktopInstalled := False;
  DockerCliOK := False;
  DockerDaemonOK := False;
  DockerImagesOK := False;
  Wsl2OK := False;
  VirtualizationCapabilityOK := False;
  VirtualMachineDetected := False;
  NestedVirtualizationOK := True;
  DetectedBrowserPath := '';
  DetectedChromePath := '';
  DetectedEdgePath := '';
  DetectedBravePath := '';
  BrowserDetected := False;
  ChromeDetected := False;
  EdgeDetected := False;
  BraveDetected := False;
#endif

#ifdef UiSmokeVmNoNested
  DockerDesktopInstalled := True;
  DetectedDockerDesktopPath :=
    ExpandConstant('{pf}\Docker\Docker\Docker Desktop.exe');
  DetectedDockerPath :=
    ExpandConstant('{pf}\Docker\Docker\resources\bin\docker.exe');
  DockerCliOK := True;
  DockerDaemonOK := False;
  DockerImagesOK := False;
  Wsl2OK := False;
  VirtualizationCapabilityOK := False;
  VirtualMachineDetected := True;
  NestedVirtualizationOK := False;
#endif

  if VCRuntimeOK then
  begin
    VCRuntimeStatusText := CustomMessage('PrereqVCRuntimeOK');
    if DetectedVCRuntimeVersion <> '' then
      VCRuntimeStatusText := VCRuntimeStatusText + ' ' +
        CustomMessage('PrereqVersion') + DetectedVCRuntimeVersion;
    AppendPrerequisiteLine(
      CustomMessage('PrereqOK'), VCRuntimeStatusText, '');
  end
  else
  begin
    AppendPrerequisiteLine(
      CustomMessage('PrereqActionRequired'),
      CustomMessage('PrereqVCRuntimeMissing'),
      '');
    AppendPrerequisiteBlocker(CustomMessage('PrereqVCRuntimeMissing'));
  end;

  if not PythonVersionOK then
  begin
    AppendPrerequisiteLine(
      CustomMessage('PrereqActionRequired'), CustomMessage('PrereqPythonMissing'),
      DetectedPythonPath);
    AppendPrerequisiteBlocker(CustomMessage('PrereqPythonMissing'));
  end
  else
  begin
    AppendPrerequisiteLine(
      CustomMessage('PrereqOK'), CustomMessage('PrereqPythonOK'),
      DetectedPythonPath);
    if PythonRuntimeOK then
      AppendPrerequisiteLine(
        CustomMessage('PrereqOK'), CustomMessage('PrereqMcpOK'), '')
    else
    begin
      AppendPrerequisiteLine(
        CustomMessage('PrereqActionRequired'), CustomMessage('PrereqMcpMissing'),
        DetectedPythonPath);
      AppendPrerequisiteBlocker(CustomMessage('PrereqMcpMissing'));
    end;
  end;

  if DockerDesktopInstalled then
    AppendPrerequisiteLine(
      CustomMessage('PrereqPrepared'), CustomMessage('PrereqDockerDesktopOK'),
      DetectedDockerDesktopPath)
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqSafeMode'), CustomMessage('PrereqDockerDesktopMissing'), '');

  if DockerImagesOK then
    AppendPrerequisiteLine(
      CustomMessage('PrereqOK'), CustomMessage('PrereqDockerOK'),
      DetectedDockerPath)
  else if not DockerCliOK then
    AppendPrerequisiteLine(
      CustomMessage('PrereqSafeMode'), CustomMessage('PrereqDockerCliMissing'), '')
  else
  begin
    if not DockerDaemonOK then
      AppendPrerequisiteLine(
        CustomMessage('PrereqSafeMode'), CustomMessage('PrereqDockerDaemonMissing'),
        DetectedDockerPath)
    else
      AppendPrerequisiteLine(
        CustomMessage('PrereqSafeMode'), CustomMessage('PrereqDockerImagesMissing'),
        DetectedDockerPath);
  end;
  if DockerInstalledBySetup and (not DockerDaemonOK) then
    AppendPrerequisiteLine(
      CustomMessage('PrereqWarning'),
      CustomMessage('PrereqDockerFirstStart'),
      DetectedDockerPath);

  if Wsl2OK then
    AppendPrerequisiteLine(
      CustomMessage('PrereqOK'), CustomMessage('PrereqWsl2OK'), '')
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqSafeMode'), CustomMessage('PrereqWsl2Missing'), '');

  if VirtualizationCapabilityOK then
    AppendPrerequisiteLine(
      CustomMessage('PrereqOK'), CustomMessage('PrereqVirtualizationOK'), '')
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqSafeMode'), CustomMessage('PrereqVirtualizationMissing'), '');

  if VirtualMachineDetected then
  begin
    if NestedVirtualizationOK then
      AppendPrerequisiteLine(
        CustomMessage('PrereqOK'), CustomMessage('PrereqVmNestedOK'), '')
    else
      AppendPrerequisiteLine(
        CustomMessage('PrereqWarning'), CustomMessage('PrereqVmNestedMissing'), '');
  end
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqOK'), CustomMessage('PrereqVmHostPhysical'), '');

  if IsSafeModeExpected then
    AppendPrerequisiteLine(
      CustomMessage('PrereqSafeMode'), CustomMessage('PrereqSafeModeExplanation'), '');

  if WizardIsComponentSelected('claude') then
  begin
    if ClaudeDetected then
      AppendPrerequisiteLine(
        CustomMessage('PrereqOK'), CustomMessage('PrereqClaudeOK'),
        DetectedClaudePath)
    else
    begin
      AppendPrerequisiteLine(
        CustomMessage('PrereqActionRequired'), CustomMessage('PrereqClaudeMissing'), '');
      AppendManualPrerequisiteBlocker(CustomMessage('PrereqClaudeMissing'));
    end;
  end
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqNotSelected'), CustomMessage('PrereqClaudeNotSelected'), '');

  if WizardIsComponentSelected('chatbridge') then
  begin
    if NodeVersionOK then
      AppendPrerequisiteLine(
        CustomMessage('PrereqOK'), CustomMessage('PrereqNodeOK'),
        DetectedNodePath)
    else
    begin
      AppendPrerequisiteLine(
        CustomMessage('PrereqActionRequired'), CustomMessage('PrereqNodeMissing'),
        DetectedNodePath);
      AppendPrerequisiteBlocker(CustomMessage('PrereqNodeMissing'));
    end;
    if BrowserDetected then
      AppendPrerequisiteLine(
        CustomMessage('PrereqOK'), CustomMessage('PrereqBrowserOK'),
        DetectedBrowserPath)
    else
    begin
      AppendPrerequisiteLine(
        CustomMessage('PrereqActionRequired'), CustomMessage('PrereqBrowserMissing'), '');
      AppendManualPrerequisiteBlocker(CustomMessage('PrereqBrowserMissing'));
    end;
  end
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqNotSelected'), CustomMessage('PrereqBridgeNotSelected'), '');

  if WizardIsComponentSelected('codex') then
  begin
    if CodexDetected then
      AppendPrerequisiteLine(
        CustomMessage('PrereqPrepared'), CustomMessage('PrereqCodexOK'),
        DetectedCodexPath)
    else
      AppendPrerequisiteLine(
        CustomMessage('PrereqWarning'), CustomMessage('PrereqCodexMissing'), '');
  end
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqNotSelected'), CustomMessage('PrereqCodexNotSelected'), '');

  if WizardIsComponentSelected('odysseus') then
  begin
    if OdysseusDetected then
      AppendPrerequisiteLine(
        CustomMessage('PrereqPrepared'), CustomMessage('PrereqOdysseusOK'),
        DetectedOdysseusPath)
    else
      AppendPrerequisiteLine(
        CustomMessage('PrereqWarning'), CustomMessage('PrereqOdysseusMissing'), '');
  end
  else
    AppendPrerequisiteLine(
      CustomMessage('PrereqNotSelected'), CustomMessage('PrereqOdysseusNotSelected'), '');

  PrerequisiteReport := PrerequisiteReport + #13#10;
  if PrerequisiteBlockers = '' then
    PrerequisiteReport := PrerequisiteReport + CustomMessage('PrereqGatePassed')
  else
    PrerequisiteReport := PrerequisiteReport + CustomMessage('PrereqGateFailed');
end;

function IsValidThreshold(Value: String): Boolean;
var
  Number: Integer;
begin
  Number := StrToIntDef(Trim(Value), -1);
  Result := (Number >= 0) and (Number <= 100);
end;

function IsBooleanText(Value: String): Boolean;
begin
  Value := Lowercase(Trim(Value));
  Result := (Value = 'true') or (Value = 'false');
end;

function IsValidProfileName(Value: String): Boolean;
var
  I: Integer;
  C: Char;
begin
  Value := Trim(Value);
  Result := (Value <> '') and (Value <> '.') and (Value <> '..');
  if not Result then
    Exit;

  for I := 1 to Length(Value) do
  begin
    C := Value[I];
    if not (((C >= 'a') and (C <= 'z')) or
            ((C >= 'A') and (C <= 'Z')) or
            ((C >= '0') and (C <= '9')) or
            (C = '-') or (C = '_') or (C = '.')) then
    begin
      Result := False;
      Exit;
    end;
  end;
end;

function JsonEscape(Value: String): String;
begin
  Result := Value;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '"', '\"', True);
  StringChangeEx(Result, #13, '\r', True);
  StringChangeEx(Result, #10, '\n', True);
  StringChangeEx(Result, #9, '\t', True);
end;

function TomlQuote(Value: String): String;
begin
  Result := JsonEscape(Value);
end;

function ResolvePythonPath: String;
var
  Candidate: String;
begin
  if PythonPrerequisitesOK and (DetectedPythonPath <> '') then
  begin
    Result := DetectedPythonPath;
    Exit;
  end;

  Candidate := GetGatewayPath('') + '\python.exe';
  if FileExists(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;

  Candidate := GetGatewayPath('') + '\python\python.exe';
  if FileExists(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;

  Candidate := FileSearch('python.exe', GetEnv('PATH'));
  if Candidate <> '' then
    Result := Candidate
  else
    Result := '<PYTHON_3_11_OR_NEWER>\python.exe';
end;

function GetConfigurationPythonPath(Param: String): String;
var
  PythonPath: String;
  WindowedPythonPath: String;
begin
  PythonPath := ResolvePythonPath;
  WindowedPythonPath := AddBackslash(ExtractFileDir(PythonPath)) + 'pythonw.exe';
  if FileExists(WindowedPythonPath) then
    Result := WindowedPythonPath
  else
    Result := PythonPath;
end;

function GetConfigurationLanguage: String;
begin
  if CompareText(ActiveLanguage, 'german') = 0 then
    Result := 'de'
  else
    Result := 'en';
end;

function GetConfigurationArguments(Param: String): String;
begin
  Result :=
    '"' + GetConfigurationScriptPath + '"' +
    ' --project-root "' + GetDataRoot + '"' +
    ' --installer-config-root "' + GetConfigPath('') + '"' +
    ' --gateway-root "' + GetGatewayPath('') + '"' +
    ' --workspace "' + GetWorkspacePath('') + '"' +
    ' --profiles "' + GetProfilesPath('') + '"' +
    ' --active-profile "' + GetProfileName + '"' +
    ' --memory-threshold "' + GetMemoryThreshold + '"' +
    ' --persona-threshold "' + GetPersonaThreshold + '"' +
    ' --temperament-threshold "' + GetTemperamentThreshold + '"' +
    ' --qdrant-enabled "' + GetQdrantEnabled + '"' +
    ' --persona-layer-disabled "' + GetPersonaLayerDisabled + '"' +
    ' --language "' + GetConfigurationLanguage + '"';
  if GetSecurityConfigPath <> '' then
    Result := Result + ' --security-config "' + GetSecurityConfigPath + '"';
end;

function GetGettingStartedArguments(Param: String): String;
begin
  Result := GetConfigurationArguments('') + ' --start-page "getting-started"';
end;

function BuildCodexSnippet: String;
var
  PythonPath: String;
begin
  PythonPath := ResolvePythonPath;
  Result :=
    '# ' + CustomMessage('SnippetPreparedComment') + #13#10 +
    '[mcp_servers.plwc-gateway]' + #13#10 +
    'enabled = true' + #13#10 +
    'required = false' + #13#10 +
    'command = "' + TomlQuote(PythonPath) + '"' + #13#10 +
    'args = ["' + TomlQuote(GetGatewayServerPath) + '"]' + #13#10 +
    'env = { "PLWC_WORKSPACE_ROOT" = "' + TomlQuote(GetWorkspacePath('')) +
      '", "PLWC_PROFILE_ROOT" = "' + TomlQuote(GetProfilesPath('')) +
      '", "PLWC_ACTIVE_PROFILE_NAME" = "' + TomlQuote(GetProfileName) +
      '", "PLWC_CONFIG_FILE" = "' + TomlQuote(GetSecurityConfigPath) +
      '", "PLWC_MEMORY_WRITE_THRESHOLD" = "' + TomlQuote(GetMemoryThreshold) +
      '", "PLWC_PERSONA_WRITE_THRESHOLD" = "' + TomlQuote(GetPersonaThreshold) +
      '", "PLWC_TEMPERAMENT_WRITE_THRESHOLD" = "' + TomlQuote(GetTemperamentThreshold) +
       '", "PLWC_QDRANT_ENABLED" = "' + TomlQuote(GetQdrantEnabled) +
      '", "PLWC_PERSONA_LAYER_DISABLED" = "' + TomlQuote(GetPersonaLayerDisabled) +
      '", "PLWC_DOCKER_EXE" = "' + TomlQuote(DetectedDockerPath) + '" }' + #13#10;
end;

function BuildOdysseusSnippet: String;
var
  PythonPath: String;
begin
  PythonPath := ResolvePythonPath;
  Result :=
    '{' + #13#10 +
    '  "_comment": "' + JsonEscape(CustomMessage('SnippetPreparedComment')) + '",' + #13#10 +
    '  "mcpServers": {' + #13#10 +
    '    "plwc-gateway": {' + #13#10 +
    '      "command": "' + JsonEscape(PythonPath) + '",' + #13#10 +
    '      "args": ["' + JsonEscape(GetGatewayServerPath) + '"],' + #13#10 +
    '      "env": {' + #13#10 +
    '        "PLWC_WORKSPACE_ROOT": "' + JsonEscape(GetWorkspacePath('')) + '",' + #13#10 +
    '        "PLWC_PROFILE_ROOT": "' + JsonEscape(GetProfilesPath('')) + '",' + #13#10 +
    '        "PLWC_ACTIVE_PROFILE_NAME": "' + JsonEscape(GetProfileName) + '",' + #13#10 +
    '        "PLWC_CONFIG_FILE": "' + JsonEscape(GetSecurityConfigPath) + '",' + #13#10 +
    '        "PLWC_MEMORY_WRITE_THRESHOLD": "' + JsonEscape(GetMemoryThreshold) + '",' + #13#10 +
    '        "PLWC_PERSONA_WRITE_THRESHOLD": "' + JsonEscape(GetPersonaThreshold) + '",' + #13#10 +
    '        "PLWC_TEMPERAMENT_WRITE_THRESHOLD": "' + JsonEscape(GetTemperamentThreshold) + '",' + #13#10 +
        '        "PLWC_QDRANT_ENABLED": "' + JsonEscape(GetQdrantEnabled) + '",' + #13#10 +
        '        "PLWC_PERSONA_LAYER_DISABLED": "' + JsonEscape(GetPersonaLayerDisabled) + '",' + #13#10 +
        '        "PLWC_DOCKER_EXE": "' + JsonEscape(DetectedDockerPath) + '"' + #13#10 +
    '      }' + #13#10 +
    '    }' + #13#10 +
    '  }' + #13#10 +
    '}' + #13#10;
end;

function BuildBridgeConfig: String;
var
  SecurityEnvironmentLine: String;
begin
  if GetSecurityConfigPath <> '' then
    SecurityEnvironmentLine :=
      '      "PLWC_CONFIG_FILE": "' + JsonEscape(GetSecurityConfigPath) + '",' + #13#10
  else
    SecurityEnvironmentLine := '';

  Result :=
    '{' + #13#10 +
    '  "name": "PLwC Chat Bridge",' + #13#10 +
    '  "track": "v1.0.0",' + #13#10 +
    '  "bridge": {' + #13#10 +
    '    "host": "127.0.0.1",' + #13#10 +
    '    "port": 3007,' + #13#10 +
    '    "transport": "websocket",' + #13#10 +
    '    "path": "/message",' + #13#10 +
    '    "implementation": "plwc-owned-node-bridge"' + #13#10 +
    '  },' + #13#10 +
    '  "gateway": {' + #13#10 +
    '    "command": "' + JsonEscape(ResolvePythonPath) + '",' + #13#10 +
    '    "args": ["' + JsonEscape(GetGatewayServerPath) + '"],' + #13#10 +
    '    "cwd": "' + JsonEscape(GetGatewayPath('')) + '",' + #13#10 +
    '    "env": {' + #13#10 +
    '      "PLWC_WORKSPACE_ROOT": "' + JsonEscape(GetWorkspacePath('')) + '",' + #13#10 +
    '      "PLWC_PROFILE_ROOT": "' + JsonEscape(GetProfilesPath('')) + '",' + #13#10 +
    '      "PLWC_ACTIVE_PROFILE_NAME": "' + JsonEscape(GetProfileName) + '",' + #13#10 +
    SecurityEnvironmentLine +
    '      "PLWC_MEMORY_WRITE_THRESHOLD": "' + JsonEscape(GetMemoryThreshold) + '",' + #13#10 +
    '      "PLWC_PERSONA_WRITE_THRESHOLD": "' + JsonEscape(GetPersonaThreshold) + '",' + #13#10 +
    '      "PLWC_TEMPERAMENT_WRITE_THRESHOLD": "' + JsonEscape(GetTemperamentThreshold) + '",' + #13#10 +
      '      "PLWC_QDRANT_ENABLED": "' + JsonEscape(GetQdrantEnabled) + '",' + #13#10 +
      '      "PLWC_PERSONA_LAYER_DISABLED": "' + JsonEscape(GetPersonaLayerDisabled) + '",' + #13#10 +
      '      "PLWC_DOCKER_EXE": "' + JsonEscape(DetectedDockerPath) + '"' + #13#10 +
    '    }' + #13#10 +
    '  },' + #13#10 +
    '  "tools": {' + #13#10 +
    '    "publicFacadeOnly": true,' + #13#10 +
    '    "expectedPublicToolCount": 8' + #13#10 +
    '  },' + #13#10 +
    '  "executionPolicy": {' + #13#10 +
    '    "readOnlyAutoExecution": "default-enabled-user-configurable",' + #13#10 +
    '    "automaticResultSubmission": "read-only-or-explicitly-confirmed",' + #13#10 +
    '    "writesRequireConfirmation": true,' + #13#10 +
    '    "sandboxRequiresConfirmationByDefault": true,' + #13#10 +
    '    "sandboxStandingConfirmation": "default-disabled-user-configurable",' + #13#10 +
    '    "governorApplyRequiresConfirmation": true,' + #13#10 +
    '    "retryMutatingCallsAfterAmbiguousTimeout": false' + #13#10 +
    '  }' + #13#10 +
    '}' + #13#10;
end;

function GetSetupExeSha256: String;
begin
  if SetupExeSha256 = '' then
  begin
    SetupExeSha256 := Lowercase(GetSHA256OfFile(ExpandConstant('{srcexe}')));
    if Length(SetupExeSha256) <> 64 then
      RaiseException(CustomMessage('ErrorSetupHash'));
  end;
  Result := SetupExeSha256;
end;

function GetInstallerBuildId: String;
begin
  Result :=
    'plwc-windows-setup@{#AppVersion}/{#InstallerRevision}#sha256:' +
    GetSetupExeSha256;
end;

function GetInstallationMode: String;
begin
  Result := WizardSetupType(False);
end;

function GetSelectedComponentIds: String;
begin
  Result := WizardSelectedComponents(False);
end;

function BuildIdentitySummary: String;
begin
  Result :=
    CustomMessage('SummaryBuildIdentity') + #13#10 +
    CustomMessage('SummaryBuildId') + GetInstallerBuildId + #13#10 +
    CustomMessage('SummaryInstallerRevision') + '{#InstallerRevision}' + #13#10 +
    CustomMessage('SummarySetupSha256') + GetSetupExeSha256 + #13#10 +
    CustomMessage('SummaryGatewayVersion') + '{#GatewayVersion}' + #13#10 +
    CustomMessage('SummaryNodeBridgeVersion') + '{#NodeBridgeVersion}' + #13#10 +
    CustomMessage('SummaryBrowserExtensionVersion') +
      '{#BrowserExtensionVersion}' + #13#10 +
    CustomMessage('SummaryNativeLauncherVersion') +
      '{#NativeLauncherVersion}' + #13#10 +
    CustomMessage('SummaryInstallationMode') + GetInstallationMode + #13#10 +
    CustomMessage('SummarySelectedComponentIds') +
      GetSelectedComponentIds + #13#10 + #13#10;
end;

function SelectedComponentSummary: String;
begin
  Result := '  - ' + CustomMessage('ComponentGateway') + #13#10;
  if WizardIsComponentSelected('claude') then
    Result := Result + '  - ' + CustomMessage('ComponentClaude') + #13#10;
  if WizardIsComponentSelected('codex') then
    Result := Result + '  - ' + CustomMessage('ComponentCodex') + #13#10;
  if WizardIsComponentSelected('odysseus') then
    Result := Result + '  - ' + CustomMessage('ComponentOdysseus') + #13#10;
  if WizardIsComponentSelected('chatbridge') then
    Result := Result + '  - ' + CustomMessage('ComponentChatBridge') + #13#10;
end;

function BuildInstallSummary: String;
begin
  if PrerequisiteReport = '' then
    RunPrerequisiteChecks;
  Result :=
    CustomMessage('SummaryTitle') + #13#10 +
    '=================' + #13#10 + #13#10 +
    BuildIdentitySummary +
    CustomMessage('SummaryApp') + GetAppPath + #13#10 +
    CustomMessage('SummaryGateway') + GetGatewayPath('') + #13#10;
  if WizardIsComponentSelected('chatbridge') then
    Result := Result +
      CustomMessage('SummaryChatBridge') + GetBridgePath('') + #13#10;
  Result := Result +
    CustomMessage('SummaryWorkspace') + GetWorkspacePath('') + #13#10 +
    CustomMessage('SummaryProfiles') + GetProfilesPath('') + #13#10 +
    CustomMessage('SummaryConfig') + GetConfigPath('') + #13#10 +
    CustomMessage('SummaryState') + GetStatePath('') + #13#10 +
    CustomMessage('SummaryLogs') + GetLogsPath('') + #13#10 +
    CustomMessage('SummaryBackups') + GetBackupsPath('') + #13#10 +
    CustomMessage('SummaryActiveProfile') + GetProfileName + #13#10 +
    CustomMessage('SummarySecurity') + GetSecurityConfigPath + #13#10 +
    CustomMessage('SummaryMemoryThreshold') + GetMemoryThreshold + #13#10 +
    CustomMessage('SummaryPersonaThreshold') + GetPersonaThreshold + #13#10 +
    CustomMessage('SummaryTemperamentThreshold') + GetTemperamentThreshold + #13#10 +
    CustomMessage('SummaryQdrant') +
      LocalizedBoolean(RuntimeOptionsPage.Values[0]) + #13#10 +
    CustomMessage('SummaryPersonaDisabled') +
      LocalizedBoolean(RuntimeOptionsPage.Values[1]) + #13#10 +
    CustomMessage('SummarySafeMode') + LocalizedBoolean(IsSafeModeExpected) + #13#10 +
    'safe_mode_expected=' + BooleanIniValue(IsSafeModeExpected) + #13#10 + #13#10 +
    CustomMessage('SummaryPrerequisites') + #13#10 +
    PrerequisiteReport + #13#10 + #13#10 +
    CustomMessage('SummaryComponents') + #13#10 + SelectedComponentSummary + #13#10;

  if WizardIsComponentSelected('codex') then
    Result := Result + CustomMessage('SummaryCodexSnippet') + GetCodexSnippetPath('') + #13#10;
  if WizardIsComponentSelected('odysseus') then
    Result := Result + CustomMessage('SummaryOdysseusSnippet') + GetOdysseusSnippetPath('') + #13#10;
  if WizardIsComponentSelected('claude') then
    Result := Result + CustomMessage('SummaryClaudeFolder') + GetClaudeFolder('') + #13#10;
  if WizardIsComponentSelected('chatbridge') then
  begin
    Result := Result + CustomMessage('SummaryBridgeFolder') + GetBridgePath('') + #13#10;
    Result := Result + CustomMessage('SummaryBridgeConfig') + GetBridgeConfigPath + #13#10;
    Result := Result + CustomMessage('SummaryNativeStable') +
      ChatBridgeExtensionId + #13#10;
    Result := Result + CustomMessage('SummaryBridgeAutostart') + #13#10;
  end;

  Result := Result + #13#10 +
    CustomMessage('SummaryHostUnchanged') + #13#10 +
    CustomMessage('SummaryDataRemain') + #13#10;

  if not FileExists(GetGatewayServerPath) then
    Result := Result + #13#10 +
      CustomMessage('SummaryDevPayload') + #13#10;
  if Pos('<PYTHON_3_11_OR_NEWER>', ResolvePythonPath) = 1 then
    Result := Result +
      CustomMessage('SummaryPythonPlaceholder') + #13#10;
end;

procedure EnsureDirectory(Path: String);
begin
  if not ForceDirectories(Path) then
    RaiseException(CustomMessage('ErrorCreateDir') + Path);
end;

#include "assets\workspace-structure.iss"

function GetInstallerDiagnosticPath: String;
begin
  Result := ExpandConstant(
    '{localappdata}\PLwC\logs\setup\installer-diagnostic.log');
end;

function BuildInstallerDiagnosticRecord(
  EventName, AdditionalText: String): String;
begin
  Result :=
    GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':') + #13#10 +
    'event=' + EventName + #13#10 +
    'build_id=' + GetInstallerBuildId + #13#10 +
    'installer_revision={#InstallerRevision}' + #13#10 +
    'setup_exe_sha256=' + GetSetupExeSha256 + #13#10 +
    'gateway_version={#GatewayVersion}' + #13#10 +
    'node_bridge_version={#NodeBridgeVersion}' + #13#10 +
    'browser_extension_version={#BrowserExtensionVersion}' + #13#10 +
    'native_launcher_version={#NativeLauncherVersion}' + #13#10 +
    'installation_mode=' + GetInstallationMode + #13#10 +
    'selected_components=' + GetSelectedComponentIds + #13#10;
  if AdditionalText <> '' then
    Result := Result + AdditionalText;
  Result := Result + #13#10;
end;

procedure AppendInstallerDiagnosticRecord(
  EventName, AdditionalText: String);
var
  DiagnosticPath: String;
begin
  DiagnosticPath := GetInstallerDiagnosticPath;
  EnsureDirectory(ExtractFileDir(DiagnosticPath));
  if not SaveStringToFile(
    DiagnosticPath,
    BuildInstallerDiagnosticRecord(EventName, AdditionalText),
    True) then
    RaiseException(CustomMessage('ErrorDiagnostic'));
end;

function QuoteMaintenanceArgument(Value: String): String;
begin
  Result := '"' + Value + '"';
end;

function GetInstallerSelectionPath: String;
begin
  Result := GetConfigPath('') + '\installer\selection.ini';
end;

function GetInstalledPayloadManifestPath: String;
begin
  Result := GetAppPath + '\installation\payload-manifest.json';
end;

function GetInstallerMaintenanceReportPath(ActionName: String): String;
begin
  if ActionName = 'preflight-prepare' then
    Result := InstallerPreflightReportPath
  else if ActionName = 'rollback' then
    Result := InstallerRollbackReportPath
  else
    Result := InstallerPostflightReportPath;
end;

function BuildInstallerMaintenanceArguments(ActionName: String): String;
begin
  Result :=
    QuoteMaintenanceArgument(ExpandConstant('{tmp}\installer-maintenance.py')) +
    ' ' + ActionName +
    ' --installation-root ' + QuoteMaintenanceArgument(GetDataRoot) +
    ' --app-root ' + QuoteMaintenanceArgument(GetAppPath) +
    ' --gateway-root ' + QuoteMaintenanceArgument(GetGatewayPath('')) +
    ' --bridge-root ' + QuoteMaintenanceArgument(GetBridgePath('')) +
    ' --workspace-root ' + QuoteMaintenanceArgument(GetWorkspacePath('')) +
    ' --profile-root ' + QuoteMaintenanceArgument(GetProfilesPath('')) +
    ' --config-root ' + QuoteMaintenanceArgument(GetConfigPath('')) +
    ' --state-root ' + QuoteMaintenanceArgument(GetStatePath('')) +
    ' --logs-root ' + QuoteMaintenanceArgument(GetLogsPath('')) +
    ' --backups-root ' + QuoteMaintenanceArgument(GetBackupsPath('')) +
    ' --selection-path ' + QuoteMaintenanceArgument(GetInstallerSelectionPath) +
    ' --transaction-path ' + QuoteMaintenanceArgument(InstallerMigrationTransactionPath) +
    ' --report-path ' + QuoteMaintenanceArgument(GetInstallerMaintenanceReportPath(ActionName));
  if ActionName = 'postflight' then
    Result := Result +
      ' --payload-manifest ' + QuoteMaintenanceArgument(GetInstalledPayloadManifestPath) +
      ' --extension-id ' + ChatBridgeExtensionId;
end;

function RunInstallerMaintenance(ActionName: String; var ResultCode: Integer): Boolean;
var
  Parameters: String;
  Started: Boolean;
begin
  ResultCode := -1;
  Parameters := BuildInstallerMaintenanceArguments(ActionName);
  Log('Executing r26 installer maintenance action: ' + ActionName);
  Started := Exec(
    ResolvePythonPath,
    Parameters,
    ExpandConstant('{tmp}'),
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode);
  Result := Started and (ResultCode = 0);
  Log(
    'r26 installer maintenance action=' + ActionName +
    '; started=' + IntToStr(Ord(Started)) +
    '; exit=' + IntToStr(ResultCode) +
    '; report=' + GetInstallerMaintenanceReportPath(ActionName));
end;

procedure PrepareInstallerMigration;
var
  ResultCode: Integer;
begin
  WizardForm.StatusLabel.Caption := CustomMessage('InstallerMigrationStatus');
  InstallerMigrationTransactionPath := GetStatePath('') +
    '\installation\r26-installer-transaction.json';
  InstallerPreflightReportPath := GetLogsPath('') +
    '\setup\r26-installer-preflight.json';
  InstallerPostflightReportPath := GetLogsPath('') +
    '\setup\r26-installer-postflight.json';
  InstallerRollbackReportPath := GetLogsPath('') +
    '\setup\r26-installer-rollback.json';
  EnsureDirectory(ExtractFileDir(InstallerMigrationTransactionPath));
  EnsureDirectory(ExtractFileDir(InstallerPostflightReportPath));
  ExtractTemporaryFile('installer-maintenance.py');
  ExtractTemporaryFile('installer_state.py');
  ExtractTemporaryFile('doctor.py');
  if not RunInstallerMaintenance('preflight-prepare', ResultCode) then
  begin
    AppendInstallerDiagnosticRecord(
      'installer_preflight',
      'status=failure' + #13#10 +
      'exit_code=' + IntToStr(ResultCode) + #13#10 +
      'report=' + InstallerPreflightReportPath + #13#10);
    RaiseException(
      CustomMessage('ErrorInstallerPreflight') + #13#10 +
      InstallerPreflightReportPath + #13#10 +
      'Exit code: ' + IntToStr(ResultCode));
  end;
  AppendInstallerDiagnosticRecord(
    'installer_preflight',
    'status=prepared' + #13#10 +
    'transaction=' + InstallerMigrationTransactionPath + #13#10 +
    'legacy_bridge=' + LegacyBridgePath + #13#10 +
    'target_bridge=' + GetBridgePath('') + #13#10);
  InstallerMigrationPrepared := True;
end;

function RollbackInstallerMigration: Boolean;
var
  ResultCode: Integer;
begin
  Result := RunInstallerMaintenance('rollback', ResultCode);
  InstallerRollbackAttempted := True;
  if not Result then
    Log('r26 installer rollback failed with exit code ' + IntToStr(ResultCode));
end;

procedure RunHardInstallerPostflight;
var
  ResultCode: Integer;
begin
  WizardForm.StatusLabel.Caption := CustomMessage('InstallerPostflightStatus');
  if not RunInstallerMaintenance('postflight', ResultCode) then
    RaiseException(
      CustomMessage('ErrorInstallerPostflight') + #13#10 +
      InstallerPostflightReportPath + #13#10 +
      'Exit code: ' + IntToStr(ResultCode));
end;

procedure SetPrerequisitePhase(Phase: String);
begin
  CurrentPrerequisitePhase := Phase;
  Log('Prerequisite phase: ' + Phase);
end;

procedure ReportPrerequisiteException(Phase, ErrorText: String);
var
  DiagnosticPath: String;
  DiagnosticText: String;
begin
  DiagnosticPath := GetInstallerDiagnosticPath;
  DiagnosticText := BuildInstallerDiagnosticRecord(
    'prerequisite_failure',
    'phase=' + Phase + #13#10 +
    'error=' + ErrorText + #13#10);
  Log(
    'Unexpected prerequisite error; build={#AppVersion}-{#InstallerRevision}' +
    ' phase=' + Phase + ' error=' + ErrorText);
  if ForceDirectories(ExtractFileDir(DiagnosticPath)) then
    SaveStringToFile(DiagnosticPath, DiagnosticText, True);
  MsgBox(
    CustomMessage('PrereqUnexpectedFailure') + #13#10 + #13#10 +
    CustomMessage('PrereqUnexpectedPhase') + Phase + #13#10 +
    CustomMessage('PrereqUnexpectedDetails') + ErrorText + #13#10 +
    CustomMessage('PrereqUnexpectedLog') + DiagnosticPath,
    mbError,
    MB_OK);
end;

function GetPrerequisiteLogRoot: String;
begin
  Result := GetDataRoot + '\logs\setup\prerequisites';
end;

function CreatePrerequisiteLogPath(ComponentId: String): String;
begin
  EnsureDirectory(GetPrerequisiteLogRoot);
  Result := AddBackslash(GetPrerequisiteLogRoot) +
    GetDateTimeString('yyyymmdd-hhnnss', #0, #0) + '-' + ComponentId + '.log';
end;

procedure AppendPrerequisiteStatusLog(
  LogPath, ComponentName, Executable, Parameters: String;
  Started: Boolean; ResultCode: Integer);
var
  StatusText: String;
begin
  if Started then
    StatusText := 'started'
  else
    StatusText := 'launch_failed';
  SaveStringToFile(
    LogPath,
    Chr(13) + Chr(10) + '[PLwC Setup]' + #13#10 +
    'timestamp=' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':') + #13#10 +
    'component=' + ComponentName + #13#10 +
    'status=' + StatusText + #13#10 +
    'executable=' + Executable + #13#10 +
    'parameters=' + Parameters + #13#10 +
    'exit_code=' + IntToStr(ResultCode) + #13#10,
    True);
  Log(
    'Prerequisite component=' + ComponentName +
    ' started=' + StatusText +
    ' exit_code=' + IntToStr(ResultCode) +
    ' diagnostic_log=' + LogPath);
end;

function PrerequisiteExitCodeHint(Started: Boolean; ResultCode: Integer): String;
begin
  if (ResultCode = 1223) or (ResultCode = 1602) then
    Result := CustomMessage('PrereqFailureUacCancelled')
  else if (not Started) and ((ResultCode = 2) or (ResultCode = 3)) then
    Result := CustomMessage('PrereqFailurePath')
  else if not Started then
    Result := CustomMessage('PrereqFailureLaunch')
  else
  begin
    case ResultCode of
      0:
        Result := CustomMessage('PrereqFailureNotDetected');
      1603:
        Result := CustomMessage('PrereqFailureFatal');
      1618:
        Result := CustomMessage('PrereqFailureBusy');
    else
      Result := '';
    end;
  end;
end;

procedure ShowPrerequisiteFailure(
  BaseMessage, ComponentName: String; Started: Boolean; ResultCode: Integer;
  LogPath, NextStep: String);
var
  ErrorMessage: String;
  Hint: String;
begin
  Hint := PrerequisiteExitCodeHint(Started, ResultCode);
  ErrorMessage := BaseMessage + #13#10 + #13#10 +
    CustomMessage('PrereqFailureComponent') + ComponentName + #13#10 +
    CustomMessage('PrereqFailureExitCode') + IntToStr(ResultCode) + #13#10 +
    CustomMessage('PrereqFailureLog') + LogPath;
  if Hint <> '' then
    ErrorMessage := ErrorMessage + #13#10 + #13#10 + Hint;
  ErrorMessage := ErrorMessage + #13#10 + #13#10 + NextStep;
  MsgBox(ErrorMessage, mbError, MB_OK);
end;

procedure StoreInstallerRoots;
begin
  if not RegWriteStringValue(HKCU, InstallerSettingsKey, 'AppPath', GetAppPath) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'GatewayPath', GetGatewayPath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'BridgePath', GetBridgePath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'WorkspacePath', GetWorkspacePath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'ProfilesPath', GetProfilesPath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'ConfigPath', GetConfigPath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'StatePath', GetStatePath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'LogsPath', GetLogsPath('')) or
     not RegWriteStringValue(HKCU, InstallerSettingsKey, 'BackupsPath', GetBackupsPath('')) then
    RaiseException(CustomMessage('ErrorStoreDirs'));
end;

procedure SynchronizeSharedSettings; forward;

procedure SaveGeneratedFiles;
var
  SelectionPath: String;
begin
  EnsureDirectory(GetConfigPath('') + '\installer');
  EnsureDirectory(GetLogsPath(''));
  EnsureDirectory(GetBackupsPath(''));
  EnsureDirectory(GetStatePath(''));
  EnsureWorkspaceStructureAt(GetWorkspacePath(''));
  EnsureDirectory(GetProfilesPath(''));
  EnsureDirectory(AddBackslash(GetProfilesPath('')) + GetProfileName);

  SelectionPath := GetConfigPath('') + '\installer\selection.ini';
  SetIniString('PLwC', 'AppPath', GetAppPath, SelectionPath);
  SetIniString('PLwC', 'GatewayPath', GetGatewayPath(''), SelectionPath);
  SetIniString('PLwC', 'BridgePath', GetBridgePath(''), SelectionPath);
  SetIniString('PLwC', 'WorkspacePath', GetWorkspacePath(''), SelectionPath);
  SetIniString('PLwC', 'ProfilesPath', GetProfilesPath(''), SelectionPath);
  SetIniString('PLwC', 'ConfigPath', GetConfigPath(''), SelectionPath);
  SetIniString('PLwC', 'StatePath', GetStatePath(''), SelectionPath);
  SetIniString('PLwC', 'LogsPath', GetLogsPath(''), SelectionPath);
  SetIniString('PLwC', 'BackupsPath', GetBackupsPath(''), SelectionPath);
  SetIniString('PLwC', 'ActiveProfile', GetProfileName, SelectionPath);
  SetIniString('PLwC', 'SecurityConfig', GetSecurityConfigPath, SelectionPath);
  SetIniString('PLwC', 'MemoryWriteThreshold', GetMemoryThreshold, SelectionPath);
  SetIniString('PLwC', 'PersonaWriteThreshold', GetPersonaThreshold, SelectionPath);
  SetIniString('PLwC', 'TemperamentWriteThreshold', GetTemperamentThreshold, SelectionPath);
  SetIniString('PLwC', 'QdrantEnabled', GetQdrantEnabled, SelectionPath);
  SetIniString('PLwC', 'PersonaLayerDisabled', GetPersonaLayerDisabled, SelectionPath);
  SetIniString(
    'PLwC', 'SafeModeExpected', BooleanIniValue(IsSafeModeExpected), SelectionPath);
  SetIniString('BuildIdentity', 'BuildId', GetInstallerBuildId, SelectionPath);
  SetIniString('BuildIdentity', 'InstallerRevision', '{#InstallerRevision}', SelectionPath);
  SetIniString('BuildIdentity', 'SetupExeSha256', GetSetupExeSha256, SelectionPath);
  SetIniString('BuildIdentity', 'GatewayVersion', '{#GatewayVersion}', SelectionPath);
  SetIniString('BuildIdentity', 'NodeBridgeVersion', '{#NodeBridgeVersion}', SelectionPath);
  SetIniString(
    'BuildIdentity', 'BrowserExtensionVersion',
    '{#BrowserExtensionVersion}', SelectionPath);
  SetIniString(
    'BuildIdentity', 'NativeLauncherVersion',
    '{#NativeLauncherVersion}', SelectionPath);
  SetIniString('BuildIdentity', 'InstallationMode', GetInstallationMode, SelectionPath);
  if ExistingInstallDetected then
    SetIniString('BuildIdentity', 'InstallAction', 'update', SelectionPath)
  else
    SetIniString('BuildIdentity', 'InstallAction', 'install', SelectionPath);
  SetIniString(
    'BuildIdentity', 'SelectedComponents',
    GetSelectedComponentIds, SelectionPath);
  SetIniString('Diagnostics', 'PythonPath', DetectedPythonPath, SelectionPath);
  SetIniString('Diagnostics', 'NodePath', DetectedNodePath, SelectionPath);
  SetIniString('Diagnostics', 'BrowserPath', DetectedBrowserPath, SelectionPath);
  SetIniString('Diagnostics', 'ChromeDetected', BooleanIniValue(ChromeDetected), SelectionPath);
  SetIniString('Diagnostics', 'EdgeDetected', BooleanIniValue(EdgeDetected), SelectionPath);
  SetIniString('Diagnostics', 'BraveDetected', BooleanIniValue(BraveDetected), SelectionPath);
  SetIniString('Diagnostics', 'DockerDesktopInstalled', BooleanIniValue(DockerDesktopInstalled), SelectionPath);
  SetIniString('Diagnostics', 'DockerDesktopPath', DetectedDockerDesktopPath, SelectionPath);
  SetIniString('Diagnostics', 'DockerCliPath', DetectedDockerPath, SelectionPath);
  SetIniString('Diagnostics', 'DockerDaemonReachable', BooleanIniValue(DockerDaemonOK), SelectionPath);
  SetIniString('Diagnostics', 'DockerImagesAvailable', BooleanIniValue(DockerImagesOK), SelectionPath);
  SetIniString('Diagnostics', 'Wsl2Available', BooleanIniValue(Wsl2OK), SelectionPath);
  SetIniString('Diagnostics', 'VirtualizationCapability', BooleanIniValue(VirtualizationCapabilityOK), SelectionPath);
  SetIniString('Diagnostics', 'VirtualMachineDetected', BooleanIniValue(VirtualMachineDetected), SelectionPath);
  SetIniString('Diagnostics', 'NestedVirtualizationAvailable', BooleanIniValue(NestedVirtualizationOK), SelectionPath);
  SetIniString('Components', 'ClaudeMCPB', BooleanIniValue(WizardIsComponentSelected('claude')), SelectionPath);
  SetIniString('Components', 'CodexSTDIO', BooleanIniValue(WizardIsComponentSelected('codex')), SelectionPath);
  SetIniString('Components', 'OdysseusSTDIO', BooleanIniValue(WizardIsComponentSelected('odysseus')), SelectionPath);
  SetIniString('Components', 'ChatBridge', BooleanIniValue(WizardIsComponentSelected('chatbridge')), SelectionPath);

  if WizardIsComponentSelected('codex') then
  begin
    EnsureDirectory(ExtractFileDir(GetCodexSnippetPath('')));
    if not SaveStringToFile(GetCodexSnippetPath(''), BuildCodexSnippet, False) then
      RaiseException(CustomMessage('ErrorCodexSnippet'));
  end;

  if WizardIsComponentSelected('odysseus') then
  begin
    EnsureDirectory(ExtractFileDir(GetOdysseusSnippetPath('')));
    if not SaveStringToFile(GetOdysseusSnippetPath(''), BuildOdysseusSnippet, False) then
      RaiseException(CustomMessage('ErrorOdysseusSnippet'));
  end;

  if WizardIsComponentSelected('chatbridge') then
  begin
    EnsureDirectory(ExtractFileDir(GetBridgeConfigPath));
    if not SaveStringToFile(GetBridgeConfigPath, BuildBridgeConfig, False) then
      RaiseException(CustomMessage('ErrorBridgeConfig'));
  end;

  SynchronizeSharedSettings;

  if not SaveStringToFile(GetInstallSummaryPath(''), BuildInstallSummary, False) then
    RaiseException(CustomMessage('ErrorSummary'));
end;

procedure SynchronizeSharedSettings;
var
  ResultCode: Integer;
  Started: Boolean;
  Parameters: String;
begin
  if not FileExists(GetConfigurationScriptPath) then
    RaiseException(CustomMessage('ErrorSharedSync') + ' -1');
  Parameters := GetConfigurationArguments('') +
    ' --sync-installation --no-browser';
  ResultCode := -1;
  Started := Exec(
    ResolvePythonPath,
    Parameters,
    GetAppPath + '\configuration',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode);
  Log(
    'Shared settings synchronization: started=' + IntToStr(Ord(Started)) +
    '; exit=' + IntToStr(ResultCode));
  if (not Started) or (ResultCode <> 0) then
    RaiseException(CustomMessage('ErrorSharedSync') + ' ' + IntToStr(ResultCode));
end;

function GetBridgeScriptLanguage: String;
begin
  if CompareText(ActiveLanguage, 'german') = 0 then
    Result := 'de'
  else
    Result := 'en';
end;

function GetBridgeAutostartArguments(Param: String): String;
begin
  Result := '--start --delay-seconds 20 --lang ' + GetBridgeScriptLanguage;
end;

function VerifyBridgeAutostartShortcut: Boolean;
var
  ShellObject: Variant;
  ShortcutObject: Variant;
  ShortcutTarget: String;
  ShortcutArguments: String;
begin
  Result := False;
  if not FileExists(GetBridgeAutostartShortcutPath) then
  begin
    Log('PLwC Chat Bridge Startup shortcut is missing.');
    Exit;
  end;
  try
    ShellObject := CreateOleObject('WScript.Shell');
    ShortcutObject := ShellObject.CreateShortcut(GetBridgeAutostartShortcutPath);
    ShortcutTarget := ShortcutObject.TargetPath;
    ShortcutArguments := ShortcutObject.Arguments;
    Result :=
      (CompareText(
        NormalizePath(ShortcutTarget),
        NormalizePath(GetNativeHostExePath)) = 0) and
      (CompareText(
        Trim(ShortcutArguments),
        GetBridgeAutostartArguments('')) = 0);
    if not Result then
      Log(
        'PLwC Chat Bridge Startup shortcut target or arguments do not ' +
        'match the installed native launcher.');
  except
    Log(
      'PLwC Chat Bridge Startup shortcut verification failed: ' +
      GetExceptionMessage);
    Result := False;
  end;
end;

function ExecuteNativeLauncher(
  Arguments: String; var ResultCode: Integer): Boolean;
var
  Started: Boolean;
begin
  Result := False;
  ResultCode := -1;
  if not FileExists(GetNativeHostExePath) then
  begin
    Log('PLwC Chat Bridge native launcher is missing: ' + GetNativeHostExePath);
    Exit;
  end;
  Log('Executing PLwC Chat Bridge native launcher: ' + Arguments);
  Started := Exec(
    GetNativeHostExePath,
    Arguments,
    GetBridgePath(''),
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode);
  Result := Started and (ResultCode = 0);
  Log(
    'PLwC Chat Bridge native launcher result: started=' +
    IntToStr(Ord(Started)) + '; exit=' + IntToStr(ResultCode));
end;

function FindDockerDesktopExecutable: String;
begin
  Result := FindDockerDesktopApplicationPath;
end;

procedure StartDockerDesktopAfterSetup;
var
  DockerDesktopPath: String;
  ResultCode: Integer;
  Started: Boolean;
begin
  if not DockerInstalledBySetup then
    Exit;

  DockerDesktopPath := FindDockerDesktopExecutable;
  if DockerDesktopPath = '' then
  begin
    Log(
      'Docker Desktop was installed by setup, but its desktop executable ' +
      'was not found for first launch.');
    Exit;
  end;

  ResultCode := -1;
  Started := ExecAsOriginalUser(
    DockerDesktopPath,
    '',
    ExtractFileDir(DockerDesktopPath),
    SW_SHOWNORMAL,
    ewNoWait,
    ResultCode);
  if not Started then
    Started := Exec(
      DockerDesktopPath,
      '',
      ExtractFileDir(DockerDesktopPath),
      SW_SHOWNORMAL,
      ewNoWait,
      ResultCode);
  Log(
    'Docker Desktop first launch requested: started=' +
    IntToStr(Ord(Started)) + '; path=' + DockerDesktopPath);
end;

procedure ConfigureChatBridgeWindowsIntegration;
var
  ResultCode: Integer;
  RollbackCode: Integer;
  FailurePhase: String;
begin
  if not WizardIsComponentSelected('chatbridge') then
    Exit;

  if not FileExists(GetNativeHostExePath) then
  begin
    Log(CustomMessage('LogNativeHostMissing') + GetNativeHostExePath);
    RaiseException(CustomMessage('ErrorNativeHostMissing') + GetNativeHostExePath);
  end;

  WizardForm.StatusLabel.Caption := CustomMessage('BridgeIntegrationStatus');
  FailurePhase := 'legacy_autostart_migration';
  if ExecuteNativeLauncher('--remove-legacy-autostart', ResultCode) then
  begin
    FailurePhase := 'native_messaging_registration';
    if ExecuteNativeLauncher(
      '--register --browser all --lang ' + GetBridgeScriptLanguage +
      ' --extension-id ' + ChatBridgeExtensionId,
      ResultCode) then
    begin
      FailurePhase := 'native_messaging_status';
      if ExecuteNativeLauncher('--status --browser all', ResultCode) then
      begin
        FailurePhase := 'startup_shortcut';
        if VerifyBridgeAutostartShortcut then
        begin
          FailurePhase := 'bridge_identity_and_tools';
          if ExecuteNativeLauncher(
            '--start --lang ' + GetBridgeScriptLanguage,
            ResultCode) then
          begin
            AppendInstallerDiagnosticRecord(
              'chat_bridge_postflight',
              'status=success' + #13#10 +
              'native_launcher=verified' + #13#10 +
              'startup_shortcut=verified' + #13#10 +
              'build_identity=verified' + #13#10 +
              'tool_count=8' + #13#10);
            Exit;
          end;
        end
        else
          ResultCode := -2;
      end;
    end;
  end;

  AppendInstallerDiagnosticRecord(
    'chat_bridge_postflight',
    'status=failure' + #13#10 +
    'phase=' + FailurePhase + #13#10 +
    'exit_code=' + IntToStr(ResultCode) + #13#10);
  DeleteFile(GetBridgeAutostartShortcutPath);
  if FileExists(GetNativeHostExePath) then
  begin
    RollbackCode := -1;
    ExecuteNativeLauncher('--unregister --browser all', RollbackCode);
  end;
  RaiseException(CustomMessage('ErrorBridgeIntegration') + ' ' + IntToStr(ResultCode));
end;

procedure RemoveChatBridgeWindowsIntegration;
var
  ResultCode: Integer;
begin
  DeleteFile(GetBridgeAutostartShortcutPath);
  if FileExists(GetNativeHostExePath) then
  begin
    ExecuteNativeLauncher('--remove-legacy-autostart', ResultCode);
    ExecuteNativeLauncher('--unregister --browser all', ResultCode);
  end;
end;

procedure RemoveGeneratedFiles;
var
  ConfigPath: String;
begin
  ConfigPath := GetConfigPath('');
  DeleteFile(ConfigPath + '\installer\installation-summary.txt');
  DeleteFile(ConfigPath + '\installer\selection.ini');
  DeleteFile(ConfigPath + '\clients\codex\plwc-gateway.generated.toml');
  DeleteFile(ConfigPath + '\clients\odysseus\plwc-gateway.generated.json');
  DeleteFile(GetBridgeConfigPath);
  RemoveDir(ConfigPath + '\clients\codex');
  RemoveDir(ConfigPath + '\clients\odysseus');
  RemoveDir(ConfigPath + '\clients');
  RemoveDir(ConfigPath + '\installer');
  RemoveDir(GetBridgePath('') + '\config');
end;

procedure RemoveInstallerRootSettings;
begin
  RegDeleteValue(HKCU, InstallerSettingsKey, 'AppPath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'GatewayPath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'BridgePath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'WorkspacePath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'ProfilesPath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'ConfigPath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'StatePath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'LogsPath');
  RegDeleteValue(HKCU, InstallerSettingsKey, 'BackupsPath');
  RegDeleteKeyIfEmpty(HKCU, InstallerSettingsKey);
end;

procedure OpenOfficialDownloadPage(Url: String);
var
  ErrorCode: Integer;
begin
  if not ShellExec('', Url, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode) then
    MsgBox(CustomMessage('PrereqOpenPageFailed'), mbError, MB_OK);
end;

procedure PythonDownloadButtonClick(Sender: TObject);
begin
  OpenOfficialDownloadPage(PythonDownloadPageUrl);
  if not VCRuntimeOK then
    OpenOfficialDownloadPage(VCRuntimeDownloadPageUrl);
end;

procedure NodeDownloadButtonClick(Sender: TObject);
begin
  OpenOfficialDownloadPage(NodeDownloadPageUrl);
end;

procedure DockerDownloadButtonClick(Sender: TObject);
begin
  OpenOfficialDownloadPage(DockerDownloadPageUrl);
end;

function ExecutePrerequisiteInstaller(
  Executable, Parameters, ProgressText: String; ShowCmd: Integer;
  Elevated: Boolean; var ResultCode: Integer): Boolean; forward;

function FindWindowsCurl: String;
begin
  Result := '';
  if IsWin64 and FileExists(ExpandConstant('{sysnative}\curl.exe')) then
    Result := ExpandConstant('{sysnative}\curl.exe');
  if (Result = '') and FileExists(ExpandConstant('{sys}\curl.exe')) then
    Result := ExpandConstant('{sys}\curl.exe');
  if Result = '' then
    Result := FindExecutable('curl.exe');
end;

function DownloadVerifiedInstallerWithCurl(
  Url, FileName, Sha256: String; var DownloadedPath, ErrorText: String): Boolean;
var
  CurlPath: String;
  ResultCode: Integer;
begin
  Result := False;
  ErrorText := '';
  DownloadedPath := ExpandConstant('{tmp}\') + FileName;
  DeleteFile(DownloadedPath);
  CurlPath := FindWindowsCurl;
  if CurlPath = '' then
  begin
    ErrorText := CustomMessage('PrereqCurlUnavailable');
    Exit;
  end;

  ResultCode := -1;
  if (not ExecutePrerequisiteInstaller(
        CurlPath,
        '--fail --location --retry 2 --retry-all-errors ' +
          '--connect-timeout 30 --max-time 900 --silent --show-error ' +
          '--output "' + DownloadedPath + '" "' + Url + '"',
        CustomMessage('PrereqProgressFallbackDownload'),
        SW_HIDE,
        False,
        ResultCode)) or (ResultCode <> 0) then
  begin
    ErrorText := CustomMessage('PrereqCurlFailed') + IntToStr(ResultCode);
    Exit;
  end;

  if (not FileExists(DownloadedPath)) or
     (CompareText(GetSHA256OfFile(DownloadedPath), Sha256) <> 0) then
  begin
    DeleteFile(DownloadedPath);
    ErrorText := CustomMessage('PrereqDownloadHashMismatch');
    Exit;
  end;
  Result := True;
end;

function DownloadVerifiedInstaller(
  Url, FileName, Sha256: String; var DownloadedPath: String): Boolean;
var
  PrimaryError: String;
  FallbackError: String;
  ErrorMessage: String;
  AbortedByUser: Boolean;
begin
  Result := False;
  DownloadedPath := '';
  PrimaryError := '';
  AbortedByUser := False;
  DependencyDownloadPage.Clear;
  DependencyDownloadPage.Add(Url, FileName, Sha256);
  DependencyDownloadPage.Show;
  try
    try
      DependencyDownloadPage.Download;
      DownloadedPath := ExpandConstant('{tmp}\') + FileName;
      Result := FileExists(DownloadedPath);
    except
      AbortedByUser := DependencyDownloadPage.AbortedByUser;
      if not AbortedByUser then
      begin
        PrimaryError := GetExceptionMessage;
        Log('Primary prerequisite download failed for ' + FileName +
          ' from ' + Url + ': ' + PrimaryError);
      end;
    end;
  finally
    DependencyDownloadPage.Hide;
  end;

  if Result or AbortedByUser then
    Exit;

  if DownloadVerifiedInstallerWithCurl(
       Url, FileName, Sha256, DownloadedPath, FallbackError) then
  begin
    Result := True;
    Exit;
  end;

  ErrorMessage := CustomMessage('PrereqDownloadFailed') + FileName + #13#10 +
    Url + #13#10 + #13#10 + PrimaryError;
  if FallbackError <> '' then
    ErrorMessage := ErrorMessage + #13#10 + FallbackError;
  if Pos('12007', PrimaryError) > 0 then
    ErrorMessage := ErrorMessage + #13#10 + #13#10 +
      CustomMessage('PrereqDownloadDnsHint');
  ErrorMessage := ErrorMessage + #13#10 + #13#10 +
    CustomMessage('PrereqDownloadRetryHint');
  MsgBox(ErrorMessage, mbError, MB_OK);
end;

function IsSuccessfulInstallerExitCode(ResultCode: Integer): Boolean;
begin
  Result := (ResultCode = 0) or (ResultCode = 3010) or (ResultCode = 1641);
  if (ResultCode = 3010) or (ResultCode = 1641) then
    DependencyRestartRequired := True;
end;

function ExecutePrerequisiteInstaller(
  Executable, Parameters, ProgressText: String; ShowCmd: Integer;
  Elevated: Boolean; var ResultCode: Integer): Boolean;
var
  StandaloneProgress: Boolean;
  ProgressDetail: String;
begin
  Result := False;
  ResultCode := -1;
  if (Executable = '') or (not FileExists(Executable)) then
    Exit;

  StandaloneProgress := not PrerequisiteBatchActive;
  ProgressDetail := CustomMessage('PrereqProgressWait');
  if PrerequisiteBatchActive then
    ProgressDetail := ProgressDetail + #13#10 +
      CustomMessage('PrereqProgressPlanLocked') + PrerequisiteBatchPlan;
  DependencyInstallPage.SetText(
    ProgressText,
    ProgressDetail);
  if StandaloneProgress then
  begin
    DependencyInstallPage.Show;
    DependencyInstallPage.Animate;
  end;
  try
    if Elevated then
      Result := ShellExec(
        'runas', Executable, Parameters, '', ShowCmd,
        ewWaitUntilTerminated, ResultCode)
    else
      Result := Exec(
        Executable, Parameters, '', ShowCmd,
        ewWaitUntilTerminated, ResultCode);
  finally
    if StandaloneProgress then
      DependencyInstallPage.Hide;
  end;
end;

function InstallVCRuntimePrerequisite(ForceInstall: Boolean): Boolean;
var
  InstallerPath: String;
  LogPath: String;
  Parameters: String;
  ResultCode: Integer;
  Started: Boolean;
  InstallExitOK: Boolean;
begin
  ProbeVCRuntime;
  if VCRuntimeOK and (not ForceInstall) then
  begin
    Result := True;
    Exit;
  end;

  Result := False;
  ResultCode := -1;
  Started := False;
  SetPrerequisitePhase(CustomMessage('PrereqPhaseVCRuntimeDownload'));
  if not DownloadVerifiedInstaller(
       VCRuntimeInstallerUrl,
       VCRuntimeInstallerFileName,
       VCRuntimeInstallerSha256,
       InstallerPath) then
    Exit;

  SetPrerequisitePhase(CustomMessage('PrereqPhaseVCRuntimePrepare'));
  LogPath := CreatePrerequisiteLogPath('vc-runtime');
  Parameters := '/install /passive /norestart /log "' + LogPath + '"';
  SetPrerequisitePhase(CustomMessage('PrereqPhaseVCRuntimeInstall'));
  Started := ExecutePrerequisiteInstaller(
    InstallerPath,
    Parameters,
    CustomMessage('PrereqProgressVCRuntime'),
    SW_SHOW,
    True,
    ResultCode);
  AppendPrerequisiteStatusLog(
    LogPath,
    'Microsoft Visual C++ runtime x64 14.51.36247',
    InstallerPath,
    Parameters,
    Started,
    ResultCode);

  InstallExitOK := IsSuccessfulInstallerExitCode(ResultCode) or
    (ResultCode = 1638);
  if (not Started) or (not InstallExitOK) then
  begin
    ShowPrerequisiteFailure(
      CustomMessage('PrereqVCRuntimeInstallFailed'),
      CustomMessage('PrereqComponentVCRuntime'),
      Started,
      ResultCode,
      LogPath,
      CustomMessage('PrereqFailureNextVCRuntime'));
    Exit;
  end;
  if DependencyRestartRequired then
  begin
    Result := True;
    Exit;
  end;

  ProbeVCRuntime;
  Result := VCRuntimeOK;
  if not Result then
    ShowPrerequisiteFailure(
      CustomMessage('PrereqVCRuntimeInstallFailed'),
      CustomMessage('PrereqComponentVCRuntime'),
      Started,
      ResultCode,
      LogPath,
      CustomMessage('PrereqFailureNextVCRuntime'));
end;

function InstallPythonPrerequisite: Boolean;
var
  InstallerPath: String;
  LockPath: String;
  LogPath: String;
  Parameters: String;
  PythonPathForRuntime: String;
  ResultCode: Integer;
  Started: Boolean;
begin
  Result := False;
  LogPath := '';
  ResultCode := -1;
  Started := False;
  PythonPathForRuntime := '';

  if not PythonVersionOK then
  begin
    SetPrerequisitePhase(CustomMessage('PrereqPhasePythonDownload'));
    if not DownloadVerifiedInstaller(
         PythonInstallerUrl,
         PythonInstallerFileName,
         PythonInstallerSha256,
         InstallerPath) then
      Exit;

    SetPrerequisitePhase(CustomMessage('PrereqPhasePythonPrepare'));
    LogPath := CreatePrerequisiteLogPath('python-installer');
    Parameters :=
      '/passive InstallAllUsers=0 PrependPath=1 Include_pip=1 ' +
      'Include_test=0 SimpleInstall=1 /log "' + LogPath + '"';
#ifdef UiSmokeDownloadFixture
    Log('UI_SMOKE_DOWNLOAD_VERIFIED');
    Log('UI_SMOKE_POST_DOWNLOAD_PREPARED path=' + LogPath);
    DeleteFile(InstallerPath);
    Result := True;
    Exit;
#endif
    SetPrerequisitePhase(CustomMessage('PrereqPhasePythonInstall'));
    Started := ExecutePrerequisiteInstaller(
      InstallerPath,
      Parameters,
      CustomMessage('PrereqProgressPython'),
      SW_SHOW,
      False,
      ResultCode);
    AppendPrerequisiteStatusLog(
        LogPath, 'Python 3.13', InstallerPath, Parameters, Started, ResultCode);
    if (not Started) or (not IsSuccessfulInstallerExitCode(ResultCode)) then
    begin
      ShowPrerequisiteFailure(
        CustomMessage('PrereqPythonInstallFailed'),
        CustomMessage('PrereqComponentPython'),
        Started,
        ResultCode,
        LogPath,
        CustomMessage('PrereqFailureNextPython'));
      Exit;
    end;
    if DependencyRestartRequired then
    begin
      Result := True;
      Exit;
    end;
    ProbePython;
  end;

  if PythonVersionOK and ((not PythonRuntimeOK) or (not VCRuntimeOK)) then
  begin
    PythonPathForRuntime := DetectedPythonPath;
    if not VCRuntimeOK then
    begin
      VCRuntimeRepairAttempted := True;
      if not InstallVCRuntimePrerequisite(False) then
        Exit;
      if DependencyRestartRequired then
      begin
        Result := True;
        Exit;
      end;
    end;

    ProbeVCRuntime;
    LogPath := CreatePrerequisiteLogPath('python-runtime-probe');
    PythonRuntimeOK := VCRuntimeOK and
      RunPythonRuntimeProbe(PythonPathForRuntime, LogPath);
    if PythonRuntimeOK then
    begin
      DetectedPythonPath := PythonPathForRuntime;
      Result := PythonPrerequisitesOK;
      Exit;
    end;

    SetPrerequisitePhase(CustomMessage('PrereqPhasePythonModules'));
    ExtractTemporaryFile('mcp-runtime-lock.txt');
    LockPath := ExpandConstant('{tmp}\mcp-runtime-lock.txt');
    LogPath := CreatePrerequisiteLogPath('python-modules');
    Parameters :=
      '-m pip --disable-pip-version-check --no-input --log "' + LogPath +
      '" install --user --only-binary=:all: --require-hashes -r "' +
      LockPath + '"';
    ResultCode := -1;
    Started := ExecutePrerequisiteInstaller(
      PythonPathForRuntime,
      Parameters,
      CustomMessage('PrereqProgressMcp'),
      SW_HIDE,
      False,
      ResultCode);
    AppendPrerequisiteStatusLog(
      LogPath, 'PLwC Python modules', PythonPathForRuntime, Parameters,
      Started, ResultCode);
    if (not Started) or (ResultCode <> 0) then
    begin
      ShowPrerequisiteFailure(
        CustomMessage('PrereqPythonInstallFailed'),
        CustomMessage('PrereqComponentPythonModules'),
        Started,
        ResultCode,
        LogPath,
        CustomMessage('PrereqFailureNextPython'));
      Exit;
    end;
    PythonVersionOK := RunProbeWithTimeout(
      PythonPathForRuntime,
      '-c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"',
      5000);
    DetectedPythonPath := PythonPathForRuntime;
    PythonRuntimeOK := PythonVersionOK and VCRuntimeOK and
      RunPythonRuntimeProbe(PythonPathForRuntime, LogPath);
    if (not PythonRuntimeOK) and (not VCRuntimeRepairAttempted) then
    begin
      VCRuntimeRepairAttempted := True;
      Log(
        'PLwC Python imports still fail after pip; repairing the pinned ' +
        'Microsoft Visual C++ runtime once.');
      if not InstallVCRuntimePrerequisite(True) then
        Exit;
      if DependencyRestartRequired then
      begin
        Result := True;
        Exit;
      end;
      ProbeVCRuntime;
      LogPath := CreatePrerequisiteLogPath('python-runtime-repair-probe');
      PythonRuntimeOK := PythonVersionOK and VCRuntimeOK and
        RunPythonRuntimeProbe(PythonPathForRuntime, LogPath);
    end;
  end;

  Result := PythonPrerequisitesOK;
  if not Result then
    ShowPrerequisiteFailure(
      CustomMessage('PrereqPythonInstallFailed'),
      CustomMessage('PrereqComponentPythonBundle'),
      Started,
      ResultCode,
      LogPath,
      CustomMessage('PrereqFailureNextPython'));
end;

function InstallNodePrerequisite: Boolean;
var
  InstallerPath: String;
  MsiexecPath: String;
  LogPath: String;
  Parameters: String;
  ResultCode: Integer;
  Started: Boolean;
begin
  if NodeVersionOK then
  begin
    Result := True;
    Exit;
  end;

  Result := False;
  SetPrerequisitePhase(CustomMessage('PrereqPhaseNodeDownload'));
  if not DownloadVerifiedInstaller(
       NodeInstallerUrl,
       NodeInstallerFileName,
       NodeInstallerSha256,
       InstallerPath) then
    Exit;

  SetPrerequisitePhase(CustomMessage('PrereqPhaseNodePrepare'));
  { The Sysnative alias is not resolvable after the UAC ShellExecute handoff. }
  MsiexecPath := ExpandConstant('{sys}\msiexec.exe');
  LogPath := CreatePrerequisiteLogPath('node-msi');
  Parameters :=
    '/i "' + InstallerPath + '" /passive /norestart ALLUSERS=1 ' +
    '/L*v "' + LogPath + '"';
  ResultCode := -1;
  SetPrerequisitePhase(CustomMessage('PrereqPhaseNodeInstall'));
  Started := ExecutePrerequisiteInstaller(
    MsiexecPath,
    Parameters,
    CustomMessage('PrereqProgressNode'),
    SW_SHOW,
    True,
    ResultCode);
  AppendPrerequisiteStatusLog(
    LogPath, 'Node.js 24 LTS', MsiexecPath, Parameters, Started, ResultCode);
  if (not Started) or (not IsSuccessfulInstallerExitCode(ResultCode)) then
  begin
    ShowPrerequisiteFailure(
      CustomMessage('PrereqNodeInstallFailed'),
      CustomMessage('PrereqComponentNode'),
      Started,
      ResultCode,
      LogPath,
      CustomMessage('PrereqFailureNextNode'));
    Exit;
  end;
  if DependencyRestartRequired then
  begin
    Result := True;
    Exit;
  end;
  ProbeNode;
  Result := NodeVersionOK;
  if not Result then
    ShowPrerequisiteFailure(
      CustomMessage('PrereqNodeInstallFailed'),
      CustomMessage('PrereqComponentNode'),
      Started,
      ResultCode,
      LogPath,
      CustomMessage('PrereqFailureNextNode'));
end;

function InstallDockerPrerequisite: Boolean;
var
  InstallerPath: String;
  LogPath: String;
  Parameters: String;
  ResultCode: Integer;
  Started: Boolean;
begin
  if DockerCliOK then
  begin
    Result := True;
    Exit;
  end;

  Result := False;
  SetPrerequisitePhase(CustomMessage('PrereqPhaseDockerDownload'));
  if not DownloadVerifiedInstaller(
       DockerInstallerUrl,
       DockerInstallerFileName,
       DockerInstallerSha256,
       InstallerPath) then
    Exit;

  SetPrerequisitePhase(CustomMessage('PrereqPhaseDockerPrepare'));
  LogPath := CreatePrerequisiteLogPath('docker-desktop');
  Parameters := 'install --user --quiet --backend=wsl-2 --no-windows-containers';
  ResultCode := -1;
  SetPrerequisitePhase(CustomMessage('PrereqPhaseDockerInstall'));
  Started := ExecutePrerequisiteInstaller(
    InstallerPath,
    Parameters,
    CustomMessage('PrereqProgressDocker'),
    SW_SHOW,
    False,
    ResultCode);
  AppendPrerequisiteStatusLog(
    LogPath, 'Docker Desktop', InstallerPath, Parameters, Started, ResultCode);
  if Started and IsSuccessfulInstallerExitCode(ResultCode) then
  begin
    DockerInstalledBySetup := True;
    ProbeDocker;
    Result := True;
  end
  else
    ShowPrerequisiteFailure(
      CustomMessage('PrereqDockerInstallFailed'),
      CustomMessage('PrereqComponentDocker'),
      Started,
      ResultCode,
      LogPath,
      CustomMessage('PrereqFailureNextDocker'));
end;

function SelectedPrerequisiteDownloadMiB: Integer;
begin
  Result := 0;
  if PrerequisiteActionsPage.Values[0] then
    Result := Result + {#PythonDownloadMiB};
  if PrerequisiteActionsPage.Values[1] then
    Result := Result + {#NodeDownloadMiB};
  if PrerequisiteActionsPage.Values[2] then
    Result := Result + {#DockerDownloadMiB};
end;

function BuildPrerequisiteSizeText: String;
begin
  Result :=
    CustomMessage('SizeHeading') + #13#10 +
    CustomMessage('SizePlwc') + #13#10 +
    CustomMessage('SizePython') + #13#10 +
    CustomMessage('SizeNode') + #13#10 +
    CustomMessage('SizeDocker') + #13#10 +
    CustomMessage('SizeWslImages') + CustomMessage('SizeUnknown') +
      CustomMessage('SizeWslImagesNote') + #13#10 +
    CustomMessage('SizeFirstUse') + CustomMessage('SizeUnknown') + #13#10 + #13#10 +
    CustomMessage('SizeSelected') +
      IntToStr(SelectedPrerequisiteDownloadMiB) + ' MB' + #13#10 +
    CustomMessage('SizeSelectedVariable') +
      CustomMessage('SizeUnknown') + #13#10 +
    CustomMessage('SizeEstimateAsOf') + #13#10 +
      CustomMessage('SizeLogLocation') + GetPrerequisiteLogRoot;
end;

procedure AppendPrerequisitePlanItem(var PlanText: String; ItemText: String);
begin
  if PlanText <> '' then
    PlanText := PlanText + '; ';
  PlanText := PlanText + ItemText;
end;

function BuildPrerequisiteBatchPlan(
  InstallPythonSelected, InstallNodeSelected,
  InstallDockerSelected: Boolean): String;
begin
  Result := '';
  if InstallPythonSelected then
    AppendPrerequisitePlanItem(
      Result, CustomMessage('PrereqComponentPythonBundle'));
  if InstallNodeSelected then
    AppendPrerequisitePlanItem(
      Result, CustomMessage('PrereqComponentNode'));
  if InstallDockerSelected then
    AppendPrerequisitePlanItem(
      Result, CustomMessage('PrereqComponentDocker'));
  if Result = '' then
    Result := CustomMessage('ActionNothingSelected');
end;

procedure SetPrerequisiteActionControlsEnabled(Enabled: Boolean);
begin
  PrerequisiteActionsPage.CheckListBox.Enabled := Enabled;
  PythonDownloadButton.Enabled := Enabled;
  NodeDownloadButton.Enabled := Enabled;
  DockerDownloadButton.Enabled := Enabled;
  RecheckPrerequisitesButton.Enabled := Enabled;
  WizardForm.BackButton.Enabled := Enabled;
  if not Enabled then
    WizardForm.NextButton.Enabled := False;
  if Enabled then
    Log('Prerequisite action controls unlocked')
  else
    Log('Prerequisite action controls locked');
end;

procedure BeginPrerequisiteCheck;
begin
  PrerequisiteOperationBusy := True;
  SetPrerequisiteActionControlsEnabled(False);
  PrerequisitesPage.RichEditViewer.Lines.Text :=
    CustomMessage('PrereqProgressCheckingLocked');
  PrerequisiteActionStatusLabel.Caption :=
    CustomMessage('PrereqProgressCheckingLocked');
end;

procedure EndPrerequisiteCheck;
begin
  PrerequisiteOperationBusy := False;
  SetPrerequisiteActionControlsEnabled(True);
end;

procedure BeginPrerequisiteBatch(
  InstallPythonSelected, InstallNodeSelected,
  InstallDockerSelected: Boolean);
begin
  PrerequisiteBatchPlan := BuildPrerequisiteBatchPlan(
    InstallPythonSelected, InstallNodeSelected, InstallDockerSelected);
  PrerequisiteOperationBusy := True;
  PrerequisiteBatchActive := True;
  SetPrerequisiteActionControlsEnabled(False);
  DependencyInstallPage.SetText(
    CustomMessage('PrereqProgressBatch'),
    CustomMessage('PrereqProgressPlanLocked') + PrerequisiteBatchPlan);
  DependencyInstallPage.Show;
  DependencyInstallPage.Animate;
  Log('Prerequisite batch started; selected_plan=' + PrerequisiteBatchPlan);
end;

procedure EndPrerequisiteBatch;
begin
  Log('Prerequisite batch finished; selected_plan=' + PrerequisiteBatchPlan);
  DependencyInstallPage.Hide;
  PrerequisiteBatchActive := False;
  PrerequisiteOperationBusy := False;
  PrerequisiteBatchPlan := '';
  SetPrerequisiteActionControlsEnabled(True);
end;

procedure UpdatePrerequisiteActionNavigation;
var
  PythonNeedsSetup: Boolean;
  NodeNeedsSetup: Boolean;
  RequiredPlanComplete: Boolean;
begin
  if PrerequisiteOperationBusy then
  begin
    WizardForm.NextButton.Enabled := False;
    PrerequisiteActionStatusLabel.Caption :=
      CustomMessage('PrereqProgressCheckingLocked');
    Exit;
  end;

  PythonNeedsSetup := not PythonPrerequisitesOK;
  NodeNeedsSetup := WizardIsComponentSelected('chatbridge') and
    (not NodeVersionOK);
  RequiredPlanComplete :=
    (PrerequisiteManualBlockers = '') and
    ((not PythonNeedsSetup) or PrerequisiteActionsPage.Values[0]) and
    ((not NodeNeedsSetup) or PrerequisiteActionsPage.Values[1]);

  WizardForm.NextButton.Enabled := RequiredPlanComplete;
  WizardForm.NextButton.Caption := DefaultNextButtonCaption;
  if not RequiredPlanComplete then
    PrerequisiteActionStatusLabel.Caption :=
      CustomMessage('ActionSelectRequired')
  else if PrerequisiteAcquisitionFailed then
    PrerequisiteActionStatusLabel.Caption :=
      CustomMessage('ActionRetrySelected')
  else if PrerequisiteActionsPage.Values[0] or
          PrerequisiteActionsPage.Values[1] or
          PrerequisiteActionsPage.Values[2] then
    PrerequisiteActionStatusLabel.Caption :=
      CustomMessage('ActionInstallSelected')
  else
    PrerequisiteActionStatusLabel.Caption :=
      CustomMessage('ActionNothingSelected');
  PrerequisiteSizeMemo.Lines.Text := BuildPrerequisiteSizeText;
end;

procedure UpdatePrerequisiteActionState;
begin
  PrerequisiteActionsPage.CheckListBox.ItemEnabled[0] :=
    (PrerequisiteManualBlockers = '') and
    (not PythonPrerequisitesOK);
  PrerequisiteActionsPage.CheckListBox.ItemEnabled[1] :=
    (PrerequisiteManualBlockers = '') and
    WizardIsComponentSelected('chatbridge') and (not NodeVersionOK);
  PrerequisiteActionsPage.CheckListBox.ItemEnabled[2] :=
    (PrerequisiteManualBlockers = '') and (not DockerCliOK);

  if not PrerequisiteActionsPage.CheckListBox.ItemEnabled[0] then
    PrerequisiteActionsPage.Values[0] := False;
  if not PrerequisiteActionsPage.CheckListBox.ItemEnabled[1] then
    PrerequisiteActionsPage.Values[1] := False;
  if not PrerequisiteActionsPage.CheckListBox.ItemEnabled[2] then
    PrerequisiteActionsPage.Values[2] := False;
  UpdatePrerequisiteActionNavigation;
end;

procedure PrerequisiteOptionClick(Sender: TObject);
var
  ErrorText: String;
begin
  if PrerequisiteOperationBusy then
    Exit;
  try
    PrerequisiteAcquisitionFailed := False;
    UpdatePrerequisiteActionNavigation;
  except
    ErrorText := GetExceptionMessage;
    PrerequisiteAcquisitionFailed := True;
    WizardForm.NextButton.Enabled := False;
    ReportPrerequisiteException(
      CustomMessage('PrereqPhaseSelection'), ErrorText);
  end;
end;

procedure RecheckPrerequisitesButtonClick(Sender: TObject);
var
  ErrorText: String;
begin
  try
    BeginPrerequisiteCheck;
    try
      RunPrerequisiteChecks;
    finally
      EndPrerequisiteCheck;
    end;
    PrerequisiteAcquisitionFailed := False;
    PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
    UpdatePrerequisiteActionState;
  except
    ErrorText := GetExceptionMessage;
    PrerequisiteAcquisitionFailed := True;
    WizardForm.NextButton.Enabled := False;
    ReportPrerequisiteException(
      CustomMessage('PrereqPhaseRecheck'), ErrorText);
  end;
end;

function InstallSelectedPrerequisites: Boolean;
var
  InstallPythonSelected: Boolean;
  InstallNodeSelected: Boolean;
  InstallDockerSelected: Boolean;
  HadException: Boolean;
  OriginalExceptionPhase: String;
  OriginalExceptionText: String;
begin
  Result := True;
  if WizardSilent then
    Exit;

  SetPrerequisitePhase(CustomMessage('PrereqPhaseInstall'));
  InstallPythonSelected := PrerequisiteActionsPage.Values[0] and
    (not PythonPrerequisitesOK);
  InstallNodeSelected := PrerequisiteActionsPage.Values[1] and
    WizardIsComponentSelected('chatbridge') and (not NodeVersionOK);
  InstallDockerSelected := PrerequisiteActionsPage.Values[2] and
    (not DockerCliOK);
  PrerequisiteAcquisitionFailed := False;
  DockerInstalledBySetup := False;
  HadException := False;
  OriginalExceptionPhase := '';
  OriginalExceptionText := '';

  if not (InstallPythonSelected or InstallNodeSelected or
          InstallDockerSelected) then
    Exit;

  BeginPrerequisiteBatch(
    InstallPythonSelected, InstallNodeSelected, InstallDockerSelected);
  try
    try
      if InstallPythonSelected then
      begin
        if not InstallPythonPrerequisite then
        begin
          Result := False;
          Exit;
        end;
        if DependencyRestartRequired then
          Exit;
      end;

      if InstallNodeSelected then
      begin
        if not InstallNodePrerequisite then
        begin
          Result := False;
          Exit;
        end;
        if DependencyRestartRequired then
          Exit;
      end;

      if InstallDockerSelected then
        if not InstallDockerPrerequisite then
          Result := False;
    except
      HadException := True;
      OriginalExceptionPhase := CurrentPrerequisitePhase;
      OriginalExceptionText := GetExceptionMessage;
      Result := False;
    end;
  finally
    try
      if not HadException then
      begin
        SetPrerequisitePhase(CustomMessage('PrereqPhaseFinalCheck'));
        RunPrerequisiteChecks;
      end;
      PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
      if (not Result) and (not DependencyRestartRequired) then
      begin
        PrerequisiteActionsPage.Values[0] := InstallPythonSelected and
          (not PythonPrerequisitesOK);
        PrerequisiteActionsPage.Values[1] := InstallNodeSelected and
          WizardIsComponentSelected('chatbridge') and (not NodeVersionOK);
        PrerequisiteActionsPage.Values[2] := InstallDockerSelected and
          (not DockerCliOK);
        PrerequisiteAcquisitionFailed := True;
      end;
    finally
      EndPrerequisiteBatch;
      UpdatePrerequisiteActionState;
    end;
  end;
  if HadException then
  begin
    if OriginalExceptionPhase = '' then
      OriginalExceptionPhase := CustomMessage('PrereqPhaseInstall');
    CurrentPrerequisitePhase := OriginalExceptionPhase;
    RaiseException(OriginalExceptionText);
  end;
end;

function NeedRestart: Boolean;
begin
  Result := DependencyRestartRequired;
end;

function GetCustomSetupExitCode: Integer;
begin
  Result := InstallerFailureExitCode;
end;

procedure InitializeWizard;
var
  ActionButtonWidth: Integer;
  ActionButtonRow1Top: Integer;
  ActionButtonRow2Top: Integer;
  SizeMemoTop: Integer;
begin
  ExistingInstallDetected := DetectExistingInstall;
  ExistingSettingsComplete := ExistingInstallDetected and HasCompleteExistingSettings;
  LegacyBridgePath := ReadStoredPath('BridgePath', '');
  InstallerMigrationTransactionPath := GetDataRoot +
    '\state\installation\r26-installer-transaction.json';
  InstallerPreflightReportPath := GetDataRoot +
    '\logs\setup\r26-installer-preflight.json';
  InstallerPostflightReportPath := GetLogsPath('') +
    '\setup\r26-installer-postflight.json';
  InstallerRollbackReportPath := GetDataRoot +
    '\logs\setup\r26-installer-rollback.json';
  if ExistingInstallDetected then
    LastAppRoot := NormalizePath(ReadStoredPath('AppPath', WizardDirValue))
  else
    LastAppRoot := NormalizePath(WizardDirValue);
  Log(
    'Existing PLwC installation detected=' + IntToStr(Ord(ExistingInstallDetected)) +
    '; complete_settings=' + IntToStr(Ord(ExistingSettingsComplete)));
  DefaultNextButtonCaption := SetupMessage(msgButtonNext);
  PrerequisiteAcquisitionFailed := False;
  PrerequisiteOperationBusy := False;
  PrerequisiteBatchActive := False;
  PrerequisiteBatchPlan := '';
  CurrentPrerequisitePhase := '';
  InstallerMigrationPrepared := False;
  InstallerRollbackAttempted := False;
  InstallerInstallationCompleted := False;
  InstallerFailureExitCode := 0;

#ifdef UiSmokeTimedProbeFixture
  if WaitNamedPipe('\\.\pipe\docker_engine', 2000) then
    Log('UI_SMOKE_NAMED_PIPE_REACHABLE')
  else
    Log('UI_SMOKE_NAMED_PIPE_UNAVAILABLE');
  if not RunProbeWithTimeout(
       ExpandConstant('{cmd}'), '/c exit 0', 5000) then
    RaiseException('UI_SMOKE_TIMED_PROBE_FAILED');
  Log('UI_SMOKE_TIMED_PROBE_COMPLETED');
#endif

  PrerequisitesPage := CreateOutputMsgMemoPage(
    wpSelectComponents,
    CustomMessage('PagePrereqTitle'),
    CustomMessage('PagePrereqDescription'),
    CustomMessage('PagePrereqSubCaption'),
    CustomMessage('PrereqChecking'));
  PrerequisitesPage.RichEditViewer.Lines.Text := CustomMessage('PrereqChecking');

  PrerequisiteActionsPage := CreateInputOptionPage(
    PrerequisitesPage.ID,
    CustomMessage('PagePrereqActionTitle'),
    CustomMessage('PagePrereqActionDescription'),
    CustomMessage('PagePrereqActionSubCaption'),
    False,
    False);
  PrerequisiteActionsPage.Add(CustomMessage('OptionInstallPython'));
  PrerequisiteActionsPage.Add(CustomMessage('OptionInstallNode'));
  PrerequisiteActionsPage.Add(CustomMessage('OptionInstallDocker'));
  PrerequisiteActionsPage.Values[0] := False;
  PrerequisiteActionsPage.Values[1] := False;
  PrerequisiteActionsPage.Values[2] := False;
  PrerequisiteActionsPage.CheckListBox.OnClickCheck :=
    @PrerequisiteOptionClick;
  PrerequisiteActionsPage.CheckListBox.Height := ScaleY(68);

  ActionButtonWidth :=
    (PrerequisiteActionsPage.SurfaceWidth - ScaleX(8)) div 2;
  ActionButtonRow1Top := PrerequisiteActionsPage.SurfaceHeight - ScaleY(52);
  ActionButtonRow2Top := PrerequisiteActionsPage.SurfaceHeight - ScaleY(25);

  PrerequisiteActionStatusLabel := TNewStaticText.Create(PrerequisiteActionsPage);
  PrerequisiteActionStatusLabel.Parent := PrerequisiteActionsPage.Surface;
  PrerequisiteActionStatusLabel.Left := 0;
  PrerequisiteActionStatusLabel.Top :=
    PrerequisiteActionsPage.CheckListBox.Top +
    PrerequisiteActionsPage.CheckListBox.Height + ScaleY(4);
  PrerequisiteActionStatusLabel.Width := PrerequisiteActionsPage.SurfaceWidth;
  PrerequisiteActionStatusLabel.Height := ScaleY(34);
  PrerequisiteActionStatusLabel.AutoSize := False;
  PrerequisiteActionStatusLabel.WordWrap := True;
  PrerequisiteActionStatusLabel.Font.Style := [fsBold];
  PrerequisiteActionStatusLabel.Caption :=
    CustomMessage('ActionNothingSelected');

  SizeMemoTop :=
    PrerequisiteActionStatusLabel.Top +
    PrerequisiteActionStatusLabel.Height + ScaleY(3);
  PrerequisiteSizeMemo := TNewMemo.Create(PrerequisiteActionsPage);
  PrerequisiteSizeMemo.Parent := PrerequisiteActionsPage.Surface;
  PrerequisiteSizeMemo.Left := 0;
  PrerequisiteSizeMemo.Top := SizeMemoTop;
  PrerequisiteSizeMemo.Width := PrerequisiteActionsPage.SurfaceWidth;
  PrerequisiteSizeMemo.Height :=
    ActionButtonRow1Top - SizeMemoTop - ScaleY(6);
  PrerequisiteSizeMemo.ReadOnly := True;
  PrerequisiteSizeMemo.TabStop := False;
  PrerequisiteSizeMemo.WordWrap := True;
  PrerequisiteSizeMemo.ScrollBars := ssVertical;
  PrerequisiteSizeMemo.Lines.Text := BuildPrerequisiteSizeText;

  PythonDownloadButton := TNewButton.Create(PrerequisiteActionsPage);
  PythonDownloadButton.Parent := PrerequisiteActionsPage.Surface;
  PythonDownloadButton.Left := 0;
  PythonDownloadButton.Top := ActionButtonRow1Top;
  PythonDownloadButton.Width := ActionButtonWidth;
  PythonDownloadButton.Height := ScaleY(23);
  PythonDownloadButton.Caption := CustomMessage('ButtonPythonDownload');
  PythonDownloadButton.OnClick := @PythonDownloadButtonClick;

  NodeDownloadButton := TNewButton.Create(PrerequisiteActionsPage);
  NodeDownloadButton.Parent := PrerequisiteActionsPage.Surface;
  NodeDownloadButton.Left := ActionButtonWidth + ScaleX(8);
  NodeDownloadButton.Top := ActionButtonRow1Top;
  NodeDownloadButton.Width := ActionButtonWidth;
  NodeDownloadButton.Height := ScaleY(23);
  NodeDownloadButton.Caption := CustomMessage('ButtonNodeDownload');
  NodeDownloadButton.OnClick := @NodeDownloadButtonClick;

  DockerDownloadButton := TNewButton.Create(PrerequisiteActionsPage);
  DockerDownloadButton.Parent := PrerequisiteActionsPage.Surface;
  DockerDownloadButton.Left := 0;
  DockerDownloadButton.Top := ActionButtonRow2Top;
  DockerDownloadButton.Width := ActionButtonWidth;
  DockerDownloadButton.Height := ScaleY(23);
  DockerDownloadButton.Caption := CustomMessage('ButtonDockerDownload');
  DockerDownloadButton.OnClick := @DockerDownloadButtonClick;

  RecheckPrerequisitesButton := TNewButton.Create(PrerequisiteActionsPage);
  RecheckPrerequisitesButton.Parent := PrerequisiteActionsPage.Surface;
  RecheckPrerequisitesButton.Left := ActionButtonWidth + ScaleX(8);
  RecheckPrerequisitesButton.Top := ActionButtonRow2Top;
  RecheckPrerequisitesButton.Width := ActionButtonWidth;
  RecheckPrerequisitesButton.Height := ScaleY(23);
  RecheckPrerequisitesButton.Caption :=
    CustomMessage('ButtonRecheckPrerequisites');
  RecheckPrerequisitesButton.OnClick := @RecheckPrerequisitesButtonClick;

  DependencyDownloadPage := CreateDownloadPage(
    CustomMessage('PageDownloadTitle'),
    CustomMessage('PageDownloadDescription') + '. ' +
      CustomMessage('PageDownloadSubCaption'),
    nil);
  DependencyDownloadPage.ShowBaseNameInsteadOfUrl := True;

  DependencyInstallPage := CreateOutputMarqueeProgressPage(
    CustomMessage('PageInstallProgressTitle'),
    CustomMessage('PageInstallProgressDescription'));

  RuntimeDirsPage := CreateInputDirPage(
    PrerequisiteActionsPage.ID,
    CustomMessage('PageRuntimeDirsTitle'),
    CustomMessage('PageRuntimeDirsDescription'),
    CustomMessage('PageRuntimeDirsSubCaption'),
    False,
    '');
  RuntimeDirsPage.Add(CustomMessage('FieldApp'));
  RuntimeDirsPage.Add(CustomMessage('FieldGateway'));
  RuntimeDirsPage.Add(CustomMessage('FieldChatBridge'));
  RuntimeDirsPage.Values[0] := ReadStoredPath('AppPath', LastAppRoot);
  RuntimeDirsPage.Values[1] := ReadStoredPath('GatewayPath', LastAppRoot + '\gateway');
  RuntimeDirsPage.Values[2] := LastAppRoot + '\{#BridgeDirectoryName}';
  RuntimeDirsPage.Edits[2].ReadOnly := True;

  DataDirsPage := CreateInputDirPage(
    RuntimeDirsPage.ID,
    CustomMessage('PageCoreDirsTitle'),
    CustomMessage('PageCoreDirsDescription'),
    CustomMessage('PageCoreDirsSubCaption'),
    False,
    '');
  DataDirsPage.Add(CustomMessage('FieldWorkspace'));
  DataDirsPage.Add(CustomMessage('FieldProfiles'));
  DataDirsPage.Add(CustomMessage('FieldConfig'));
  DataDirsPage.Values[0] := ReadStoredPath('WorkspacePath', GetDataRoot + '\workspace');
  DataDirsPage.Values[1] := ReadStoredPath('ProfilesPath', GetDataRoot + '\profiles');
  DataDirsPage.Values[2] := ReadStoredPath('ConfigPath', GetDataRoot + '\config');

  OperatingDirsPage := CreateInputDirPage(
    DataDirsPage.ID,
    CustomMessage('PageOpsDirsTitle'),
    CustomMessage('PageOpsDirsDescription'),
    CustomMessage('PageOpsDirsSubCaption'),
    False,
    '');
  OperatingDirsPage.Add(CustomMessage('FieldState'));
  OperatingDirsPage.Add(CustomMessage('FieldLogs'));
  OperatingDirsPage.Add(CustomMessage('FieldBackups'));
  OperatingDirsPage.Values[0] := ReadStoredPath('StatePath', GetDataRoot + '\state');
  OperatingDirsPage.Values[1] := ReadStoredPath('LogsPath', GetDataRoot + '\logs');
  OperatingDirsPage.Values[2] := ReadStoredPath('BackupsPath', GetDataRoot + '\profile_backups');

  ProfilePage := CreateInputQueryPage(
    OperatingDirsPage.ID,
    CustomMessage('PageProfileTitle'),
    CustomMessage('PageProfileDescription'),
    CustomMessage('PageProfileSubCaption'));
  ProfilePage.Add(CustomMessage('FieldProfileName'), False);
  ProfilePage.Add(CustomMessage('FieldSecurityConfig'), False);
  ProfilePage.Values[0] := ReadStoredSetting('ActiveProfile', 'default');
  ProfilePage.Values[1] := ReadStoredSetting('SecurityConfig', '');

  RuntimeSettingsPage := CreateInputQueryPage(
    ProfilePage.ID,
    CustomMessage('PageThresholdTitle'),
    CustomMessage('PageThresholdDescription'),
    CustomMessage('PageThresholdSubCaption'));
  RuntimeSettingsPage.Add(CustomMessage('FieldMemoryThreshold'), False);
  RuntimeSettingsPage.Add(CustomMessage('FieldPersonaThreshold'), False);
  RuntimeSettingsPage.Add(CustomMessage('FieldTemperamentThreshold'), False);
  RuntimeSettingsPage.Values[0] := ReadStoredSetting('MemoryWriteThreshold', '2');
  RuntimeSettingsPage.Values[1] := ReadStoredSetting('PersonaWriteThreshold', '3');
  RuntimeSettingsPage.Values[2] := ReadStoredSetting('TemperamentWriteThreshold', '2');

  RuntimeOptionsPage := CreateInputOptionPage(
    RuntimeSettingsPage.ID,
    CustomMessage('PageFeatureTitle'),
    CustomMessage('PageFeatureDescription'),
    CustomMessage('PageFeatureSubCaption'),
    False,
    False);
  RuntimeOptionsPage.Add(CustomMessage('OptionQdrant'));
  RuntimeOptionsPage.Add(CustomMessage('OptionPersonaDisabled'));
  RuntimeOptionsPage.Values[0] := ReadStoredBoolean('QdrantEnabled', False);
  RuntimeOptionsPage.Values[1] := ReadStoredBoolean('PersonaLayerDisabled', True);
end;

procedure CurPageChanged(CurPageID: Integer);
var
  CurrentAppRoot: String;
  ErrorText: String;
begin
  if PrerequisiteOperationBusy then
  begin
    Log('Prerequisite page refresh suppressed while an operation is active');
    Exit;
  end;

  if CurPageID = PrerequisitesPage.ID then
  begin
    try
      BeginPrerequisiteCheck;
      try
        RunPrerequisiteChecks;
      finally
        EndPrerequisiteCheck;
      end;
      PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
      WizardForm.NextButton.Enabled := True;
    except
      ErrorText := GetExceptionMessage;
      WizardForm.NextButton.Enabled := False;
      ReportPrerequisiteException(
        CustomMessage('PrereqPhasePageCheck'), ErrorText);
    end;
  end;

  if CurPageID = PrerequisiteActionsPage.ID then
  begin
    try
      BeginPrerequisiteCheck;
      try
        RunPrerequisiteChecks;
      finally
        EndPrerequisiteCheck;
      end;
      PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
      UpdatePrerequisiteActionState;
    except
      ErrorText := GetExceptionMessage;
      PrerequisiteAcquisitionFailed := True;
      WizardForm.NextButton.Enabled := False;
      ReportPrerequisiteException(
        CustomMessage('PrereqPhasePageCheck'), ErrorText);
    end;
  end;

  if CurPageID = RuntimeDirsPage.ID then
  begin
    CurrentAppRoot := NormalizePath(RuntimeDirsPage.Values[0]);
    if CompareText(NormalizePath(RuntimeDirsPage.Values[1]), LastAppRoot + '\gateway') = 0 then
      RuntimeDirsPage.Values[1] := CurrentAppRoot + '\gateway';
    RuntimeDirsPage.Values[2] := CurrentAppRoot + '\{#BridgeDirectoryName}';
    LastAppRoot := CurrentAppRoot;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := ExistingSettingsComplete and
    ((PageID = RuntimeDirsPage.ID) or
     (PageID = DataDirsPage.ID) or
     (PageID = OperatingDirsPage.ID) or
     (PageID = ProfilePage.ID) or
     (PageID = RuntimeSettingsPage.ID) or
     (PageID = RuntimeOptionsPage.ID));
end;

function GetDataPathByIndex(Index: Integer): String;
begin
  case Index of
    0: Result := DataDirsPage.Values[0];
    1: Result := DataDirsPage.Values[1];
    2: Result := DataDirsPage.Values[2];
    3: Result := OperatingDirsPage.Values[0];
    4: Result := OperatingDirsPage.Values[1];
    5: Result := OperatingDirsPage.Values[2];
  end;
end;

procedure SetDataPathByIndex(Index: Integer; Value: String);
begin
  case Index of
    0: DataDirsPage.Values[0] := Value;
    1: DataDirsPage.Values[1] := Value;
    2: DataDirsPage.Values[2] := Value;
    3: OperatingDirsPage.Values[0] := Value;
    4: OperatingDirsPage.Values[1] := Value;
    5: OperatingDirsPage.Values[2] := Value;
  end;
end;

function GetDataLabelByIndex(Index: Integer): String;
begin
  case Index of
    0: Result := CustomMessage('FieldWorkspace');
    1: Result := CustomMessage('FieldProfiles');
    2: Result := CustomMessage('FieldConfig');
    3: Result := CustomMessage('FieldState');
    4: Result := CustomMessage('FieldLogs');
    5: Result := CustomMessage('FieldBackups');
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  AppPath: String;
  GatewayPath: String;
  BridgePath: String;
  DataPaths: array[0..5] of String;
  DataLabels: array[0..5] of String;
  AcquisitionSucceeded: Boolean;
  ErrorText: String;
  I: Integer;
  J: Integer;
begin
  Result := True;
#ifdef UiSmokeMode
  if CurPageID = wpReady then
  begin
    Log('UI_SMOKE_READY_BLOCKED');
    Result := False;
    Exit;
  end;
#endif
  AppPath := NormalizePath(GetAppPath);

  if CurPageID = PrerequisitesPage.ID then
  begin
    try
      RunPrerequisiteChecks;
      PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
    except
      ErrorText := GetExceptionMessage;
      ReportPrerequisiteException(
        CustomMessage('PrereqPhasePageCheck'), ErrorText);
      Result := False;
      Exit;
    end;
    if PrerequisiteManualBlockers <> '' then
    begin
      MsgBox(
        CustomMessage('PrereqManualGateFailed') + #13#10 + #13#10 +
        PrerequisiteManualBlockers,
        mbError,
        MB_OK);
      Result := False;
      Exit;
    end;
  end;

  if CurPageID = PrerequisiteActionsPage.ID then
  begin
    if DependencyRestartRequired then
    begin
      MsgBox(CustomMessage('PrereqRestartRequired'), mbInformation, MB_OK);
      Result := False;
      Exit;
    end;
    try
      BeginPrerequisiteCheck;
      try
        RunPrerequisiteChecks;
      finally
        EndPrerequisiteCheck;
      end;
      PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
      UpdatePrerequisiteActionState;
    except
      ErrorText := GetExceptionMessage;
      PrerequisiteAcquisitionFailed := True;
      WizardForm.NextButton.Enabled := False;
      ReportPrerequisiteException(
        CustomMessage('PrereqPhasePageCheck'), ErrorText);
      Result := False;
      Exit;
    end;
    if PrerequisiteManualBlockers <> '' then
    begin
      MsgBox(
        CustomMessage('PrereqManualGateFailed') + #13#10 + #13#10 +
        PrerequisiteManualBlockers,
        mbError,
        MB_OK);
      Result := False;
      Exit;
    end;
    if ((not PythonPrerequisitesOK) and
        (not PrerequisiteActionsPage.Values[0])) or
       (WizardIsComponentSelected('chatbridge') and
        (not NodeVersionOK) and
        (not PrerequisiteActionsPage.Values[1])) then
    begin
      MsgBox(
        CustomMessage('PrereqAcquisitionPlanIncomplete') + #13#10 + #13#10 +
        PrerequisiteBlockers,
        mbError,
        MB_OK);
      Result := False;
      Exit;
    end;

#ifdef UiSmokePrerequisiteGuard
    Log('UI_SMOKE_PREREQUISITE_PLAN_ACCEPTED');
    Result := False;
    Exit;
#endif
    try
      AcquisitionSucceeded := InstallSelectedPrerequisites;
    except
      ErrorText := GetExceptionMessage;
      PrerequisiteAcquisitionFailed := True;
      WizardForm.NextButton.Enabled := False;
      if CurrentPrerequisitePhase = '' then
        CurrentPrerequisitePhase := CustomMessage('PrereqPhaseInstall');
      ReportPrerequisiteException(
        CurrentPrerequisitePhase, ErrorText);
      Result := False;
      Exit;
    end;
#ifdef UiSmokeDownloadFixture
    if AcquisitionSucceeded then
      Log('UI_SMOKE_DOWNLOAD_PATH_COMPLETED')
    else
      Log('UI_SMOKE_DOWNLOAD_PATH_FAILED');
    Result := False;
    Exit;
#endif
    if DependencyRestartRequired then
    begin
      MsgBox(CustomMessage('PrereqRestartRequired'), mbInformation, MB_OK);
      Result := False;
      Exit;
    end;
    if not AcquisitionSucceeded then
    begin
      Result := False;
      Exit;
    end;
    if PrerequisiteBlockers <> '' then
    begin
      MsgBox(
        CustomMessage('PrereqGateFailed') + #13#10 + #13#10 +
        PrerequisiteBlockers,
        mbError,
        MB_OK);
      Result := False;
      Exit;
    end;
  end;

  if CurPageID = RuntimeDirsPage.ID then
  begin
    if (Trim(RuntimeDirsPage.Values[0]) = '') or
       (Trim(RuntimeDirsPage.Values[1]) = '') or
       (Trim(RuntimeDirsPage.Values[2]) = '') then
    begin
      MsgBox(CustomMessage('ErrorPathsRequired'), mbError, MB_OK);
      Result := False;
      Exit;
    end;

    AppPath := NormalizePath(RuntimeDirsPage.Values[0]);
    GatewayPath := NormalizePath(RuntimeDirsPage.Values[1]);
    BridgePath := NormalizePath(RuntimeDirsPage.Values[2]);
    if (CompareText(GatewayPath, AppPath) = 0) or
       (not IsSameOrChildPath(GatewayPath, AppPath)) or
       (CompareText(BridgePath, AppPath) = 0) or
       (not IsSameOrChildPath(BridgePath, AppPath)) or
       (CompareText(BridgePath, AppPath + '\{#BridgeDirectoryName}') <> 0) then
    begin
      MsgBox(CustomMessage('ErrorRuntimeChildren'), mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if PathsOverlap(GatewayPath, BridgePath) then
    begin
      MsgBox(CustomMessage('ErrorRuntimeOverlap'), mbError, MB_OK);
      Result := False;
      Exit;
    end;
    RuntimeDirsPage.Values[0] := AppPath;
    RuntimeDirsPage.Values[1] := GatewayPath;
    RuntimeDirsPage.Values[2] := BridgePath;
    WizardForm.DirEdit.Text := AppPath;
    LastAppRoot := AppPath;
  end;

  if (CurPageID = DataDirsPage.ID) or (CurPageID = OperatingDirsPage.ID) then
  begin
    AppPath := NormalizePath(GetAppPath);
    for I := 0 to 5 do
      DataLabels[I] := GetDataLabelByIndex(I);

    for I := 0 to 5 do
    begin
      if Trim(GetDataPathByIndex(I)) = '' then
      begin
        MsgBox(CustomMessage('ErrorDataRequired') + DataLabels[I], mbError, MB_OK);
        Result := False;
        Exit;
      end;
      DataPaths[I] := NormalizePath(GetDataPathByIndex(I));
      SetDataPathByIndex(I, DataPaths[I]);
      if PathsOverlap(DataPaths[I], AppPath) then
      begin
        MsgBox(CustomMessage('ErrorDataInApp') + DataLabels[I], mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;

    for I := 0 to 4 do
    begin
      for J := I + 1 to 5 do
      begin
        if PathsOverlap(DataPaths[I], DataPaths[J]) then
        begin
          MsgBox(CustomMessage('ErrorDataOverlap') + DataLabels[I] + ' / ' +
            DataLabels[J], mbError, MB_OK);
          Result := False;
          Exit;
        end;
      end;
    end;
  end;

  if CurPageID = ProfilePage.ID then
  begin
    if not IsValidProfileName(ProfilePage.Values[0]) then
    begin
      MsgBox(CustomMessage('ErrorProfileName'), mbError, MB_OK);
      Result := False;
      Exit;
    end;
    ProfilePage.Values[0] := Trim(ProfilePage.Values[0]);
    if Trim(ProfilePage.Values[1]) <> '' then
    begin
      ProfilePage.Values[1] := RemoveBackslashUnlessRoot(
        ExpandFileName(Trim(ProfilePage.Values[1])));
      if not FileExists(ProfilePage.Values[1]) then
      begin
        MsgBox(CustomMessage('ErrorSecurityFile'), mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
  end;

  if CurPageID = RuntimeSettingsPage.ID then
  begin
    if not IsValidThreshold(RuntimeSettingsPage.Values[0]) or
       not IsValidThreshold(RuntimeSettingsPage.Values[1]) or
       not IsValidThreshold(RuntimeSettingsPage.Values[2]) then
    begin
      MsgBox(CustomMessage('ErrorThresholds'), mbError, MB_OK);
      Result := False;
      Exit;
    end;
    RuntimeSettingsPage.Values[0] := IntToStr(StrToInt(Trim(RuntimeSettingsPage.Values[0])));
    RuntimeSettingsPage.Values[1] := IntToStr(StrToInt(Trim(RuntimeSettingsPage.Values[1])));
    RuntimeSettingsPage.Values[2] := IntToStr(StrToInt(Trim(RuntimeSettingsPage.Values[2])));
  end;

end;

function UpdateReadyMemo(
  Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := '';
  if ExistingInstallDetected then
    Result := CustomMessage('ReadyUpdateMode') + NewLine + NewLine;
  Result := Result + CustomMessage('ReadyRuntime') + NewLine +
    Space + CustomMessage('SummaryApp') + GetAppPath + NewLine +
    Space + CustomMessage('SummaryGateway') + GetGatewayPath('') + NewLine;
  if WizardIsComponentSelected('chatbridge') then
    Result := Result +
      Space + CustomMessage('SummaryChatBridge') + GetBridgePath('') + NewLine;
  Result := Result + NewLine + CustomMessage('ReadyData') + NewLine +
    Space + CustomMessage('SummaryWorkspace') + GetWorkspacePath('') + NewLine +
    Space + CustomMessage('SummaryProfiles') + GetProfilesPath('') + NewLine +
    Space + CustomMessage('SummaryConfig') + GetConfigPath('') + NewLine +
    Space + CustomMessage('SummaryState') + GetStatePath('') + NewLine +
    Space + CustomMessage('SummaryLogs') + GetLogsPath('') + NewLine +
    Space + CustomMessage('SummaryBackups') + GetBackupsPath('') + NewLine +
    Space + CustomMessage('ReadyProfile') + GetProfileName + NewLine +
    Space + CustomMessage('ReadySecurity') + GetSecurityConfigPath + NewLine +
    Space + CustomMessage('ReadyThresholds') +
      GetMemoryThreshold + '/' + GetPersonaThreshold + '/' + GetTemperamentThreshold + NewLine +
    Space + CustomMessage('ReadyQdrant') +
      LocalizedBoolean(RuntimeOptionsPage.Values[0]) + NewLine +
    Space + CustomMessage('ReadyPersona') +
      LocalizedBoolean(RuntimeOptionsPage.Values[1]) + NewLine +
    Space + CustomMessage('ReadySafeMode') +
      LocalizedBoolean(IsSafeModeExpected) + NewLine + NewLine +
    CustomMessage('SummaryPrerequisites') + NewLine +
    PrerequisiteReport + NewLine + NewLine +
    MemoTypeInfo + NewLine + NewLine +
    MemoComponentsInfo + NewLine + NewLine +
    CustomMessage('ReadyHostConfig');

  if WizardIsComponentSelected('codex') or
     WizardIsComponentSelected('odysseus') then
    Result := Result + NewLine + Space + CustomMessage('ReadySnippets');
  if WizardIsComponentSelected('claude') then
    Result := Result + NewLine + Space + CustomMessage('ReadyClaude');

  if WizardIsComponentSelected('chatbridge') then
    Result := Result + NewLine + Space + CustomMessage('ReadyNativeStable') +
      ChatBridgeExtensionId + NewLine + Space +
      CustomMessage('ReadyBridgeAutostart');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  RunPrerequisiteChecks;
  PrerequisitesPage.RichEditViewer.Lines.Text := PrerequisiteReport;
  if PrerequisiteBlockers <> '' then
    Result := CustomMessage('PrereqGateFailed') + #13#10 + #13#10 +
      PrerequisiteBlockers
  else
    Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorText: String;
  RollbackComplete: Boolean;
begin
  if CurStep = ssInstall then
    PrepareInstallerMigration;

  if CurStep = ssPostInstall then
  begin
    try
      StoreInstallerRoots;
      SaveGeneratedFiles;
      StartDockerDesktopAfterSetup;
      ConfigureChatBridgeWindowsIntegration;
      RunHardInstallerPostflight;
      AppendInstallerDiagnosticRecord(
        'installation_completed',
        'status=success' + #13#10 +
        'postflight_report=' + InstallerPostflightReportPath + #13#10);
      InstallerInstallationCompleted := True;
    except
      ErrorText := GetExceptionMessage;
      RollbackComplete := RollbackInstallerMigration;
      if RollbackComplete then
        InstallerFailureExitCode := 30
      else
        InstallerFailureExitCode := 50;
      AppendInstallerDiagnosticRecord(
        'installation_completed',
        'status=failure' + #13#10 +
        'error=' + ErrorText + #13#10 +
        'rollback_complete=' + IntToStr(Ord(RollbackComplete)) + #13#10 +
        'rollback_report=' + InstallerRollbackReportPath + #13#10 +
        'postflight_report=' + InstallerPostflightReportPath + #13#10);
      RaiseException(ErrorText);
    end;
  end;
end;

procedure DeinitializeSetup;
begin
  if InstallerMigrationPrepared and
     (not InstallerInstallationCompleted) and
     (not InstallerRollbackAttempted) then
  begin
    Log('Setup ended before r26 postflight success; attempting installer rollback.');
    RollbackInstallerMigration;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    RemoveChatBridgeWindowsIntegration;
    RemoveGeneratedFiles;
    RemoveInstallerRootSettings;
  end;
end;

function InstallSummaryExists: Boolean;
begin
  Result := FileExists(GetInstallSummaryPath(''));
end;

function GettingStartedExists: Boolean;
begin
  Result := FileExists(GetGettingStartedPath(''));
end;

function ConfigurationUiExists: Boolean;
begin
  Result := FileExists(GetConfigurationScriptPath) and
    FileExists(GetAppPath + '\configuration\plwc-config.js') and
    FileExists(GetAppPath + '\configuration\plwc-config.css');
end;

function GettingStartedUiExists: Boolean;
begin
  Result := GettingStartedExists and ConfigurationUiExists;
end;

function ShouldOfferClaudeFolder: Boolean;
begin
  Result := WizardIsComponentSelected('claude') and DirExists(GetClaudeFolder(''));
end;

function ShouldOfferCodexSnippet: Boolean;
begin
  Result := WizardIsComponentSelected('codex') and FileExists(GetCodexSnippetPath(''));
end;

function ShouldOfferOdysseusSnippet: Boolean;
begin
  Result := WizardIsComponentSelected('odysseus') and FileExists(GetOdysseusSnippetPath(''));
end;

function ShouldOfferExtensionFolder: Boolean;
begin
  Result := WizardIsComponentSelected('chatbridge') and DirExists(GetExtensionFolder(''));
end;
