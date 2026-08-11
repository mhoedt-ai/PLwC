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
    noMissingAnswers: "keine"
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
    noMissingAnswers: "none"
  }
}[language];

const elements = Object.fromEntries([
  "notice", "refresh-button", "active-profile", "profile-state", "profile-source",
  "gateway-version", "profile-select", "review-profile-button", "profiles-path",
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
  "creation-plan-missing"
].map((id) => [id, document.getElementById(id)]));

let currentState = null;
let currentPlan = null;
let currentCreationPlan = null;

const onboardingFields = [
  "profile_name", "role_use_case", "preferred_name", "form_of_address", "tone",
  "working_style", "strictness", "memory_scope", "confirmation_boundaries",
  "project_context", "language_preference", "special_instructions"
];

function setBusy(isBusy) {
  document.body.classList.toggle("busy", isBusy);
  [
    elements["refresh-button"], elements["save-button"], elements["review-profile-button"],
    elements["new-profile-button"], elements["review-create-profile-button"]
  ].forEach((button) => {
    if (button) {
      button.disabled = isBusy;
    }
  });
  if (!isBusy) {
    updateProfileButton();
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

async function request(path, options = {}) {
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
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
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

  const profileSelect = elements["profile-select"];
  profileSelect.replaceChildren();
  for (const profile of runtime.available_profiles) {
    const option = document.createElement("option");
    option.value = profile;
    option.textContent = profile;
    option.selected = profile.toLocaleLowerCase() === String(runtime.active_profile_name).toLocaleLowerCase();
    profileSelect.append(option);
  }
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
  updateProfileButton();
}

function updateProfileButton() {
  const selected = elements["profile-select"].value;
  const active = currentState?.runtime?.active_profile_name;
  const same = selected && active && selected.toLocaleLowerCase() === active.toLocaleLowerCase();
  elements["review-profile-button"].disabled = !selected || same || document.body.classList.contains("busy");
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
    });
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
    });
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
elements["review-profile-button"].addEventListener("click", reviewProfile);
elements["new-profile-button"].addEventListener("click", openCreateProfile);
elements["review-create-profile-button"].addEventListener("click", reviewProfileCreation);
elements["back-to-profile-form-button"].addEventListener("click", backToCreationForm);
elements["create-profile-button"].addEventListener("click", applyProfileCreation);
elements["profile-select"].addEventListener("change", updateProfileButton);
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
