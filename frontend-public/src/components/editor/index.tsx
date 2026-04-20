'use client';

import { useState, useRef, useEffect, useCallback, useMemo, useReducer } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import type { EditorMode, QAMode, LeftTab, BlockRegistryEntry, CanonicalDocument, SaveStatus } from './types';
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
import { clientToLogical, hitTest, clampRectToSection, type HitAreaEntry } from './utils/hit-test';
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

// Autosave cadence (Stage 4 Task 2). `AUTOSAVE_DEBOUNCE_MS` is the quiet
// window after the last mutating reducer action before a PATCH fires.
// `RETRY_DELAYS_MS` is the exponential backoff schedule used when a save
// fails; after all four attempts are exhausted, auto-retry stops and the
// user can trigger a manual retry from the NotificationBanner.
const AUTOSAVE_DEBOUNCE_MS = 2000;
const RETRY_DELAYS_MS = [2000, 4000, 8000, 16000] as const;

// Maximum wait for `document.fonts.ready` before flipping `fontsReady`
// true anyway (Stage 4 Task 3). Guards against pathological browser
// states where the promise hangs; normal warm-cache loads resolve in
// sub-100ms and never hit this ceiling. A dev-only console.warn on
// timeout documents the fallback for development.
const FONTS_TIMEOUT_MS = 5000;

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
  // Font-load gate (Stage 4 Task 3). `next/font` loads fonts async; until
  // they're ready, canvas `ctx.font` falls back to `system-ui`/`monospace`
  // and preview/export silently diverge from the real typography. The
  // mount effect below races `document.fonts.ready` against a 5s timeout
  // and flips this true in either case. Render effect and exportPNG both
  // gate on it; Export button disables until true.
  const [fontsReady, setFontsReady] = useState<boolean>(false);

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
  // Autosave UI status (Stage 4 Task 2). Local state — not reducer — because
  // it is ephemeral, per-session, and has no place in undo history or
  // persistence. `saveStatus` plus `dirty` fully describes the TopBar
  // indicator.
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  // Debounce timer for autosave. Reset on every mutating doc change; cleared
  // on Ctrl+S, unmount, and when the effect finds nothing to save.
  const autosaveTimerRef = useRef<number | null>(null);
  // Retry orchestration (Stage 4 Task 2). `retryAttemptRef` is 0-indexed
  // into RETRY_DELAYS_MS; at length == RETRY_DELAYS_MS.length the budget
  // is exhausted. `retryCountdownMs` drives the banner countdown text
  // and is the only piece of retry state that needs to render.
  //
  // `saveFailureGen` is a monotonic counter incremented on every
  // SAVE_FAILED dispatch. The retry effect depends on it so successive
  // failures with an identical error message still re-trigger the
  // effect (React dep comparison uses Object.is; the counter guarantees
  // a changed dep on every failure).
  const retryAttemptRef = useRef<number>(0);
  const retryTimerRef = useRef<number | null>(null);
  const retryCountdownIntervalRef = useRef<number | null>(null);
  const [retryCountdownMs, setRetryCountdownMs] = useState<number | null>(null);
  const [saveFailureGen, setSaveFailureGen] = useState<number>(0);
  // Auto-retry eligibility for the current saveError.
  // - true  (default): error is transient (network, 5xx) → retry effect schedules backoff.
  // - false: error is terminal (404 or other non-recoverable) → retry effect
  //   skips scheduling; banner still shows with manual "Retry now" button.
  //
  // Reset to true on:
  //   - any new user edit (edit-reset effect)
  //   - manual "Retry now" click
  //   - successful save (implicit — saveError clears, effect resets)
  const canAutoRetryRef = useRef<boolean>(true);
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
    // Stage 4 Task 3: skip rendering until fonts are loaded. When
    // fontsReady flips true this callback re-memoizes (new dep value),
    // the render-trigger effect re-runs, and the first real paint
    // happens with correct typography instead of system fallbacks.
    // Leave hitAreasRef untouched on this path — it is initially `[]`
    // and handlers remain consistent until the first real render.
    if (!fontsReady) return;
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
    // Clamp each hitArea to its owning section rect. Block renderers may
    // return a hitArea whose height exceeds the visible section (copy-fit
    // overflow); canvas rendering clips draws to section bounds but raw
    // hit areas don't, so uncovered pixels in an adjacent section could
    // otherwise steal selection from the overflowing block.
    hitAreasRef.current = results.map(r => ({
      blockId: r.blockId,
      hitArea: clampRectToSection(r.result.hitArea, r.sectionRect),
    }));
  }, [doc, pal, sz, fontsReady]);
  useEffect(() => { render(); }, [render]);

  // Mount-time font-load gate (Stage 4 Task 3). Races `document.fonts.ready`
  // against a 5s timeout; flips `fontsReady` true on either outcome. The
  // promise is idempotent and cached by the browser, so re-running this
  // on hot reloads or remounts is safe but unnecessary — hence the
  // empty dependency array. The `cancelled` flag prevents a late-resolving
  // race from calling setState on an unmounted component.
  useEffect(() => {
    let cancelled = false;

    if (typeof document === 'undefined' || !document.fonts || !document.fonts.ready) {
      if (process.env.NODE_ENV !== 'production') {
        console.warn(
          '[InfographicEditor] document.fonts API unavailable — rendering with fallback fonts',
        );
      }
      setFontsReady(true);
      return;
    }

    const readyPromise = document.fonts.ready.then(() => 'ready' as const);
    const timeoutPromise = new Promise<'timeout'>((resolve) => {
      window.setTimeout(() => resolve('timeout'), FONTS_TIMEOUT_MS);
    });

    void Promise.race([readyPromise, timeoutPromise]).then((outcome) => {
      if (cancelled) return;
      if (outcome === 'timeout' && process.env.NODE_ENV !== 'production') {
        console.warn(
          `[InfographicEditor] document.fonts.ready timed out after ${FONTS_TIMEOUT_MS}ms — rendering with fallback fonts`,
        );
      }
      setFontsReady(true);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  // Overlay render — hover + selection outlines on a separate canvas.
  // Ordered AFTER the content-render effect so `hitAreasRef.current` is
  // up to date when this runs in the same commit cycle.
  //
  // `doc` and `pal` appear in the dependency array even though
  // renderOverlay does not read them directly. They are proxies for
  // "the content render just ran and hitAreasRef.current is now up to
  // date". Without them, a content-only change (e.g. editing a block's
  // text) would not trigger an overlay redraw even though the new hit
  // areas are stored in the ref — the selection/hover outlines would
  // continue drawing at the previous block positions until the next
  // selection/hover change.
  //
  // Do not refactor to read hitAreasRef as a state value — that would
  // churn undo history and double-render. The ref-as-derived-data
  // pattern is the intentional tradeoff.
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

  // Persistence via the admin proxy. When `publicationId` is set, PATCH
  // the document. Without a publicationId the save is a no-op — the
  // legacy JSON download was removed in Stage 4 Task 0 (see
  // docs/modules/editor.md).
  //
  // Snapshot-based save (B2): capture the doc reference at save start and
  // dispatch SAVED_IF_MATCHES with it. The reducer only clears `dirty`
  // if the current doc is still the same reference — i.e. the user did
  // not edit during the in-flight PATCH. If they did, the new edits
  // never reached the backend, so keeping `dirty: true` is correct.
  //
  // Error routing (B4): save failures land on `state.saveError` via
  // SAVE_FAILED, distinct from the import-error channel. NotificationBanner
  // priority: saveError > importError > _lastRejection > warnings.
  //
  // Status transitions (Stage 4 Task 2) happen here at the call site, not
  // inside the reducer: `saving` before PATCH, `idle` on success, `error`
  // on failure. The `'pending'` → `'saving'` transition is owned by the
  // debounce effect, not this function, because `'pending'` represents a
  // scheduled timer that this function never sees.
  const performSave = useCallback(() => {
    if (!dirty || !publicationId || savingRef.current) return;

    setSaveStatus('saving');
    const snapshotDoc = doc;
    savingRef.current = true;

    const payload = buildUpdatePayload(snapshotDoc);
    updateAdminPublication(publicationId, payload)
      .then(() => {
        dispatch({ type: "SAVED_IF_MATCHES", snapshotDoc });
        // If the reducer kept dirty=true (user edited mid-flight), the
        // debounce effect will re-arm `'pending'` on its next run — so
        // dropping to `'idle'` here is safe.
        setSaveStatus('idle');
      })
      .catch((err: unknown) => {
        if (err instanceof AdminPublicationNotFoundError) {
          // Terminal condition. Do NOT auto-retry — the resource does not
          // exist on the server, and repeat PATCHes will 404 identically.
          // Manual "Retry now" is still available (the user may have created
          // the publication in another tab); it resets canAutoRetryRef.
          canAutoRetryRef.current = false;
          dispatch({
            type: "SAVE_FAILED",
            error: 'Publication not found — reload the page',
          });
          // IMPORTANT: do NOT increment saveFailureGen here. The retry effect
          // watches [state.saveError, saveFailureGen]; leaving gen unchanged
          // still fires the effect (because saveError transitions null→string),
          // but the canAutoRetryRef guard below makes it a no-op schedule.
          setSaveStatus('error');
          return;
        }

        // Transient / unknown failure — retry with backoff.
        canAutoRetryRef.current = true;
        const msg = err instanceof Error ? err.message : String(err);
        dispatch({ type: "SAVE_FAILED", error: msg });
        // Bump the failure generation so the retry effect re-runs even
        // when the error string is identical to a previous attempt.
        setSaveFailureGen((n) => n + 1);
        setSaveStatus('error');
      })
      .finally(() => {
        savingRef.current = false;
      });
  }, [dirty, doc, publicationId]);

  // Debounced autosave (Stage 4 Task 2). Every mutating reducer action
  // produces a new `state.doc` reference; navigational actions (SELECT,
  // SET_MODE, save-channel bookkeeping) preserve identity. Watching `doc`
  // here is therefore a clean "did content change" signal, no new reducer
  // fields required.
  useEffect(() => {
    if (autosaveTimerRef.current !== null) {
      window.clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }

    // During active saveError, the retry effect is the sole save
    // orchestrator. A user edit resets retry state (via the edit-reset
    // effect), and the retry effect then schedules the next attempt using
    // RETRY_DELAYS_MS[0] = 2000ms — functionally identical to a debounce
    // window. Having both effects schedule would create two timers racing
    // to call performSave, the second no-op'ing against savingRef but
    // adding noise to countdown semantics.
    if (state.saveError) {
      return;
    }

    if (!dirty || !publicationId) {
      // Either nothing to save or no backend target. Drop a stale
      // `pending`/`saving` status back to `idle`. Functional update
      // avoids adding `saveStatus` to deps (which would cause a
      // re-schedule storm on every status transition).
      setSaveStatus((prev) => (prev === 'pending' || prev === 'saving' ? 'idle' : prev));
      return;
    }

    // Only promote `idle` → `pending`. Don't clobber `saving` (a PATCH
    // is in flight) or `error` (retry orchestration is active).
    setSaveStatus((prev) => (prev === 'idle' ? 'pending' : prev));

    // Re-arm pattern (B4): when the timer fires while a previous PATCH
    // is still in flight, performSave would no-op against savingRef and
    // edits would remain unsaved until the next mutating action or Ctrl+S.
    // Instead, detect savingRef and schedule one more debounce cycle so
    // the latest doc gets saved once savingRef clears. Bounded delay
    // (AUTOSAVE_DEBOUNCE_MS per iteration), not a tight loop.
    const scheduleAutosave = () => {
      autosaveTimerRef.current = window.setTimeout(() => {
        autosaveTimerRef.current = null;
        if (savingRef.current) {
          scheduleAutosave();
          return;
        }
        performSave();
      }, AUTOSAVE_DEBOUNCE_MS);
    };
    scheduleAutosave();

    return () => {
      if (autosaveTimerRef.current !== null) {
        window.clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [doc, dirty, publicationId, performSave, state.saveError]);

  // A new user edit while in error state deserves a fresh attempt cycle.
  // Reset the attempt counter so the retry orchestration effect re-enters
  // at delay index 0. We intentionally do NOT depend on `state.saveError`
  // here — including it would reset attempts on every SAVE_FAILED
  // dispatch, defeating the exponential-backoff progression.
  //
  // Declared BEFORE the retry effect so the reset lands before the retry
  // effect body reads `retryAttemptRef`. React runs useEffect bodies in
  // declaration order on each commit; swapping these two effects would
  // leave the retry effect reading a stale (pre-edit) attempt count and
  // scheduling at the old delay index.
  useEffect(() => {
    if (state.saveError) {
      retryAttemptRef.current = 0;
      canAutoRetryRef.current = true;
    }
    // Intentional: react only to doc changes, not to saveError flipping.
    // Including state.saveError would reset attempts on every SAVE_FAILED
    // dispatch, defeating exponential-backoff progression.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc]);

  // Retry orchestration (Stage 4 Task 2). Watches `state.saveError`;
  // schedules an exponential-backoff auto-retry (2s → 4s → 8s → 16s)
  // whenever an error is active and the attempt budget is not exhausted.
  // Driven by an effect, not by performSave's .catch, so the save
  // function stays pure and reusable from both debounce and manual paths.
  useEffect(() => {
    // Rebuild every run: always clear in-flight timers up front.
    if (retryTimerRef.current !== null) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (retryCountdownIntervalRef.current !== null) {
      window.clearInterval(retryCountdownIntervalRef.current);
      retryCountdownIntervalRef.current = null;
    }

    if (!state.saveError) {
      // Saved successfully (SAVED_IF_MATCHES cleared saveError) or user
      // dismissed. Reset the retry budget.
      retryAttemptRef.current = 0;
      setRetryCountdownMs(null);
      return;
    }

    // Terminal error — no auto-retry. Banner shows with manual Retry button.
    // Do not touch retryAttemptRef here; a user edit or manual Retry
    // will reset it independently.
    if (!canAutoRetryRef.current) {
      setRetryCountdownMs(null);
      return;
    }

    const attempt = retryAttemptRef.current;
    if (attempt >= RETRY_DELAYS_MS.length) {
      // Budget exhausted. Banner persists with manual Retry button.
      setRetryCountdownMs(null);
      return;
    }

    const delay = RETRY_DELAYS_MS[attempt];
    setRetryCountdownMs(delay);

    const tickMs = 250;
    retryCountdownIntervalRef.current = window.setInterval(() => {
      setRetryCountdownMs((prev) => {
        if (prev === null) return null;
        const next = prev - tickMs;
        return next > 0 ? next : 0;
      });
    }, tickMs);

    retryTimerRef.current = window.setTimeout(() => {
      retryTimerRef.current = null;
      if (retryCountdownIntervalRef.current !== null) {
        window.clearInterval(retryCountdownIntervalRef.current);
        retryCountdownIntervalRef.current = null;
      }
      retryAttemptRef.current = attempt + 1;
      setRetryCountdownMs(null);
      performSave();
    }, delay);

    return () => {
      if (retryTimerRef.current !== null) {
        window.clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
      if (retryCountdownIntervalRef.current !== null) {
        window.clearInterval(retryCountdownIntervalRef.current);
        retryCountdownIntervalRef.current = null;
      }
    };
  }, [state.saveError, saveFailureGen, performSave]);

  // Manual "Retry now" from the NotificationBanner. Cancels any scheduled
  // retry + countdown, resets the attempt budget, and fires the save
  // immediately. On failure, the retry effect will re-enter at delay 0.
  const handleManualRetry = useCallback(() => {
    // User override: explicit "Retry now" resets both the attempt counter
    // and the terminal-error flag. If the next attempt fails terminally
    // again, canAutoRetryRef flips back to false inside performSave.catch.
    retryAttemptRef.current = 0;
    canAutoRetryRef.current = true;
    if (retryTimerRef.current !== null) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (retryCountdownIntervalRef.current !== null) {
      window.clearInterval(retryCountdownIntervalRef.current);
      retryCountdownIntervalRef.current = null;
    }
    setRetryCountdownMs(null);
    performSave();
  }, [performSave]);

  // beforeunload guard (Stage 4 Task 2). Covers the 2s debounce window
  // between an edit and the next scheduled save. Modern browsers ignore
  // custom messages; assigning returnValue is still required to trigger
  // the native prompt. Re-runs only on `dirty` flips — `savingRef` is a
  // ref and does not drive re-renders, but `dirty` is always true when
  // a save is in flight (SAVED_IF_MATCHES clears it only on success),
  // so gating on `dirty` alone is sufficient.
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      const isEditable = shouldSkipGlobalShortcut(e);

      // Inside editable fields: only Ctrl+S fires (save is always useful).
      if (isEditable) {
        if ((e.ctrlKey || e.metaKey) && key === "s") {
          e.preventDefault();
          if (autosaveTimerRef.current !== null) {
            window.clearTimeout(autosaveTimerRef.current);
            autosaveTimerRef.current = null;
          }
          performSave();
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
        if (autosaveTimerRef.current !== null) {
          window.clearTimeout(autosaveTimerRef.current);
          autosaveTimerRef.current = null;
        }
        performSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [performSave]);

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

  const exportPNG = useCallback(async () => {
    // QA gate: never produce broken output. PNG export is blocked when there
    // are validation errors; JSON export and SAVE are always allowed so users
    // can checkpoint work-in-progress.
    if (!canExp) return;
    // Stage 4 Task 3: button is disabled while !fontsReady, so this
    // early-return is belt-and-suspenders for the pathological case
    // (devtools prop override, stale memoization).
    if (!fontsReady) return;

    // Defensive await: idempotent after first resolution. Protects against
    // a race where fontsReady flipped true on the timeout path but the
    // real fonts finished loading just after — awaiting here guarantees
    // the export canvas sees the same font state as the preview.
    if (typeof document !== 'undefined' && document.fonts?.ready) {
      await document.fonts.ready;
    }

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
  }, [canExp, fontsReady, doc, pal, sz]);

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
        markSaved={performSave}
        exportPNG={exportPNG}
        saveStatus={saveStatus}
        fontsReady={fontsReady}
      />
      <NotificationBanner
        state={state}
        importError={importError}
        importWarnings={importWarnings}
        onClearImportError={() => setImportError(null)}
        onClearImportWarnings={() => setImportWarnings([])}
        dispatch={dispatch}
        retryCountdownMs={retryCountdownMs}
        onManualRetry={handleManualRetry}
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
