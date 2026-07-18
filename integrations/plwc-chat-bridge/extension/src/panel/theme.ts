export const TERMINAL_THEME = `
:host {
  all: initial;
  color-scheme: dark;
  font-family: Consolas, "Lucida Console", "Courier New", monospace;
  font-size: 13px;
  letter-spacing: 0;
  pointer-events: none;
}

*, *::before, *::after { box-sizing: border-box; }
button, input, textarea { font: inherit; letter-spacing: 0; }
button { cursor: pointer; }

.bridge-panel, .bridge-launcher, .composer-launcher {
  position: fixed;
  z-index: 2147483000;
  pointer-events: auto;
}

.bridge-panel {
  top: 12px;
  right: 12px;
  bottom: 12px;
  width: var(--plwc-panel-width, 380px);
  min-width: 280px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #8fd99a;
  background: #020403;
  border: 1px solid #123d1e;
  border-radius: 2px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 45%);
}

.bridge-launcher {
  top: 12px;
  right: 12px;
  width: 44px;
  height: 44px;
  display: none;
  place-items: center;
  padding: 5px;
  background: #020403;
  border: 1px solid #5cff7a;
  border-radius: 2px;
}

.bridge-launcher img { width: 32px; height: 32px; display: block; }
.is-collapsed .bridge-panel { display: none; }
.is-collapsed .bridge-launcher { display: grid; }
.is-collapsed.has-composer-launcher .bridge-launcher { display: none; }

.composer-launcher {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  padding: 4px;
  color: #8fd99a;
  background: #020403;
  border: 1px solid #123d1e;
  border-radius: 2px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 40%);
}
.composer-launcher:hover, .composer-launcher[aria-pressed="true"] { border-color: #5cff7a; }
.composer-launcher:disabled { cursor: not-allowed; opacity: 0.55; }
.composer-launcher.is-hidden { display: none; }
.composer-launcher img { width: 28px; height: 28px; display: block; }

.bridge-header {
  height: 54px;
  flex: 0 0 54px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 9px;
  border-bottom: 1px solid #123d1e;
  background: #050806;
}

.bridge-header img { width: 34px; height: 34px; }
.bridge-title { min-width: 0; flex: 1; color: #5cff7a; font-weight: 700; white-space: nowrap; }
.status-dot { width: 8px; height: 8px; flex: 0 0 8px; background: #52705a; border-radius: 50%; }
.status-dot.connected { background: #5cff7a; box-shadow: 0 0 5px rgb(92 255 122 / 55%); }
.status-dot.error { background: #ff667d; }

.icon-button {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  padding: 0;
  color: #8fd99a;
  background: #020403;
  border: 1px solid #123d1e;
  border-radius: 2px;
}

.tabs { display: flex; flex: 0 0 40px; overflow-x: auto; border-bottom: 1px solid #123d1e; background: #050806; }
.tab {
  height: 39px;
  flex: 0 0 auto;
  padding: 0 10px;
  color: #8fd99a;
  background: transparent;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  white-space: nowrap;
}
.tab[aria-selected="true"] { color: #5cff7a; border-bottom-color: #5cff7a; }

.views { min-height: 0; flex: 1; overflow: auto; }
.view { display: none; padding: 12px; }
.view.active { display: block; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.toolbar .spacer { flex: 1; }
.label { color: #5cff7a; font-weight: 700; }
.muted { color: #6f9d78; }
.error-text { color: #ff8293; }

.command-button {
  min-height: 34px;
  padding: 6px 10px;
  color: #020403;
  background: #5cff7a;
  border: 1px solid #5cff7a;
  border-radius: 2px;
  font-weight: 700;
}
.command-button.secondary { color: #8fd99a; background: #050806; border-color: #123d1e; }
.command-button:disabled { cursor: not-allowed; color: #52705a; background: #0a110c; border-color: #123d1e; }

.contract-state, .status-grid, .settings-block { margin-bottom: 12px; padding: 9px; border: 1px solid #123d1e; border-radius: 2px; background: #050806; }
.tool { border-top: 1px solid #123d1e; padding: 9px 0; }
.tool:first-child { border-top: 0; }
.tool-name { color: #5cff7a; overflow-wrap: anywhere; }
.tool-description { margin-top: 4px; color: #8fd99a; line-height: 1.4; }
details { margin-top: 6px; }
summary { cursor: pointer; color: #6f9d78; }
pre { max-height: 220px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; color: #8fd99a; }

.primer-preview {
  width: 100%;
  min-height: 330px;
  resize: vertical;
  padding: 9px;
  color: #8fd99a;
  background: #050806;
  border: 1px solid #123d1e;
  border-radius: 2px;
  line-height: 1.4;
}
.hash { display: block; margin: 8px 0 10px; overflow-wrap: anywhere; color: #6f9d78; }
.policy-table { width: 100%; border-collapse: collapse; }
.policy-table th, .policy-table td { padding: 8px 5px; text-align: left; vertical-align: top; border-bottom: 1px solid #123d1e; }
.policy-table th { color: #5cff7a; }
.status-grid { display: grid; grid-template-columns: 88px minmax(0, 1fr); gap: 7px; }
.status-grid dt { color: #6f9d78; }
.status-grid dd { margin: 0; overflow-wrap: anywhere; }
.setting-row { display: flex; align-items: flex-start; gap: 8px; }
.setting-row input { accent-color: #5cff7a; }
.settings-source { margin: 0 0 9px; color: #6f9d78; overflow-wrap: anywhere; }
.settings-section-label { margin: 16px 0 9px; }
.configuration-grid { display: grid; grid-template-columns: minmax(112px, 0.8fr) minmax(0, 1.2fr); gap: 8px 10px; margin: 0; }
.configuration-grid dt { color: #6f9d78; }
.configuration-grid dd { min-width: 0; margin: 0; color: #8fd99a; overflow-wrap: anywhere; }
.configuration-grid dd.muted { color: #6f9d78; }
.run-queue { margin-top: 18px; }
.run-card { margin-top: 10px; padding: 9px; border: 1px solid #123d1e; background: #050806; }
.run-header { display: flex; align-items: center; gap: 8px; }
.run-header .tool-name { min-width: 0; flex: 1; }
.run-state { padding: 2px 5px; color: #8fd99a; border: 1px solid #123d1e; }
.run-state.succeeded { color: #5cff7a; }
.run-state.denied, .run-state.failed, .run-state.unknown { color: #ff8293; }
.run-arguments, .run-result { max-height: 180px; margin: 8px 0; }
.run-confirmation { margin: 9px 0; }

button:focus-visible, textarea:focus-visible, input:focus-visible { outline: 2px solid #5cff7a; outline-offset: 1px; }

@media (max-width: 899px) {
  .bridge-panel { max-width: calc(100vw - 24px); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
}
`;
