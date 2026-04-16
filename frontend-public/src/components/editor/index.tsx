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
  const [mode, setMode] = useState<EditorMode>("design");
  const fileRef = useRef<HTMLInputElement>(null);

  const { doc, selectedBlockId: selId, undoStack, redoStack, dirty } = state;
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
    // Revoke URL after click to free memory
    setTimeout(() => URL.revokeObjectURL(url), 100);
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
    setTimeout(() => URL.revokeObjectURL(url), 100);
    // Mark clean
    dispatch({ type: "SAVED" });
  }, [dirty, doc]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) { e.preventDefault(); dispatch({ type: "UNDO" }); }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) { e.preventDefault(); dispatch({ type: "REDO" }); }
      if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); markSavedAndBackup(); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [markSavedAndBackup]);

  const importJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = ev => {
      let raw: unknown;
      try {
        raw = JSON.parse(ev.target?.result as string);
      } catch {
        alert("Invalid JSON file");
        return;
      }
      let hydrated;
      try {
        hydrated = hydrateImportedDoc(raw);
      } catch (hydrationErr: any) {
        alert(`Import error: ${hydrationErr?.message ?? "hydration failed"}`);
        return;
      }
      const err = validateImport(hydrated);
      if (err) {
        alert(`Import error: ${err}`);
        return;
      }
      dispatch({ type: "IMPORT", doc: hydrated });
    };
    r.readAsText(f);
    e.target.value = "";
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
        setTimeout(() => URL.revokeObjectURL(url), 100);
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
