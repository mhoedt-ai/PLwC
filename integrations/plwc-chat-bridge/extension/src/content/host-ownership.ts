export interface PlwcHostOwner {
  extensionId: string;
  packageVersion: string;
}

const STORE_EXTENSION_IDS = new Set([
  "feceodobnhefdbfgmbinkndhogpfkicb",
  "nncomdhcalhlgkfjhkckdgooiekhoplk",
]);
const DEVELOPMENT_EXTENSION_ID = "nlogfcafjdfdoknpkbehjgihpafpipdb";

export function plwcHostPriority(extensionId: string | undefined): number {
  if (extensionId !== undefined && STORE_EXTENSION_IDS.has(extensionId)) return 3;
  if (extensionId === DEVELOPMENT_EXTENSION_ID) return 2;
  return extensionId ? 1 : 0;
}

export function shouldClaimPlwcHost(
  current: PlwcHostOwner,
  existing: PlwcHostOwner | null,
): boolean {
  if (existing === null) return true;
  if (existing.extensionId === current.extensionId) {
    return existing.packageVersion !== current.packageVersion;
  }
  return plwcHostPriority(current.extensionId) > plwcHostPriority(existing.extensionId);
}
