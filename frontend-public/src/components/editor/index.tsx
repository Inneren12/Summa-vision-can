'use client';

import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from 'react';
import type { EditorMode, QAMode, LeftTab, BlockRegistryEntry } from './types';
import { TK } from './config/tokens';
import { PALETTES } from './config/palettes';
import { BGS } from './config/backgrounds';
import { SIZES } from './config/sizes';
import { BREG } from './registry/blocks';
import { validateImportStrict, hydrateImportedDoc } from './registry/guards';
import { reducer, initState } from './store/reducer';
import { PERMS, WORKFLOW_PERMISSIONS } from './store/permissions';
import { isReadOnlyWorkflow } from './store/workflow';
import { renderDoc } from './renderer/engine';
import { validate } from './validation/validate';
import { deferRevoke } from './utils/download';
import { shouldSkipGlobalShortcut } from './utils/shortcuts';
import { TopBar } from './components/TopBar';
import { LeftPanel } from './components/LeftPanel';
import { Canvas } from './components/Canvas';
import { RightRail } from './components/RightRail';
import { QAPanel } from './components/QAPanel';
import { ReadOnlyBanner } from './components/ReadOnlyBanner';
import { NotificationBanner } from './components/NotificationBanner';
import { NoteModal } from './components/NoteModal';
import type { NoteRequestConfig } from './components/noteRequest';

export default function InfographicEditor() {
  const cvs = useRef<HTMLCanvasElement>(null);
  const [state, dispatch] = useReducer(reducer, null, initState);
  const [ltab, setLtab] = useState<LeftTab>("templates");
  const [qaOpen, setQaOpen] = useState(true);
  const [qaMode, setQaMode] = useState<QAMode>("publish");
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Single NoteModal instance, owned here and shared by every surface that
  // needs free-text user input (ReviewPanel comment composition, ReviewPanel
  // transition notes, ReadOnlyBanner RETURN_TO_DRAFT). Centralising ownership
  // keeps the audit path uniform — note-bearing transitions always flow
  // through NoteModal.onSubmit → dispatch, regardless of initiating surface.
  const [noteRequest, setNoteRequest] = useState<NoteRequestConfig | null>(null);
  const requestNote = useCallback((config: NoteRequestConfig) => {
    setNoteRequest(config);
  }, []);
  const handleNoteSubmit = useCallback((text: string) => {
    const req = noteRequest;
    setNoteRequest(null);
    req?.onSubmit(text);
  }, [noteRequest]);
  const handleNoteCancel = useCallback(() => {
    setNoteRequest(null);
  }, []);

  const { doc, selectedBlockId: selId, undoStack, redoStack, dirty, mode } = state;
  // Mode lives in reducer state (single source of truth for permission gate).
  // setMode is a thin wrapper that dispatches SET_MODE.
  const setMode = useCallback((m: EditorMode) => dispatch({ type: "SET_MODE", mode: m }), []);
  const pal = PALETTES[doc.page.palette] || PALETTES.housing;
  const sz = SIZES[doc.page.size] || SIZES.instagram_1080;
  const selB = selId ? doc.blocks[selId] : null;
  const selR = selB ? BREG[selB.type] : null;
  const basePerms = PERMS[mode] || PERMS.design;
  const workflowPerms = WORKFLOW_PERMISSIONS[doc.review.workflow];
  const isReadOnly = isReadOnlyWorkflow(doc.review.workflow);
  // Effective permissions overlay: workflow gate disables capabilities even
  // when mode would allow them. editBlock / toggleVisibility are functions —
  // intercept those to also return false in read-only workflows so the
  // Inspector reflects the workflow lockdown.
  const perms = useMemo(() => ({
    ...basePerms,
    switchTemplate: basePerms.switchTemplate && workflowPerms.style,
    changePalette: basePerms.changePalette && workflowPerms.style,
    changeBackground: basePerms.changeBackground && workflowPerms.style,
    changeSize: basePerms.changeSize && workflowPerms.style,
    editBlock: (reg: BlockRegistryEntry, k: string): boolean =>
      !isReadOnly && basePerms.editBlock(reg, k),
    toggleVisibility: (reg: BlockRegistryEntry): boolean =>
      !isReadOnly && workflowPerms.structural && basePerms.toggleVisibility(reg),
  }), [basePerms, workflowPerms, isReadOnly]);

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
      const key = e.key.toLowerCase();
      const isEditable = shouldSkipGlobalShortcut(e);

      // Inside editable fields: only Ctrl+S fires (save is always useful).
      if (isEditable) {
        if ((e.ctrlKey || e.metaKey) && key === "s") {
          e.preventDefault();
          markSavedAndBackup();
        }
        return;
      }

      // Outside editable fields: editor-level shortcuts.
      if ((e.ctrlKey || e.metaKey) && key === "z" && !e.shiftKey) {
        e.preventDefault();
        dispatch({ type: "UNDO" });
      }
      if ((e.ctrlKey || e.metaKey) && (key === "y" || (key === "z" && e.shiftKey))) {
        e.preventDefault();
        dispatch({ type: "REDO" });
      }
      if ((e.ctrlKey || e.metaKey) && key === "s") {
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
        let validated;
        try {
          validated = validateImportStrict(result.doc);
        } catch (validationErr: any) {
          setImportError(`Import error: ${validationErr?.message ?? "validation failed"}`);
          setImportWarnings(result.warnings);
          return;
        }
        setImportError(null);
        setImportWarnings(result.warnings);
        dispatch({ type: "IMPORT", doc: validated });
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

    // Create a separate export canvas at canonical preset size.
    // Preview canvas stays DPR-scaled; export is exact 1:1 dimensions.
    const exportCvs = document.createElement("canvas");
    exportCvs.width = sz.w;
    exportCvs.height = sz.h;
    const ctx = exportCvs.getContext("2d");
    if (!ctx) return;

    const bgFn = BGS[doc.page.background] || BGS.solid_dark;
    bgFn.r(ctx, sz.w, sz.h, pal);
    renderDoc(ctx, doc, sz.w, sz.h, pal);

    // toBlob keeps exports async/memory-safe and avoids base64 data URL inflation.
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
  }, [canExp, doc, pal, sz]);

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
      <NotificationBanner
        state={state}
        importError={importError}
        importWarnings={importWarnings}
        onClearImportError={() => setImportError(null)}
        onClearImportWarnings={() => setImportWarnings([])}
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
          <ReadOnlyBanner
            state={state}
            dispatch={dispatch}
            onRequestNote={requestNote}
          />
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

        <RightRail
          state={state}
          dispatch={dispatch}
          selB={selB}
          selR={selR ?? null}
          selId={selId}
          mode={mode}
          canEdit={(reg, k) => canEdit(reg, k)}
          onRequestNote={requestNote}
        />
      </div>

      <NoteModal
        isOpen={noteRequest !== null}
        title={noteRequest?.title ?? ''}
        label={noteRequest?.label ?? ''}
        placeholder={noteRequest?.placeholder}
        initialValue={noteRequest?.initialValue}
        submitLabel={noteRequest?.submitLabel}
        required={noteRequest?.required ?? false}
        onSubmit={handleNoteSubmit}
        onCancel={handleNoteCancel}
      />
    </div>
  );
}
