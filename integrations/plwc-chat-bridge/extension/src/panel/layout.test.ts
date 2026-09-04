import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateComposerBusyOverlayPosition,
  calculateComposerLauncherPosition,
  calculatePanelLayout,
} from "./layout";

test("keeps a desktop panel inside the space to the right of host navigation", () => {
  assert.deepEqual(
    calculatePanelLayout({ leftNavigationRight: 260, viewportWidth: 1_024 }),
    { canOpen: true, collapsed: false, width: 380 },
  );
});

test("starts collapsed below 900 pixels but remains user-openable when space permits", () => {
  assert.deepEqual(
    calculatePanelLayout({ leftNavigationRight: 0, viewportWidth: 768 }),
    { canOpen: true, collapsed: true, width: 380 },
  );
  assert.equal(
    calculatePanelLayout({ leftNavigationRight: 0, userCollapsed: false, viewportWidth: 768 }).collapsed,
    false,
  );
});

test("forces collapse before the panel can overlap left navigation", () => {
  const layout = calculatePanelLayout({ leftNavigationRight: 260, userCollapsed: false, viewportWidth: 390 });
  assert.equal(layout.canOpen, false);
  assert.equal(layout.collapsed, true);
});

test("anchors the composer launcher outside the input without crossing left navigation", () => {
  assert.deepEqual(
    calculateComposerLauncherPosition({
      composer: { bottom: 820, left: 420, right: 1_060, top: 750 },
      leftNavigationRight: 260,
      viewportHeight: 900,
      viewportWidth: 1_440,
    }),
    { left: 372, top: 765, visible: true },
  );
});

test("moves the composer launcher above the input when neither side has room", () => {
  assert.deepEqual(
    calculateComposerLauncherPosition({
      composer: { bottom: 820, left: 12, right: 378, top: 750 },
      leftNavigationRight: 0,
      viewportHeight: 844,
      viewportWidth: 390,
    }),
    { left: 12, top: 702, visible: true },
  );
});

test("keeps the busy overlay compact at the bottom of an expanded composer", () => {
  assert.deepEqual(
    calculateComposerBusyOverlayPosition({ bottom: 900, height: 420, left: 120, width: 880 }),
    { height: 64, left: 120, top: 836, width: 880 },
  );
  assert.deepEqual(
    calculateComposerBusyOverlayPosition({ bottom: 900, height: 56, left: 120, width: 880 }),
    { height: 56, left: 120, top: 844, width: 880 },
  );
});
