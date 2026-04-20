import { TK } from '../config/tokens';

/** Coordinates are in logical (pre-DPR) pixels, matching engine.ts convention. */
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DebugSectionEntry {
  /** Section type key from SECTION_LAYOUT (header / hero / context / chart / footer). */
  type: string;
  rect: Rect;
}

export interface DebugBlockEntry {
  blockId: string;
  blockType: string;
  rawHitArea: Rect;
  clampedHitArea: Rect;
  sectionRect: Rect;
  /** True iff rawHitArea is not fully contained within sectionRect. */
  overflow: boolean;
}

export interface DebugOverlayRenderInput {
  ctx: CanvasRenderingContext2D;
  logicalW: number;
  logicalH: number;
  dpr: number;
  sections: readonly DebugSectionEntry[];
  entries: readonly DebugBlockEntry[];
}

/**
 * Developer-only colour palette for the debug overlay. Not part of the
 * design system — do not add to TK. Values chosen for visual distinction
 * from content pixels; five hues for five section types.
 */
const DEBUG_PALETTE = {
  sections: {
    header:  { fill: 'rgba(56, 189, 248, 0.08)',  stroke: 'rgba(56, 189, 248, 0.9)'  },
    hero:    { fill: 'rgba(232, 121, 249, 0.08)', stroke: 'rgba(232, 121, 249, 0.9)' },
    context: { fill: 'rgba(163, 230, 53, 0.08)',  stroke: 'rgba(163, 230, 53, 0.9)'  },
    chart:   { fill: 'rgba(251, 191, 36, 0.08)',  stroke: 'rgba(251, 191, 36, 0.9)'  },
    footer:  { fill: 'rgba(251, 146, 60, 0.08)',  stroke: 'rgba(251, 146, 60, 0.9)'  },
  } as const,
  block: {
    stroke: 'rgba(255, 255, 255, 0.95)',
    label: '#FFFFFF',
    labelBg: 'rgba(0, 0, 0, 0.65)',
  },
  overflow: {
    stroke: 'rgba(239, 68, 68, 0.95)',
    dash: [6, 4] as const,
  },
  sectionLabel: {
    color: 'rgba(255, 255, 255, 0.85)',
    bg: 'rgba(0, 0, 0, 0.55)',
  },
} as const;

const LABEL_FONT_PX = 10;
const SECTION_LABEL_FONT_PX = 11;

/** Render the debug overlay onto an already-sized canvas context. */
export function renderDebugOverlay({
  ctx,
  logicalW,
  logicalH,
  dpr,
  sections,
  entries,
}: DebugOverlayRenderInput): void {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, logicalW * dpr, logicalH * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  drawSections(ctx, sections);
  drawBlocks(ctx, entries);
}

function drawSections(
  ctx: CanvasRenderingContext2D,
  sections: readonly DebugSectionEntry[],
): void {
  for (const s of sections) {
    const pal =
      (DEBUG_PALETTE.sections as Record<string, { fill: string; stroke: string }>)[
        s.type
      ];
    if (!pal) continue;

    ctx.save();
    ctx.fillStyle = pal.fill;
    ctx.fillRect(s.rect.x, s.rect.y, s.rect.w, s.rect.h);
    ctx.strokeStyle = pal.stroke;
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    ctx.strokeRect(s.rect.x + 0.5, s.rect.y + 0.5, s.rect.w - 1, s.rect.h - 1);
    ctx.restore();

    drawLabel(
      ctx,
      s.type,
      s.rect.x + 4,
      s.rect.y + 4,
      SECTION_LABEL_FONT_PX,
      DEBUG_PALETTE.sectionLabel.color,
      DEBUG_PALETTE.sectionLabel.bg,
    );
  }
}

function drawBlocks(
  ctx: CanvasRenderingContext2D,
  entries: readonly DebugBlockEntry[],
): void {
  for (const e of entries) {
    ctx.save();
    ctx.strokeStyle = DEBUG_PALETTE.block.stroke;
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    ctx.strokeRect(
      e.clampedHitArea.x + 0.5,
      e.clampedHitArea.y + 0.5,
      e.clampedHitArea.w - 1,
      e.clampedHitArea.h - 1,
    );
    ctx.restore();

    if (e.overflow) {
      ctx.save();
      ctx.strokeStyle = DEBUG_PALETTE.overflow.stroke;
      ctx.lineWidth = 1;
      ctx.setLineDash([...DEBUG_PALETTE.overflow.dash]);
      ctx.strokeRect(
        e.rawHitArea.x + 0.5,
        e.rawHitArea.y + 0.5,
        e.rawHitArea.w - 1,
        e.rawHitArea.h - 1,
      );
      ctx.restore();
    }

    const labelText = `${e.blockType}·${e.blockId.slice(0, 6)}`;
    drawLabel(
      ctx,
      labelText,
      e.clampedHitArea.x + 4,
      e.clampedHitArea.y + 4,
      LABEL_FONT_PX,
      DEBUG_PALETTE.block.label,
      DEBUG_PALETTE.block.labelBg,
    );
  }
}

function drawLabel(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  fontPx: number,
  color: string,
  bg: string,
): void {
  ctx.save();
  ctx.font = `500 ${fontPx}px ${TK.font.data}`;
  ctx.textBaseline = 'top';
  const metrics = ctx.measureText(text);
  const padX = 3;
  const padY = 2;
  const boxW = metrics.width + padX * 2;
  const boxH = fontPx + padY * 2;

  ctx.fillStyle = bg;
  ctx.fillRect(x, y, boxW, boxH);

  ctx.fillStyle = color;
  ctx.fillText(text, x + padX, y + padY);
  ctx.restore();
}
