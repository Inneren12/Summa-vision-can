import React, { useState } from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NoteModal } from "../../../src/components/editor/components/NoteModal";

function makeProps(overrides: Partial<React.ComponentProps<typeof NoteModal>> = {}) {
  return {
    isOpen: true,
    title: "Test modal",
    label: "Comment",
    onSubmit: jest.fn(),
    onCancel: jest.fn(),
    ...overrides,
  };
}

describe("NoteModal", () => {
  test("does not render when isOpen=false", () => {
    const props = makeProps({ isOpen: false });
    render(<NoteModal {...props} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("renders dialog with aria-modal and aria-labelledby pointing at heading", () => {
    const props = makeProps();
    render(<NoteModal {...props} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    const labelledBy = dialog.getAttribute("aria-labelledby");
    expect(labelledBy).toBeTruthy();
    const heading = document.getElementById(labelledBy!);
    expect(heading).toHaveTextContent("Test modal");
  });

  test("focuses textarea on open", async () => {
    const props = makeProps();
    render(<NoteModal {...props} />);
    // queueMicrotask used inside; wait one tick
    await act(async () => { await Promise.resolve(); });
    const ta = screen.getByRole("textbox");
    expect(ta).toHaveFocus();
  });

  test("Escape calls onCancel", async () => {
    const props = makeProps();
    render(<NoteModal {...props} />);
    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape" });
    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  test("Tab from last focusable wraps to first", async () => {
    const props = makeProps();
    render(<NoteModal {...props} />);
    await act(async () => { await Promise.resolve(); });
    const dialog = screen.getByRole("dialog");
    const submitBtn = screen.getByRole("button", { name: "Submit" });
    submitBtn.focus();
    expect(submitBtn).toHaveFocus();
    fireEvent.keyDown(dialog, { key: "Tab" });
    const ta = screen.getByRole("textbox");
    expect(ta).toHaveFocus();
  });

  test("Shift+Tab from first focusable wraps to last", async () => {
    const props = makeProps();
    render(<NoteModal {...props} />);
    await act(async () => { await Promise.resolve(); });
    const dialog = screen.getByRole("dialog");
    const ta = screen.getByRole("textbox");
    ta.focus();
    fireEvent.keyDown(dialog, { key: "Tab", shiftKey: true });
    const submitBtn = screen.getByRole("button", { name: "Submit" });
    expect(submitBtn).toHaveFocus();
  });

  test("submit button disabled when required and value trims to empty", () => {
    const props = makeProps({ required: true });
    render(<NoteModal {...props} />);
    const submitBtn = screen.getByRole("button", { name: "Submit" });
    expect(submitBtn).toBeDisabled();
  });

  test("submit button disabled when value exceeds maxLength", async () => {
    const user = userEvent.setup();
    const props = makeProps({ maxLength: 5 });
    render(<NoteModal {...props} />);
    const ta = screen.getByRole("textbox");
    await user.click(ta);
    await user.keyboard("1234567");
    const submitBtn = screen.getByRole("button", { name: "Submit" });
    expect(submitBtn).toBeDisabled();
  });

  test("character counter turns red over limit", async () => {
    const user = userEvent.setup();
    const props = makeProps({ maxLength: 3 });
    render(<NoteModal {...props} />);
    const ta = screen.getByRole("textbox");
    await user.click(ta);
    await user.keyboard("abcd");
    const counter = screen.getByText("4 / 3");
    // err color is #E11D48 -> rgb(225, 29, 72)
    expect(counter.style.color.toLowerCase()).toContain("rgb(225, 29, 72)");
  });

  test("Ctrl+Enter triggers submit when enabled", async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<NoteModal {...props} />);
    const ta = screen.getByRole("textbox");
    await user.click(ta);
    await user.keyboard("hello");
    fireEvent.keyDown(ta, { key: "Enter", ctrlKey: true });
    expect(props.onSubmit).toHaveBeenCalledWith("hello");
  });

  test("onSubmit receives trimmed value", async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<NoteModal {...props} />);
    const ta = screen.getByRole("textbox");
    await user.click(ta);
    await user.keyboard("  spaced  ");
    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(props.onSubmit).toHaveBeenCalledWith("spaced");
  });

  test("backdrop click calls onCancel", () => {
    const props = makeProps();
    const { container } = render(<NoteModal {...props} />);
    // Backdrop is the outer fixed-positioned div, the parent of the dialog
    const dialog = screen.getByRole("dialog");
    const backdrop = dialog.parentElement!;
    fireEvent.click(backdrop);
    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  test("clicking inside dialog does NOT trigger backdrop close", () => {
    const props = makeProps();
    render(<NoteModal {...props} />);
    const dialog = screen.getByRole("dialog");
    fireEvent.click(dialog);
    expect(props.onCancel).not.toHaveBeenCalled();
  });

  test("restores focus to previously focused element on unmount", async () => {
    const before = document.createElement("button");
    before.id = "before";
    document.body.appendChild(before);
    before.focus();
    expect(before).toHaveFocus();
    const props = makeProps();
    const { unmount } = render(<NoteModal {...props} />);
    await act(async () => { await Promise.resolve(); });
    unmount();
    expect(before).toHaveFocus();
    document.body.removeChild(before);
  });

  test("Submit-disabled Ctrl+Enter does not call onSubmit", async () => {
    const props = makeProps({ required: true });
    render(<NoteModal {...props} />);
    const ta = screen.getByRole("textbox");
    fireEvent.keyDown(ta, { key: "Enter", ctrlKey: true });
    expect(props.onSubmit).not.toHaveBeenCalled();
  });

  test("Cancel button calls onCancel", async () => {
    const user = userEvent.setup();
    const props = makeProps();
    render(<NoteModal {...props} />);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });
});

describe("NoteModal — accessibility lifecycle (Issue 4)", () => {
  test("restores focus to previously focused element on close (Escape path)", async () => {
    const user = userEvent.setup();
    function Host() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button data-testid="opener" onClick={() => setOpen(true)}>Open</button>
          <NoteModal
            isOpen={open}
            title="T"
            label="L"
            onSubmit={() => setOpen(false)}
            onCancel={() => setOpen(false)}
          />
        </>
      );
    }
    render(<Host />);
    const opener = screen.getByTestId("opener");
    opener.focus();
    await user.click(opener);
    await act(async () => { await Promise.resolve(); });

    expect(screen.getByRole("textbox")).toHaveFocus();

    await user.keyboard("{Escape}");

    expect(opener).toHaveFocus();
  });

  test("does not throw when previously focused element is unmounted before close", async () => {
    const user = userEvent.setup();
    function Host() {
      const [open, setOpen] = useState(false);
      const [showOpener, setShowOpener] = useState(true);
      return (
        <>
          {showOpener && (
            <button
              data-testid="opener"
              onClick={() => { setOpen(true); setShowOpener(false); }}
            >
              Open
            </button>
          )}
          <NoteModal
            isOpen={open}
            title="T"
            label="L"
            onSubmit={() => setOpen(false)}
            onCancel={() => setOpen(false)}
          />
        </>
      );
    }
    render(<Host />);
    await user.click(screen.getByTestId("opener"));
    // opener is now unmounted — guard must prevent throw on close.
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("locks body scroll while open, restores on unmount", () => {
    document.body.style.overflow = "";
    const originalOverflow = document.body.style.overflow;
    const { unmount } = render(
      <NoteModal
        isOpen={true}
        title="T"
        label="L"
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    expect(document.body.style.overflow).toBe("hidden");

    unmount();
    expect(document.body.style.overflow).toBe(originalOverflow);
  });

  test("locks body scroll on open, restores on close via prop change", () => {
    document.body.style.overflow = "";
    function Host() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button data-testid="opener" onClick={() => setOpen(true)}>Open</button>
          <button data-testid="closer" onClick={() => setOpen(false)}>Close</button>
          <NoteModal
            isOpen={open}
            title="T"
            label="L"
            onSubmit={() => setOpen(false)}
            onCancel={() => setOpen(false)}
          />
        </>
      );
    }
    render(<Host />);
    expect(document.body.style.overflow).toBe("");
    fireEvent.click(screen.getByTestId("opener"));
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.click(screen.getByTestId("closer"));
    expect(document.body.style.overflow).toBe("");
  });

  test("removes keydown listener on unmount", () => {
    const spy = jest.spyOn(document, "removeEventListener");
    const { unmount } = render(
      <NoteModal
        isOpen={true}
        title="T"
        label="L"
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    unmount();
    const keydownRemovals = spy.mock.calls.filter((c) => c[0] === "keydown");
    expect(keydownRemovals.length).toBeGreaterThan(0);
    spy.mockRestore();
  });
});
