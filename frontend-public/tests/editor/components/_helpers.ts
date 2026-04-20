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

/**
 * Mock `document.fonts` with a ready promise whose resolution the test
 * controls. Stage 4 Task 3 introduced a `document.fonts.ready` gate on
 * canvas render + PNG export; jsdom exposes the API shape but its
 * default resolution timing is not deterministic for our needs.
 *
 * Usage (pending by default):
 *
 *   const fonts = mockDocumentFontsReady();
 *   // render editor, assert EXPORT disabled ...
 *   fonts.resolve();
 *   await flushPromises();
 *   // assert EXPORT enabled ...
 *   fonts.restore();
 *
 * For tests that don't care about the pending state, pass { initial: 'resolved' }.
 */
export interface FontsReadyHandle {
  resolve: () => void;
  restore: () => void;
}

export function mockDocumentFontsReady(
  opts: { initial?: "pending" | "resolved" } = {},
): FontsReadyHandle {
  const initial = opts.initial ?? "pending";

  let resolveFn: () => void = () => {};
  const ready =
    initial === "resolved"
      ? Promise.resolve()
      : new Promise<void>((resolve) => {
          resolveFn = resolve;
        });

  const originalFonts = Object.getOwnPropertyDescriptor(document, "fonts");

  Object.defineProperty(document, "fonts", {
    configurable: true,
    value: {
      ready,
      load: () => ready.then(() => []),
    },
  });

  return {
    resolve: () => resolveFn(),
    restore: () => {
      if (originalFonts) {
        Object.defineProperty(document, "fonts", originalFonts);
      } else {
        delete (document as unknown as { fonts?: unknown }).fonts;
      }
    },
  };
}
