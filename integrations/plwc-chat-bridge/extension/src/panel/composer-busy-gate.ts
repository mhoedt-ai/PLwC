type WatchdogHandle = ReturnType<typeof setTimeout>;
type WatchdogSchedule = (callback: () => void, milliseconds: number) => WatchdogHandle;
type WatchdogCancel = (handle: WatchdogHandle) => void;

export class ComposerBusyGate {
  private readonly activeCallKeys = new Set<string>();
  private automationDepth = 0;
  private released = false;
  private watchdog: WatchdogHandle | null = null;

  constructor(
    private readonly onChange: () => void,
    private readonly schedule: WatchdogSchedule = (callback, milliseconds) =>
      setTimeout(callback, milliseconds),
    private readonly cancel: WatchdogCancel = (handle) => clearTimeout(handle),
  ) {}

  get activeCount(): number {
    return this.activeCallKeys.size;
  }

  get blocking(): boolean {
    return this.activeCallKeys.size > 0 && !this.released;
  }

  get locksComposerDom(): boolean {
    return this.blocking && this.automationDepth === 0;
  }

  begin(callKey: string, timeoutSeconds: number): void {
    const wasIdle = this.activeCallKeys.size === 0;
    this.activeCallKeys.add(callKey);
    if (wasIdle) this.restartWatchdog(timeoutSeconds);
    this.onChange();
  }

  end(callKey: string): void {
    this.activeCallKeys.delete(callKey);
    if (this.activeCallKeys.size === 0) {
      this.clearWatchdog();
      this.automationDepth = 0;
      this.released = false;
    }
    this.onChange();
  }

  release(): void {
    if (this.activeCallKeys.size === 0 || this.released) return;
    this.clearWatchdog();
    this.released = true;
    this.onChange();
  }

  updateTimeout(timeoutSeconds: number): void {
    if (this.activeCallKeys.size === 0) return;
    this.restartWatchdog(timeoutSeconds);
    this.onChange();
  }

  beginAutomation(): void {
    if (this.activeCallKeys.size === 0) return;
    this.automationDepth += 1;
    this.onChange();
  }

  endAutomation(): void {
    if (this.automationDepth === 0) return;
    this.automationDepth -= 1;
    this.onChange();
  }

  private restartWatchdog(timeoutSeconds: number): void {
    this.clearWatchdog();
    this.released = timeoutSeconds <= 0;
    if (this.released) return;
    this.watchdog = this.schedule(() => {
      this.watchdog = null;
      this.released = true;
      this.onChange();
    }, timeoutSeconds * 1_000);
  }

  private clearWatchdog(): void {
    if (this.watchdog === null) return;
    this.cancel(this.watchdog);
    this.watchdog = null;
  }
}
