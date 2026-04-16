'use client';

import React from 'react';
import type { CanonicalDocument, EditorAction, EditorMode } from '../types';
import { TK } from '../config/tokens';
import { TPLS } from '../registry/templates';

interface TopBarProps {
  doc: CanonicalDocument;
  dispatch: React.Dispatch<EditorAction>;
  undoStack: CanonicalDocument[];
  redoStack: CanonicalDocument[];
  dirty: boolean;
  mode: EditorMode;
  setMode: (m: EditorMode) => void;
  errs: number;
  warns: number;
  si: string;
  canExp: boolean;
  fileRef: React.RefObject<HTMLInputElement | null>;
  importJSON: (e: React.ChangeEvent<HTMLInputElement>) => void;
  exportJSON: () => void;
  markSaved: () => void;
  exportPNG: () => void;
}

export function TopBar({ doc, dispatch, undoStack, redoStack, dirty, mode, setMode, errs, warns, si, canExp, fileRef, importJSON, exportJSON, markSaved, exportPNG }: TopBarProps) {
  return (
    <div style={{ padding: "6px 12px", borderBottom: `1px solid ${TK.c.brd}`, display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontFamily: TK.font.display, fontWeight: 700, color: TK.c.acc, fontSize: "12px" }}>SUMMA</span>
        <span style={{ fontFamily: TK.font.display, fontWeight: 400, color: TK.c.txtS, fontSize: "12px" }}>VISION</span>
        <span style={{ fontSize: "8px", color: TK.c.txtM, fontFamily: TK.font.data, padding: "2px 5px", background: TK.c.bgAct, borderRadius: "2px", marginLeft: "4px" }}>{TPLS[doc.templateId]?.fam} {"\u2014"} {TPLS[doc.templateId]?.vr}</span>
        <div style={{ display: "flex", gap: "1px", background: TK.c.bgSurf, borderRadius: "3px", padding: "1px", border: `1px solid ${TK.c.brd}`, marginLeft: "6px" }}>
          {(["template", "design"] as const).map(m => <button key={m} onClick={() => setMode(m)} style={{ padding: "2px 7px", fontSize: "8px", fontFamily: TK.font.data, textTransform: "uppercase", background: mode === m ? TK.c.bgAct : "transparent", color: mode === m ? TK.c.acc : TK.c.txtM, border: "none", borderRadius: "2px", cursor: "pointer" }}>{m}</button>)}
        </div>
        <div style={{ display: "flex", gap: "2px", marginLeft: "8px" }}>
          <button onClick={() => dispatch({ type: "UNDO" })} disabled={!undoStack.length} style={{ padding: "2px 6px", fontSize: "10px", background: "transparent", border: "none", color: undoStack.length ? TK.c.txtS : TK.c.txtM, cursor: undoStack.length ? "pointer" : "default", opacity: undoStack.length ? 1 : .3 }} title="Undo">{"\u21A9"}</button>
          <button onClick={() => dispatch({ type: "REDO" })} disabled={!redoStack.length} style={{ padding: "2px 6px", fontSize: "10px", background: "transparent", border: "none", color: redoStack.length ? TK.c.txtS : TK.c.txtM, cursor: redoStack.length ? "pointer" : "default", opacity: redoStack.length ? 1 : .3 }} title="Redo">{"\u21AA"}</button>
        </div>
        {dirty && <span style={{ fontSize: "7px", color: TK.c.acc, fontFamily: TK.font.data }}>{"\u25CF"}</span>}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
        <span style={{ fontSize: "9px" }} title={`${errs}err ${warns}warn`}>{si}</span>
        <span style={{ fontSize: "7px", color: TK.c.txtM, fontFamily: TK.font.data }}>v{doc.meta.version}</span>
        <input ref={fileRef} type="file" accept=".json" onChange={importJSON} style={{ display: "none" }} />
        <button onClick={() => fileRef.current?.click()} style={{ padding: "3px 6px", fontSize: "8px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtS, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", cursor: "pointer" }}>IMPORT</button>
        <button onClick={exportJSON} style={{ padding: "3px 6px", fontSize: "8px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtS, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", cursor: "pointer" }}>JSON</button>
        <button onClick={markSaved} disabled={!dirty} style={{ padding: "3px 6px", fontSize: "8px", fontFamily: TK.font.data, background: dirty ? TK.c.pos : TK.c.bgSurf, color: dirty ? TK.c.bgApp : TK.c.txtM, border: `1px solid ${dirty ? TK.c.pos : TK.c.brd}`, borderRadius: "2px", cursor: dirty ? "pointer" : "default", fontWeight: dirty ? 700 : 400, opacity: dirty ? 1 : .5 }} title="Ctrl+S">SAVE</button>
        <button onClick={exportPNG} disabled={!canExp} style={{ padding: "3px 7px", fontSize: "8px", fontFamily: TK.font.data, background: canExp ? TK.c.acc : TK.c.txtM, color: TK.c.bgApp, border: "none", borderRadius: "2px", cursor: canExp ? "pointer" : "not-allowed", fontWeight: 700, opacity: canExp ? 1 : .5 }}>EXPORT</button>
      </div>
    </div>
  );
}
