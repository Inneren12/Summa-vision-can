import React from "react";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import InfographicEditor from "../../src/components/editor";

class MockFileReader {
  public onload: ((ev: { target: { result: string } }) => void) | null = null;
  readAsText() {
    this.onload?.({ target: { result: "{bad json" } });
  }
}

describe("editor UI a11y + import warnings", () => {
  test("renders tab semantics + import control + in-app import error without alert()", async () => {
    const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});
    const originalFileReader = window.FileReader;
    Object.defineProperty(window, "FileReader", {
      writable: true,
      value: MockFileReader,
    });

    const { container } = render(<InfographicEditor />);

    expect(screen.getByRole("tablist", { name: /left panel sections/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /templates tab/i })).toHaveAttribute("aria-controls");
    // PR 3 added the right-rail tabpanels alongside LeftPanel's; assert at
    // least one tabpanel is reachable rather than a singular one.
    expect(screen.getAllByRole("tabpanel").length).toBeGreaterThan(0);

    expect(screen.getByRole("tablist", { name: /editor mode/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /import document from json/i })).toBeInTheDocument();

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["bad"], "bad.json", { type: "application/json" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("Invalid JSON file")).toBeInTheDocument();
    });
    expect(alertSpy).not.toHaveBeenCalled();

    Object.defineProperty(window, "FileReader", {
      writable: true,
      value: originalFileReader,
    });
  });
});

describe("Stage 3 PR 3 — full-tree integration", () => {
  test("default state: TopBar StatusBadge shows DRAFT", () => {
    render(<InfographicEditor />);
    const badges = screen.getAllByTestId("status-badge");
    // Initially only the TopBar compact badge is rendered. ReviewPanel's
    // regular badge appears only after the user activates the Review tab.
    expect(badges).toHaveLength(1);
    expect(badges[0]).toHaveTextContent("DRAFT");
  });

  test("UNDO in in_review surfaces NotificationBanner with rejection; dismiss clears it", async () => {
    const user = userEvent.setup();
    render(<InfographicEditor />);
    // Make an edit to populate the undo stack.
    fireEvent.click(screen.getByRole("tab", { name: /blocks tab/i }));
    const blocksTabpanel = screen.getByRole("tabpanel", { name: /blocks tab/i });
    const blockBtns = within(blocksTabpanel).getAllByRole("button", { name: /select block/i });
    fireEvent.click(blockBtns[0]);
    const textboxes = screen.queryAllByRole("textbox");
    if (textboxes.length > 0) {
      fireEvent.change(textboxes[0], { target: { value: "edit-1" } });
    }
    // Submit for review via Review tab.
    fireEvent.click(screen.getByRole("tab", { name: /review/i }));
    fireEvent.click(screen.getByTestId("transition-SUBMIT_FOR_REVIEW"));
    // Workflow gate now blocks UNDO. Click the Undo button.
    const undoBtn = await screen.findByRole("button", { name: /^undo$/i });
    fireEvent.click(undoBtn);
    const banner = await screen.findByTestId("notification-banner");
    expect(banner).toHaveAttribute("data-kind", "rejection");
    expect(banner).toHaveTextContent(/undo/i);
    // Dismiss button.
    const dismiss = within(banner).getByRole("button", { name: /dismiss/i });
    await user.click(dismiss);
    expect(screen.queryByTestId("notification-banner")).not.toBeInTheDocument();
  });

  test("select block → Add comment → submit → thread + count pills update", async () => {
    const user = userEvent.setup();
    render(<InfographicEditor />);
    // Pick a block from LeftPanel Blocks tab.
    fireEvent.click(screen.getByRole("tab", { name: /blocks tab/i }));
    const blocksTabpanel = screen.getByRole("tabpanel", { name: /blocks tab/i });
    const blockBtns = within(blocksTabpanel).getAllByRole("button", { name: /select block/i });
    const targetBtn = blockBtns[0];
    fireEvent.click(targetBtn);
    expect(within(targetBtn).queryByTestId("block-unresolved-pill")).not.toBeInTheDocument();
    // Switch to Review tab.
    fireEvent.click(screen.getByRole("tab", { name: /review/i }));
    fireEvent.click(screen.getByTestId("add-comment-button"));
    const ta = await screen.findByRole("textbox");
    await user.click(ta);
    await user.keyboard("first comment");
    await user.click(screen.getByRole("button", { name: "Add" }));
    // Thread appears in ReviewPanel.
    await waitFor(() => {
      expect(screen.getAllByTestId("thread-card")).toHaveLength(1);
    });
    expect(screen.getByTestId("review-tab-pill")).toHaveTextContent("1");
    // LeftPanel block row pill now shows 1.
    const updated = within(blocksTabpanel)
      .getAllByRole("button", { name: /select block/i })
      .find((btn) => within(btn).queryByTestId("block-unresolved-pill"));
    expect(updated).toBeDefined();
    expect(within(updated!).getByTestId("block-unresolved-pill")).toHaveTextContent("1");
  });

  test("approved state: ReadOnlyBanner; Palette disabled; Return-to-draft clears banner", async () => {
    render(<InfographicEditor />);
    fireEvent.click(screen.getByRole("tab", { name: /review/i }));
    fireEvent.click(screen.getByTestId("transition-SUBMIT_FOR_REVIEW"));
    await waitFor(() => {
      expect(screen.getByTestId("transition-APPROVE")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("transition-APPROVE"));
    const banner = await screen.findByTestId("read-only-banner");
    expect(banner).toBeInTheDocument();
    // Theme tab — palette buttons disabled by effectivePerms.
    fireEvent.click(screen.getByRole("tab", { name: /theme tab/i }));
    const themeTabpanel = screen.getByRole("tabpanel", { name: /theme tab/i });
    const palBtns = within(themeTabpanel).getAllByRole("button", { name: /palette:/i });
    expect(palBtns.some((b) => (b as HTMLButtonElement).disabled)).toBe(true);
    // Click "Return to draft" in the banner.
    const returnBtn = within(banner).getByRole("button", { name: /return to draft/i });
    fireEvent.click(returnBtn);
    await waitFor(() => {
      expect(screen.queryByTestId("read-only-banner")).not.toBeInTheDocument();
    });
  });
});
