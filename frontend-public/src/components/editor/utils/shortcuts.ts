export function isEditableTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  const tag = el?.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    el?.isContentEditable === true
  );
}

export function shouldSkipGlobalShortcut(e: Pick<KeyboardEvent, "isComposing" | "target">): boolean {
  return e.isComposing || isEditableTarget(e.target);
}
