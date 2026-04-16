'use client';

import React from 'react';
import { TK } from '../config/tokens';

interface CanvasProps {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
}

export function Canvas({ canvasRef }: CanvasProps) {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "10px", background: `repeating-conic-gradient(${TK.c.bgSurf} 0% 25%, ${TK.c.bgApp} 0% 50%) 50% / 12px 12px`, overflow: "auto" }}>
      <div style={{ maxWidth: "720px", width: "100%", boxShadow: "0 6px 32px rgba(0,0,0,0.5)", borderRadius: "2px", overflow: "hidden" }}>
        <canvas ref={canvasRef} style={{ display: "block" }} />
      </div>
    </div>
  );
}
