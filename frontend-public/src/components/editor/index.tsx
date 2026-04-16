'use client';

import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from 'react';
import type { EditorMode, QAMode, LeftTab } from './types';
import { TK } from './config/tokens';
import { PALETTES } from './config/palettes';
import { BGS } from './config/backgrounds';
import { SIZES } from './config/sizes';
import { BREG } from './registry/blocks';
import { validateImport, hydrateImportedDoc } from './registry/guards';
import { reducer, initState } from './store/reducer';
import { PERMS } from './store/permissions';
import { renderDoc } from './renderer/engine';
import { validate } from './validation/validate';
import { deferRevoke } from './utils/download';
import { shouldSkipGlobalShortcut } from './utils/shortcuts';
import { TopBar } from './components/TopBar';
import { LeftPanel } from './components/LeftPanel';
import { Canvas } from './components/Canvas';
import { Inspector } from './components/Inspector';
import { QAPanel } from './components/QAPanel';

export default function InfographicEditor() {
  const cvs = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(reducer, null, initState);
  const [ltab, setLtab] = useState<LeftTab>("templates");
  const [qaOpen, setQaOpen] = useState(true);
  const [qaMode, setQaMode] = useState<QAMode>("publish");
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { doc, selectedBlockId: selId, undoStack, redoStack, dirty, mode } = state;
  // Mode lives in reducer state (single source of truth for permission gate).
  // setMode is a thin wrapper that dispatches SET_MODE.
  const setMode = useCallback((m: EditorMode) => dispatch({ type: "SET_MODE", mode: m }), []);
  const pal = PALETTES[doc.page.palette] || PALETTES.housing;
  const sz = SIZES[doc.page.size] || SIZES.instagram_1080;
  const selB = selId ? doc.blocks[selId] : null;
  const selR = selB ? BREG[selB.type] : null;
  const perms = PERMS[mode] || PERMS.design;

  const vr = useMemo(() => validate(doc), [doc]);
  const dispErr = qaMode === "publish" ? vr.errors : [];
  const errs = vr.errors.length, warns = vr.warnings.length;
  const canExp = errs === 0;
  const si = errs > 0 ? "\uD83D\uDD34" : warns > 0 ? "\uD83D\uDFE1" : "\uD83D\uDFE2";

  const render = useCallback(() => {
    const c = cvs.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 2;
    c.width = sz.w * dpr;
    c.height = sz.h * dpr;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    (BGS[doc.page.background] || BGS.solid_dark).r(ctx, sz.w, sz.h, pal);
    renderDoc(ctx, doc, sz.w, sz.h, pal);
  }, [doc, pal, sz]);
  useEffect(() => { render(); }, [render]);

  const exportJSON = useCallback(() => {
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `summa-${doc.templateId}-v${doc.meta.version}.json`;
    a.click();
    deferRevoke(url);
  }, [doc]);

  // TODO: Replace local JSON backup with POST /api/v1/admin/publications
  // once backend endpoint exists. Current impl serves as temp persistence.
  const markSavedAndBackup = useCallback(() => {
    if (!dirty) return;
    // Save local backup as JSON
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `summa-${doc.templateId}-draft-v${doc.meta.version}.json`;
    a.click();
    deferRevoke(url);
    // Mark clean
    dispatch({ type: "SAVED" });
  }, [dirty, doc]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isEditable = shouldSkipGlobalShortcut(e);

      // Inside editable fields: only Ctrl+S still fires (save is always useful).
      // Undo/redo fall through to native behavior in text inputs.
      if (isEditable) {
        if ((e.ctrlKey || e.metaKey) && e.key === "s") {
          e.preventDefault();
          markSavedAndBackup();
        }
        return;
      }

      // Outside editable fields: editor-level shortcuts
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        dispatch({ type: "UNDO" });
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
        e.preventDefault();
        dispatch({ type: "REDO" });
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        markSavedAndBackup();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [markSavedAndBackup]);

  const importJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const input = e.target;
    const r = new FileReader();
    r.onload = ev => {
      try {
        let raw: unknown;
        try {
          raw = JSON.parse(ev.target?.result as string);
        } catch {
          setImportError("Invalid JSON file");
          setImportWarnings([]);
          return;
        }
        let result;
        try {
          result = hydrateImportedDoc(raw);
        } catch (hydrationErr: any) {
          setImportError(`Import error: ${hydrationErr?.message ?? "hydration failed"}`);
          setImportWarnings([]);
          return;
        }
        const err = validateImport(result.doc);
        if (err) {
          setImportError(`Import error: ${err}`);
          setImportWarnings(result.warnings);
          return;
        }
        setImportError(null);
        setImportWarnings(result.warnings);
        dispatch({ type: "IMPORT", doc: result.doc });
      } finally {
        // Reset so re-selecting the same file re-fires change event
        input.value = "";
      }
    };
    r.readAsText(f);
  };

  const exportPNG = useCallback(() => {
    // QA gate: never produce broken output. PNG export is blocked when there
    // are validation errors; JSON export and SAVE are always allowed so users
    // can checkpoint work-in-progress.
    if (!canExp) return;

    // Render to an offscreen canvas at canonical preset size (no DPR scaling)
    const exportCvs = document.createElement("canvas");
    exportCvs.width = sz.w;
    exportCvs.height = sz.h;
    const ctx = exportCvs.getContext("2d");
    if (!ctx) return;

    // Render at 1:1 (no DPR transform)
    const bgFn = BGS[doc.page.background] || BGS.solid_dark;
    bgFn.r(ctx, sz.w, sz.h, pal);
    renderDoc(ctx, doc, sz.w, sz.h, pal);

    // toBlob is async + memory-efficient (vs. toDataURL ~40MB base64 for Story@DPR3)
    requestAnimationFrame(() => {
      exportCvs.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `summa-${doc.templateId}-${doc.page.size}.png`;
        a.click();
        deferRevoke(url);
      }, "image/png");
    });
  }, [doc, pal, sz, canExp]);

  const canEdit = (reg: typeof selR, k: string) => reg ? perms.editBlock(reg, k) : false;

  return (
    <div style={{ fontFamily: TK.font.body, background: TK.c.bgApp, color: TK.c.txtP, height: "100dvh", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <TopBar
        doc={doc}
        dispatch={dispatch}
        undoStack={undoStack}
        redoStack={redoStack}
        dirty={dirty}
        mode={mode}
        setMode={setMode}
        errs={errs}
        warns={warns}
        si={si}
        canExp={canExp}
        fileRef={fileRef}
        importJSON={importJSON}
        exportJSON={exportJSON}
        markSaved={markSavedAndBackup}
        exportPNG={exportPNG}
      />
      {(importError || importWarnings.length > 0) && (
        <div
          role={importError ? "alert" : "status"}
          aria-live="polite"
          style={{
            borderBottom: `1px solid ${TK.c.brd}`,
            background: importError ? `${TK.c.err}14` : `${TK.c.acc}14`,
            color: importError ? TK.c.err : TK.c.txtP,
            padding: "6px 12px",
            display: "flex",
            gap: "8px",
            alignItems: "flex-start",
          }}
        >
          <div style={{ fontSize: "8px", fontFamily: TK.font.data, textTransform: "uppercase", minWidth: "90px" }}>
            {importError ? "Import error" : "Import warnings"}
          </div>
          <div style={{ fontSize: "9px", lineHeight: 1.4, flex: 1 }}>
            {importError && <div>{importError}</div>}
            {importWarnings.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: "16px" }}>
                {importWarnings.map((w, i) => <li key={`${w}_${i}`}>{w}</li>)}
              </ul>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              setImportError(null);
              setImportWarnings([]);
            }}
            style={{ background: "none", border: "none", color: TK.c.txtM, cursor: "pointer", fontSize: "10px", padding: 0 }}
            aria-label="Dismiss import notices"
            title="Dismiss import notices"
          >
            {"\u2715"}
          </button>
        </div>
      )}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <LeftPanel
          doc={doc}
          dispatch={dispatch}
          selId={selId}
          ltab={ltab}
          setLtab={setLtab}
          perms={perms}
        />

        {/* CENTER */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <Canvas canvasRef={cvs} />
          <QAPanel
            qaOpen={qaOpen}
            setQaOpen={setQaOpen}
            qaMode={qaMode}
            setQaMode={setQaMode}
            vr={vr}
            dispErr={dispErr}
            si={si}
          />
        </div>

        <Inspector
          selB={selB}
          selR={selR ?? null}
          selId={selId}
          mode={mode}
          canEdit={(reg, k) => canEdit(reg, k)}
          dispatch={dispatch}
        />
      </div>
    </div>
  );
}
