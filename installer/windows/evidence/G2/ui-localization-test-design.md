# G2 UI and localization test design - r27

Date: 2026-09-05

Status: **APPROVED**

## Existing inventory

The canonical expected values are the literal `english.<ID>` and `german.<ID>`
entries in the `[CustomMessages]` section of `PLwCSetup.iss`. At the G2
baseline the parser observes **293 English and 293 German values, 293 unique
IDs, zero missing pairs**. `L10N-KEYS-001` snapshots that entire parsed map in
test output and fails on a missing/extra key, empty value or unintended
fallback. Thus every existing visible custom string has an exact English and
German expected value rather than only a key-count assertion.

Inno standard pages/buttons use the selected official language catalog. The UI
smoke inventories their visible captions from the running control tree and
compares them to the selected language; `/LANG`, Windows-language default and
manual first-dialog override are separate cases.

## Exact r27 additions

| ID | English expected value | German expected value |
| --- | --- | --- |
| `PageRuntimeImagesTitle` | PLwC runtime images | PLwC-Laufzeit-Images |
| `PageRuntimeImagesDescription` | Prepare the optional Docker runtimes | Optionale Docker-Laufzeiten vorbereiten |
| `PageRuntimeImagesSubCaption` | Review source, size and Safe Mode before downloading. | Prüfen Sie vor dem Download Quelle, Größe und Safe Mode. |
| `OptionInstallRuntimeImages` | Download and verify the three PLwC runtime images | Die drei PLwC-Laufzeit-Images herunterladen und prüfen |
| `RuntimeImagesSource` | Source: GitHub Container Registry (ghcr.io/mhoedt-ai) | Quelle: GitHub Container Registry (ghcr.io/mhoedt-ai) |
| `RuntimeImagesPlatform` | Platform: Linux AMD64 for Docker Desktop / WSL2 | Plattform: Linux AMD64 für Docker Desktop / WSL2 |
| `RuntimeImagesVersions` | Images: Document Worker, Node Runner and Python Runner | Images: Document Worker, Node Runner und Python Runner |
| `RuntimeImagesDownloadSize` | Estimated download: | Geschätzter Download: |
| `RuntimeImagesDiskSize` | Required Docker storage: | Benötigter Docker-Speicher: |
| `RuntimeImagesConsentRequired` | This download starts only after you select the checkbox and click Next. | Dieser Download startet erst, wenn Sie das Kontrollkästchen auswählen und auf „Weiter“ klicken. |
| `RuntimeImagesDeclinedSafeMode` | Without the images, PLwC installs in Safe Mode and document, Python and Node operations remain unavailable. | Ohne die Images wird PLwC im Safe Mode installiert; Dokument-, Python- und Node-Operationen bleiben nicht verfügbar. |
| `RuntimeImagesProgressInventory` | Checking local runtime images... | Lokale Laufzeit-Images werden geprüft... |
| `RuntimeImagesProgressPull` | Downloading PLwC runtime image... | PLwC-Laufzeit-Image wird heruntergeladen... |
| `RuntimeImagesProgressVerify` | Verifying image digest and platform... | Image-Digest und Plattform werden geprüft... |
| `RuntimeImagesProgressProbe` | Running the offline runtime probe... | Der Offline-Laufzeittest wird ausgeführt... |
| `RuntimeImagesCancelled` | The runtime image download was cancelled. PLwC will remain in Safe Mode. | Der Download der Laufzeit-Images wurde abgebrochen. PLwC bleibt im Safe Mode. |
| `RuntimeImagesFailed` | A runtime image could not be prepared. PLwC will remain in Safe Mode. | Ein Laufzeit-Image konnte nicht vorbereitet werden. PLwC bleibt im Safe Mode. |
| `RuntimeImagesRetry` | Review the diagnostic report and click Next to start a new attempt. | Prüfen Sie den Diagnosebericht und klicken Sie für einen neuen Versuch auf „Weiter“. |
| `RuntimeImagesReady` | All three runtime images passed their offline probes. | Alle drei Laufzeit-Images haben ihre Offline-Tests bestanden. |
| `RuntimeImagesReportLocation` | Diagnostic report: | Diagnosebericht: |

These 20 IDs raise the expected r27 inventory to **313 paired IDs**, unless an
implementation change deliberately adds another visible message. Any addition
requires an English and German literal, a reviewed expectation update and a G2
design update before G4.

## Page and state matrix

The executable UI test visits every standard/custom page in both languages and
captures control type, bounds, enabled/visible state, caption and screenshot at
1366x768/100%. The runtime-image page is exercised with:

- Docker unavailable: page not actionable; localized Safe Mode summary;
- all images missing, unchecked; all images missing, checked;
- all images already exact; checked validation without download;
- longest repository/digest/size/report text;
- pull progress, cancellation, timeout, digest failure, probe failure;
- final ready and Safe Mode summaries;
- Back/Next navigation and silent-mode source contract.

Assertions: no overlap/clipping/off-client control, no Boolean text edit, fixed
navigation captions, scroll/wrap for long read-only values, one failure dialog,
no mixed installer-owned language and keyboard accessibility for the checkbox.

Machine/vendor output inside a diagnostic detail is not treated as an
installer translation, but its surrounding label and guidance always use the
selected language.
