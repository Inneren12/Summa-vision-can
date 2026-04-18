import React, { useState } from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReadOnlyBanner } from "../../../src/components/editor/components/ReadOnlyBanner";
import { NoteModal } from "../../../src/components/editor/components/NoteModal";
import type { NoteRequestConfig } from "../../../src/components/editor/components/noteRequest";
import type { EditorState } from "../../../src/components/editor/types";
import { baseState, setWorkflow } from "./_helpers";

function Host({ state, dispatch }: { state: EditorState; dispatch: jest.Mock }) {
  const [req, setReq] = useState<NoteRequestConfig | null>(null);
  return (
    <>
      <ReadOnlyBanner state={state} dispatch={dispatch} onRequestNote={setReq} />
      <NoteModal
        isOpen={req !== null}
        title={req?.title ?? ""}
        label={req?.label ?? ""}
        placeholder={req?.placeholder}
        initialValue={req?.initialValue}
        submitLabel={req?.submitLabel}
        required={req?.required ?? false}
        onSubmit={(text) => {
          const r = req;
          setReq(null);
          r?.onSubmit(text);
        }}
        onCancel={() => setReq(null)}
      />
    </>
  );
}

function mountBanner(state: EditorState) {
  const dispatch = jest.fn();
  return {
    dispatch,
    ...render(<Host state={state} dispatch={dispatch} />),
  };
}

describe("ReadOnlyBanner — visibility gating", () => {
  test("does not render in draft", () => {
    mountBanner(baseState());
    expect(screen.queryByTestId("read-only-banner")).not.toBeInTheDocument();
  });

  test("does not render in in_review", () => {
    mountBanner(setWorkflow(baseState(), "in_review"));
    expect(screen.queryByTestId("read-only-banner")).not.toBeInTheDocument();
  });

  test.each(["approved", "exported", "published"] as const)(
    "renders in %s (read-only workflow)",
    (wf) => {
      mountBanner(setWorkflow(baseState(), wf));
      expect(screen.getByTestId("read-only-banner")).toHaveAttribute("data-workflow", wf);
    },
  );
});

describe("ReadOnlyBanner — per-state CTA mapping (Issue 2)", () => {
  test("approved: only Return to draft is visible; no Duplicate", () => {
    mountBanner(setWorkflow(baseState(), "approved"));
    expect(screen.getByTestId("banner-return-to-draft")).toBeInTheDocument();
    expect(screen.queryByTestId("banner-duplicate")).not.toBeInTheDocument();
  });

  test("approved: clicking Return to draft opens NoteModal (no direct dispatch)", async () => {
    const user = userEvent.setup();
    const { dispatch } = mountBanner(setWorkflow(baseState(), "approved"));
    await user.click(screen.getByTestId("banner-return-to-draft"));
    const dialog = screen.getByRole("dialog");
    // The <h2> heading inside the dialog carries the title.
    expect(within(dialog).getByRole("heading", { name: "Return to draft" })).toBeInTheDocument();
    // No dispatch has happened yet — waiting for note submit.
    expect(dispatch).not.toHaveBeenCalled();
  });

  test("approved: submitting NoteModal with a reason dispatches RETURN_TO_DRAFT with note", async () => {
    const user = userEvent.setup();
    const { dispatch } = mountBanner(setWorkflow(baseState(), "approved"));
    await user.click(screen.getByTestId("banner-return-to-draft"));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("textbox"));
    await user.keyboard("copy needs edits");
    await user.click(within(dialog).getByRole("button", { name: /return to draft/i }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "RETURN_TO_DRAFT",
      note: "copy needs edits",
    });
  });

  test("approved: submitting NoteModal with an empty note dispatches with note: undefined", async () => {
    const user = userEvent.setup();
    const { dispatch } = mountBanner(setWorkflow(baseState(), "approved"));
    await user.click(screen.getByTestId("banner-return-to-draft"));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /return to draft/i }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "RETURN_TO_DRAFT",
      note: undefined,
    });
  });

  test("exported: both Duplicate AND Return to draft are visible", () => {
    mountBanner(setWorkflow(baseState(), "exported"));
    expect(screen.getByTestId("banner-duplicate")).toBeInTheDocument();
    expect(screen.getByTestId("banner-return-to-draft")).toBeInTheDocument();
  });

  test("exported: clicking Duplicate dispatches DUPLICATE_AS_DRAFT directly (no modal)", async () => {
    const user = userEvent.setup();
    const { dispatch } = mountBanner(setWorkflow(baseState(), "exported"));
    await user.click(screen.getByTestId("banner-duplicate"));
    expect(dispatch).toHaveBeenCalledWith({ type: "DUPLICATE_AS_DRAFT" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("exported: clicking Return to draft opens NoteModal", async () => {
    const user = userEvent.setup();
    const { dispatch } = mountBanner(setWorkflow(baseState(), "exported"));
    await user.click(screen.getByTestId("banner-return-to-draft"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(dispatch).not.toHaveBeenCalled();
  });

  test("published: only Duplicate is visible; no Return to draft", () => {
    mountBanner(setWorkflow(baseState(), "published"));
    expect(screen.getByTestId("banner-duplicate")).toBeInTheDocument();
    expect(screen.queryByTestId("banner-return-to-draft")).not.toBeInTheDocument();
  });

  test("published: clicking Duplicate dispatches DUPLICATE_AS_DRAFT directly", async () => {
    const user = userEvent.setup();
    const { dispatch } = mountBanner(setWorkflow(baseState(), "published"));
    await user.click(screen.getByTestId("banner-duplicate"));
    expect(dispatch).toHaveBeenCalledWith({ type: "DUPLICATE_AS_DRAFT" });
  });
});
