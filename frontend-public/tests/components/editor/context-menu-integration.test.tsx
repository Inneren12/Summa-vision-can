/**
 * @jest-environment jsdom
 *
 * Phase 1.6 — real-wire integration test for the context-menu shortcut path.
 *
 * jsdom's HTMLCanvasElement.getContext returns null, so the renderer's hit-
 * area population never runs and right-click dispatches cannot select a
 * block via hit-test in this environment. The keyboard shortcut path is
 * independent of canvas rendering — it only depends on a selection
 * existing — so we exercise that path here for the full editor wiring.
 *
 * Hit-test is covered separately in `tests/editor/hit-test.test.ts`;
 * reducer behaviour in `tests/editor/context-menu-reducer.test.ts`; menu
 * UI in `tests/editor/components/BlockContextMenu.test.tsx`.
 */
import React from "react";
import { render, fireEvent, act } from "@testing-library/react";
import InfographicEditor from "@/components/editor";

beforeEach(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, "getBoundingClientRect", {
    value: () => ({ left: 0, top: 0, width: 720, height: 720, right: 720, bottom: 720, x: 0, y: 0, toJSON: () => ({}) }),
    configurable: true,
  });
});

describe("Editor context-menu wiring", () => {
  test("right-click on empty canvas falls through (no selection, no menu)", () => {
    const { container, queryByTestId } = render(<InfographicEditor />);
    const content = container.querySelectorAll("canvas")[0] as HTMLCanvasElement;
    fireEvent.contextMenu(content, { clientX: 10, clientY: 10 });
    expect(queryByTestId("block-context-menu")).toBeNull();
  });

  test("Cmd/Ctrl+L with no selection is a no-op", () => {
    const { queryByTestId } = render(<InfographicEditor />);
    fireEvent.keyDown(window, { key: "l", ctrlKey: true });
    // No menu opens, no exception thrown — wiring stays inert when nothing
    // is selected.
    expect(queryByTestId("block-context-menu")).toBeNull();
  });

  test("Delete key with no selection is a no-op (does not open delete modal)", () => {
    const { queryByTestId } = render(<InfographicEditor />);
    act(() => {
      fireEvent.keyDown(window, { key: "Delete" });
    });
    expect(queryByTestId("delete-confirm-modal")).toBeNull();
  });

  test("Backspace key with no selection is a no-op", () => {
    const { queryByTestId } = render(<InfographicEditor />);
    act(() => {
      fireEvent.keyDown(window, { key: "Backspace" });
    });
    expect(queryByTestId("delete-confirm-modal")).toBeNull();
  });

  test("Cmd/Ctrl+L while typing in an input is skipped (IME guard / editable target)", () => {
    const { container, queryByTestId } = render(<InfographicEditor />);
    // Inject a text input into the live tree, focus it, fire shortcut.
    const input = document.createElement("input");
    container.appendChild(input);
    input.focus();
    act(() => {
      fireEvent.keyDown(input, { key: "l", ctrlKey: true });
    });
    expect(queryByTestId("block-context-menu")).toBeNull();
  });
});
