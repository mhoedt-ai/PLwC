import type { ConnectionState, LauncherStatus } from "./messages";

export type UiLanguage = "de" | "en";

type TextKey =
  | "bridge_error"
  | "bridge_offline"
  | "error_none"
  | "label_bridge"
  | "label_build_id"
  | "label_build_match"
  | "label_bridge_version"
  | "label_endpoint"
  | "label_error"
  | "label_extension_version"
  | "label_launcher"
  | "label_launcher_version"
  | "label_log"
  | "label_pending"
  | "label_tools"
  | "launcher_busy"
  | "launcher_failed"
  | "launcher_health_timeout"
  | "launcher_invalid"
  | "launcher_node_missing"
  | "launcher_not_requested"
  | "launcher_port_in_use"
  | "launcher_ready"
  | "launcher_setup_required"
  | "launcher_start_failed"
  | "launcher_starting"
  | "launcher_store_boundary"
  | "local_status"
  | "no_runtime_status"
  | "reconnect"
  | "runtime_status"
  | "setup_download"
  | "unexpected_error"
  | "working";

const TEXT: Record<UiLanguage, Record<TextKey, string>> = {
  de: {
    bridge_error: "Verbindungsfehler",
    bridge_offline: "Keine Verbindung zur lokalen Bridge.",
    error_none: "keiner",
    label_bridge: "Bridge",
    label_bridge_version: "Node-Bridge-Version",
    label_build_id: "Gemeinsamer Build",
    label_build_match: "Build-Abgleich",
    label_endpoint: "Endpunkt",
    label_error: "Fehler",
    label_extension_version: "Extension-Version",
    label_launcher: "Nativer Start",
    label_launcher_version: "Launcher-Version",
    label_log: "Protokoll",
    label_pending: "Ausstehend",
    label_tools: "Werkzeuge",
    launcher_busy: "Die Bridge-Einrichtung wird bereits ausgeführt.",
    launcher_failed: "Die lokale Bridge konnte nicht gestartet werden. Prüfen Sie das Protokoll.",
    launcher_health_timeout: "Die Bridge ist noch nicht betriebsbereit. Erwartet werden 8 von 8 Werkzeugen.",
    launcher_invalid: "Die Bridge-Einrichtung hat eine ungültige Antwort geliefert.",
    launcher_node_missing: "Node.js 22.12 oder neuer fehlt. Öffnen Sie die PLwC Bridge-Einrichtung.",
    launcher_not_requested: "Der native Start war nicht erforderlich oder wurde noch nicht angefordert.",
    launcher_port_in_use: "Port 3007 wird von einem anderen oder nicht betriebsbereiten Dienst verwendet.",
    launcher_ready: "Verbunden, 8 von 8 Werkzeugen sind bereit.",
    launcher_setup_required: "Die PLwC Bridge-Einrichtung fehlt. Starten Sie die PLwC-Einrichtung erneut.",
    launcher_start_failed: "Die Bridge konnte nicht gestartet werden. Prüfen Sie das Protokoll.",
    launcher_starting: "Die lokale Bridge wird gestartet und geprüft.",
    launcher_store_boundary: "Der Browser Store installiert nur die Erweiterung. PLwC Setup installiert die lokale Anwendung und den Native Launcher.",
    local_status: "LOKALER STATUS",
    no_runtime_status: "In dieser Ansicht wurde noch kein Laufzeitstatus abgerufen.",
    reconnect: "Neu verbinden",
    runtime_status: "Laufzeitstatus prüfen",
    setup_download: "Offizielle PLwC-Downloads öffnen",
    unexpected_error: "Unerwarteter Fehler der PLwC Chat Bridge.",
    working: "Wird ausgeführt...",
  },
  en: {
    bridge_error: "Connection error",
    bridge_offline: "No connection to the local bridge.",
    error_none: "none",
    label_bridge: "Bridge",
    label_bridge_version: "Node Bridge version",
    label_build_id: "Common build",
    label_build_match: "Build match",
    label_endpoint: "Endpoint",
    label_error: "Error",
    label_extension_version: "Extension version",
    label_launcher: "Native start",
    label_launcher_version: "Launcher version",
    label_log: "Log",
    label_pending: "Pending",
    label_tools: "Tools",
    launcher_busy: "Bridge setup is already running.",
    launcher_failed: "The local bridge could not be started. Check the log.",
    launcher_health_timeout: "The bridge is not ready yet. 8 of 8 tools are required.",
    launcher_invalid: "Bridge setup returned an invalid response.",
    launcher_node_missing: "Node.js 22.12 or newer is missing. Open PLwC Bridge Setup.",
    launcher_not_requested: "Native start was not needed or has not been requested yet.",
    launcher_port_in_use: "Port 3007 is used by another or unhealthy service.",
    launcher_ready: "Connected, 8 of 8 tools are ready.",
    launcher_setup_required: "PLwC Bridge Setup is missing. Run PLwC Setup again.",
    launcher_start_failed: "The bridge could not be started. Check the log.",
    launcher_starting: "Starting and verifying the local bridge.",
    launcher_store_boundary: "The browser Store installs only the extension. PLwC Setup installs the local application and Native Launcher.",
    local_status: "LOCAL STATUS",
    no_runtime_status: "No runtime status has been requested in this view.",
    reconnect: "Reconnect",
    runtime_status: "Check Runtime Status",
    setup_download: "Open official PLwC downloads",
    unexpected_error: "Unexpected PLwC Chat Bridge error.",
    working: "Working...",
  },
};

export function resolveUiLanguage(value?: string | null): UiLanguage {
  return value?.toLowerCase().startsWith("de") ? "de" : "en";
}

export function text(key: TextKey, language: UiLanguage): string {
  return TEXT[language][key];
}

export function localizeConnectionState(state: ConnectionState, language: UiLanguage): string {
  const states: Record<UiLanguage, Record<ConnectionState, string>> = {
    de: {
      connected: "verbunden",
      connecting: "wird verbunden",
      disconnected: "getrennt",
      error: "Fehler",
    },
    en: {
      connected: "connected",
      connecting: "connecting",
      disconnected: "disconnected",
      error: "error",
    },
  };
  return states[language][state];
}

export function localizeBridgeError(message: string, language: UiLanguage): string {
  if (message.trim() === "") return text("error_none", language);
  if (/websocket|not connected|connection (?:closed|failed)|endpoint/i.test(message)) {
    return text("bridge_offline", language);
  }
  if (/native launcher|eight-tool bridge contract/i.test(message)) {
    return text("launcher_failed", language);
  }
  return message;
}

export function localizeBuildIdentityMatch(
  verified: boolean | null,
  language: UiLanguage,
): string {
  if (verified === null) return language === "de" ? "nicht geprueft" : "not verified";
  if (verified) return language === "de" ? "stimmt ueberein" : "matched";
  return language === "de" ? "abweichend - Ausfuehrung gesperrt" : "mismatch - execution locked";
}

export function localizeLauncherStatus(status: LauncherStatus, language: UiLanguage): string {
  if (status.state === "starting") return text("launcher_starting", language);
  if (
    (status.state === "started" || status.state === "already_running") &&
    status.toolCount === 8
  ) {
    return text("launcher_ready", language);
  }

  switch (status.code) {
    case "ready":
      return text("launcher_ready", language);
    case "native_host_missing":
    case "native_launcher_unavailable":
      return text("launcher_setup_required", language);
    case "node_missing":
      return text("launcher_node_missing", language);
    case "port_in_use":
      return text("launcher_port_in_use", language);
    case "health_timeout":
    case "native_launcher_timeout":
      return text("launcher_health_timeout", language);
    case "process_start_failed":
    case "bridge_files_missing":
    case "bridge_config_missing":
      return text("launcher_start_failed", language);
    case "startup_busy":
      return text("launcher_busy", language);
    case "native_launcher_invalid_response":
      return text("launcher_invalid", language);
    case "build_identity_mismatch":
      return language === "de"
        ? "Die Buildidentitaet stimmt nicht ueberein. Die Ausfuehrung bleibt gesperrt."
        : "Build identity mismatch. Execution remains locked.";
    case "not_requested":
      return text("launcher_not_requested", language);
    default:
      return status.message.trim() || text("launcher_failed", language);
  }
}
