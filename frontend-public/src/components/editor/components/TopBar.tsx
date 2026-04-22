'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import type { CanonicalDocument, EditorAction, EditorMode, SaveStatus } from '../types';
import { TK } from '../config/tokens';
import { TPLS } from '../registry/templates';
import { StatusBadge } from './StatusBadge';
import { SaveStatusIndicator } from './SaveStatusIndicator';

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
  saveStatus: SaveStatus;
  fontsReady: boolean;
  // Stage 4 Task 4: debug overlay toggle. Availability is computed by the
  // editor (dev auto / prod `?debug=1`); the button is only rendered when
  // `debugAvailable === true`. The active-state styling is driven by
  // `debugEnabled`.
  debugAvailable?: boolean;
  debugEnabled?: boolean;
  onToggleDebug?: () => void;
}

export function TopBar({
  doc,
  dispatch,
  undoStack,
  redoStack,
  dirty,
  mode,
  setMode,
  errs,
  warns,
  si,
  canExp,
  fileRef,
  importJSON,
  exportJSON,
  markSaved,
  exportPNG,
  saveStatus,
  fontsReady,
  debugAvailable,
  debugEnabled,
  onToggleDebug,
}: TopBarProps) {
  const tQa = useTranslations('qa');
  const tDebug = useTranslations('debug');
  const tExport = useTranslations('export');
  const tImport = useTranslations('import');
  const tEditor = useTranslations('editor');
  const tUndo = useTranslations('undo');
  const tRedo = useTranslations('redo');
  const tSave = useTranslations('save');
  const tDraft = useTranslations('draft');

  // Stage 4 Task 3: EXPORT button composes two gates. Validation errors
  // take priority in the tooltip — the user has to fix those anyway
  // before export works, and the fonts-loading window is typically
  // sub-100ms on warm cache.
  const exportDisabled = !canExp || !fontsReady;
  const exportMessage = !canExp
    ? tExport('disabled.validation_errors', { count: errs })
    : !fontsReady
      ? tExport('disabled.loading_fonts')
      : tExport('png.verb');

  return (
    <div style={{ padding: "6px 12px", borderBottom: `1px solid ${TK.c.brd}`, display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontFamily: TK.font.display, fontWeight: 700, color: TK.c.acc, fontSize: "12px" }}>SUMMA</span>
        <span style={{ fontFamily: TK.font.display, fontWeight: 400, color: TK.c.txtS, fontSize: "12px" }}>VISION</span>
        <span style={{ fontSize: "8px", color: TK.c.txtM, fontFamily: TK.font.data, padding: "2px 5px", background: TK.c.bgAct, borderRadius: "2px", marginLeft: "4px" }}>{TPLS[doc.templateId]?.fam} {"\u2014"} {TPLS[doc.templateId]?.vr}</span>
        <StatusBadge workflow={doc.review.workflow} size="compact" />
        <div role="tablist" aria-label={tEditor('mode.aria')} style={{ display: "flex", gap: "1px", background: TK.c.bgSurf, borderRadius: "3px", padding: "1px", border: `1px solid ${TK.c.brd}`, marginLeft: "6px" }}>
          {(["template", "design"] as const).map(m => <button type="button" key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)} aria-label={tEditor('mode.switch_to', { mode: m })} style={{ padding: "2px 7px", fontSize: "8px", fontFamily: TK.font.data, textTransform: "uppercase", background: mode === m ? TK.c.bgAct : "transparent", color: mode === m ? TK.c.acc : TK.c.txtM, border: "none", borderRadius: "2px", cursor: "pointer" }}>{m}</button>)}
        </div>
        <div style={{ display: "flex", gap: "2px", marginLeft: "8px" }}>
          <button type="button" onClick={() => dispatch({ type: "UNDO" })} disabled={!undoStack.length} aria-label={tUndo('verb')} style={{ padding: "2px 6px", fontSize: "10px", background: "transparent", border: "none", color: undoStack.length ? TK.c.txtS : TK.c.txtM, cursor: undoStack.length ? "pointer" : "default", opacity: undoStack.length ? 1 : .3 }} title={tUndo('shortcut')}>{"\u21A9"}</button>
          <button type="button" onClick={() => dispatch({ type: "REDO" })} disabled={!redoStack.length} aria-label={tRedo('verb')} style={{ padding: "2px 6px", fontSize: "10px", background: "transparent", border: "none", color: redoStack.length ? TK.c.txtS : TK.c.txtM, cursor: redoStack.length ? "pointer" : "default", opacity: redoStack.length ? 1 : .3 }} title={tRedo('shortcut')}>{"\u21AA"}</button>
        </div>
        <SaveStatusIndicator dirty={dirty} saveStatus={saveStatus} />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
        <span style={{ fontSize: "9px" }} title={tQa('summary.compact', { errors: errs, warnings: warns })}>{si}</span>
        <span style={{ fontSize: "7px", color: TK.c.txtM, fontFamily: TK.font.data }}>v{doc.meta.version}</span>
        {debugAvailable && (
          <button
            type="button"
            onClick={onToggleDebug}
            aria-label={debugEnabled ? tDebug('overlay.disable') : tDebug('overlay.enable')}
            title={debugEnabled ? tDebug('overlay.on') : tDebug('overlay.off')}
            style={{
              padding: "3px 6px",
              fontSize: "8px",
              fontFamily: TK.font.data,
              background: debugEnabled ? TK.c.acc : TK.c.bgSurf,
              color: debugEnabled ? TK.c.bgApp : TK.c.txtS,
              border: `1px solid ${debugEnabled ? TK.c.acc : TK.c.brd}`,
              borderRadius: "2px",
              cursor: "pointer",
              fontWeight: debugEnabled ? 700 : 400,
            }}
          >DBG</button>
        )}
        <input ref={fileRef} type="file" accept=".json" onChange={importJSON} style={{ display: "none" }} tabIndex={-1} aria-hidden="true" />
        <button type="button" onClick={() => fileRef.current?.click()} aria-label={tImport('document_json')} title={tImport('document_json')} style={{ padding: "3px 6px", fontSize: "8px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtS, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", cursor: "pointer" }}>{tImport('label_short')}</button>
        <button type="button" onClick={exportJSON} aria-label={tExport('document_json')} title={tExport('document_json')} style={{ padding: "3px 6px", fontSize: "8px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtS, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", cursor: "pointer" }}>{tExport('json_label_short')}</button>
        <button type="button" onClick={markSaved} disabled={!dirty} aria-label={dirty ? tDraft('save.unsaved') : tDraft('save.unchanged')} style={{ padding: "3px 6px", fontSize: "8px", fontFamily: TK.font.data, background: dirty ? TK.c.pos : TK.c.bgSurf, color: dirty ? TK.c.bgApp : TK.c.txtM, border: `1px solid ${dirty ? TK.c.pos : TK.c.brd}`, borderRadius: "2px", cursor: dirty ? "pointer" : "default", fontWeight: dirty ? 700 : 400, opacity: dirty ? 1 : .5 }} title={tSave('shortcut')}>{tSave('label_short')}</button>
        <button
          type="button"
          onClick={exportPNG}
          disabled={exportDisabled}
          aria-label={exportDisabled ? exportMessage : tExport('png.verb')}
          title={exportMessage}
          style={{ padding: "3px 7px", fontSize: "8px", fontFamily: TK.font.data, background: exportDisabled ? TK.c.txtM : TK.c.acc, color: TK.c.bgApp, border: "none", borderRadius: "2px", cursor: exportDisabled ? "not-allowed" : "pointer", fontWeight: 700, opacity: exportDisabled ? 0.5 : 1 }}
        >{tExport('label_short')}</button>
      </div>
    </div>
  );
}
