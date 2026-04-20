export interface HitAreaEntry {
  blockId: string;
  hitArea: { x: number; y: number; w: number; h: number };
}

/**
 * Find the topmost block at logical (x, y). Iterates in reverse so the
 * last-drawn block wins on overlap — mirrors the engine draw order.
 *
 * Zero-area rects (w === 0 or h === 0) never match. Clamping a block's
 * hit area against a non-overlapping section collapses it to a
 * zero-area rect (see `clampRectToSection`); that collapsed rect must
 * be unreachable by pointer events so the invisible block cannot steal
 * selection from anything.
 */
export function hitTest(
  entries: readonly HitAreaEntry[],
  x: number,
  y: number,
): string | null {
  for (let i = entries.length - 1; i >= 0; i--) {
    const { blockId, hitArea } = entries[i];
    if (hitArea.w <= 0 || hitArea.h <= 0) continue;
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

/**
 * Clamp a block's hit rect to its containing section's visible bounds.
 *
 * Block renderers may return a hitArea that extends beyond the section
 * they were drawn into — for example, an overflowing text block whose
 * measured height exceeds the available section height. Canvas
 * rendering clips draws to section bounds, but raw hit areas don't.
 * Without clamping, hover/click pixels where nothing is visible can
 * match the overflowing block, potentially stealing selection from a
 * block in an adjacent section.
 *
 * Returns the intersection of `hit` and `section`. If the intersection
 * is empty (negative or zero width/height), returns a zero-area rect
 * at the section origin — hitTest's inclusive-edge check will simply
 * never match it.
 *
 * Pure function. No I/O, no side effects.
 */
export function clampRectToSection(
  hit: { x: number; y: number; w: number; h: number },
  section: { x: number; y: number; w: number; h: number },
): { x: number; y: number; w: number; h: number } {
  const x1 = Math.max(hit.x, section.x);
  const y1 = Math.max(hit.y, section.y);
  const x2 = Math.min(hit.x + hit.w, section.x + section.w);
  const y2 = Math.min(hit.y + hit.h, section.y + section.h);

  const w = Math.max(0, x2 - x1);
  const h = Math.max(0, y2 - y1);

  // Empty intersection: collapse to a zero-area rect at the section
  // origin. hitTest rejects any rect with w <= 0 or h <= 0 up front, so
  // a collapsed rect is provably unreachable by pointer events even
  // though the origin point is technically inside the inclusive edges.
  if (w === 0 || h === 0) {
    return { x: section.x, y: section.y, w: 0, h: 0 };
  }

  return { x: x1, y: y1, w, h };
}
