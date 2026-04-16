'use client';

import React from 'react';
import type { ValidationResult } from '../types';
import { TK } from '../config/tokens';

interface QAPanelProps {
  qaOpen: boolean;
  setQaOpen: (v: boolean) => void;
  qaMode: string;
  setQaMode: (m: string) => void;
  vr: ValidationResult;
  dispErr: string[];
  si: string;
}

export function QAPanel({ qaOpen, setQaOpen, qaMode, setQaMode, vr, dispErr, si }: QAPanelProps) {
  if (!qaOpen) {
    return (
      <button onClick={() => setQaOpen(true)} style={{ padding: "2px 12px", borderTop: `1px solid ${TK.c.brd}`, background: TK.c.bgSurf, border: "none", color: TK.c.txtM, cursor: "pointer", fontSize: "7px", fontFamily: TK.font.data, textAlign: "left", flexShrink: 0 }}>{si} QA</button>
    );
  }

  return (
    <div style={{ padding: "5px 12px", borderTop: `1px solid ${TK.c.brd}`, background: TK.c.bgSurf, flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}>
        <span style={{ fontSize: "7px", fontFamily: TK.font.data, color: TK.c.txtS, textTransform: "uppercase" }}>QA</span>
        <div style={{ display: "flex", gap: "1px", background: TK.c.bgApp, borderRadius: "2px", padding: "1px" }}>
          {["draft", "publish"].map(m => <button key={m} onClick={() => setQaMode(m)} style={{ padding: "1px 6px", fontSize: "7px", fontFamily: TK.font.data, textTransform: "uppercase", background: qaMode === m ? TK.c.bgAct : "transparent", color: qaMode === m ? TK.c.acc : TK.c.txtM, border: "none", borderRadius: "2px", cursor: "pointer" }}>{m}</button>)}
        </div>
        <button onClick={() => setQaOpen(false)} style={{ marginLeft: "auto", background: "none", border: "none", color: TK.c.txtM, cursor: "pointer", fontSize: "9px" }}>{"\u2715"}</button>
      </div>
      <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "2px", flexWrap: "wrap" }}>
        {vr.passed.map((m, i) => <span key={`p${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.pos, whiteSpace: "nowrap" }}>{"\u2705"}{m}</span>)}
        {dispErr.map((m, i) => <span key={`e${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.err, whiteSpace: "nowrap" }}>{"\u274C"}{m}</span>)}
        {vr.warnings.map((m, i) => <span key={`w${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.acc, whiteSpace: "nowrap" }}>{"\u26A0\uFE0F"}{m}</span>)}
        {vr.info.map((m, i) => <span key={`i${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, whiteSpace: "nowrap" }}>{"\u2139\uFE0F"}{m}</span>)}
      </div>
    </div>
  );
}
