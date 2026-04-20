export interface HitAreaEntry {
  blockId: string;
  hitArea: { x: number; y: number; w: number; h: number };
}

/**
 * Find the topmost block at logical (x, y). Iterates in reverse so the
 * last-drawn block wins on overlap — mirrors the engine draw order.
 */
export function hitTest(
  entries: readonly HitAreaEntry[],
  x: number,
  y: number,
): string | null {
  for (let i = entries.length - 1; i >= 0; i--) {
    const { blockId, hitArea } = entries[i];
    if (
      x >= hitArea.x &&
      x <= hitArea.x + hitArea.w &&
      y >= hitArea.y &&
      y <= hitArea.y + hitArea.h
    ) {
      return blockId;
    }
  }
  return null;
}

/**
 * Map pointer-event client coords to canvas logical (pre-DPR) coords.
 * DPR is not part of the transform: `ctx.setTransform(dpr, ...)` already
 * maps logical → backing-store, and hit areas live in logical space.
 */
export function clientToLogical(
  canvas: HTMLCanvasElement,
  clientX: number,
  clientY: number,
  logicalW: number,
  logicalH: number,
): { x: number; y: number } {
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) {
    return { x: 0, y: 0 };
  }
  const scaleX = logicalW / rect.width;
  const scaleY = logicalH / rect.height;
  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  };
}
