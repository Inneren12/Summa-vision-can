import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RightRail } from "../../../src/components/editor/components/RightRail";
import { BREG } from "../../../src/components/editor/registry/blocks";
import type { Block, BlockRegistryEntry } from "../../../src/components/editor/types";
import {
  baseState,
  firstBlockId,
  makeComment,
  withComments,
} from "./_helpers";

function mountRail(stateOverride?: ReturnType<typeof baseState>) {
  const state = stateOverride ?? baseState();
  const dispatch = jest.fn();
  const selId = firstBlockId(state);
  const selB: Block | null = state.doc.blocks[selId] ?? null;
  const selR: BlockRegistryEntry | null = selB ? BREG[selB.type] ?? null : null;
  const canEdit = jest.fn(() => true);
  const onRequestNote = jest.fn();
  return {
    state,
    dispatch,
    canEdit,
    onRequestNote,
    ...render(
      <RightRail
        state={state}
        dispatch={dispatch}
        selB={selB}
        selR={selR}
        selId={selId}
        mode="design"
        canEdit={canEdit}
        onRequestNote={onRequestNote}
      />,
    ),
  };
}

describe("RightRail", () => {
  test("renders two tabs; Inspector selected by default", () => {
    mountRail();
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(2);
    const [inspector, review] = tabs;
    expect(inspector).toHaveTextContent(/inspector/i);
    expect(inspector).toHaveAttribute("aria-selected", "true");
    expect(review).toHaveTextContent(/review/i);
    expect(review).toHaveAttribute("aria-selected", "false");
  });

  test("clicking Review switches aria-selected and visible tabpanel", () => {
    mountRail();
    const reviewTab = screen.getByRole("tab", { name: /review/i });
    fireEvent.click(reviewTab);
    expect(reviewTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("review-panel")).toBeInTheDocument();
  });

  test("Review tab pill is hidden when no unresolved comments", () => {
    mountRail();
    expect(screen.queryByTestId("review-tab-pill")).not.toBeInTheDocument();
  });

  test("Review tab pill shows total unresolved count across threads", () => {
    const s0 = baseState();
    const bid = firstBlockId(s0);
    const state = withComments(s0, [
      makeComment({ id: "c1", blockId: bid }),
      makeComment({
        id: "c2",
        blockId: bid,
        parentId: "c1",
        text: "reply",
        createdAt: "2026-04-18T09:01:00.000Z",
      }),
      makeComment({
        id: "c3",
        blockId: bid,
        text: "another root",
        createdAt: "2026-04-18T09:02:00.000Z",
      }),
      makeComment({
        id: "c4",
        blockId: bid,
        text: "done",
        resolved: true,
        resolvedAt: "2026-04-18T09:03:00.000Z",
        resolvedBy: "you",
        createdAt: "2026-04-18T08:00:00.000Z",
      }),
    ]);
    mountRail(state);
    const pill = screen.getByTestId("review-tab-pill");
    expect(pill).toHaveTextContent("3");
  });
});

describe("RightRail — keyboard navigation (W3C ARIA tabs pattern)", () => {
  test("inactive tab has tabIndex=-1, active tab has tabIndex=0 (roving focus)", () => {
    mountRail();
    expect(screen.getByRole("tab", { name: /inspector/i })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: /review/i })).toHaveAttribute("tabindex", "-1");
  });

  test("ArrowRight moves focus from Inspector tab to Review tab and activates it", async () => {
    const user = userEvent.setup();
    mountRail();
    const inspectorTab = screen.getByRole("tab", { name: /inspector/i });
    inspectorTab.focus();
    expect(inspectorTab).toHaveFocus();

    await user.keyboard("{ArrowRight}");

    const reviewTab = screen.getByRole("tab", { name: /review/i });
    expect(reviewTab).toHaveFocus();
    expect(reviewTab).toHaveAttribute("aria-selected", "true");
    expect(reviewTab).toHaveAttribute("tabindex", "0");
    expect(inspectorTab).toHaveAttribute("tabindex", "-1");
  });

  test("ArrowLeft from Review wraps to Inspector", async () => {
    const user = userEvent.setup();
    mountRail();
    const reviewTab = screen.getByRole("tab", { name: /review/i });
    fireEvent.click(reviewTab);
    reviewTab.focus();
    await user.keyboard("{ArrowLeft}");
    const inspectorTab = screen.getByRole("tab", { name: /inspector/i });
    expect(inspectorTab).toHaveFocus();
    expect(inspectorTab).toHaveAttribute("aria-selected", "true");
  });

  test("ArrowRight from Review wraps to Inspector (circular)", async () => {
    const user = userEvent.setup();
    mountRail();
    const reviewTab = screen.getByRole("tab", { name: /review/i });
    fireEvent.click(reviewTab);
    reviewTab.focus();
    await user.keyboard("{ArrowRight}");
    const inspectorTab = screen.getByRole("tab", { name: /inspector/i });
    expect(inspectorTab).toHaveFocus();
  });

  test("Home moves to first tab; End moves to last tab", async () => {
    const user = userEvent.setup();
    mountRail();
    const reviewTab = screen.getByRole("tab", { name: /review/i });
    fireEvent.click(reviewTab);
    reviewTab.focus();

    await user.keyboard("{Home}");
    const inspectorTab = screen.getByRole("tab", { name: /inspector/i });
    expect(inspectorTab).toHaveFocus();
    expect(inspectorTab).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: /review/i })).toHaveFocus();
    expect(screen.getByRole("tab", { name: /review/i })).toHaveAttribute("aria-selected", "true");
  });

  test("unrelated keys are ignored (no tab switch)", async () => {
    const user = userEvent.setup();
    mountRail();
    const inspectorTab = screen.getByRole("tab", { name: /inspector/i });
    inspectorTab.focus();
    await user.keyboard("a");
    expect(inspectorTab).toHaveAttribute("aria-selected", "true");
  });
});
