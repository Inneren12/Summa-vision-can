import React from "react";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../../../src/components/editor/components/StatusBadge";
import type { WorkflowState } from "../../../src/components/editor/types";

describe("StatusBadge", () => {
  const states: WorkflowState[] = [
    "draft",
    "in_review",
    "approved",
    "exported",
    "published",
  ];

  test.each(states)("renders correct label for workflow state %s", (wf) => {
    const { container } = render(<StatusBadge workflow={wf} />);
    const badge = container.querySelector("[data-testid='status-badge']") as HTMLElement;
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("data-workflow", wf);
    const label = wf === "in_review" ? "IN REVIEW" : wf.toUpperCase();
    expect(badge.textContent).toBe(label);
  });

  test.each(states)("each workflow state %s has a non-default color tone", (wf) => {
    const { container } = render(<StatusBadge workflow={wf} />);
    const badge = container.querySelector("[data-testid='status-badge']") as HTMLElement;
    // Tone present — background and color must both be set on inline style
    expect(badge.style.background).not.toBe("");
    expect(badge.style.color).not.toBe("");
  });

  test("compact size uses smaller font and padding than regular", () => {
    const { container: compact } = render(<StatusBadge workflow="draft" size="compact" />);
    const { container: regular } = render(<StatusBadge workflow="draft" size="regular" />);
    const c = compact.querySelector("[data-testid='status-badge']") as HTMLElement;
    const r = regular.querySelector("[data-testid='status-badge']") as HTMLElement;
    expect(c.style.fontSize).toBe("8px");
    expect(r.style.fontSize).toBe("11px");
    expect(c.style.padding).toBe("2px 5px");
    expect(r.style.padding).toBe("4px 10px");
  });

  test("default size is compact", () => {
    const { container } = render(<StatusBadge workflow="draft" />);
    const badge = container.querySelector("[data-testid='status-badge']") as HTMLElement;
    expect(badge.style.fontSize).toBe("8px");
  });

  test("text is uppercase via inline style", () => {
    const { container } = render(<StatusBadge workflow="approved" />);
    const badge = container.querySelector("[data-testid='status-badge']") as HTMLElement;
    expect(badge.style.textTransform).toBe("uppercase");
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
  });
});
