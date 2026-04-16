import { isEditableTarget, shouldSkipGlobalShortcut } from "../../src/components/editor/utils/shortcuts";

describe("isEditableTarget", () => {
  test("returns true for input/textarea/select/contenteditable", () => {
    const input = document.createElement("input");
    const ta = document.createElement("textarea");
    const sel = document.createElement("select");
    const div = document.createElement("div");
    Object.defineProperty(div, "isContentEditable", { value: true, configurable: true });

    expect(isEditableTarget(input)).toBe(true);
    expect(isEditableTarget(ta)).toBe(true);
    expect(isEditableTarget(sel)).toBe(true);
    expect(isEditableTarget(div)).toBe(true);
  });

  test("returns false for non-editable elements", () => {
    const button = document.createElement("button");
    expect(isEditableTarget(button)).toBe(false);
    expect(isEditableTarget(null)).toBe(false);
  });
});

describe("shouldSkipGlobalShortcut", () => {
  test("skips when composing", () => {
    expect(shouldSkipGlobalShortcut({ isComposing: true, target: document.body } as KeyboardEvent)).toBe(true);
  });

  test("skips when target is editable", () => {
    const input = document.createElement("input");
    expect(shouldSkipGlobalShortcut({ isComposing: false, target: input } as KeyboardEvent)).toBe(true);
  });

  test("does not skip for non-editable, non-composition events", () => {
    const div = document.createElement("div");
    expect(shouldSkipGlobalShortcut({ isComposing: false, target: div } as KeyboardEvent)).toBe(false);
  });
});
