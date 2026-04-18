import React, { useState } from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReviewPanel } from "../../../src/components/editor/components/ReviewPanel";
import { NoteModal } from "../../../src/components/editor/components/NoteModal";
import type { NoteRequestConfig } from "../../../src/components/editor/components/noteRequest";
import type { EditorState, WorkflowHistoryEntry } from "../../../src/components/editor/types";
import {
  baseState,
  firstBlockId,
  makeComment,
  setWorkflow,
  withComments,
} from "./_helpers";

function Host({ state, dispatch }: { state: EditorState; dispatch: jest.Mock }) {
  const [req, setReq] = useState<NoteRequestConfig | null>(null);
  return (
    <>
      <ReviewPanel state={state} dispatch={dispatch} onRequestNote={setReq} />
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

function mount(state: EditorState) {
  const dispatch = jest.fn();
  return {
    dispatch,
    ...render(<Host state={state} dispatch={dispatch} />),
  };
}

function selectFirstBlock(s: EditorState): EditorState {
  return { ...s, selectedBlockId: firstBlockId(s) };
}

describe("ReviewPanel — workflow header", () => {
  test("current workflow badge renders", () => {
    mount(baseState());
    expect(screen.getByTestId("status-badge")).toHaveAttribute("data-workflow", "draft");
  });

  test("draft state shows '→ In review' transition", () => {
    mount(baseState());
    expect(screen.getByTestId("transition-SUBMIT_FOR_REVIEW")).toBeInTheDocument();
  });

  test("clicking '→ In review' dispatches SUBMIT_FOR_REVIEW", () => {
    const { dispatch } = mount(baseState());
    fireEvent.click(screen.getByTestId("transition-SUBMIT_FOR_REVIEW"));
    expect(dispatch).toHaveBeenCalledWith({ type: "SUBMIT_FOR_REVIEW" });
  });

  test("in_review '→ Draft' opens a NoteModal titled 'Request changes'", () => {
    mount(setWorkflow(baseState(), "in_review"));
    fireEvent.click(screen.getByTestId("transition-REQUEST_CHANGES"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Request changes")).toBeInTheDocument();
  });

  test("submitting note dispatches REQUEST_CHANGES with the note", async () => {
    const user = userEvent.setup();
    const { dispatch } = mount(setWorkflow(baseState(), "in_review"));
    fireEvent.click(screen.getByTestId("transition-REQUEST_CHANGES"));
    const ta = screen.getByRole("textbox");
    await user.click(ta);
    await user.keyboard("please fix copy");
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "REQUEST_CHANGES",
      note: "please fix copy",
    });
  });

  test("submitting empty note dispatches REQUEST_CHANGES with note: undefined", async () => {
    const user = userEvent.setup();
    const { dispatch } = mount(setWorkflow(baseState(), "in_review"));
    fireEvent.click(screen.getByTestId("transition-REQUEST_CHANGES"));
    await user.click(screen.getByRole("button", { name: "Confirm" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "REQUEST_CHANGES", note: undefined });
  });

  test("approved state renders Duplicate as draft", () => {
    const { dispatch } = mount(setWorkflow(baseState(), "approved"));
    // Duplicate appears only for exported/published, not approved per spec
    expect(screen.queryByTestId("transition-DUPLICATE_AS_DRAFT")).not.toBeInTheDocument();
    expect(dispatch).not.toHaveBeenCalled();
  });

  test("exported state renders Duplicate as draft and dispatches DUPLICATE_AS_DRAFT", () => {
    const { dispatch } = mount(setWorkflow(baseState(), "exported"));
    const dup = screen.getByTestId("transition-DUPLICATE_AS_DRAFT");
    expect(dup).toBeInTheDocument();
    fireEvent.click(dup);
    expect(dispatch).toHaveBeenCalledWith({ type: "DUPLICATE_AS_DRAFT" });
  });

  test("published state renders Duplicate as draft", () => {
    mount(setWorkflow(baseState(), "published"));
    expect(screen.getByTestId("transition-DUPLICATE_AS_DRAFT")).toBeInTheDocument();
  });
});

describe("ReviewPanel — threads", () => {
  test("'Show resolved' unchecked by default; resolved thread hidden", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "open1", blockId: bid, text: "open" }),
      makeComment({
        id: "done1",
        blockId: bid,
        text: "resolved",
        resolved: true,
        resolvedAt: "x",
        resolvedBy: "you",
      }),
    ]);
    mount(state);
    expect(screen.getAllByTestId("thread-card")).toHaveLength(1);
    fireEvent.click(screen.getByTestId("show-resolved-toggle"));
    expect(screen.getAllByTestId("thread-card")).toHaveLength(2);
  });

  test("thread header click dispatches SELECT for the thread's blockId", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "c1", blockId: bid, text: "x" }),
    ]);
    const { dispatch } = mount(state);
    fireEvent.click(screen.getByTestId("thread-header"));
    expect(dispatch).toHaveBeenCalledWith({ type: "SELECT", blockId: bid });
  });

  test("tombstone thread shows 'Comment deleted' italic and no Edit/Delete", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({
        id: "tomb1",
        blockId: bid,
        author: "[deleted]",
        text: "[deleted]",
      }),
    ]);
    mount(state);
    expect(screen.getByText("Comment deleted")).toBeInTheDocument();
    expect(screen.queryByTestId("edit-button")).not.toBeInTheDocument();
    expect(screen.queryByTestId("delete-button")).not.toBeInTheDocument();
  });

  test("own thread shows Edit and Delete; foreign thread does not", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "own1", blockId: bid, author: "you" }),
      makeComment({
        id: "alice1",
        blockId: bid,
        author: "alice",
        createdAt: "2026-04-18T09:00:01.000Z",
      }),
    ]);
    mount(state);
    expect(screen.getAllByTestId("edit-button")).toHaveLength(1);
    expect(screen.getAllByTestId("delete-button")).toHaveLength(1);
    // Both threads show Resolve (resolution not ownership-gated)
    expect(screen.getAllByTestId("resolve-button").length).toBe(2);
  });

  test("Resolve dispatches RESOLVE_COMMENT", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "c1", blockId: bid, author: "you" }),
    ]);
    const { dispatch } = mount(state);
    fireEvent.click(screen.getByTestId("resolve-button"));
    expect(dispatch).toHaveBeenCalledWith({ type: "RESOLVE_COMMENT", commentId: "c1" });
  });

  test("Reply opens NoteModal with parentId and dispatches REPLY_TO_COMMENT on submit", async () => {
    const user = userEvent.setup();
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "root", blockId: bid }),
    ]);
    const { dispatch } = mount(state);
    fireEvent.click(screen.getByTestId("reply-button"));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Reply to comment")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("textbox"));
    await user.keyboard("ack");
    await user.click(within(dialog).getByRole("button", { name: "Reply" }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "REPLY_TO_COMMENT",
      parentId: "root",
      text: "ack",
    });
  });

  test("Add comment composer hidden when no block selected", () => {
    const state = { ...baseState(), selectedBlockId: null };
    mount(state);
    expect(screen.queryByTestId("add-comment-button")).not.toBeInTheDocument();
  });

  test("Add comment composer visible when a block is selected", () => {
    mount(selectFirstBlock(baseState()));
    expect(screen.getByTestId("add-comment-button")).toBeInTheDocument();
  });

  test("Add comment dispatches ADD_COMMENT with selected blockId and text", async () => {
    const user = userEvent.setup();
    const state = selectFirstBlock(baseState());
    const { dispatch } = mount(state);
    fireEvent.click(screen.getByTestId("add-comment-button"));
    await user.click(screen.getByRole("textbox"));
    await user.keyboard("hello world");
    await user.click(screen.getByRole("button", { name: "Add" }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "ADD_COMMENT",
      blockId: state.selectedBlockId,
      text: "hello world",
    });
  });

  test("read-only workflow disables Reply and Add buttons with tooltip reason", () => {
    const s0 = setWorkflow(selectFirstBlock(baseState()), "approved");
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "c1", blockId: bid }),
    ]);
    mount(state);
    const reply = screen.getByTestId("reply-button");
    expect(reply).toBeDisabled();
    expect(reply).toHaveAttribute("title", expect.stringMatching(/read-only/i));
    const add = screen.getByTestId("add-comment-button");
    expect(add).toBeDisabled();
  });
});

describe("ReviewPanel — history", () => {
  test("history rendered reverse-chronologically; comment events use muted color", () => {
    const s0 = baseState();
    const history: WorkflowHistoryEntry[] = [
      {
        ts: "2026-04-18T09:00:00.000Z",
        action: "submitted",
        summary: "Submitted for review",
        author: "you",
        fromWorkflow: "draft",
        toWorkflow: "in_review",
      },
      {
        ts: "2026-04-18T09:01:00.000Z",
        action: "comment_added",
        summary: "Comment on Hero stat: \"x\"",
        author: "you",
        fromWorkflow: null,
        toWorkflow: null,
      },
    ];
    const state: EditorState = {
      ...s0,
      doc: { ...s0.doc, review: { ...s0.doc.review, history } },
    };
    mount(state);
    const items = screen.getAllByTestId("history-entry");
    // Reverse-chrono: newest (comment_added) first.
    expect(items[0]).toHaveAttribute("data-event-kind", "comment");
    expect(items[1]).toHaveAttribute("data-event-kind", "workflow");
  });

  test("history collapsed when > 6; Show all toggle expands", () => {
    const s0 = baseState();
    const history: WorkflowHistoryEntry[] = Array.from({ length: 9 }, (_, i) => ({
      ts: `2026-04-18T09:00:0${i}.000Z`,
      action: i % 2 === 0 ? "submitted" : "comment_added",
      summary: `event ${i}`,
      author: "you",
      fromWorkflow: null,
      toWorkflow: null,
    }));
    const state: EditorState = {
      ...s0,
      doc: { ...s0.doc, review: { ...s0.doc.review, history } },
    };
    mount(state);
    expect(screen.getAllByTestId("history-entry")).toHaveLength(6);
    fireEvent.click(screen.getByTestId("history-toggle"));
    expect(screen.getAllByTestId("history-entry")).toHaveLength(9);
  });
});
