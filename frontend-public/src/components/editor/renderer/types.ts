/**
 * Rich result from a block renderer.
 *
 * Used by:
 *   - engine.renderDoc to track cumulative consumed height
 *   - future click-to-select (hitArea)
 *   - future debug overlays (warnings, overflow)
 *   - future smart QA (render-time warnings fed back to validate())
 */
export interface RenderResult {
  /** Height consumed by this block in canvas units (clamped to available space when overflow occurs) */
  height: number;
  /** The height the block WOULD have consumed without clamping. Equal to `height` when no overflow. */
  intrinsicHeight?: number;
  /** True if content was clipped or truncated during render */
  overflow: boolean;
  /** Warnings produced during render (e.g., "text truncated", "too many items") */
  warnings: string[];
  /** Bounding box for click-to-select and debug overlays */
  hitArea: { x: number; y: number; w: number; h: number };
}

export type BlockRenderer = (
  ctx: CanvasRenderingContext2D,
  props: any,
  x: number,
  y: number,
  w: number,
  h: number,
  palette: any,
  scale: number
) => RenderResult;
