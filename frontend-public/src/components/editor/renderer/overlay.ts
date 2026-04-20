import { TK } from '../config/tokens';
import type { HitAreaEntry } from '../utils/hit-test';

export interface OverlayRenderInput {
  ctx: CanvasRenderingContext2D;
  logicalW: number;
  logicalH: number;
  hitAreas: readonly HitAreaEntry[];
  selectedBlockId: string | null;
  hoveredBlockId: string | null;
  dpr: number;
}

interface OutlineStyle {
  strokeStyle: string;
  lineWidth: number;
  dash: number[];
}

/**
 * Outline colour tokens:
 *   - hover:    TK.c.txtS  (secondary text grey, #8B949E) — subtle,
 *     non-competing with selection. Reads clearly against dark
 *     backgrounds without pulling focus from the yellow selection ring.
 *   - selected: TK.c.acc   (yellow accent, #FBBF24) — matches the
 *     accent border LeftPanel uses for the selected block row so the
 *     canvas-side and panel-side selection indicators are visually
 *     linked.
 *
 * The initial Stage 4 Task 1 prompt referenced TK.c.fgSec / TK.c.bgAct,
 * but neither is usable:
 *   - fgSec does not exist in config/tokens.ts.
 *   - bgAct is a dark background fill (#22252D) and would be invisible
 *     as a stroke on the editor's dark canvas.
 * txtS/acc are the confirmed equivalents in use.
 */
const OVERLAY_STYLE: { hover: OutlineStyle; selected: OutlineStyle } = {
  hover: {
    strokeStyle: TK.c.txtS,
    lineWidth: 1,
    dash: [4, 4],
  },
  selected: {
    strokeStyle: TK.c.acc,
    lineWidth: 2,
    dash: [],
  },
};

/**
 * Draw hover + selection outlines onto the overlay canvas.
 *
 * Selection beats hover when both resolve to the same block — we skip the
 * hover outline entirely in that case so outlines don't stack. Hover is
 * painted first so the bolder selection outline sits on top when hover
 * and selection target different blocks.
 */
export function renderOverlay({
  ctx,
  logicalW,
  logicalH,
  hitAreas,
  selectedBlockId,
  hoveredBlockId,
  dpr,
}: OverlayRenderInput): void {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, logicalW * dpr, logicalH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const hoveredEntry =
    hoveredBlockId && hoveredBlockId !== selectedBlockId
      ? hitAreas.find((e) => e.blockId === hoveredBlockId)
      : undefined;
  const selectedEntry = selectedBlockId
    ? hitAreas.find((e) => e.blockId === selectedBlockId)
    : undefined;

  if (hoveredEntry) {
    drawOutline(ctx, hoveredEntry.hitArea, OVERLAY_STYLE.hover);
  }
  if (selectedEntry) {
    drawOutline(ctx, selectedEntry.hitArea, OVERLAY_STYLE.selected);
  }
}

function drawOutline(
  ctx: CanvasRenderingContext2D,
  rect: { x: number; y: number; w: number; h: number },
  style: OutlineStyle,
): void {
  ctx.save();
  ctx.strokeStyle = style.strokeStyle;
  ctx.lineWidth = style.lineWidth;
  ctx.setLineDash(style.dash);
  const inset = style.lineWidth / 2;
  ctx.strokeRect(
    rect.x + inset,
    rect.y + inset,
    rect.w - style.lineWidth,
    rect.h - style.lineWidth,
  );
  ctx.restore();
}
