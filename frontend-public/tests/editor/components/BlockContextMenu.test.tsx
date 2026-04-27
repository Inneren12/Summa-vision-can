/**
 * Phase 1.6 — context-menu component integration test.
 *
 * Per TEST_INFRASTRUCTURE.md §4: assert on `namespace.key` strings (the
 * global next-intl mock returns `${namespace}.${key}`). Do NOT modify the
 * mock to return localised strings.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { BlockContextMenu } from "../../../src/components/editor/components/BlockContextMenu";
import type { Block } from "../../../src/components/editor/types";

function mkBlock(over: Partial<Block> = {}): Block {
  return {
    id: "blk_001",
    type: "body_annotation",
    props: { text: "Hello world" },
    visible: true,
    ...over,
  };
}

interface MountOpts {
  block?: Block;
  designMode?: boolean;
  canStructuralEdit?: boolean;
  position?: { x: number; y: number };
}

function mountMenu(opts: MountOpts = {}) {
  const onClose = jest.fn();
  const onLock = jest.fn();
  const onHide = jest.fn();
  const onDuplicate = jest.fn();
  const onDelete = jest.fn();
  const block = opts.block ?? mkBlock();
  const result = render(
    <BlockContextMenu
      block={block}
      position={opts.position ?? { x: 100, y: 100 }}
      onClose={onClose}
      onLock={onLock}
      onHide={onHide}
      onDuplicate={onDuplicate}
      onDelete={onDelete}
      designMode={opts.designMode ?? true}
      canStructuralEdit={opts.canStructuralEdit ?? true}
    />,
  );
  return { onClose, onLock, onHide, onDuplicate, onDelete, ...result };
}

describe("BlockContextMenu", () => {
  test("renders four menu items with key labels and shortcut hints", () => {
    mountMenu();
    expect(screen.getByTestId("block-context-menu")).toBeInTheDocument();
    expect(screen.getByTestId("ctx-lock")).toHaveTextContent("editor.context_menu.lock");
    expect(screen.getByTestId("ctx-hide")).toHaveTextContent("editor.context_menu.hide");
    expect(screen.getByTestId("ctx-duplicate")).toHaveTextContent("editor.context_menu.duplicate");
    expect(screen.getByTestId("ctx-delete")).toHaveTextContent("editor.context_menu.delete");
    // Shortcut hints rendered alongside.
    expect(screen.getByTestId("ctx-lock")).toHaveTextContent("⌘L");
    expect(screen.getByTestId("ctx-hide")).toHaveTextContent("⌘H");
    expect(screen.getByTestId("ctx-duplicate")).toHaveTextContent("⌘D");
    expect(screen.getByTestId("ctx-delete")).toHaveTextContent("Delete");
  });

  test("Lock label flips to Unlock when block.locked is true", () => {
    mountMenu({ block: mkBlock({ locked: true }) });
    expect(screen.getByTestId("ctx-lock")).toHaveTextContent("editor.context_menu.unlock");
  });

  test("Hide label flips to Show when block.visible is false", () => {
    mountMenu({ block: mkBlock({ visible: false }) });
    expect(screen.getByTestId("ctx-hide")).toHaveTextContent("editor.context_menu.show");
  });

  test("clicking each item invokes its callback then closes the menu", () => {
    const { onLock, onClose } = mountMenu();
    fireEvent.click(screen.getByTestId("ctx-lock"));
    expect(onLock).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test("Duplicate is disabled in template mode", () => {
    const { onDuplicate } = mountMenu({ designMode: false });
    const dup = screen.getByTestId("ctx-duplicate");
    expect(dup).toBeDisabled();
    fireEvent.click(dup);
    expect(onDuplicate).not.toHaveBeenCalled();
  });

  test("Delete is disabled for required_locked block (source_footer)", () => {
    const { onDelete } = mountMenu({
      block: mkBlock({ id: "blk_src", type: "source_footer", props: { text: "Src" } }),
    });
    const del = screen.getByTestId("ctx-delete");
    expect(del).toBeDisabled();
    fireEvent.click(del);
    expect(onDelete).not.toHaveBeenCalled();
  });

  test("Delete is disabled for required_editable block (headline_editorial)", () => {
    const { onDelete } = mountMenu({
      block: mkBlock({ id: "blk_h", type: "headline_editorial", props: { text: "H" } }),
    });
    expect(screen.getByTestId("ctx-delete")).toBeDisabled();
    fireEvent.click(screen.getByTestId("ctx-delete"));
    expect(onDelete).not.toHaveBeenCalled();
  });

  test("Hide is disabled when the block is locked", () => {
    const { onHide } = mountMenu({ block: mkBlock({ locked: true }) });
    expect(screen.getByTestId("ctx-hide")).toBeDisabled();
    fireEvent.click(screen.getByTestId("ctx-hide"));
    expect(onHide).not.toHaveBeenCalled();
  });

  test("Escape key closes the menu", () => {
    const { onClose } = mountMenu();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test("pointerdown outside the menu closes it", () => {
    const { onClose } = mountMenu();
    // jsdom lacks PointerEvent; the listener treats a synthetic Event with
    // .target set as functionally identical for click-outside dismissal.
    const event = new Event("pointerdown", { bubbles: true });
    Object.defineProperty(event, "target", { value: document.body });
    document.dispatchEvent(event);
    expect(onClose).toHaveBeenCalled();
  });

  test("pointerdown inside the menu does NOT close it", () => {
    const { onClose } = mountMenu();
    const inside = screen.getByTestId("block-context-menu");
    const event = new Event("pointerdown", { bubbles: true });
    Object.defineProperty(event, "target", { value: inside });
    document.dispatchEvent(event);
    expect(onClose).not.toHaveBeenCalled();
  });

  test("scroll on the document closes the menu (capture phase)", () => {
    const { onClose } = mountMenu();
    document.dispatchEvent(new Event("scroll"));
    expect(onClose).toHaveBeenCalled();
  });

  test("aria-label is wired from i18n for the menu container", () => {
    mountMenu();
    expect(screen.getByRole("menu")).toHaveAttribute(
      "aria-label",
      "editor.context_menu.aria_label",
    );
  });

  test("Lock is disabled when canStructuralEdit=false", () => {
    const { onLock } = mountMenu({ canStructuralEdit: false });
    const lock = screen.getByTestId("ctx-lock");
    expect(lock).toBeDisabled();
    expect(lock).toHaveAttribute("title", "editor.context_menu.disabled_workflow");
    fireEvent.click(lock);
    expect(onLock).not.toHaveBeenCalled();
  });

  test("Hide is disabled when canStructuralEdit=false", () => {
    const { onHide } = mountMenu({ canStructuralEdit: false });
    const hide = screen.getByTestId("ctx-hide");
    expect(hide).toBeDisabled();
    expect(hide).toHaveAttribute("title", "editor.context_menu.disabled_workflow");
    fireEvent.click(hide);
    expect(onHide).not.toHaveBeenCalled();
  });

  test("Duplicate is disabled when canStructuralEdit=false even in designMode", () => {
    const { onDuplicate } = mountMenu({ canStructuralEdit: false, designMode: true });
    const dup = screen.getByTestId("ctx-duplicate");
    expect(dup).toBeDisabled();
    expect(dup).toHaveAttribute("title", "editor.context_menu.disabled_workflow");
    fireEvent.click(dup);
    expect(onDuplicate).not.toHaveBeenCalled();
  });

  test("Delete is disabled when canStructuralEdit=false even in designMode for non-required block", () => {
    const { onDelete } = mountMenu({ canStructuralEdit: false, designMode: true });
    const del = screen.getByTestId("ctx-delete");
    expect(del).toBeDisabled();
    expect(del).toHaveAttribute("title", "editor.context_menu.disabled_workflow");
    fireEvent.click(del);
    expect(onDelete).not.toHaveBeenCalled();
  });

  test("templateRequired tooltip wins over disabled_workflow", () => {
    mountMenu({
      block: mkBlock({ id: "blk_src", type: "source_footer", props: { text: "Src" } }),
      canStructuralEdit: false,
    });
    const del = screen.getByTestId("ctx-delete");
    expect(del).toBeDisabled();
    expect(del).toHaveAttribute(
      "title",
      "editor.context_menu.delete_disabled_template_locked",
    );
  });

  test("Hide locked tooltip wins over disabled_workflow", () => {
    // Locked block + workflow disallows structural edit. The locked
    // reason is more informative for the operator (the cause is on
    // the block, not the workflow), so it must win.
    const { onHide } = mountMenu({
      block: mkBlock({ locked: true }),
      canStructuralEdit: false,
    });
    const hide = screen.getByTestId("ctx-hide");
    expect(hide).toBeDisabled();
    expect(hide).toHaveAttribute(
      "title",
      "editor.context_menu.hide_disabled_locked",
    );
    fireEvent.click(hide);
    expect(onHide).not.toHaveBeenCalled();
  });
});
