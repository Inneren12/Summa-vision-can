import type { CanonicalDocument, Palette } from '../types';
import { TK } from '../config/tokens';
import { BR } from './blocks';

export const SECTION_LAYOUT: Record<string, (w: number, h: number, s: number, p: number) => { x: number; y: number; w: number; h: number }> = {
  header: (w, h, s, p) => ({ x: p, y: p, w: w - p * 2, h: 130 * s }),
  hero: (w, h, s, p) => ({ x: p, y: h * .34, w: w - p * 2, h: 160 * s }),
  context: (w, h, s, p) => ({ x: p, y: h * .58, w: w - p * 2, h: 100 * s }),
  chart: (w, h, s, p) => ({ x: p, y: h * .22, w: w - p * 2, h: h * .55 }),
  footer: (w, h, s, p) => ({ x: p, y: h - p - 40 * s, w: w - p * 2, h: 40 * s }),
};

export function renderDoc(ctx: CanvasRenderingContext2D, doc: CanonicalDocument, w: number, h: number, pal: Palette): void {
  const s = w / 1080, pad = 64 * s;
  ctx.fillStyle = TK.c.acc;
  ctx.fillRect(0, 0, w, 4 * s);
  doc.sections.forEach(sec => {
    const lf = SECTION_LAYOUT[sec.type];
    if (!lf) return;
    const la = lf(w, h, s, pad);
    let cy = 0;
    sec.blockIds.forEach(bid => {
      const b = doc.blocks[bid];
      if (!b || !b.visible) return;
      const fn = BR[b.type];
      if (!fn) return;
      cy += fn(ctx, b.props, la.x, la.y + cy, la.w, la.h, pal, s);
    });
  });
}
