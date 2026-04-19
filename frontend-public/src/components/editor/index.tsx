'use client';

import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import type { EditorMode, QAMode, LeftTab, BlockRegistryEntry, CanonicalDocument } from './types';
import { TK } from './config/tokens';
import { PALETTES } from './config/palettes';
import { BGS } from './config/backgrounds';
import { SIZES } from './config/sizes';
import { BREG } from './registry/blocks';
import { validateImportStrict, hydrateImportedDoc } from './registry/guards';
import { reducer, initState } from './store/reducer';
import { PERMS, WORKFLOW_PERMISSIONS, canEditKeyInWorkflow } from './store/permissions';
import { renderDoc } from './renderer/engine';
import { renderOverlay } from './renderer/overlay';
import { validate } from './validation/validate';
import { deferRevoke } from './utils/download';
import { buildUpdatePayload } from './utils/persistence';
import { shouldSkipGlobalShortcut } from './utils/shortcuts';
import { clientToLogical, hitTest, type HitAreaEntry } from './utils/hit-test';
import {
  updateAdminPublication,
  AdminPublicationNotFoundError,
} from '@/lib/api/admin';
import { TopBar } from './components/TopBar';
import { LeftPanel } from './components/LeftPanel';
import { Canvas } from './components/Canvas';
import { RightRail } from './components/RightRail';
import { QAPanel } from './components/QAPanel';
import { ReadOnlyBanner } from './components/ReadOnlyBanner';
import { NotificationBanner } from './components/NotificationBanner';
import { NoteModal } from './components/NoteModal';
import type { NoteRequestConfig } from './components/noteRequest';

export interface InfographicEditorProps {
  /**
   * Optional document to seed the editor with. If omitted or invalid,
   * the editor falls back to the default `single_stat_hero` template.
   *
   * Validation runs through `validateImportStrict` — invalid docs are
   * logged (dev only), surfaced in the NotificationBanner via import
   * error state, and the fallback is used.
   */
  initialDoc?: CanonicalDocument;

  /**
   * Optional publication id. When present, Ctrl+S PATCHes the document
   * to the backend via the admin proxy. When absent, Ctrl+S is a
   * no-op (the legacy JSON download was removed in Stage 4 Task 0).
   */
  publicationId?: string;
}

export default function InfographicEditor({
  initialDoc,
  publicationId,
}: InfographicEditorProps = {}) {
  const cvs = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLCanvasElement>(null);
  // Per-frame derived data from the content render. Populated synchronously
  // by the render effect below; read by the canvas click/hover handlers and
  // by the overlay render effect. A ref (not state) because it is purely
  // derived from `doc/sz/pal` — storing it in state would double-render.
  const hitAreasRef = useRef<HitAreaEntry[]>([]);
  const [hoveredBlockId, setHoveredBlockId] = useState<string | null>(null);

  // Synchronously validate initialDoc at mount time so the reducer never
  // sees an invalid doc. Validation failure falls back to the default
  // template and surfaces the error through importError banner state.
  const [initialValidatedDoc, initialValidationError] = useMemo(() => {
    if (!initialDoc) return [undefined, null] as const;
    try {
      const validated = validateImportStrict(initialDoc);
      return [validated, null] as const;
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') {
        console.error('[InfographicEditor] initialDoc validation failed:', err);
      }
      return [
        undefined,
        err instanceof Error ? err.message : String(err),
      ] as const;
    }
  }, [initialDoc]);

  const [state, dispatch] = useReducer(
    reducer,
    undefined,
    () => initState(initialValidatedDoc),
  );
  const savingRef = useRef<boolean>(false);
  const [ltab, setLtab] = useState<LeftTab>("templates");
  const [qaOpen, setQaOpen] = useState(true);
  const [qaMode, setQaMode] = useState<QAMode>("publish");
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const [importError, setImportError] = useState<string | null>(
    initialValidationError
      ? `Failed to load publication — using template defaults. ${initialValidationError}`
      : null,
  );
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
  const workflow = doc.review.workflow;
  const workflowPerms = WORKFLOW_PERMISSIONS[workflow];
  // `effectivePerms`: the mode × workflow permission overlay, the single
  // source of truth for UI-side disable state. Distinct name from the raw
  // module-level `PERMS[mode]` so future greps find the combined version.
  // `editBlock` consults both the mode-axis base and the workflow-key-category
  // helper so the Inspector's disable state tracks exactly what the reducer's
  // checkWorkflowPermission would allow for an UPDATE_PROP action. The
  // style-axis booleans gate on `workflowPerms.style` explicitly — it's false
  // in every non-draft workflow, including `in_review`.
  const effectivePerms = useMemo(() => ({
    ...basePerms,
    switchTemplate: basePerms.switchTemplate && workflowPerms.style,
    changePalette: basePerms.changePalette && workflowPerms.style,
    changeBackground: basePerms.changeBackground && workflowPerms.style,
    changeSize: basePerms.changeSize && workflowPerms.style,
    editBlock: (reg: BlockRegistryEntry, k: string): boolean =>
      canEditKeyInWorkflow(workflow, k) && basePerms.editBlock(reg, k),
    toggleVisibility: (reg: BlockRegistryEntry): boolean =>
      workflowPerms.structural && basePerms.toggleVisibility(reg),
  }), [basePerms, workflow, workflowPerms]);

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
    if (!ctx) {
      // jsdom / headless: render can't run but the hit-area ref must still
      // be consistent with the doc state the handlers will see.
      hitAreasRef.current = [];
      return;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    (BGS[doc.page.background] || BGS.solid_dark).r(ctx, sz.w, sz.h, pal);
    const results = renderDoc(ctx, doc, sz.w, sz.h, pal);
    hitAreasRef.current = results.map(r => ({ blockId: r.blockId, hitArea: r.result.hitArea }));
  }, [doc, pal, sz]);
  useEffect(() => { render(); }, [render]);

  // Overlay render — hover + selection outlines on a separate canvas.
  // Ordered AFTER the content-render effect so `hitAreasRef.current` is
  // up to date when this runs in the same commit cycle.
  useEffect(() => {
    const c = overlay.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 2;
    const wantW = sz.w * dpr;
    const wantH = sz.h * dpr;
    // Skip the implicit clear that width/height assignment triggers when
    // the backing store is already the right size.
    if (c.width !== wantW) c.width = wantW;
    if (c.height !== wantH) c.height = wantH;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    renderOverlay({
      ctx,
      logicalW: sz.w,
      logicalH: sz.h,
      hitAreas: hitAreasRef.current,
      selectedBlockId: selId,
      hoveredBlockId,
      dpr,
    });
  }, [selId, hoveredBlockId, sz, doc, pal]);

  const handleCanvasMouseDown = useCallback((e: ReactMouseEvent<HTMLCanvasElement>) => {
    const canvas = cvs.current;
    if (!canvas) return;
    const { x, y } = clientToLogical(canvas, e.clientX, e.clientY, sz.w, sz.h);
    const hit = hitTest(hitAreasRef.current, x, y);
    // `null` hit ⇒ empty-space click deselects. Mirrors the implicit
    // deselect that SWITCH_TPL / IMPORT already do in the reducer.
    dispatch({ type: "SELECT", blockId: hit });
  }, [sz.w, sz.h]);

  const handleCanvasMouseMove = useCallback((e: ReactMouseEvent<HTMLCanvasElement>) => {
    const canvas = cvs.current;
    if (!canvas) return;
    const { x, y } = clientToLogical(canvas, e.clientX, e.clientY, sz.w, sz.h);
    const hit = hitTest(hitAreasRef.current, x, y);
    setHoveredBlockId(prev => (prev === hit ? prev : hit));
  }, [sz.w, sz.h]);

  const handleCanvasMouseLeave = useCallback(() => {
    setHoveredBlockId(null);
  }, []);

  const exportJSON = useCallback(() => {
    const blob = new Blob([JSON.stringify(doc, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `summa-${doc.templateId}-v${doc.meta.version}.json`;
    a.click();
    deferRevoke(url);
  }, [doc]);

  // Ctrl+S persistence. When `publicationId` is set, PATCH the document
  // to the backend via the admin proxy. Without a publicationId the save
  // command is a no-op — the legacy JSON download was removed in
  // Stage 4 Task 0 (see docs/modules/editor.md).
  //
  // Snapshot-based save (B2): we capture the doc reference at save start
  // and dispatch SAVED_IF_MATCHES with it. The reducer only clears
  // `dirty` if the current doc is still the same reference — i.e. the
  // user did not edit during the in-flight PATCH. If they did, the new
  // edits never reached the backend, so keeping `dirty: true` is correct.
  //
  // Error routing (B4): save failures land on `state.saveError` via
  // SAVE_FAILED, distinct from the import-error channel. NotificationBanner
  // priority: saveError > importError > _lastRejection > warnings.
  const markSavedAndBackup = useCallback(() => {
    if (!dirty) return;
    if (!publicationId) {
      if (process.env.NODE_ENV !== 'production') {
        console.warn('[InfographicEditor] Ctrl+S pressed but no publicationId — save skipped.');
      }
      return;
    }
    if (savingRef.current) return;

    const snapshotDoc = doc;
    savingRef.current = true;

    const payload = buildUpdatePayload(snapshotDoc);
    updateAdminPublication(publicationId, payload)
      .then(() => {
        dispatch({ type: "SAVED_IF_MATCHES", snapshotDoc });
      })
      .catch((err: unknown) => {
        if (err instanceof AdminPublicationNotFoundError) {
          dispatch({
            type: "SAVE_FAILED",
            error: 'Publication not found — reload the page',
          });
        } else {
          const msg = err instanceof Error ? err.message : String(err);
          dispatch({ type: "SAVE_FAILED", error: msg });
        }
      })
      .finally(() => {
        savingRef.current = false;
      });
  }, [dirty, doc, publicationId]);

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

  const canEdit = (reg: typeof selR, k: string) => reg ? effectivePerms.editBlock(reg, k) : false;

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
        dispatch={dispatch}
      />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <LeftPanel
          doc={doc}
          dispatch={dispatch}
          selId={selId}
          ltab={ltab}
          setLtab={setLtab}
          effectivePerms={effectivePerms}
        />

        {/* CENTER */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <ReadOnlyBanner
            state={state}
            dispatch={dispatch}
            onRequestNote={requestNote}
          />
          <Canvas
            canvasRef={cvs}
            overlayRef={overlay}
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleCanvasMouseMove}
            onMouseLeave={handleCanvasMouseLeave}
          />
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
