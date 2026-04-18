import React from "react";
import { render, screen, within } from "@testing-library/react";
import { LeftPanel } from "../../../src/components/editor/components/LeftPanel";
import { PERMS } from "../../../src/components/editor/store/permissions";
import type { CanonicalDocument, EditorAction, LeftTab } from "../../../src/components/editor/types";
import { baseState, firstBlockId, makeComment, withComments } from "./_helpers";

function renderLeftPanel(doc: CanonicalDocument, selId: string | null) {
  const dispatch = jest.fn<void, [EditorAction]>();
  const setLtab = jest.fn<void, [LeftTab]>();
  return {
    dispatch,
    setLtab,
    ...render(
      <LeftPanel
        doc={doc}
        dispatch={dispatch}
        selId={selId}
        ltab="blocks"
        setLtab={setLtab}
        perms={PERMS.design}
      />,
    ),
  };
}

describe("LeftPanel — comment count pill sync", () => {
  test("no unresolved comments: pill hidden on every block row", () => {
    const s = baseState();
    renderLeftPanel(s.doc, null);
    expect(screen.queryAllByTestId("block-unresolved-pill")).toHaveLength(0);
  });

  test("adding an unresolved comment surfaces a '1' pill on the target block row", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const s1 = withComments(s0, [makeComment({ id: "c1", blockId: bid })]);
    const { rerender } = renderLeftPanel(s1.doc, null);
    const pill = screen.getByTestId("block-unresolved-pill");
    expect(pill).toHaveAttribute("data-block-id", bid);
    expect(pill).toHaveTextContent("1");

    // Resolving the comment clears the pill on the next render.
    const s2 = withComments(s0, [
      makeComment({
        id: "c1",
        blockId: bid,
        resolved: true,
        resolvedAt: "2026-04-18T09:01:00.000Z",
        resolvedBy: "you",
      }),
    ]);
    const dispatch = jest.fn();
    const setLtab = jest.fn();
    rerender(
      <LeftPanel
        doc={s2.doc}
        dispatch={dispatch}
        selId={null}
        ltab="blocks"
        setLtab={setLtab}
        perms={PERMS.design}
      />,
    );
    expect(screen.queryAllByTestId("block-unresolved-pill")).toHaveLength(0);
  });

  test("pill shows total across root + replies (thread sum, not just root)", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const s1 = withComments(s0, [
      makeComment({ id: "root", blockId: bid }),
      makeComment({
        id: "r1",
        blockId: bid,
        parentId: "root",
        text: "reply 1",
        createdAt: "2026-04-18T09:01:00.000Z",
      }),
      makeComment({
        id: "r2",
        blockId: bid,
        parentId: "root",
        text: "reply 2",
        createdAt: "2026-04-18T09:02:00.000Z",
      }),
    ]);
    renderLeftPanel(s1.doc, null);
    // root + 2 replies = 3 unresolved
    expect(screen.getByTestId("block-unresolved-pill")).toHaveTextContent("3");
  });
});
