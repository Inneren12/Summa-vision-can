'use client';

import React from 'react';
import { TK } from '../config/tokens';

interface CanvasProps {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  overlayRef: React.RefObject<HTMLCanvasElement | null>;
  onMouseDown?: React.MouseEventHandler<HTMLCanvasElement>;
  onMouseMove?: React.MouseEventHandler<HTMLCanvasElement>;
  onMouseLeave?: React.MouseEventHandler<HTMLCanvasElement>;
}

export function Canvas({
  canvasRef,
  overlayRef,
  onMouseDown,
  onMouseMove,
  onMouseLeave,
}: CanvasProps) {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "10px", background: `repeating-conic-gradient(${TK.c.bgSurf} 0% 25%, ${TK.c.bgApp} 0% 50%) 50% / 12px 12px`, overflow: "auto" }}>
      <div style={{ maxWidth: "720px", width: "100%", boxShadow: "0 6px 32px rgba(0,0,0,0.5)", borderRadius: "2px", overflow: "hidden" }}>
        <div style={{ position: "relative", width: "100%" }}>
          <canvas
            ref={canvasRef}
            style={{ display: "block", width: "100%", height: "auto" }}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseLeave={onMouseLeave}
          />
          <canvas
            ref={overlayRef}
            aria-hidden="true"
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
            }}
          />
        </div>
      </div>
    </div>
  );
}
