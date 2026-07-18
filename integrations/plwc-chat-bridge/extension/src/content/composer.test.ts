import assert from "node:assert/strict";
import test from "node:test";

import { findChatGptComposerSurface } from "./composer";

type Rect = Pick<DOMRect, "bottom" | "height" | "left" | "right" | "top" | "width">;

function mockElement(rect: Rect, parentElement: HTMLElement | null = null): HTMLElement {
  return {
    getBoundingClientRect: () => rect as DOMRect,
    parentElement,
  } as unknown as HTMLElement;
}

test("uses the rounded composer shell for vertical launcher alignment", () => {
  const outer = mockElement({ bottom: 980, height: 80, left: 600, right: 1_500, top: 900, width: 900 });
  const shell = mockElement(
    { bottom: 965.6, height: 52, left: 666, right: 1_434, top: 913.6, width: 768 },
    outer,
  );
  const editorRow = mockElement(
    { bottom: 969, height: 59, left: 710, right: 1_257, top: 910, width: 547 },
    shell,
  );
  const composer = mockElement(
    { bottom: 968, height: 42, left: 717, right: 1_251, top: 926, width: 534 },
    editorRow,
  );
  const radii = new Map<HTMLElement, string>([
    [outer, "28px"],
    [shell, "28px"],
  ]);
  const documentValue = {
    defaultView: {
      getComputedStyle: (element: HTMLElement) => {
        const radius = radii.get(element) ?? "0px";
        return {
          borderBottomLeftRadius: radius,
          borderBottomRightRadius: radius,
          borderTopLeftRadius: radius,
          borderTopRightRadius: radius,
        } as CSSStyleDeclaration;
      },
    },
  } as unknown as Document;

  assert.equal(findChatGptComposerSurface(composer, documentValue), shell);
});
