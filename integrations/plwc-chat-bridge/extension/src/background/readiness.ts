import type { BridgeReadiness, ReadinessState } from "../shared/messages";

const EXPECTED_TOOL_COUNT = 8 as const;

function snapshot(state: ReadinessState, generation: number): BridgeReadiness {
  return {
    buildVerified: state === "loading_tools" || state === "ready",
    expectedToolCount: EXPECTED_TOOL_COUNT,
    generation,
    state,
    toolCount: state === "ready" ? EXPECTED_TOOL_COUNT : 0,
    toolsVerified: state === "ready",
  };
}

export class AtomicBridgeReadiness {
  private generationValue = 0;
  private value = snapshot("disconnected", 0);

  get current(): BridgeReadiness {
    return { ...this.value };
  }

  get generation(): number {
    return this.generationValue;
  }

  begin(): number {
    this.generationValue += 1;
    this.value = snapshot("connecting", this.generationValue);
    return this.generationValue;
  }

  connected(generation: number): boolean {
    return this.transition(generation, "checking_build");
  }

  buildVerified(generation: number): boolean {
    return this.transition(generation, "loading_tools");
  }

  toolsVerified(generation: number, toolCount: number): boolean {
    if (toolCount !== EXPECTED_TOOL_COUNT) return this.fail(generation, "incompatible");
    return this.transition(generation, "ready");
  }

  fail(generation: number, state: "incompatible" | "error"): boolean {
    return this.transition(generation, state);
  }

  disconnect(): number {
    this.generationValue += 1;
    this.value = snapshot("disconnected", this.generationValue);
    return this.generationValue;
  }

  isCurrent(generation: number): boolean {
    return generation === this.generationValue;
  }

  private transition(generation: number, state: ReadinessState): boolean {
    if (!this.isCurrent(generation)) return false;
    this.value = snapshot(state, generation);
    return true;
  }
}
