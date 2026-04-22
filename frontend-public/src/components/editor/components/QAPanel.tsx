'use client';

import React from 'react';
import type { ValidationResult, QAMode } from '../types';
import { TK } from '../config/tokens';
import { formatValidationMessageDev } from '../validation/types';

interface QAPanelProps {
  qaOpen: boolean;
  setQaOpen: (v: boolean) => void;
  qaMode: QAMode;
  setQaMode: (m: QAMode) => void;
  vr: ValidationResult;
  dispErr: ValidationResult['errors'];
  si: string;
}

export function QAPanel({ qaOpen, setQaOpen, qaMode, setQaMode, vr, dispErr, si }: QAPanelProps) {
  if (!qaOpen) {
    return (
      <button type="button" onClick={() => setQaOpen(true)} aria-label="Expand QA panel" style={{ padding: "2px 12px", background: TK.c.bgSurf, border: 0, borderTop: `1px solid ${TK.c.brd}`, color: TK.c.txtM, cursor: "pointer", fontSize: "7px", fontFamily: TK.font.data, textAlign: "left", flexShrink: 0 }}>{si} QA</button>
    );
  }

  return (
    <div style={{ padding: "5px 12px", borderTop: `1px solid ${TK.c.brd}`, background: TK.c.bgSurf, flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}>
        <span style={{ fontSize: "7px", fontFamily: TK.font.data, color: TK.c.txtS, textTransform: "uppercase" }}>QA</span>
        <div role="tablist" aria-label="QA mode" style={{ display: "flex", gap: "1px", background: TK.c.bgApp, borderRadius: "2px", padding: "1px" }}>
          {(["draft", "publish"] as const).map(m => <button type="button" key={m} role="tab" aria-selected={qaMode === m} onClick={() => setQaMode(m)} style={{ padding: "1px 6px", fontSize: "7px", fontFamily: TK.font.data, textTransform: "uppercase", background: qaMode === m ? TK.c.bgAct : "transparent", color: qaMode === m ? TK.c.acc : TK.c.txtM, border: "none", borderRadius: "2px", cursor: "pointer" }}>{m}</button>)}
        </div>
        <button type="button" onClick={() => setQaOpen(false)} style={{ marginLeft: "auto", background: "none", border: "none", color: TK.c.txtM, cursor: "pointer", fontSize: "9px" }}>{"\u2715"}</button>
      </div>
      <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "2px", flexWrap: "wrap" }}>
        {vr.passed.map((m, i) => <span key={`p${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.pos, whiteSpace: "nowrap" }}>{"\u2705"}{formatValidationMessageDev(m)}</span>)}
        {dispErr.map((m, i) => <span key={`e${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.err, whiteSpace: "nowrap" }}>{"\u274C"}{formatValidationMessageDev(m)}</span>)}
        {vr.warnings.map((m, i) => <span key={`w${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.acc, whiteSpace: "nowrap" }}>{"\u26A0\uFE0F"}{formatValidationMessageDev(m)}</span>)}
        {vr.info.map((m, i) => <span key={`i${i}`} style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, whiteSpace: "nowrap" }}>{"\u2139\uFE0F"}{formatValidationMessageDev(m)}</span>)}
      </div>
    </div>
  );
}
