export const PANEL_WIDTH = 380;
export const MIN_PANEL_WIDTH = 280;
export const PANEL_GAP = 12;

export interface PanelLayoutInput {
  leftNavigationRight: number;
  userCollapsed?: boolean;
  viewportWidth: number;
}

export interface PanelLayout {
  canOpen: boolean;
  collapsed: boolean;
  width: number;
}

export function calculatePanelLayout(input: PanelLayoutInput): PanelLayout {
  const available = Math.max(0, input.viewportWidth - input.leftNavigationRight - PANEL_GAP * 2);
  const canOpen = available >= MIN_PANEL_WIDTH;
  const defaultCollapsed = input.viewportWidth < 900;
  return {
    canOpen,
    collapsed: !canOpen || (input.userCollapsed ?? defaultCollapsed),
    width: Math.max(MIN_PANEL_WIDTH, Math.min(PANEL_WIDTH, available)),
  };
}

export function findLeftNavigationRight(documentValue: Document = document): number {
  const selectors = [
    "[data-testid*='sidebar']",
    "[aria-label*='chat history' i]",
    "[aria-label*='sidebar' i]",
    "aside",
    "nav",
  ];
  const candidates = [...documentValue.querySelectorAll<HTMLElement>(selectors.join(","))];
  const viewportHeight = documentValue.defaultView?.innerHeight ?? 0;
  const viewportWidth = documentValue.defaultView?.innerWidth ?? 0;

  return candidates.reduce((right, element) => {
    const rect = element.getBoundingClientRect();
    const style = documentValue.defaultView?.getComputedStyle(element);
    const visible = style?.display !== "none" && style?.visibility !== "hidden" && Number(style?.opacity ?? 1) > 0;
    const looksLikeLeftNavigation =
      visible && rect.left <= 12 && rect.width >= 44 && rect.height >= viewportHeight * 0.45 && rect.right > 0;
    return looksLikeLeftNavigation ? Math.max(right, Math.min(rect.right, viewportWidth)) : right;
  }, 0);
}
