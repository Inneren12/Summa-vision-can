import React from "react";
import { render, screen } from "@testing-library/react";
import { Inspector } from "../../../src/components/editor/components/Inspector";
import { BREG } from "../../../src/components/editor/registry/blocks";
import type { Block, BlockRegistryEntry, EditorAction } from "../../../src/components/editor/types";
import type { ContrastIssue } from "../../../src/components/editor/validation/contrast";

function mockIssue(over: Partial<ContrastIssue> = {}): ContrastIssue {
  return {
    blockId: "block-1",
    blockType: "headline_editorial",
    slot: "primary",
    textColor: "#F3F4F6",
    bgColor: "#0B0D11",
    bgPoint: "base",
    ratio: 3.27,
    threshold: 4.5,
    severity: "error",
    message: { key: "validation.contrast.below_threshold", params: { blockType: "headline_editorial", slot: "primary", ratio: "3.27", threshold: 4.5, background: "#0B0D11" } },
    ...over,
  };
}

function renderInspector(args: {
  selB: Block | null;
  selId: string | null;
  contrastIssues: ContrastIssue[];
}) {
  const selR: BlockRegistryEntry | null = args.selB ? BREG[args.selB.type] : null;
  const dispatch = jest.fn<void, [EditorAction]>();
  return render(
    <Inspector
      selB={args.selB}
      selR={selR}
      selId={args.selId}
      mode="design"
      canEdit={() => true}
      dispatch={dispatch}
      contrastIssues={args.contrastIssues}
    />,
  );
}

function makeHeadlineBlock(id: string): Block {
  return {
    id,
    type: "headline_editorial",
    props: { text: "Canadian Mortgage Rates", align: "left" },
    visible: true,
  };
}

describe("Inspector contrast surface", () => {
  test("renders contrast section when selected block has issues", () => {
    const block = makeHeadlineBlock("block-1");
    renderInspector({
      selB: block,
      selId: "block-1",
      contrastIssues: [mockIssue({ blockId: "block-1" })],
    });
    expect(screen.getByTestId("inspector-contrast")).toBeInTheDocument();
    expect(screen.getByText("validation.contrast.title")).toBeInTheDocument();
    expect(screen.getByText(/3\.27:1 vs 4\.5:1/)).toBeInTheDocument();
  });

  test("gradient warning suffix is rendered when bgPoint is lightestStop", () => {
    const block = makeHeadlineBlock("block-1");
    renderInspector({
      selB: block,
      selId: "block-1",
      contrastIssues: [mockIssue({
        blockId: "block-1",
        severity: "warning",
        bgPoint: "lightestStop",
        ratio: 3.8,
      })],
    });
    expect(screen.getByText(/3\.80:1 vs 4\.5:1validation\.contrast\.gradient_suffix/)).toBeInTheDocument();
  });

  test("does not render contrast section when selected block has no issues", () => {
    const block = makeHeadlineBlock("block-other");
    renderInspector({
      selB: block,
      selId: "block-other",
      contrastIssues: [mockIssue({ blockId: "block-1" })],
    });
    expect(screen.queryByTestId("inspector-contrast")).not.toBeInTheDocument();
    expect(screen.queryByText("validation.contrast.title")).not.toBeInTheDocument();
  });

  test("does not render contrast section when nothing is selected", () => {
    renderInspector({
      selB: null,
      selId: null,
      contrastIssues: [mockIssue({ blockId: "block-1" })],
    });
    expect(screen.queryByTestId("inspector-contrast")).not.toBeInTheDocument();
  });
});
