import assert from "node:assert/strict";
import test from "node:test";

import { ComposerBusyGate } from "./composer-busy-gate";

interface ScheduledWatchdog {
  callback: () => void;
  milliseconds: number;
}

function fixture(): {
  cancelled: ScheduledWatchdog[];
  changes: boolean[];
  gate: ComposerBusyGate;
  scheduled: ScheduledWatchdog[];
} {
  const changes: boolean[] = [];
  const scheduled: ScheduledWatchdog[] = [];
  const cancelled: ScheduledWatchdog[] = [];
  let gate: ComposerBusyGate;
  gate = new ComposerBusyGate(
    () => changes.push(gate.blocking),
    (callback, milliseconds) => {
      const watchdog = { callback, milliseconds };
      scheduled.push(watchdog);
      return watchdog as unknown as ReturnType<typeof setTimeout>;
    },
    (handle) => cancelled.push(handle as unknown as ScheduledWatchdog),
  );
  return { cancelled, changes, gate, scheduled };
}

test("keeps the input blocked until every active call completes", () => {
  const { gate, scheduled } = fixture();

  gate.begin("first", 60);
  gate.begin("second", 60);
  assert.equal(gate.blocking, true);
  assert.equal(gate.activeCount, 2);
  assert.equal(scheduled.length, 1);

  gate.end("first");
  assert.equal(gate.blocking, true);
  gate.end("second");
  assert.equal(gate.blocking, false);
  assert.equal(gate.activeCount, 0);
});

test("watchdog and manual release can always unlock an active call", () => {
  const watchdogFixture = fixture();
  watchdogFixture.gate.begin("slow", 30);
  assert.equal(watchdogFixture.scheduled[0]?.milliseconds, 30_000);
  watchdogFixture.scheduled[0]?.callback();
  assert.equal(watchdogFixture.gate.blocking, false);
  assert.equal(watchdogFixture.gate.activeCount, 1);

  const manualFixture = fixture();
  manualFixture.gate.begin("manual", 60);
  manualFixture.gate.release();
  assert.equal(manualFixture.gate.blocking, false);
  assert.equal(manualFixture.gate.activeCount, 1);
  assert.equal(manualFixture.cancelled.length, 1);
});

test("zero disables locking and a changed timeout re-arms the active gate", () => {
  const { gate, scheduled } = fixture();

  gate.begin("optional", 0);
  assert.equal(gate.blocking, false);
  assert.equal(scheduled.length, 0);

  gate.updateTimeout(15);
  assert.equal(gate.blocking, true);
  assert.equal(scheduled[0]?.milliseconds, 15_000);
});

test("keeps the visual gate active while automation temporarily unlocks the composer DOM", () => {
  const { gate } = fixture();

  gate.begin("result-return", 60);
  assert.equal(gate.blocking, true);
  assert.equal(gate.locksComposerDom, true);

  gate.beginAutomation();
  assert.equal(gate.blocking, true);
  assert.equal(gate.locksComposerDom, false);

  gate.endAutomation();
  assert.equal(gate.blocking, true);
  assert.equal(gate.locksComposerDom, true);
});
