import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { NotificationBanner } from "../../../src/components/editor/components/NotificationBanner";
import type { EditorState } from "../../../src/components/editor/types";
import { baseState } from "./_helpers";

function renderWith(opts: {
  state?: EditorState;
  importError?: string | null;
  importWarnings?: string[];
} = {}) {
  const onClearImportError = jest.fn();
  const onClearImportWarnings = jest.fn();
  const view = render(
    <NotificationBanner
      state={opts.state ?? baseState()}
      importError={opts.importError ?? null}
      importWarnings={opts.importWarnings ?? []}
      onClearImportError={onClearImportError}
      onClearImportWarnings={onClearImportWarnings}
    />,
  );
  return { onClearImportError, onClearImportWarnings, ...view };
}

describe("NotificationBanner", () => {
  test("renders nothing when no signals", () => {
    const { container } = renderWith();
    expect(container.firstChild).toBeNull();
  });

  test("importError takes priority over rejection and warnings", () => {
    const state: EditorState = {
      ...baseState(),
      _lastRejection: { type: "ADD_COMMENT", reason: "blocked", at: Date.now() },
    };
    renderWith({
      state,
      importError: "bad json",
      importWarnings: ["warn"],
    });
    const banner = screen.getByTestId("notification-banner");
    expect(banner).toHaveAttribute("data-kind", "import-error");
    expect(banner).toHaveTextContent("bad json");
  });

  test("rejection rendered when no importError; dismiss hides until next rejection", () => {
    const state: EditorState = {
      ...baseState(),
      _lastRejection: { type: "ADD_COMMENT", reason: "Comment text must not be empty.", at: 1 },
    };
    const { onClearImportError, rerender } = renderWith({ state });
    const banner = screen.getByTestId("notification-banner");
    expect(banner).toHaveAttribute("data-kind", "rejection");
    expect(banner).toHaveTextContent("Comment");
    expect(banner).toHaveTextContent("Comment text must not be empty.");
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
    expect(onClearImportError).not.toHaveBeenCalled();
    // New rejection (different `at`) re-surfaces banner.
    const state2: EditorState = {
      ...state,
      _lastRejection: { type: "UNDO", reason: "Document is read-only", at: 2 },
    };
    rerender(
      <NotificationBanner
        state={state2}
        importError={null}
        importWarnings={[]}
        onClearImportError={() => {}}
        onClearImportWarnings={() => {}}
      />,
    );
    expect(screen.getByTestId("notification-banner")).toHaveAttribute("data-kind", "rejection");
  });

  test("importWarnings rendered when no error or rejection", () => {
    const { onClearImportWarnings } = renderWith({
      importWarnings: ["clamped value", "missing field"],
    });
    const banner = screen.getByTestId("notification-banner");
    expect(banner).toHaveAttribute("data-kind", "import-warnings");
    expect(screen.getByText("clamped value")).toBeInTheDocument();
    expect(screen.getByText("missing field")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onClearImportWarnings).toHaveBeenCalledTimes(1);
  });

  test("importError dismiss invokes callback", () => {
    const { onClearImportError } = renderWith({ importError: "bad json" });
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(onClearImportError).toHaveBeenCalledTimes(1);
  });

  test("unknown action type falls back to raw type label", () => {
    const state: EditorState = {
      ...baseState(),
      _lastRejection: { type: "MYSTERY_ACTION", reason: "wat", at: 3 },
    };
    renderWith({ state });
    expect(screen.getByTestId("notification-banner")).toHaveTextContent("MYSTERY_ACTION");
  });
});
