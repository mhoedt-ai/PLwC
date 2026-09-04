"use strict";

const language = document.body.dataset.language === "de" ? "de" : "en";
const text = {
  de: {
    source: "Quelle",
    valid: "gültig",
    invalid: "ungültig",
    enabled: "aktiv",
    disabled: "inaktiv",
    loadingError: "Der aktuelle PLwC-Zustand konnte nicht geladen werden.",
    saved: "Die gemeinsamen PLwC-Einstellungen wurden gespeichert.",
    saveError: "Die Einstellungen konnten nicht gespeichert werden.",
    planError: "Der Profilwechsel konnte nicht geprüft werden.",
    activationError: "Das Profil konnte nicht aktiviert werden.",
    activated: "Das Profil wurde über den Governor aktiviert.",
    validPlan: "gültig und zur Bestätigung bereit",
    invalidPlan: "nicht ausführbar",
    noWrites: "keine",
    noWarnings: "Keine Setup-Warnungen.",
    warnings: "Setup-Warnungen",
    invalidNumber: "Alle Schwellen müssen ganze Zahlen zwischen 1 und 1.000.000 sein.",
    unchanged: "Dieses Profil ist bereits aktiv.",
    working: "PLwC verarbeitet die Anfrage...",
    creationPlanError: "Der Erstellungsplan konnte nicht vorbereitet werden.",
    creationApplyError: "Das neue Profil konnte nicht erstellt werden.",
    profileCreated: "Das neue Profil wurde erstellt und über den Governor aktiviert.",
    creationValid: "gültig und zur Bestätigung bereit",
    creationInvalid: "noch nicht ausführbar",
    willActivate: "wird nach der Erstellung aktiv",
    activationBlocked: "Aktivierung blockiert",
    noMissingAnswers: "keine",
    profileIncomplete: "unvollständig",
    missingFiles: "Fehlende Dateien",
    workspacePlanError: "Die Workspaceänderung konnte nicht geprüft werden.",
    workspaceApplyError: "Der Workspace konnte nicht geändert werden.",
    workspaceChanged: "Der Workspace wurde nach Bestätigung geändert.",
    workspaceUnchanged: "Dieser Workspace ist bereits aktiv.",
    noLauncherResult: "Noch kein Launcher-Ergebnis gespeichert.",
    doctorDiagnosisError: "Die PLwC-Doktor-Diagnose ist fehlgeschlagen.",
    doctorPlanError: "Der PLwC-Doktor-Reparaturplan konnte nicht erstellt werden.",
    doctorApplyError: "Die PLwC-Doktor-Reparatur ist fehlgeschlagen.",
    doctorDiagnosisComplete: "Diagnose abgeschlossen",
    doctorRepairComplete: "Die bestätigte Reparatur und der Postflight sind abgeschlossen.",
    doctorNoChanges: "Der Reparaturplan enthält keine Änderungen.",
    doctorRolledBack: "Die Reparatur ist fehlgeschlagen; ausgeführte Schritte wurden zurückgerollt.",
    doctorExported: "Der Diagnosebericht wurde zum Download bereitgestellt.",
    updateCheckError: "Die Updateprüfung ist fehlgeschlagen.",
    updatePlanError: "Der verifizierte Downloadplan konnte nicht erstellt werden.",
    updateDownloadError: "Das Update konnte nicht sicher heruntergeladen werden.",
    updateInstallError: "Der verifizierte Installer konnte nicht gestartet werden.",
    updateDownloaded: "Download vollständig; Größe, SHA-256 und Buildidentität sind verifiziert.",
    updateInstallerComplete: "Der r26-Installer wurde abgeschlossen. Sein Postflight- und Rollbackbericht ist maßgeblich.",
    unknown: "unbekannt"
  },
  en: {
    source: "Source",
    valid: "valid",
    invalid: "invalid",
    enabled: "enabled",
    disabled: "disabled",
    loadingError: "The current PLwC state could not be loaded.",
    saved: "The shared PLwC settings were saved.",
    saveError: "The settings could not be saved.",
    planError: "The profile change could not be reviewed.",
    activationError: "The profile could not be activated.",
    activated: "The profile was activated through the Governor.",
    validPlan: "valid and ready for confirmation",
    invalidPlan: "cannot be applied",
    noWrites: "none",
    noWarnings: "No setup warnings.",
    warnings: "Setup warnings",
    invalidNumber: "Every threshold must be a whole number from 1 through 1,000,000.",
    unchanged: "This profile is already active.",
    working: "PLwC is processing the request...",
    creationPlanError: "The profile creation plan could not be prepared.",
    creationApplyError: "The new profile could not be created.",
    profileCreated: "The new profile was created and activated through the Governor.",
    creationValid: "valid and ready for confirmation",
    creationInvalid: "not ready to apply",
    willActivate: "will become active after creation",
    activationBlocked: "activation blocked",
    noMissingAnswers: "none",
    profileIncomplete: "incomplete",
    missingFiles: "Missing files",
    workspacePlanError: "The workspace change could not be reviewed.",
    workspaceApplyError: "The workspace could not be changed.",
    workspaceChanged: "The workspace was changed after confirmation.",
    workspaceUnchanged: "This workspace is already active.",
    noLauncherResult: "No launcher result has been stored yet.",
    doctorDiagnosisError: "The PLwC Doctor diagnosis failed.",
    doctorPlanError: "The PLwC Doctor repair plan could not be created.",
    doctorApplyError: "The PLwC Doctor repair failed.",
    doctorDiagnosisComplete: "Diagnosis complete",
    doctorRepairComplete: "The confirmed repair and postflight completed.",
    doctorNoChanges: "The repair plan contains no changes.",
    doctorRolledBack: "The repair failed; completed steps were rolled back.",
    doctorExported: "The diagnosis report was prepared for download.",
    updateCheckError: "The update check failed.",
    updatePlanError: "The verified download plan could not be created.",
    updateDownloadError: "The update could not be downloaded safely.",
    updateInstallError: "The verified installer could not be started.",
    updateDownloaded: "Download complete; size, SHA-256, and build identity are verified.",
    updateInstallerComplete: "The r26 installer completed. Its postflight and rollback report are authoritative.",
    unknown: "unknown"
  }
}[language];

const elements = Object.fromEntries([
  "notice", "refresh-button", "active-profile", "profile-state", "profile-source",
  "gateway-version", "profile-select", "review-profile-button", "profiles-path", "workspace-input",
  "profile-details", "review-workspace-button", "component-table-body", "component-inventory-note",
  "launcher-result", "workspace-dialog", "workspace-plan-current", "workspace-plan-requested",
  "browser-extension-contact",
  "doctor-diagnose-button", "doctor-plan-button", "doctor-export-button", "doctor-summary",
  "doctor-findings", "doctor-dialog", "doctor-plan-id", "doctor-snapshot-id",
  "doctor-plan-actions", "doctor-confirmation", "doctor-apply-button",
  "workspace-plan-validation", "workspace-plan-writes", "workspace-plan-migration",
  "workspace-confirmation", "apply-workspace-button",
  "memory-threshold", "persona-threshold", "temperament-threshold", "memory-source",
  "persona-source", "temperament-source", "persona-toggle", "qdrant-toggle",
  "persona-toggle-source", "qdrant-toggle-source", "save-button", "settings-file",
  "profile-state-file", "workspace-path", "setup-warnings", "profile-dialog",
  "plan-current", "plan-requested", "plan-validation", "plan-directory", "plan-writes",
  "plan-missing-row", "plan-missing", "profile-confirmation", "activate-profile-button",
  "new-profile-button", "create-profile-dialog", "create-profile-form", "create-profile-entry",
  "create-profile-plan", "persona-onboarding-note", "review-create-profile-button",
  "back-to-profile-form-button", "create-profile-button", "create-profile-confirmation",
  "new-profile-name",
  "creation-plan-profile", "creation-plan-activation", "creation-plan-validation",
  "creation-plan-directory", "creation-plan-files", "creation-plan-missing-row",
  "creation-plan-missing", "update-check-button", "update-review-button", "update-state",
  "update-kind", "update-last-checked", "update-last-valid", "update-notes", "update-error",
  "update-dialog", "update-plan-id", "update-plan-file", "update-plan-integrity",
  "update-plan-build", "update-download-confirmation", "update-download-button",
  "update-install-step", "update-download-result", "update-install-confirmation",
  "update-install-button"
].map((id) => [id, document.getElementById(id)]));

let currentState = null;
let currentPlan = null;
let currentCreationPlan = null;
let currentWorkspacePlan = null;
let currentDoctorDiagnosis = null;
let currentDoctorPlan = null;
let currentUpdatePlan = null;
let currentUpdateDownloaded = false;

const onboardingFields = [
  "profile_name", "role_use_case", "preferred_name", "form_of_address", "tone",
  "working_style", "strictness", "memory_scope", "confirmation_boundaries",
  "project_context", "language_preference", "special_instructions"
];

function setBusy(isBusy) {
  document.body.classList.toggle("busy", isBusy);
  [
    elements["refresh-button"], elements["save-button"], elements["review-profile-button"],
    elements["new-profile-button"], elements["review-create-profile-button"],
    elements["review-workspace-button"], elements["doctor-diagnose-button"],
    elements["doctor-plan-button"], elements["doctor-export-button"],
    elements["update-check-button"], elements["update-review-button"]
  ].forEach((button) => {
    if (button) {
      button.disabled = isBusy;
    }
  });
  if (!isBusy) {
    updateProfileButton();
    updateWorkspaceButton();
    updateDoctorButtons();
    updateUpdateButtons();
  }
}

function showNotice(message, isError = false) {
  const notice = elements.notice;
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.hidden = false;
  notice.scrollIntoView({ block: "nearest" });
}

function clearNotice() {
  elements.notice.hidden = true;
  elements.notice.textContent = "";
  elements.notice.classList.remove("error");
}

function displayError(error, fallback) {
  const message = error instanceof Error && error.message ? error.message : fallback;
  showNotice(`${fallback} ${message}`, true);
}

function structuredErrorMessage(payload, status) {
  const direct = [payload?.error, payload?.reason, payload?.message, payload?.validation_error]
    .find((value) => typeof value === "string" && value.trim());
  const missing = Array.isArray(payload?.missing_files) ? payload.missing_files.filter(Boolean) : [];
  const suffix = missing.length ? `${text.missingFiles}: ${missing.join(", ")}` : "";
  return [direct, suffix].filter(Boolean).join(" — ") || `HTTP ${status}`;
}

async function request(path, options = {}, { allowBusinessRejection = false } = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-PLwC-Config": "1",
      ...(options.headers || {})
    }
  });
  let payload;
  try {
    payload = await response.json();
  } catch (_error) {
    throw new Error(`HTTP ${response.status}`);
  }
  if (!response.ok) {
    throw new Error(structuredErrorMessage(payload, response.status));
  }
  if (payload.ok === false && !allowBusinessRejection) {
    throw new Error(structuredErrorMessage(payload, response.status));
  }
  return payload;
}

function sourceLabel(value) {
  return `${text.source}: ${value || "default"}`;
}

function renderState(state) {
  currentState = state;
  const runtime = state.runtime;
  const settings = state.settings;

  elements["active-profile"].textContent = runtime.active_profile_name || "-";
  elements["profile-state"].textContent = `${runtime.active_profile_status || "-"} (${runtime.profile_valid ? text.valid : text.invalid})`;
  elements["profile-source"].textContent = runtime.active_profile_source || "-";
  elements["gateway-version"].textContent = state.gateway_version;
  elements["profiles-path"].textContent = runtime.profiles_path || "-";
  elements["settings-file"].textContent = state.files.shared_settings || "-";
  elements["profile-state-file"].textContent = state.files.active_profile_state || "-";
  elements["workspace-path"].textContent = runtime.workspace_path || "-";
  elements["workspace-input"].value = settings.workspace_path || runtime.workspace_path || "";

  const profileSelect = elements["profile-select"];
  profileSelect.replaceChildren();
  for (const rawProfile of runtime.available_profiles) {
    const profile = typeof rawProfile === "object" && rawProfile !== null
      ? rawProfile
      : { name: String(rawProfile), valid: true, activatable: true, missing_files: [] };
    const option = document.createElement("option");
    option.value = profile.name;
    option.textContent = profile.valid
      ? profile.name
      : `${profile.name} — ${text.profileIncomplete} (${(profile.missing_files || []).length})`;
    option.dataset.valid = profile.valid === true ? "true" : "false";
    option.dataset.activatable = profile.activatable === true ? "true" : "false";
    option.dataset.reason = profile.reason || profile.status || "";
    option.dataset.missingFiles = JSON.stringify(profile.missing_files || []);
    option.selected = profile.name.toLocaleLowerCase() === String(runtime.active_profile_name).toLocaleLowerCase();
    profileSelect.append(option);
  }

  renderComponentInventory(state.component_inventory);
  renderLauncherResult(state.launcher_last_result);
  renderBrowserExtensionContact(state.browser_extension_last_contact);
  renderUpdateCenter(state.update_center);
  if (!profileSelect.value && runtime.active_profile_name) {
    const option = document.createElement("option");
    option.value = runtime.active_profile_name;
    option.textContent = runtime.active_profile_name;
    option.selected = true;
    profileSelect.append(option);
  }

  elements["memory-threshold"].value = settings.memory_write_threshold;
  elements["persona-threshold"].value = settings.persona_write_threshold;
  elements["temperament-threshold"].value = settings.temperament_write_threshold;
  elements["persona-toggle"].checked = settings.persona_layer_enabled;
  elements["qdrant-toggle"].checked = settings.qdrant_enabled;
  elements["memory-source"].textContent = sourceLabel(settings.memory_write_threshold_source);
  elements["persona-source"].textContent = sourceLabel(settings.persona_write_threshold_source);
  elements["temperament-source"].textContent = sourceLabel(settings.temperament_write_threshold_source);
  elements["persona-toggle-source"].textContent = sourceLabel(settings.persona_layer_enabled_source);
  elements["qdrant-toggle-source"].textContent = sourceLabel(settings.qdrant_enabled_source);

  const warnings = Array.isArray(state.setup_warnings) ? state.setup_warnings : [];
  if (warnings.length) {
    elements["setup-warnings"].textContent = `${text.warnings}: ${warnings.join(" | ")}`;
    elements["setup-warnings"].hidden = false;
  } else {
    elements["setup-warnings"].textContent = text.noWarnings;
    elements["setup-warnings"].hidden = true;
  }
  updateProfileDetails();
  updateWorkspaceButton();
  updateProfileButton();
}

function renderComponentInventory(inventory) {
  const body = elements["component-table-body"];
  body.replaceChildren();
  const components = Array.isArray(inventory?.components) ? inventory.components : [];
  for (const component of components) {
    const row = document.createElement("tr");
    const installed = component.installed || {};
    const source = installed.source || {};
    const notInstalled = ["missing", "optional"].includes(component.status);
    const identity = installed.semantic_version || installed.build_revision || installed.build_id
      || (notInstalled ? (language === "de" ? "nicht installiert" : "not installed") : text.unknown);
    const values = [
      component.display_name || component.id,
      identity,
      component.status || text.unknown,
      source.trust || text.unknown
    ];
    values.forEach((value, index) => {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      if (index === 2) {
        cell.className = `component-status status-${String(component.status || "unknown")}`;
      }
      row.append(cell);
    });
    body.append(row);
  }
  elements["component-inventory-note"].textContent = inventory?.error
    ? String(inventory.error)
    : `${inventory?.release_family || "-"} · Matrix ${inventory?.matrix_version || "-"}`;
}

function renderLauncherResult(result) {
  if (!result) {
    elements["launcher-result"].textContent = text.noLauncherResult;
    return;
  }
  const buildId = result.buildIdentity?.buildId || text.unknown;
  elements["launcher-result"].textContent = [
    result.timestamp || text.unknown,
    result.action || text.unknown,
    result.statusCode || result.state || text.unknown,
    `${result.toolCount ?? 0}/8`,
    buildId,
    result.bridgePath || text.unknown
  ].join(" · ");
}

function renderBrowserExtensionContact(contact) {
  if (!contact) {
    elements["browser-extension-contact"].textContent = text.unknown;
    return;
  }
  elements["browser-extension-contact"].textContent = [
    contact.receivedAt || contact.reportedAt || text.unknown,
    contact.browserFamily || text.unknown,
    contact.extensionId || text.unknown,
    contact.packageVersion || text.unknown,
    `protocol ${contact.protocolVersion || text.unknown}`,
    contact.stale ? (language === "de" ? "veraltet" : "stale") : (language === "de" ? "aktuell" : "current")
  ].join(" · ");
}

function renderUpdateCenter(update) {
  const value = update || {};
  elements["update-state"].textContent = value.state || "never_checked";
  elements["update-state"].className = `component-status update-${String(value.state || "never_checked")}`;
  elements["update-kind"].textContent = value.update_kind || "-";
  elements["update-last-checked"].textContent = value.last_checked_at || "-";
  elements["update-last-valid"].textContent = value.last_valid_at || "-";
  elements["update-notes"].textContent = value.release?.notes?.[language] || "-";
  elements["update-error"].textContent = value.error || "";
  elements["update-error"].hidden = !value.error;
  updateUpdateButtons();
}

function updateUpdateButtons() {
  const busy = document.body.classList.contains("busy");
  const update = currentState?.update_center;
  const artifacts = update?.release?.artifacts;
  const verifiedAvailable = update?.integrity_verified === true || update?.cached_release_available === true;
  elements["update-check-button"].disabled = busy;
  elements["update-review-button"].disabled = busy || !verifiedAvailable || !Array.isArray(artifacts) || artifacts.length === 0;
}

async function checkUpdates() {
  clearNotice();
  setBusy(true);
  try {
    const update = await request("/api/update/check", {
      method: "POST",
      body: JSON.stringify({})
    }, { allowBusinessRejection: true });
    currentState.update_center = update;
    renderUpdateCenter(update);
  } catch (error) {
    displayError(error, text.updateCheckError);
  } finally {
    setBusy(false);
  }
}

async function reviewUpdateDownload() {
  const artifact = currentState?.update_center?.release?.artifacts?.[0];
  if (!artifact?.id) return;
  clearNotice();
  setBusy(true);
  try {
    currentUpdatePlan = await request("/api/update/download/plan", {
      method: "POST",
      body: JSON.stringify({ artifact_id: artifact.id })
    });
    currentUpdateDownloaded = false;
    const planned = currentUpdatePlan.artifact || {};
    elements["update-plan-id"].textContent = currentUpdatePlan.plan_id || "-";
    elements["update-plan-file"].textContent = planned.file_name || "-";
    elements["update-plan-integrity"].textContent = `${planned.size ?? "-"} bytes · ${planned.sha256 || "-"}`;
    elements["update-plan-build"].textContent = planned.build_identity?.build_id || "-";
    elements["update-download-confirmation"].checked = false;
    elements["update-download-button"].disabled = true;
    elements["update-install-confirmation"].checked = false;
    elements["update-install-button"].disabled = true;
    elements["update-install-step"].hidden = true;
    elements["update-download-result"].textContent = "";
    elements["update-dialog"].showModal();
  } catch (error) {
    displayError(error, text.updatePlanError);
  } finally {
    setBusy(false);
  }
}

async function downloadUpdate() {
  if (!currentUpdatePlan || !elements["update-download-confirmation"].checked) return;
  setBusy(true);
  try {
    const result = await request("/api/update/download", {
      method: "POST",
      body: JSON.stringify({ plan_id: currentUpdatePlan.plan_id, confirmed: true })
    });
    currentUpdateDownloaded = result.integrity_verified === true;
    elements["update-download-result"].textContent = `${text.updateDownloaded} ${result.artifact_path || ""}`;
    elements["update-install-step"].hidden = !currentUpdateDownloaded;
    elements["update-install-confirmation"].checked = false;
    elements["update-install-button"].disabled = true;
    elements["update-download-button"].disabled = true;
  } catch (error) {
    displayError(error, text.updateDownloadError);
  } finally {
    setBusy(false);
  }
}

async function installUpdate() {
  if (!currentUpdatePlan || !currentUpdateDownloaded || !elements["update-install-confirmation"].checked) return;
  setBusy(true);
  try {
    const result = await request("/api/update/install", {
      method: "POST",
      body: JSON.stringify({ plan_id: currentUpdatePlan.plan_id, confirmed: true })
    }, { allowBusinessRejection: true });
    elements["update-dialog"].close();
    showNotice(result.ok ? text.updateInstallerComplete : `${text.updateInstallError} ${result.rollback_report || ""}`, result.ok !== true);
  } catch (error) {
    elements["update-dialog"].close();
    displayError(error, text.updateInstallError);
  } finally {
    setBusy(false);
  }
}

function updateDoctorButtons() {
  const busy = document.body.classList.contains("busy");
  elements["doctor-diagnose-button"].disabled = busy;
  elements["doctor-plan-button"].disabled = busy || !currentDoctorDiagnosis;
  elements["doctor-export-button"].disabled = busy || !currentDoctorDiagnosis;
}

function renderDoctorDiagnosis(report) {
  currentDoctorDiagnosis = report;
  currentDoctorPlan = null;
  const summary = report.summary || {};
  elements["doctor-summary"].textContent = [
    text.doctorDiagnosisComplete,
    `Snapshot ${report.snapshot_id || text.unknown}`,
    `PASS ${summary.pass ?? 0}`,
    `WARN ${summary.warnings ?? 0}`,
    `FAIL ${summary.failures ?? 0}`,
    language === "de" ? `reparierbar ${summary.repairable ?? 0}` : `repairable ${summary.repairable ?? 0}`
  ].join(" · ");
  const findings = elements["doctor-findings"];
  findings.replaceChildren();
  for (const check of Array.isArray(report.checks) ? report.checks : []) {
    const item = document.createElement("li");
    const heading = document.createElement("strong");
    heading.textContent = `${check.status || text.unknown} — ${check.id || text.unknown}`;
    const detail = document.createElement("span");
    detail.textContent = `${check.recommendation || ""} ${check.evidence?.join(" · ") || ""}`.trim();
    item.className = `doctor-finding doctor-${String(check.status || "unknown").toLocaleLowerCase()}`;
    item.append(heading, detail);
    findings.append(item);
  }
  updateDoctorButtons();
}

async function runDoctorDiagnosis() {
  clearNotice();
  setBusy(true);
  try {
    const report = await request("/api/doctor/diagnose", {
      method: "POST",
      body: JSON.stringify({})
    });
    renderDoctorDiagnosis(report);
  } catch (error) {
    displayError(error, text.doctorDiagnosisError);
  } finally {
    setBusy(false);
  }
}

function renderDoctorPlan(plan) {
  currentDoctorPlan = plan;
  const actions = Array.isArray(plan.actions) ? plan.actions : [];
  elements["doctor-plan-id"].textContent = plan.plan_id || "-";
  elements["doctor-snapshot-id"].textContent = plan.snapshot_id || "-";
  elements["doctor-plan-actions"].textContent = actions.map((action) =>
    `${action.explanation || action.type}: ${action.path || action.source || "-"} (${action.risk || text.unknown})`
  ).join(" | ") || text.noWrites;
  elements["doctor-confirmation"].checked = false;
  elements["doctor-confirmation"].disabled = actions.length === 0;
  elements["doctor-apply-button"].disabled = true;
}

async function reviewDoctorRepair() {
  if (!currentDoctorDiagnosis) return;
  clearNotice();
  setBusy(true);
  try {
    const plan = await request("/api/doctor/plan", {
      method: "POST",
      body: JSON.stringify({ snapshot_id: currentDoctorDiagnosis.snapshot_id })
    });
    renderDoctorPlan(plan);
    elements["doctor-dialog"].showModal();
    if (plan.no_changes) showNotice(text.doctorNoChanges);
  } catch (error) {
    displayError(error, text.doctorPlanError);
  } finally {
    setBusy(false);
  }
}

async function applyDoctorRepair() {
  if (!currentDoctorPlan || !elements["doctor-confirmation"].checked || currentDoctorPlan.no_changes) return;
  setBusy(true);
  try {
    const result = await request("/api/doctor/apply", {
      method: "POST",
      body: JSON.stringify({ plan_id: currentDoctorPlan.plan_id, confirmed: true })
    }, { allowBusinessRejection: true });
    elements["doctor-dialog"].close();
    if (result.postflight) renderDoctorDiagnosis(result.postflight);
    showNotice(result.ok ? text.doctorRepairComplete : text.doctorRolledBack, result.ok !== true);
  } catch (error) {
    elements["doctor-dialog"].close();
    displayError(error, text.doctorApplyError);
  } finally {
    setBusy(false);
  }
}

function exportDoctorDiagnosis() {
  if (!currentDoctorDiagnosis) return;
  const blob = new Blob([`${JSON.stringify(currentDoctorDiagnosis, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `plwc-doctor-${currentDoctorDiagnosis.snapshot_id || "diagnosis"}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  showNotice(text.doctorExported);
}

function selectedProfile() {
  const selected = elements["profile-select"].value;
  return currentState?.runtime?.available_profiles?.find((profile) =>
    typeof profile === "object" && String(profile.name).toLocaleLowerCase() === selected.toLocaleLowerCase()
  );
}

function updateProfileDetails() {
  const profile = selectedProfile();
  if (!profile) {
    elements["profile-details"].textContent = "";
    return;
  }
  const missing = Array.isArray(profile.missing_files) ? profile.missing_files : [];
  elements["profile-details"].textContent = profile.valid
    ? `${profile.status || text.valid} · ${profile.path || ""}`
    : `${profile.reason || profile.status || text.invalid}${missing.length ? ` — ${text.missingFiles}: ${missing.join(", ")}` : ""}`;
  elements["profile-details"].classList.toggle("error-text", profile.valid !== true);
}

function updateProfileButton() {
  const selected = elements["profile-select"].value;
  const active = currentState?.runtime?.active_profile_name;
  const same = selected && active && selected.toLocaleLowerCase() === active.toLocaleLowerCase();
  elements["review-profile-button"].disabled = !selected || same || document.body.classList.contains("busy");
}

function updateWorkspaceButton() {
  const requested = elements["workspace-input"].value.trim();
  const current = currentState?.runtime?.workspace_path || "";
  elements["review-workspace-button"].disabled = !requested || requested === current ||
    document.body.classList.contains("busy");
}

async function loadState({ announce = false } = {}) {
  setBusy(true);
  try {
    const state = await request("/api/state", { method: "GET", headers: {} });
    renderState(state);
    if (announce) {
      clearNotice();
    }
  } catch (error) {
    displayError(error, text.loadingError);
  } finally {
    setBusy(false);
  }
}

function readThreshold(id) {
  const value = Number(elements[id].value);
  if (!Number.isInteger(value) || value < 1 || value > 1000000) {
    throw new Error(text.invalidNumber);
  }
  return value;
}

async function saveSettings() {
  clearNotice();
  let settings;
  try {
    settings = {
      memory_write_threshold: readThreshold("memory-threshold"),
      persona_write_threshold: readThreshold("persona-threshold"),
      temperament_write_threshold: readThreshold("temperament-threshold"),
      qdrant_enabled: elements["qdrant-toggle"].checked,
      persona_layer_enabled: elements["persona-toggle"].checked
    };
  } catch (error) {
    displayError(error, text.saveError);
    return;
  }
  setBusy(true);
  try {
    const state = await request("/api/settings", {
      method: "POST",
      body: JSON.stringify({ settings })
    });
    renderState(state);
    showNotice(text.saved);
  } catch (error) {
    displayError(error, text.saveError);
  } finally {
    setBusy(false);
  }
}

function renderWorkspacePlan(plan) {
  currentWorkspacePlan = plan;
  elements["workspace-plan-current"].textContent = plan.current_workspace_path || "-";
  elements["workspace-plan-requested"].textContent = plan.requested_workspace_path || "-";
  elements["workspace-plan-validation"].textContent = plan.valid
    ? text.validPlan
    : `${text.invalidPlan}: ${plan.reason || "-"}`;
  const writes = Array.isArray(plan.planned_writes) ? plan.planned_writes : [];
  elements["workspace-plan-writes"].textContent = writes.map((write) =>
    typeof write === "object" ? `${write.path} (${write.purpose})` : String(write)
  ).join(", ") || text.noWrites;
  elements["workspace-plan-migration"].textContent = plan.data_migration_note || "-";
  elements["workspace-confirmation"].checked = false;
  elements["workspace-confirmation"].disabled = !plan.valid;
  elements["apply-workspace-button"].disabled = true;
}

async function reviewWorkspace() {
  clearNotice();
  const workspacePath = elements["workspace-input"].value.trim();
  if (workspacePath === currentState?.runtime?.workspace_path) {
    showNotice(text.workspaceUnchanged);
    return;
  }
  setBusy(true);
  try {
    const plan = await request("/api/workspace/plan", {
      method: "POST",
      body: JSON.stringify({ workspace_path: workspacePath })
    }, { allowBusinessRejection: true });
    renderWorkspacePlan(plan);
    elements["workspace-dialog"].showModal();
  } catch (error) {
    displayError(error, text.workspacePlanError);
  } finally {
    setBusy(false);
  }
}

async function applyWorkspace() {
  if (!currentWorkspacePlan || !currentWorkspacePlan.valid || !elements["workspace-confirmation"].checked) {
    return;
  }
  setBusy(true);
  try {
    const result = await request("/api/workspace/apply", {
      method: "POST",
      body: JSON.stringify({
        workspace_path: currentWorkspacePlan.requested_workspace_path,
        plan_digest: currentWorkspacePlan.plan_digest,
        confirmed: true
      })
    });
    elements["workspace-dialog"].close();
    renderState(result.state);
    showNotice(text.workspaceChanged);
  } catch (error) {
    elements["workspace-dialog"].close();
    displayError(error, text.workspaceApplyError);
  } finally {
    setBusy(false);
  }
}

function renderPlan(plan) {
  currentPlan = plan;
  elements["plan-current"].textContent = plan.current_active_profile || "-";
  elements["plan-requested"].textContent = plan.requested_active_profile || "-";
  elements["plan-validation"].textContent = plan.valid ? text.validPlan : `${text.invalidPlan}: ${plan.reason || "-"}`;
  elements["plan-directory"].textContent = plan.target_profile_directory || "-";
  const writes = Array.isArray(plan.planned_writes) ? plan.planned_writes.map((write) => {
    if (typeof write === "string") {
      return write;
    }
    if (write && typeof write === "object") {
      const file = String(write.file || "");
      const purpose = String(write.purpose || "");
      return purpose ? `${file} (${purpose})` : file;
    }
    return String(write);
  }).filter(Boolean) : [];
  elements["plan-writes"].textContent = writes.length ? writes.join(", ") : text.noWrites;
  const missing = Array.isArray(plan.missing_files) ? plan.missing_files : [];
  elements["plan-missing"].textContent = missing.join(", ");
  elements["plan-missing-row"].hidden = missing.length === 0;
  elements["profile-confirmation"].checked = false;
  elements["profile-confirmation"].disabled = !plan.valid;
  elements["activate-profile-button"].disabled = true;
}

async function reviewProfile() {
  clearNotice();
  const profileName = elements["profile-select"].value;
  if (!profileName) {
    showNotice(text.planError, true);
    return;
  }
  if (profileName.toLocaleLowerCase() === String(currentState?.runtime?.active_profile_name).toLocaleLowerCase()) {
    showNotice(text.unchanged);
    return;
  }
  setBusy(true);
  try {
    const plan = await request("/api/profile/plan", {
      method: "POST",
      body: JSON.stringify({ profile_name: profileName })
    }, { allowBusinessRejection: true });
    renderPlan(plan);
    elements["profile-dialog"].showModal();
  } catch (error) {
    displayError(error, text.planError);
  } finally {
    setBusy(false);
  }
}

async function activateProfile() {
  if (!currentPlan || !elements["profile-confirmation"].checked || !currentPlan.valid) {
    return;
  }
  elements["activate-profile-button"].disabled = true;
  try {
    const result = await request("/api/profile/apply", {
      method: "POST",
      body: JSON.stringify({
        profile_name: currentPlan.requested_active_profile,
        plan_digest: currentPlan.plan_digest,
        confirmed: true
      })
    });
    elements["profile-dialog"].close();
    renderState(result.state);
    showNotice(text.activated);
  } catch (error) {
    elements["profile-dialog"].close();
    displayError(error, text.activationError);
  }
}

function configurePersonaOnboarding() {
  const enabled = currentState?.settings?.persona_layer_enabled !== false;
  elements["persona-onboarding-note"].hidden = enabled;
  document.querySelectorAll(".persona-onboarding-field").forEach((field) => {
    field.hidden = !enabled;
    const control = field.querySelector("input, textarea, select");
    if (control) {
      control.disabled = !enabled;
      control.required = enabled;
    }
  });
}

function resetCreationDialog() {
  currentCreationPlan = null;
  elements["create-profile-form"].reset();
  elements["create-profile-entry"].hidden = false;
  elements["create-profile-plan"].hidden = true;
  elements["create-profile-confirmation"].checked = false;
  elements["create-profile-confirmation"].disabled = false;
  elements["create-profile-button"].disabled = true;
  elements["creation-plan-missing-row"].hidden = true;
  configurePersonaOnboarding();
}

function openCreateProfile() {
  clearNotice();
  resetCreationDialog();
  elements["create-profile-dialog"].showModal();
  elements["new-profile-name"].focus();
}

function collectOnboardingAnswers() {
  const answers = {};
  for (const name of onboardingFields) {
    const control = elements["create-profile-form"].elements.namedItem(name);
    answers[name] = control && !control.disabled ? String(control.value || "").trim() : "";
  }
  return answers;
}

function renderCreationPlan(plan) {
  currentCreationPlan = plan;
  const approved = plan.approved_for_apply === true;
  const activation = plan.activation || {};
  const missing = Array.isArray(plan.missing_required_fields) ? plan.missing_required_fields : [];
  const targetFiles = Array.isArray(plan.target_files) ? plan.target_files.filter(Boolean) : [];

  elements["creation-plan-profile"].textContent = plan.profile_name || "-";
  elements["creation-plan-activation"].textContent = activation.will_be_active
    ? text.willActivate
    : `${text.activationBlocked}: ${activation.blocked_reason || "-"}`;
  elements["creation-plan-validation"].textContent = approved
    ? text.creationValid
    : `${text.creationInvalid}: ${plan.validation_error || missing.join(", ") || "-"}`;
  elements["creation-plan-directory"].textContent = plan.profile_directory || "-";
  elements["creation-plan-files"].textContent = targetFiles.length ? targetFiles.join(", ") : text.noWrites;
  elements["creation-plan-missing"].textContent = missing.length ? missing.join(", ") : text.noMissingAnswers;
  elements["creation-plan-missing-row"].hidden = missing.length === 0;
  elements["create-profile-confirmation"].checked = false;
  elements["create-profile-confirmation"].disabled = !approved;
  elements["create-profile-button"].disabled = true;
  elements["create-profile-entry"].hidden = true;
  elements["create-profile-plan"].hidden = false;
  elements["create-profile-dialog"].scrollTop = 0;
}

async function reviewProfileCreation() {
  clearNotice();
  configurePersonaOnboarding();
  if (!elements["create-profile-form"].reportValidity()) {
    return;
  }
  const onboardingAnswers = collectOnboardingAnswers();
  setBusy(true);
  try {
    const plan = await request("/api/profile/create/plan", {
      method: "POST",
      body: JSON.stringify({ onboarding_answers: onboardingAnswers })
    }, { allowBusinessRejection: true });
    renderCreationPlan(plan);
  } catch (error) {
    elements["create-profile-dialog"].close();
    displayError(error, text.creationPlanError);
  } finally {
    setBusy(false);
  }
}

function backToCreationForm() {
  currentCreationPlan = null;
  elements["create-profile-confirmation"].checked = false;
  elements["create-profile-entry"].hidden = false;
  elements["create-profile-plan"].hidden = true;
  elements["create-profile-dialog"].scrollTop = 0;
}

async function applyProfileCreation() {
  if (!currentCreationPlan || !elements["create-profile-confirmation"].checked ||
      currentCreationPlan.approved_for_apply !== true) {
    return;
  }
  elements["create-profile-button"].disabled = true;
  setBusy(true);
  try {
    const result = await request("/api/profile/create/apply", {
      method: "POST",
      body: JSON.stringify({
        onboarding_answers: currentCreationPlan.onboarding_answers,
        plan_digest: currentCreationPlan.plan_digest,
        confirmed: true
      })
    });
    elements["create-profile-dialog"].close();
    renderState(result.state);
    showNotice(text.profileCreated);
  } catch (error) {
    elements["create-profile-dialog"].close();
    displayError(error, text.creationApplyError);
  } finally {
    setBusy(false);
  }
}

elements["refresh-button"].addEventListener("click", () => loadState({ announce: true }));
elements["save-button"].addEventListener("click", saveSettings);
elements["review-workspace-button"].addEventListener("click", reviewWorkspace);
elements["review-profile-button"].addEventListener("click", reviewProfile);
elements["new-profile-button"].addEventListener("click", openCreateProfile);
elements["review-create-profile-button"].addEventListener("click", reviewProfileCreation);
elements["doctor-diagnose-button"].addEventListener("click", runDoctorDiagnosis);
elements["doctor-plan-button"].addEventListener("click", reviewDoctorRepair);
elements["doctor-export-button"].addEventListener("click", exportDoctorDiagnosis);
elements["update-check-button"].addEventListener("click", checkUpdates);
elements["update-review-button"].addEventListener("click", reviewUpdateDownload);
elements["update-download-confirmation"].addEventListener("change", () => {
  elements["update-download-button"].disabled = !elements["update-download-confirmation"].checked || !currentUpdatePlan;
});
elements["update-download-button"].addEventListener("click", downloadUpdate);
elements["update-install-confirmation"].addEventListener("change", () => {
  elements["update-install-button"].disabled = !elements["update-install-confirmation"].checked || !currentUpdateDownloaded;
});
elements["update-install-button"].addEventListener("click", installUpdate);
elements["update-dialog"].addEventListener("close", () => {
  currentUpdatePlan = null;
  currentUpdateDownloaded = false;
  elements["update-download-confirmation"].checked = false;
  elements["update-install-confirmation"].checked = false;
});
elements["doctor-confirmation"].addEventListener("change", () => {
  elements["doctor-apply-button"].disabled = !elements["doctor-confirmation"].checked ||
    !currentDoctorPlan || currentDoctorPlan.no_changes === true;
});
elements["doctor-apply-button"].addEventListener("click", applyDoctorRepair);
elements["doctor-dialog"].addEventListener("close", () => {
  currentDoctorPlan = null;
  elements["doctor-confirmation"].checked = false;
});
elements["back-to-profile-form-button"].addEventListener("click", backToCreationForm);
elements["create-profile-button"].addEventListener("click", applyProfileCreation);
elements["profile-select"].addEventListener("change", () => {
  updateProfileDetails();
  updateProfileButton();
});
elements["workspace-input"].addEventListener("input", updateWorkspaceButton);
elements["workspace-confirmation"].addEventListener("change", () => {
  elements["apply-workspace-button"].disabled = !elements["workspace-confirmation"].checked ||
    currentWorkspacePlan?.valid !== true;
});
elements["apply-workspace-button"].addEventListener("click", applyWorkspace);
elements["workspace-dialog"].addEventListener("close", () => {
  currentWorkspacePlan = null;
  elements["workspace-confirmation"].checked = false;
});
elements["profile-confirmation"].addEventListener("change", () => {
  elements["activate-profile-button"].disabled = !elements["profile-confirmation"].checked || !currentPlan?.valid;
});
elements["activate-profile-button"].addEventListener("click", activateProfile);
elements["profile-dialog"].addEventListener("close", () => {
  currentPlan = null;
  elements["profile-confirmation"].checked = false;
});
elements["create-profile-confirmation"].addEventListener("change", () => {
  elements["create-profile-button"].disabled = !elements["create-profile-confirmation"].checked ||
    currentCreationPlan?.approved_for_apply !== true;
});
elements["create-profile-dialog"].addEventListener("close", resetCreationDialog);

loadState();
