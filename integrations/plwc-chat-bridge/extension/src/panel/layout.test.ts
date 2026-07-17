import assert from "node:assert/strict";
import test from "node:test";

import { calculatePanelLayout } from "./layout";

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
