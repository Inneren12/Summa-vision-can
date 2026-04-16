'use client';

import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from 'react';
import type { CanonicalDocument } from './types';
import { TK } from './config/tokens';
import { PALETTES } from './config/palettes';
import { BGS } from './config/backgrounds';
import { SIZES } from './config/sizes';
import { BREG } from './registry/blocks';
import { TPLS } from './registry/templates';
import { validateImport } from './registry/guards';
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
  const [ltab, setLtab] = useState("templates");
  const [qaOpen, setQaOpen] = useState(true);
  const [qaMode, setQaMode] = useState("publish");
  const [mode, setMode] = useState("design");
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
    c.width = sz.w * 2;
    c.height = sz.h * 2;
    c.style.width = "100%";
    c.style.height = "auto";
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(2, 0, 0, 2, 0, 0);
    (BGS[doc.page.background] || BGS.solid_dark).r(ctx, sz.w, sz.h, pal);
    renderDoc(ctx, doc, sz.w, sz.h, pal);
  }, [doc, pal, sz]);
  useEffect(() => { render(); }, [render]);

  const saveDraft = useCallback(() => { if (!dirty) return; dispatch({ type: "SAVED" }); }, [dirty]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) { e.preventDefault(); dispatch({ type: "UNDO" }); }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) { e.preventDefault(); dispatch({ type: "REDO" }); }
      if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); saveDraft(); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [saveDraft]);

  const exportJSON = () => {
    const bl = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(bl);
    a.download = `summa-${doc.templateId}-v${doc.meta.version}.json`;
    a.click();
  };
  const importJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const r = new FileReader();
    r.onload = ev => {
      try {
        const p = JSON.parse(ev.target?.result as string) as CanonicalDocument;
        const err = validateImport(p);
        if (err) { alert(`Import error: ${err}`); return; }
        dispatch({ type: "IMPORT", doc: p });
      } catch { alert("Invalid JSON"); }
    };
    r.readAsText(f);
    e.target.value = "";
  };
  const exportPNG = () => {
    const c = cvs.current;
    if (!c) return;
    const a = document.createElement("a");
    a.href = c.toDataURL("image/png");
    a.download = `summa-${doc.templateId}-${doc.page.size}.png`;
    a.click();
  };

  const canEdit = (reg: typeof selR, k: string) => reg ? perms.editBlock(reg, k) : false;

  return (
    <div style={{ fontFamily: TK.font.body, background: TK.c.bgApp, color: TK.c.txtP, height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>
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
        saveDraft={saveDraft}
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
