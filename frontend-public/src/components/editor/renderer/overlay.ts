import { TK } from '../config/tokens';
import type { CropZone } from '../config/cropZones';
import type { HitAreaEntry } from '../utils/hit-test';

export interface OverlayRenderInput {
  ctx: CanvasRenderingContext2D;
  logicalW: number;
  logicalH: number;
  hitAreas: readonly HitAreaEntry[];
  selectedBlockId: string | null;
  hoveredBlockId: string | null;
  dpr: number;
  cropZone?: CropZone | null;
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

const CROP_BORDER_COLOR = '#9CA3AF';
const CROP_LABEL_BG = '#1F2937';
const CROP_LABEL_FG = '#FFFFFF';
const FULL_CANVAS_TOLERANCE_PX = 2;
const PLATFORM_LABELS: Record<CropZone['platform'], string> = {
  reddit: 'Reddit',
  twitter: 'Twitter',
  linkedin: 'LinkedIn',
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
  cropZone,
}: OverlayRenderInput): void {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, logicalW * dpr, logicalH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  if (cropZone) {
    drawCropZone(ctx, cropZone, logicalW, logicalH);
  }

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

export function getScaledCropRect(
  zone: CropZone,
  logicalW: number,
): { x: number; y: number; w: number; h: number } {
  const scale = logicalW / 1080;
  return {
    x: zone.x * scale,
    y: zone.y * scale,
    w: zone.w * scale,
    h: zone.h * scale,
  };
}

export function isFullCanvasCropZone(
  rect: { x: number; y: number; w: number; h: number },
  logicalW: number,
  logicalH: number,
): boolean {
  return (
    Math.abs(rect.x) <= FULL_CANVAS_TOLERANCE_PX &&
    Math.abs(rect.y) <= FULL_CANVAS_TOLERANCE_PX &&
    Math.abs(rect.w - logicalW) <= FULL_CANVAS_TOLERANCE_PX &&
    Math.abs(rect.h - logicalH) <= FULL_CANVAS_TOLERANCE_PX
  );
}

/**
 * Renders platform crop-zone aid on the editor overlay only.
 */
export function drawCropZone(
  ctx: CanvasRenderingContext2D,
  zone: CropZone,
  logicalW: number,
  logicalH: number,
): void {
  const scaledRect = getScaledCropRect(zone, logicalW);
  const { x, y, w, h } = scaledRect;
  const isFullCanvas = isFullCanvasCropZone(scaledRect, logicalW, logicalH);
  const labelText = PLATFORM_LABELS[zone.platform];

  ctx.save();
  if (!isFullCanvas) {
    ctx.strokeStyle = CROP_BORDER_COLOR;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
  }

  const fontSize = 14;
  const padding = 5;
  ctx.font = `${fontSize}px sans-serif`;
  const textMetrics = ctx.measureText(labelText);
  const labelW = textMetrics.width + padding * 2;
  const labelH = fontSize + padding * 2;
  const labelX = x + 4;
  const labelY = y + 4;
  const clampedX = Math.min(Math.max(0, labelX), logicalW - labelW);
  const clampedY = Math.min(Math.max(0, labelY), logicalH - labelH);
  const radius = 4;

  ctx.fillStyle = CROP_LABEL_BG;
  ctx.beginPath();
  ctx.moveTo(clampedX + radius, clampedY);
  ctx.lineTo(clampedX + labelW - radius, clampedY);
  ctx.quadraticCurveTo(
    clampedX + labelW,
    clampedY,
    clampedX + labelW,
    clampedY + radius,
  );
  ctx.lineTo(clampedX + labelW, clampedY + labelH - radius);
  ctx.quadraticCurveTo(
    clampedX + labelW,
    clampedY + labelH,
    clampedX + labelW - radius,
    clampedY + labelH,
  );
  ctx.lineTo(clampedX + radius, clampedY + labelH);
  ctx.quadraticCurveTo(
    clampedX,
    clampedY + labelH,
    clampedX,
    clampedY + labelH - radius,
  );
  ctx.lineTo(clampedX, clampedY + radius);
  ctx.quadraticCurveTo(clampedX, clampedY, clampedX + radius, clampedY);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = CROP_LABEL_FG;
  ctx.textBaseline = 'middle';
  ctx.fillText(labelText, clampedX + padding, clampedY + labelH / 2);
  ctx.restore();
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
