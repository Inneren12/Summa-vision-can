import { initState } from "../../../src/components/editor/store/reducer";
import type {
  Comment,
  EditorState,
  WorkflowState,
} from "../../../src/components/editor/types";

export function baseState(): EditorState {
  const s = initState();
  // Pin a deterministic clock so timestamps in audit history are stable.
  return { ...s, _timestampProvider: { now: () => "2026-04-18T10:00:00.000Z" } };
}

export function setWorkflow(state: EditorState, to: WorkflowState): EditorState {
  return {
    ...state,
    doc: { ...state.doc, review: { ...state.doc.review, workflow: to } },
  };
}

export function withComments(state: EditorState, comments: Comment[]): EditorState {
  return {
    ...state,
    doc: {
      ...state.doc,
      review: { ...state.doc.review, comments },
    },
  };
}

export function firstBlockId(state: EditorState): string {
  return Object.keys(state.doc.blocks)[0];
}

export function makeComment(over: Partial<Comment> & Pick<Comment, "id" | "blockId">): Comment {
  return {
    parentId: null,
    author: "you",
    text: "Comment text",
    createdAt: "2026-04-18T09:00:00.000Z",
    updatedAt: null,
    resolved: false,
    resolvedAt: null,
    resolvedBy: null,
    ...over,
  };
}
