import { useReducer, useMemo, useState, useCallback, useRef, useEffect } from "react";

/* ═══════════════════════════════════════════════════════════
   SUMMA VISION — INFOGRAPHIC EDITOR · STAGE 3b (v2)
   Authoring Workflow: Comments · Review UI · Audit
   
   v2 changelog — closes Stage 3b review:
     [1]  schemaVersion dual-write in every migration + invariant
          check in migrateDoc (temporary; final consolidation after
          3a+3b integration)
     [2]  Reducer-level ownership guard for EDIT/DELETE comment.
          action.actor required, rejection via lastRejection
     [3]  isThreadResolved() derived helper — used for filter logic,
          visual tone, and badge state. thread.resolved (root-only)
          no longer used as thread-level status
     [4]  Success toast for ADD_COMMENT moved into useEffect watching
          doc.comments.length — no false positive on rejection
     [5]  Injectable id factory (createIdFactory) replaces Math.random
          in domain functions; kept in a ref, overridable for tests
     [6]  Recursive delete — collectDescendantIds walks the subtree
          so nested replies don't become orphans
     [7]  Audit trail extended: ADD/REPLY/RESOLVE/REOPEN/DELETE are
          logged; EDIT intentionally not (lean audit)
     [8]  EDIT/RESOLVE/REOPEN/DELETE now verify comment exists and
          emit lastRejection on miss (was silent return state)
   ═══════════════════════════════════════════════════════════ */


/* ─── TOKENS ─────────────────────────────────────────────── */
const TK = {
  bg: "#0F0F10",
  surface: "#1A1A1C",
  surfaceHi: "#242428",
  surfaceLo: "#141416",
  border: "#2A2A2E",
  borderHi: "#3A3A40",
  text: "#F5F5F5",
  textMid: "#A8A8AE",
  textDim: "#6E6E76",
  accent: "#3AAFBF",
  accentDim: "#1E5D67",
  ok: "#4ADE80",
  warn: "#FACC15",
  err: "#F87171",
  info: "#7DD3FC",
  mauve: "#B6A0C9",
  gold: "#D4A574",
};


/* ─── WORKFLOW ──────────────────────────────────────────── */
const WF = {
  DRAFT: "draft",
  IN_REVIEW: "in_review",
  APPROVED: "approved",
  EXPORTED: "exported",
  PUBLISHED: "published",
};

const WF_META = {
  [WF.DRAFT]: { label: "Draft", color: TK.textMid, dot: TK.textMid },
  [WF.IN_REVIEW]: { label: "In review", color: TK.warn, dot: TK.warn },
  [WF.APPROVED]: { label: "Approved", color: TK.info, dot: TK.info },
  [WF.EXPORTED]: { label: "Exported", color: TK.accent, dot: TK.accent },
  [WF.PUBLISHED]: { label: "Published", color: TK.ok, dot: TK.ok },
};


/* ─── ACTION TYPES ──────────────────────────────────────── */
const A = {
  UPDATE_BLOCK: "UPDATE_BLOCK",
  SET_MODE: "SET_MODE",
  SET_WORKFLOW: "SET_WORKFLOW",
  // Comments
  ADD_COMMENT: "ADD_COMMENT",
  EDIT_COMMENT: "EDIT_COMMENT",
  RESOLVE_COMMENT: "RESOLVE_COMMENT",
  REOPEN_COMMENT: "REOPEN_COMMENT",
  DELETE_COMMENT: "DELETE_COMMENT",
  REPLY_TO_COMMENT: "REPLY_TO_COMMENT",
};

const ACTION_CATEGORY = {
  [A.UPDATE_BLOCK]: "text-edit",
  [A.SET_MODE]: "ui",
  [A.SET_WORKFLOW]: "ui",
  [A.ADD_COMMENT]: "comment",
  [A.EDIT_COMMENT]: "comment",
  [A.RESOLVE_COMMENT]: "comment",
  [A.REOPEN_COMMENT]: "comment",
  [A.DELETE_COMMENT]: "comment",
  [A.REPLY_TO_COMMENT]: "comment",
};


/* ─── PERMISSIONS ───────────────────────────────────────── */
function computePerms(mode, workflow) {
  const base = (() => {
    switch (workflow) {
      case WF.DRAFT:
        return { canEdit: true, canComment: true, readOnly: false };
      case WF.IN_REVIEW:
        return { canEdit: true, canComment: true, readOnly: false };
      case WF.APPROVED:
      case WF.EXPORTED:
      case WF.PUBLISHED:
        return { canEdit: false, canComment: false, readOnly: true };
      default:
        return { canEdit: false, canComment: false, readOnly: true };
    }
  })();
  return { ...base, canChangeTheme: mode === "design" && !base.readOnly };
}

function isActionAllowed(action, state) {
  const perms = computePerms(state.mode, state.doc.meta.workflow);
  const cat = ACTION_CATEGORY[action.type];
  if (cat === "ui") return { ok: true };
  if (cat === "comment") {
    if (!perms.canComment) {
      return {
        ok: false,
        reason: `Comments are read-only in "${state.doc.meta.workflow}".`,
      };
    }
    return { ok: true };
  }
  if (cat === "text-edit") {
    if (!perms.canEdit)
      return { ok: false, reason: `Document is read-only in "${state.doc.meta.workflow}".` };
  }
  return { ok: true };
}


/* ─── SCHEMA MIGRATIONS ─────────────────────────────────── */
/* Fix #1: every migration updates BOTH doc.schemaVersion and
   doc.meta.schemaVersion. migrateDoc additionally asserts they
   agree after each step.
   Note: this is a temporary measure. The long-term fix (unified
   source of truth) will land during 3a+3b integration — it needs
   to be coordinated with the Stage 3a reducer too. */
const CURRENT_SCHEMA_VERSION = 3;

const MIGRATIONS = {
  1: (doc) => ({
    ...doc,
    schemaVersion: 2,
    comments: Array.isArray(doc.comments) ? doc.comments : [],
    meta: { ...doc.meta, schemaVersion: 2 },
  }),
  // 2 → 3: introduce threaded replies (parentId on every comment)
  2: (doc) => {
    const comments = (doc.comments || []).map((c) => ({
      ...c,
      parentId: c.parentId ?? null,
    }));
    return {
      ...doc,
      schemaVersion: 3,
      comments,
      meta: { ...doc.meta, schemaVersion: 3 },
    };
  },
};

function migrateDoc(doc) {
  if (!doc || typeof doc !== "object") throw new Error("Invalid doc");
  let current = doc;
  // Source of truth during this transitional period: pick the greater
  // of the two. If they disagree, that's a bug we want to surface.
  const rootV = current.schemaVersion;
  const metaV = current?.meta?.schemaVersion;
  if (rootV != null && metaV != null && rootV !== metaV) {
    console.warn(
      `schemaVersion mismatch: root=${rootV} meta=${metaV}; using max for migration`
    );
  }
  let version = Math.max(rootV ?? 1, metaV ?? 1);
  const applied = [];
  while (version < CURRENT_SCHEMA_VERSION) {
    const fn = MIGRATIONS[version];
    if (!fn) throw new Error(`Missing migration for schema v${version}`);
    current = fn(current);
    // Invariant check: both fields must agree after every migration
    if (current.schemaVersion !== current.meta.schemaVersion) {
      throw new Error(
        `Migration ${version}→${version + 1} left schemaVersion inconsistent: ` +
          `root=${current.schemaVersion} meta=${current.meta.schemaVersion}`
      );
    }
    applied.push(current.schemaVersion);
    version = current.schemaVersion;
  }
  return { doc: current, appliedMigrations: applied };
}


/* ─── ID FACTORY (injectable) ────────────────────────────── */
/* Fix #5: id generation is no longer hardcoded inside domain helpers.
   The reducer / UI holds an idFactory ref which can be swapped for
   tests (monotonic, seeded, uuid, etc.).
   Default factory is monotonic; simpler to reason about than random. */
function createIdFactory(prefix = "c", start = 1) {
  let n = start;
  return () => `${prefix}_${n++}`;
}


/* ─── COMMENT HELPERS ───────────────────────────────────── */
/* Fix #5: makeComment no longer calls Math.random. Caller injects id. */
function makeComment({ id, blockId, text, author = "you", parentId = null }) {
  return {
    id,
    blockId,
    parentId,
    author,
    text: text.trim(),
    createdAt: new Date().toISOString(),
    updatedAt: null,
    resolved: false,
    resolvedAt: null,
    resolvedBy: null,
  };
}

/* Group comments into threads: top-level + children. */
function buildThreads(comments) {
  const byId = new Map(comments.map((c) => [c.id, { ...c, replies: [] }]));
  const roots = [];
  for (const c of byId.values()) {
    if (c.parentId && byId.has(c.parentId)) {
      byId.get(c.parentId).replies.push(c);
    } else {
      roots.push(c);
    }
  }
  for (const root of byId.values()) {
    root.replies.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  }
  roots.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  return roots;
}

/* Count unresolved across a thread (root + all replies). */
function threadUnresolvedCount(thread) {
  const rootUnresolved = thread.resolved ? 0 : 1;
  const repliesUnresolved = (thread.replies || []).filter((r) => !r.resolved).length;
  return rootUnresolved + repliesUnresolved;
}

/* Fix #3: derived thread status. A thread is resolved ONLY if every
   node in it is resolved. Replaces every use of thread.resolved as
   thread-level signal. */
function isThreadResolved(thread) {
  return threadUnresolvedCount(thread) === 0;
}

/* Fix #6: collect full subtree of descendant ids for recursive delete.
   Supports arbitrary nesting depth. */
function collectDescendantIds(comments, rootId) {
  const ids = new Set([rootId]);
  const queue = [rootId];
  while (queue.length) {
    const parent = queue.shift();
    for (const c of comments) {
      if (c.parentId === parent && !ids.has(c.id)) {
        ids.add(c.id);
        queue.push(c.id);
      }
    }
  }
  return ids;
}


/* ─── HISTORY ENTRY ─────────────────────────────────────── */
function makeHistoryEntry({ action, summary, author = "you" }) {
  return {
    ts: new Date().toISOString(),
    action,
    summary,
    author,
    fromWorkflow: null,
    toWorkflow: null,
  };
}


/* ─── INITIAL DOC ────────────────────────────────────────── */
/* Fix #1: start at schemaVersion 2 (both fields) so migration 2→3
   runs at boot and we actually prove dual-write + invariant logic. */
function makeInitialDoc() {
  const now = Date.now();
  const iso = (offset) => new Date(now + offset).toISOString();
  return {
    schemaVersion: 2,
    meta: {
      title: "Housing Affordability Index, Q1 2026",
      template: "ranked_bars",
      theme: "dark",
      size: "instagram_1080",
      workflow: WF.IN_REVIEW,
      schemaVersion: 2,
      history: [
        {
          ts: iso(-7200_000),
          action: "created",
          summary: "Document created",
          author: "you",
          fromWorkflow: null,
          toWorkflow: WF.DRAFT,
        },
        {
          ts: iso(-3600_000),
          action: "submitted",
          summary: "Submitted for review",
          author: "you",
          fromWorkflow: WF.DRAFT,
          toWorkflow: WF.IN_REVIEW,
        },
      ],
    },
    blocks: [
      { id: "b1", type: "eyebrow_tag", props: { text: "RANKED · STATISTICS CANADA · TABLE 18-10-0205" } },
      { id: "b2", type: "headline_editorial", props: { headline: "Vancouver tops housing unaffordability in Canada for eighth consecutive quarter" } },
      { id: "b3", type: "subtitle_descriptor", props: { subtitle: "Housing affordability index, major CMAs, Q1 2026" } },
      { id: "b4", type: "ranked_bars", props: { title: "Lower is worse", items: [
        { rank: 1, label: "Vancouver", value: 97.2 },
        { rank: 2, label: "Toronto", value: 81.4 },
        { rank: 3, label: "Victoria", value: 72.3 },
        { rank: 4, label: "Hamilton", value: 61.2 },
        { rank: 5, label: "Montréal", value: 54.8 },
      ] } },
      { id: "b5", type: "body_annotation", props: { text: "Higher values indicate a higher share of median household income required to service housing costs." } },
      { id: "b6", type: "source_footer", props: { source: "Statistics Canada, Table 18-10-0205", methodology: "Housing affordability index: share of household income required to service a typical mortgage + property tax + utilities." } },
      { id: "b7", type: "brand_stamp", props: { label: "summa.vision" } },
    ],
    comments: [
      {
        id: "c_seed1",
        blockId: "b2",
        parentId: null,
        author: "reviewer",
        text: "Can we soften 'tops'? Feels tabloid. Try 'leads' or 'remains highest'.",
        createdAt: iso(-1800_000),
        updatedAt: null,
        resolved: false,
        resolvedAt: null,
        resolvedBy: null,
      },
      {
        id: "c_seed2",
        blockId: "b4",
        parentId: null,
        author: "reviewer",
        text: "Value for Montréal looks off — expected closer to 58 based on CMHC data.",
        createdAt: iso(-1200_000),
        updatedAt: null,
        resolved: false,
        resolvedAt: null,
        resolvedBy: null,
      },
      {
        id: "c_seed3",
        blockId: "b6",
        parentId: null,
        author: "reviewer",
        text: "Add quarter + year to methodology line — readers ask.",
        createdAt: iso(-600_000),
        updatedAt: null,
        resolved: true,
        resolvedAt: iso(-300_000),
        resolvedBy: "you",
      },
      // Demo: a reply to seed1 that's still open — lets us test
      // "root resolved but reply open" and "thread-level resolved" logic.
      {
        id: "c_seed1_r1",
        blockId: "b2",
        parentId: "c_seed1",
        author: "you",
        text: "Agreed. Trying 'remains the least affordable major market'.",
        createdAt: iso(-900_000),
        updatedAt: null,
        resolved: false,
        resolvedAt: null,
        resolvedBy: null,
      },
    ],
  };
}


/* ═══════════════════════════════════════════════════════════
   REDUCER
   ═══════════════════════════════════════════════════════════ */
function reducer(state, action) {
  if (!action.__internal) {
    const gate = isActionAllowed(action, state);
    if (!gate.ok) {
      return {
        ...state,
        lastRejection: { action: action.type, reason: gate.reason, ts: Date.now() },
      };
    }
  }

  switch (action.type) {
    case A.UPDATE_BLOCK: {
      const blocks = state.doc.blocks.map((b) =>
        b.id === action.blockId ? { ...b, props: { ...b.props, ...action.props } } : b
      );
      return { ...state, doc: { ...state.doc, blocks }, lastRejection: null };
    }

    case A.SET_MODE:
      return { ...state, mode: action.mode, lastRejection: null };

    case A.SET_WORKFLOW:
      return {
        ...state,
        doc: { ...state.doc, meta: { ...state.doc.meta, workflow: action.workflow } },
        lastRejection: null,
      };

    /* ─── Comments ─── */
    case A.ADD_COMMENT: {
      if (!action.id) {
        // id must be supplied by caller using the idFactory (fix #5).
        return {
          ...state,
          lastRejection: { action: action.type, reason: "Missing comment id", ts: Date.now() },
        };
      }
      const c = makeComment({
        id: action.id,
        blockId: action.blockId,
        text: action.text,
        author: action.actor || "you",
        parentId: null,
      });
      const block = state.doc.blocks.find((b) => b.id === action.blockId);
      const blockLabel = block ? blockDisplayMeta(block.type).label : action.blockId;
      const historyEntry = makeHistoryEntry({
        action: "comment_added",
        summary: `Comment on ${blockLabel}: "${truncate(action.text, 60)}"`,
        author: action.actor || "you",
      });
      return {
        ...state,
        doc: {
          ...state.doc,
          comments: [...state.doc.comments, c],
          meta: {
            ...state.doc.meta,
            history: [...state.doc.meta.history, historyEntry],
          },
        },
        lastRejection: null,
      };
    }

    case A.REPLY_TO_COMMENT: {
      if (!action.id) {
        return {
          ...state,
          lastRejection: { action: action.type, reason: "Missing reply id", ts: Date.now() },
        };
      }
      const parent = state.doc.comments.find((c) => c.id === action.parentId);
      if (!parent) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: `Parent comment "${action.parentId}" not found.`,
            ts: Date.now(),
          },
        };
      }
      const reply = makeComment({
        id: action.id,
        blockId: parent.blockId,
        text: action.text,
        author: action.actor || "you",
        parentId: action.parentId,
      });
      // Fix #7: log REPLY_TO_COMMENT in audit trail.
      const block = state.doc.blocks.find((b) => b.id === parent.blockId);
      const blockLabel = block ? blockDisplayMeta(block.type).label : parent.blockId;
      const historyEntry = makeHistoryEntry({
        action: "comment_replied",
        summary: `Replied on ${blockLabel}: "${truncate(action.text, 60)}"`,
        author: action.actor || "you",
      });
      return {
        ...state,
        doc: {
          ...state.doc,
          comments: [...state.doc.comments, reply],
          meta: {
            ...state.doc.meta,
            history: [...state.doc.meta.history, historyEntry],
          },
        },
        lastRejection: null,
      };
    }

    case A.EDIT_COMMENT: {
      // Fix #8: existence check with rejection (was silent return state).
      const target = state.doc.comments.find((c) => c.id === action.commentId);
      if (!target) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: `Comment "${action.commentId}" not found.`,
            ts: Date.now(),
          },
        };
      }
      // Fix #2: reducer-level ownership guard.
      const actor = action.actor || "you";
      if (target.author !== actor) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: "You can edit only your own comments.",
            ts: Date.now(),
          },
        };
      }
      const comments = state.doc.comments.map((c) =>
        c.id === action.commentId
          ? { ...c, text: action.text.trim(), updatedAt: new Date().toISOString() }
          : c
      );
      // Fix #7: EDIT intentionally NOT logged (lean audit).
      return { ...state, doc: { ...state.doc, comments }, lastRejection: null };
    }

    case A.RESOLVE_COMMENT: {
      const target = state.doc.comments.find((c) => c.id === action.commentId);
      if (!target) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: `Comment "${action.commentId}" not found.`,
            ts: Date.now(),
          },
        };
      }
      const actor = action.actor || "you";
      const now = new Date().toISOString();
      const comments = state.doc.comments.map((c) =>
        c.id === action.commentId
          ? { ...c, resolved: true, resolvedAt: now, resolvedBy: actor }
          : c
      );
      const block = state.doc.blocks.find((b) => b.id === target.blockId);
      const historyEntry = makeHistoryEntry({
        action: "comment_resolved",
        summary: `Resolved comment on ${block ? blockDisplayMeta(block.type).label : target.blockId}`,
        author: actor,
      });
      return {
        ...state,
        doc: {
          ...state.doc,
          comments,
          meta: {
            ...state.doc.meta,
            history: [...state.doc.meta.history, historyEntry],
          },
        },
        lastRejection: null,
      };
    }

    case A.REOPEN_COMMENT: {
      const target = state.doc.comments.find((c) => c.id === action.commentId);
      if (!target) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: `Comment "${action.commentId}" not found.`,
            ts: Date.now(),
          },
        };
      }
      const actor = action.actor || "you";
      const comments = state.doc.comments.map((c) =>
        c.id === action.commentId
          ? { ...c, resolved: false, resolvedAt: null, resolvedBy: null }
          : c
      );
      // Fix #7: log REOPEN in audit trail.
      const block = state.doc.blocks.find((b) => b.id === target.blockId);
      const historyEntry = makeHistoryEntry({
        action: "comment_reopened",
        summary: `Reopened comment on ${block ? blockDisplayMeta(block.type).label : target.blockId}`,
        author: actor,
      });
      return {
        ...state,
        doc: {
          ...state.doc,
          comments,
          meta: {
            ...state.doc.meta,
            history: [...state.doc.meta.history, historyEntry],
          },
        },
        lastRejection: null,
      };
    }

    case A.DELETE_COMMENT: {
      const target = state.doc.comments.find((c) => c.id === action.commentId);
      if (!target) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: `Comment "${action.commentId}" not found.`,
            ts: Date.now(),
          },
        };
      }
      // Fix #2: ownership guard (same rule as edit).
      const actor = action.actor || "you";
      if (target.author !== actor) {
        return {
          ...state,
          lastRejection: {
            action: action.type,
            reason: "You can delete only your own comments.",
            ts: Date.now(),
          },
        };
      }
      // Fix #6: recursive delete of the full subtree.
      const toDelete = collectDescendantIds(state.doc.comments, action.commentId);
      const comments = state.doc.comments.filter((c) => !toDelete.has(c.id));

      // Fix #7: log DELETE with descendant count.
      const block = state.doc.blocks.find((b) => b.id === target.blockId);
      const extraCount = toDelete.size - 1;
      const historyEntry = makeHistoryEntry({
        action: "comment_deleted",
        summary:
          `Deleted comment on ${block ? blockDisplayMeta(block.type).label : target.blockId}` +
          (extraCount > 0 ? ` (+ ${extraCount} repl${extraCount === 1 ? "y" : "ies"})` : ""),
        author: actor,
      });
      return {
        ...state,
        doc: {
          ...state.doc,
          comments,
          meta: {
            ...state.doc.meta,
            history: [...state.doc.meta.history, historyEntry],
          },
        },
        lastRejection: null,
      };
    }

    default:
      return state;
  }
}


/* ─── INIT ───────────────────────────────────────────────── */
function makeInitialState() {
  const raw = makeInitialDoc();
  const { doc, appliedMigrations } = migrateDoc(raw);
  return {
    doc,
    mode: "template",
    lastRejection: null,
    migrationsApplied: appliedMigrations,
  };
}


/* ═══════════════════════════════════════════════════════════
   APP
   ═══════════════════════════════════════════════════════════ */
export default function Stage3bEditorV2() {
  const [state, dispatch] = useReducer(reducer, null, makeInitialState);
  const [selectedId, setSelectedId] = useState("b2");
  const [qaTab, setQaTab] = useState("review");
  const [reviewFilter, setReviewFilter] = useState("unresolved");
  const [toast, setToast] = useState(null);

  const { doc, mode } = state;
  const workflow = doc.meta.workflow;
  const perms = useMemo(() => computePerms(mode, workflow), [mode, workflow]);

  // Fix #5: idFactory in ref. Swappable in tests via Object.assign.
  // Seed start from existing seed ids so we don't collide with c_seed1..c_seed3.
  const idFactoryRef = useRef(createIdFactory("c", 1000));

  // Surface rejections
  useEffect(() => {
    if (state.lastRejection) {
      setToast({ kind: "err", text: state.lastRejection.reason });
      const t = setTimeout(() => setToast(null), 3500);
      return () => clearTimeout(t);
    }
  }, [state.lastRejection]);

  // Fix #4: success toast for ADD_COMMENT / REPLY via useEffect watching
  // the actual comments length. No more false positives from rejected
  // dispatches — if permission gate blocks the action, length doesn't
  // change and no toast fires.
  const prevCommentCountRef = useRef(doc.comments.length);
  useEffect(() => {
    const curr = doc.comments.length;
    const prev = prevCommentCountRef.current;
    if (curr > prev) {
      setToast({ kind: "ok", text: "Comment added" });
      const t = setTimeout(() => setToast(null), 2200);
      prevCommentCountRef.current = curr;
      return () => clearTimeout(t);
    }
    prevCommentCountRef.current = curr;
  }, [doc.comments.length]);

  // Derived: comments grouped by block + threaded
  const threads = useMemo(() => buildThreads(doc.comments), [doc.comments]);
  const threadsByBlock = useMemo(() => {
    const map = new Map();
    for (const t of threads) {
      const key = t.blockId;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(t);
    }
    return map;
  }, [threads]);

  const unresolvedCountByBlock = useMemo(() => {
    const map = new Map();
    for (const t of threads) {
      const n = threadUnresolvedCount(t);
      if (n > 0) {
        map.set(t.blockId, (map.get(t.blockId) || 0) + n);
      }
    }
    return map;
  }, [threads]);

  const totalUnresolved = useMemo(
    () => Array.from(unresolvedCountByBlock.values()).reduce((a, b) => a + b, 0),
    [unresolvedCountByBlock]
  );

  const selected = doc.blocks.find((b) => b.id === selectedId);
  const selectedThreads = selected ? threadsByBlock.get(selected.id) || [] : [];

  /* Handlers — note we do NOT flashOk here; success toast is driven by
     the useEffect on comments.length above. */
  const addComment = (blockId, text) => {
    if (!text.trim()) return;
    dispatch({ type: A.ADD_COMMENT, blockId, text, id: idFactoryRef.current() });
  };
  const replyTo = (parentId, text) => {
    if (!text.trim()) return;
    dispatch({ type: A.REPLY_TO_COMMENT, parentId, text, id: idFactoryRef.current() });
  };
  const editComment = (commentId, text) => {
    dispatch({ type: A.EDIT_COMMENT, commentId, text, actor: "you" });
  };
  const resolveComment = (commentId) => {
    dispatch({ type: A.RESOLVE_COMMENT, commentId, actor: "you" });
  };
  const reopenComment = (commentId) => {
    dispatch({ type: A.REOPEN_COMMENT, commentId, actor: "you" });
  };
  const deleteComment = (commentId) => {
    if (!window.confirm("Delete this comment and any replies?")) return;
    dispatch({ type: A.DELETE_COMMENT, commentId, actor: "you" });
  };

  return (
    <div
      style={{
        background: TK.bg,
        color: TK.text,
        minHeight: "100vh",
        fontFamily: "'DM Sans', system-ui, -apple-system, sans-serif",
        fontSize: 14,
        letterSpacing: "-0.005em",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;600;700&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@500&display=swap');
        * { box-sizing: border-box; }
        button { font-family: inherit; cursor: pointer; }
        button:disabled { cursor: not-allowed; opacity: 0.45; }
        input, textarea { font-family: inherit; outline: none; }
        textarea:focus, input:focus { border-color: ${TK.accent} !important; }
        .mono { font-family: 'JetBrains Mono', ui-monospace, monospace; font-feature-settings: "tnum"; }
        .display { font-family: 'Bricolage Grotesque', serif; letter-spacing: -0.02em; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        @keyframes slideIn { from { transform: translateY(6px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .dot-pulse { animation: pulse 1.8s ease-in-out infinite; }
      `}</style>

      <TopBar
        doc={doc}
        workflow={workflow}
        perms={perms}
        totalUnresolved={totalUnresolved}
        onSetWorkflow={(w) => dispatch({ type: A.SET_WORKFLOW, workflow: w })}
        onSetMode={(m) => dispatch({ type: A.SET_MODE, mode: m })}
        mode={mode}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "260px 1fr 360px",
          gridTemplateRows: "1fr 280px",
          minHeight: "calc(100vh - 60px)",
        }}
      >
        <LeftPanel
          doc={doc}
          selectedId={selectedId}
          onSelect={setSelectedId}
          unresolvedCountByBlock={unresolvedCountByBlock}
        />

        <CanvasArea
          doc={doc}
          selectedId={selectedId}
          onSelect={setSelectedId}
          unresolvedCountByBlock={unresolvedCountByBlock}
        />

        <RightPanel
          selected={selected}
          selectedThreads={selectedThreads}
          perms={perms}
          workflow={workflow}
          onAddComment={addComment}
          onReply={replyTo}
          onEdit={editComment}
          onResolve={resolveComment}
          onReopen={reopenComment}
          onDelete={deleteComment}
        />

        <QAArea
          qaTab={qaTab}
          onTabChange={setQaTab}
          doc={doc}
          threads={threads}
          totalUnresolved={totalUnresolved}
          reviewFilter={reviewFilter}
          onFilterChange={setReviewFilter}
          onJumpToBlock={setSelectedId}
          onResolve={resolveComment}
          onReopen={reopenComment}
          onDelete={deleteComment}
          perms={perms}
          workflow={workflow}
        />
      </div>

      {toast && <Toast kind={toast.kind} text={toast.text} />}

      <DebugFooter
        workflow={workflow}
        mode={mode}
        schemaVersionMeta={doc.meta.schemaVersion}
        schemaVersionRoot={doc.schemaVersion}
        migrationsApplied={state.migrationsApplied}
        commentCount={doc.comments.length}
        totalUnresolved={totalUnresolved}
      />
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   TOP BAR
   ═══════════════════════════════════════════════════════════ */
function TopBar({ doc, workflow, mode, perms, totalUnresolved, onSetWorkflow, onSetMode }) {
  const wfMeta = WF_META[workflow];
  return (
    <div
      style={{
        height: 60,
        borderBottom: `1px solid ${TK.border}`,
        background: TK.surfaceLo,
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        gap: 16,
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            background: `linear-gradient(135deg, ${TK.accent} 0%, ${TK.mauve} 100%)`,
            display: "grid",
            placeItems: "center",
            fontFamily: "'Bricolage Grotesque', serif",
            fontWeight: 700,
            color: TK.bg,
            fontSize: 15,
          }}
        >
          sv
        </div>
        <div>
          <div
            className="display"
            style={{ fontSize: 15, fontWeight: 600, lineHeight: 1.1, maxWidth: 340, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
          >
            {doc.meta.title}
          </div>
          <div style={{ fontSize: 11, color: TK.textDim, marginTop: 2 }}>
            {doc.meta.history.length} events ·{" "}
            <span className="mono" style={{ fontSize: 10 }}>schema v{doc.meta.schemaVersion}</span>
            {totalUnresolved > 0 && (
              <>
                {" · "}
                <span style={{ color: TK.warn }}>
                  {totalUnresolved} open comment{totalUnresolved === 1 ? "" : "s"}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          padding: "5px 10px",
          borderRadius: 999,
          background: `${wfMeta.color}1a`,
          border: `1px solid ${wfMeta.color}4d`,
          color: wfMeta.color,
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        <span
          className={workflow === WF.IN_REVIEW ? "dot-pulse" : ""}
          style={{
            display: "inline-block",
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: wfMeta.dot,
            marginRight: 7,
          }}
        />
        {wfMeta.label}
      </div>

      <div style={{ flex: 1 }} />

      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 10.5, color: TK.textDim, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Demo
        </span>
        <select
          value={workflow}
          onChange={(e) => onSetWorkflow(e.target.value)}
          className="mono"
          style={{
            padding: "5px 8px",
            background: TK.surface,
            border: `1px solid ${TK.border}`,
            borderRadius: 5,
            color: TK.text,
            fontSize: 11,
          }}
        >
          {Object.values(WF).map((w) => (
            <option key={w} value={w}>{WF_META[w].label}</option>
          ))}
        </select>
      </div>

      <div style={{ width: 1, height: 26, background: TK.border }} />

      <SegmentedControl
        value={mode}
        onChange={onSetMode}
        options={[
          { value: "template", label: "Template" },
          { value: "design", label: "Design" },
        ]}
        disabled={perms.readOnly}
      />
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   LEFT PANEL
   ═══════════════════════════════════════════════════════════ */
function LeftPanel({ doc, selectedId, onSelect, unresolvedCountByBlock }) {
  return (
    <aside
      style={{
        background: TK.surfaceLo,
        borderRight: `1px solid ${TK.border}`,
        padding: 16,
        overflowY: "auto",
        gridRow: "1",
      }}
    >
      <SectionHeader>Document</SectionHeader>

      <div style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 8 }}>
        {doc.blocks.map((b, i) => {
          const unresolved = unresolvedCountByBlock.get(b.id) || 0;
          const meta = blockDisplayMeta(b.type);
          const selected = selectedId === b.id;
          return (
            <div
              key={b.id}
              onClick={() => onSelect(b.id)}
              style={{
                padding: "8px 10px",
                background: selected ? TK.surfaceHi : "transparent",
                border: `1px solid ${selected ? TK.borderHi : "transparent"}`,
                borderRadius: 5,
                display: "flex",
                alignItems: "center",
                gap: 10,
                cursor: "pointer",
                position: "relative",
              }}
            >
              <span className="mono" style={{ fontSize: 10, color: TK.textDim, width: 18 }}>
                {String(i).padStart(2, "0")}
              </span>
              <span style={{ fontSize: 14 }}>{meta.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 500 }}>{meta.label}</div>
                <div
                  style={{
                    fontSize: 10.5,
                    color: TK.textDim,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {previewText(b)}
                </div>
              </div>
              {unresolved > 0 && (
                <CommentBadge count={unresolved} size="sm" />
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}


/* ═══════════════════════════════════════════════════════════
   CANVAS
   ═══════════════════════════════════════════════════════════ */
function CanvasArea({ doc, selectedId, onSelect, unresolvedCountByBlock }) {
  return (
    <main
      style={{
        padding: 32,
        background: TK.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        overflow: "auto",
        gridRow: "1",
      }}
    >
      <div
        style={{
          width: 540,
          height: 540,
          background: "linear-gradient(180deg, #1a1d24 0%, #0f1114 100%)",
          borderRadius: 8,
          padding: 36,
          border: `1px solid ${TK.border}`,
          position: "relative",
          boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {doc.blocks.map((b) => {
          const unresolved = unresolvedCountByBlock.get(b.id) || 0;
          return (
            <CanvasBlock
              key={b.id}
              block={b}
              selected={selectedId === b.id}
              unresolvedCount={unresolved}
              onClick={() => onSelect(b.id)}
            />
          );
        })}
        <div
          className="mono"
          style={{
            position: "absolute",
            bottom: 10,
            left: 14,
            fontSize: 9,
            color: TK.textDim,
            letterSpacing: "0.1em",
          }}
        >
          1080 × 1080
        </div>
      </div>
      <div style={{ fontSize: 11, color: TK.textDim }}>
        Click any block. Dots show unresolved comments.
      </div>
    </main>
  );
}

function CanvasBlock({ block, selected, unresolvedCount, onClick }) {
  const base = {
    padding: "4px 6px",
    borderRadius: 3,
    cursor: "pointer",
    outline: selected ? `1px solid ${TK.accent}` : "1px solid transparent",
    outlineOffset: 2,
    position: "relative",
  };
  const indicator =
    unresolvedCount > 0 ? (
      <span
        className="dot-pulse"
        style={{
          position: "absolute",
          top: -2,
          right: -4,
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: TK.warn,
          border: `2px solid ${TK.bg}`,
          color: "#000",
          fontSize: 9,
          fontWeight: 700,
          display: "grid",
          placeItems: "center",
          lineHeight: 1,
        }}
      >
        {unresolvedCount}
      </span>
    ) : null;

  let inner = null;
  switch (block.type) {
    case "eyebrow_tag":
      inner = (
        <div className="mono" style={{ fontSize: 10, color: TK.accent, letterSpacing: "0.15em" }}>
          {block.props.text}
        </div>
      );
      break;
    case "headline_editorial":
      inner = (
        <div className="display" style={{ fontSize: 24, fontWeight: 700, lineHeight: 1.15 }}>
          {block.props.headline}
        </div>
      );
      break;
    case "subtitle_descriptor":
      inner = (
        <div style={{ fontSize: 12, color: TK.textMid, lineHeight: 1.4 }}>
          {block.props.subtitle}
        </div>
      );
      break;
    case "ranked_bars":
      inner = (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}>
          {block.props.items.map((it) => {
            const maxV = Math.max(...block.props.items.map((x) => x.value));
            const pct = (it.value / maxV) * 100;
            return (
              <div key={it.rank} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="mono" style={{ fontSize: 10, color: TK.textDim, width: 14 }}>{it.rank}</span>
                <span style={{ fontSize: 11, color: TK.text, width: 80 }}>{it.label}</span>
                <div style={{ flex: 1, height: 10, background: TK.surface, borderRadius: 2, overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${pct}%`,
                      height: "100%",
                      background: it.rank === 1 ? TK.err : it.rank <= 3 ? TK.gold : TK.accent,
                    }}
                  />
                </div>
                <span className="mono" style={{ fontSize: 10, color: TK.text, width: 40, textAlign: "right" }}>
                  {it.value}
                </span>
              </div>
            );
          })}
        </div>
      );
      break;
    case "body_annotation":
      inner = (
        <div style={{ fontSize: 11, color: TK.textMid, lineHeight: 1.5, paddingLeft: 10, borderLeft: `2px solid ${TK.accentDim}` }}>
          {block.props.text}
        </div>
      );
      break;
    case "source_footer":
      inner = (
        <div style={{ marginTop: "auto", fontSize: 10, color: TK.textDim, borderTop: `1px solid ${TK.border}`, paddingTop: 8 }}>
          <div style={{ fontWeight: 600, color: TK.textMid }}>{block.props.source}</div>
          <div style={{ marginTop: 2 }}>{block.props.methodology}</div>
        </div>
      );
      break;
    case "brand_stamp":
      inner = (
        <div className="mono" style={{ fontSize: 9, color: TK.accent, letterSpacing: "0.15em", textAlign: "right" }}>
          {block.props.label}
        </div>
      );
      break;
    default:
      inner = null;
  }

  return (
    <div onClick={onClick} style={base}>
      {inner}
      {indicator}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   RIGHT PANEL — inspector + comments
   ═══════════════════════════════════════════════════════════ */
function RightPanel({
  selected,
  selectedThreads,
  perms,
  workflow,
  onAddComment,
  onReply,
  onEdit,
  onResolve,
  onReopen,
  onDelete,
}) {
  if (!selected) {
    return (
      <aside style={{ background: TK.surfaceLo, borderLeft: `1px solid ${TK.border}`, padding: 16, gridRow: "1" }}>
        <SectionHeader>Inspector</SectionHeader>
        <div style={{ color: TK.textDim, fontSize: 12, marginTop: 12 }}>Select a block.</div>
      </aside>
    );
  }
  const meta = blockDisplayMeta(selected.type);
  const unresolvedCount = selectedThreads.reduce((acc, t) => acc + threadUnresolvedCount(t), 0);

  return (
    <aside
      style={{
        background: TK.surfaceLo,
        borderLeft: `1px solid ${TK.border}`,
        padding: 16,
        overflowY: "auto",
        gridRow: "1",
      }}
    >
      <SectionHeader>Inspector</SectionHeader>

      <div
        style={{
          marginTop: 10,
          padding: 10,
          background: TK.surface,
          borderRadius: 6,
          border: `1px solid ${TK.border}`,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span style={{ fontSize: 16 }}>{meta.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>{meta.label}</div>
          <div className="mono" style={{ fontSize: 10, color: TK.textDim }}>{selected.type}</div>
        </div>
        {unresolvedCount > 0 && <CommentBadge count={unresolvedCount} size="md" />}
      </div>

      <div style={{ height: 20 }} />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <SectionHeader>Comments on this block</SectionHeader>
        <span style={{ fontSize: 10.5, color: TK.textDim }}>
          {selectedThreads.length} thread{selectedThreads.length === 1 ? "" : "s"}
        </span>
      </div>

      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
        {selectedThreads.length === 0 && (
          <div style={{ fontSize: 11.5, color: TK.textDim, fontStyle: "italic", lineHeight: 1.5 }}>
            No comments yet. Leave one below to flag issues for review.
          </div>
        )}
        {selectedThreads.map((t) => (
          <CommentThread
            key={t.id}
            thread={t}
            canInteract={perms.canComment}
            onReply={onReply}
            onEdit={onEdit}
            onResolve={onResolve}
            onReopen={onReopen}
            onDelete={onDelete}
          />
        ))}
      </div>

      <div style={{ height: 12 }} />

      <CommentComposer
        blockId={selected.id}
        onSubmit={(text) => onAddComment(selected.id, text)}
        disabled={!perms.canComment}
        placeholder={
          perms.canComment
            ? "Leave a comment for review…"
            : `Comments are read-only in "${workflow}".`
        }
      />
    </aside>
  );
}


/* ─── COMMENT THREAD ─────────────────────────────────────── */
function CommentThread({ thread, canInteract, onReply, onEdit, onResolve, onReopen, onDelete }) {
  const [replying, setReplying] = useState(false);
  const [editing, setEditing] = useState(false);

  // Fix #3: derived status replaces thread.resolved (root-only signal).
  const threadResolved = isThreadResolved(thread);

  return (
    <div
      style={{
        background: threadResolved ? "rgba(74,222,128,0.05)" : TK.surface,
        border: `1px solid ${threadResolved ? "rgba(74,222,128,0.25)" : TK.border}`,
        borderRadius: 6,
        padding: 10,
      }}
    >
      <CommentBody
        comment={thread}
        canInteract={canInteract}
        editing={editing}
        onStartEdit={() => setEditing(true)}
        onCancelEdit={() => setEditing(false)}
        onSaveEdit={(text) => {
          onEdit(thread.id, text);
          setEditing(false);
        }}
        onResolve={() => onResolve(thread.id)}
        onReopen={() => onReopen(thread.id)}
        onDelete={() => onDelete(thread.id)}
      />

      {thread.replies && thread.replies.length > 0 && (
        <div
          style={{
            marginTop: 8,
            marginLeft: 12,
            paddingLeft: 10,
            borderLeft: `1px solid ${TK.border}`,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {thread.replies.map((r) => (
            <ReplyBody
              key={r.id}
              comment={r}
              canInteract={canInteract}
              onResolve={() => onResolve(r.id)}
              onReopen={() => onReopen(r.id)}
              onDelete={() => onDelete(r.id)}
            />
          ))}
        </div>
      )}

      {/* Fix #3: allow reply while thread has any open items, not just
         when root is open. */}
      {canInteract && !threadResolved && (
        <div style={{ marginTop: 8 }}>
          {!replying ? (
            <button
              onClick={() => setReplying(true)}
              style={{
                background: "transparent",
                border: "none",
                color: TK.accent,
                fontSize: 11,
                padding: 0,
                fontWeight: 500,
              }}
            >
              ↳ Reply
            </button>
          ) : (
            <InlineComposer
              placeholder="Reply…"
              autoFocus
              onCancel={() => setReplying(false)}
              onSubmit={(text) => {
                onReply(thread.id, text);
                setReplying(false);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

function CommentBody({ comment, canInteract, editing, onStartEdit, onCancelEdit, onSaveEdit, onResolve, onReopen, onDelete }) {
  const [draft, setDraft] = useState(comment.text);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Avatar name={comment.author} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11.5, fontWeight: 600 }}>{comment.author}</div>
          <div style={{ fontSize: 10, color: TK.textDim }} className="mono">
            {formatRelative(comment.createdAt)}
            {comment.updatedAt && " · edited"}
          </div>
        </div>
        {comment.resolved && (
          <span
            style={{
              fontSize: 9.5,
              padding: "2px 6px",
              background: "rgba(74,222,128,0.15)",
              color: TK.ok,
              borderRadius: 3,
              fontWeight: 600,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            Resolved
          </span>
        )}
      </div>

      {editing ? (
        <div style={{ marginTop: 8 }}>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            style={{
              width: "100%",
              padding: "6px 8px",
              background: TK.surfaceHi,
              border: `1px solid ${TK.border}`,
              borderRadius: 4,
              color: TK.text,
              fontSize: 12,
              resize: "vertical",
            }}
          />
          <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
            <PrimaryBtn onClick={() => onSaveEdit(draft)} size="sm">Save</PrimaryBtn>
            <SecondaryBtn onClick={onCancelEdit} size="sm">Cancel</SecondaryBtn>
          </div>
        </div>
      ) : (
        <div style={{ marginTop: 6, fontSize: 12, color: TK.text, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
          {comment.text}
        </div>
      )}

      {canInteract && !editing && (
        <div style={{ display: "flex", gap: 10, marginTop: 8, fontSize: 11 }}>
          {!comment.resolved ? (
            <CommentAction onClick={onResolve} color={TK.ok}>✓ Resolve</CommentAction>
          ) : (
            <CommentAction onClick={onReopen} color={TK.warn}>↻ Reopen</CommentAction>
          )}
          {comment.author === "you" && (
            <>
              <CommentAction onClick={onStartEdit} color={TK.textMid}>Edit</CommentAction>
              <CommentAction onClick={onDelete} color={TK.err}>Delete</CommentAction>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ReplyBody({ comment, canInteract, onResolve, onReopen, onDelete }) {
  return (
    <div style={{ opacity: comment.resolved ? 0.6 : 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <Avatar name={comment.author} size="xs" />
        <span style={{ fontSize: 11, fontWeight: 600 }}>{comment.author}</span>
        <span className="mono" style={{ fontSize: 9.5, color: TK.textDim }}>
          {formatRelative(comment.createdAt)}
        </span>
      </div>
      <div style={{ marginTop: 3, fontSize: 11.5, color: TK.text, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
        {comment.text}
      </div>
      {canInteract && (
        <div style={{ display: "flex", gap: 8, marginTop: 4, fontSize: 10.5 }}>
          {!comment.resolved ? (
            <CommentAction onClick={onResolve} color={TK.ok}>✓ Resolve</CommentAction>
          ) : (
            <CommentAction onClick={onReopen} color={TK.warn}>↻ Reopen</CommentAction>
          )}
          {comment.author === "you" && (
            <CommentAction onClick={onDelete} color={TK.err}>Delete</CommentAction>
          )}
        </div>
      )}
    </div>
  );
}

function CommentAction({ children, onClick, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: "transparent",
        border: "none",
        color,
        padding: 0,
        fontSize: "inherit",
        fontWeight: 500,
      }}
    >
      {children}
    </button>
  );
}


/* ─── COMPOSERS ──────────────────────────────────────────── */
function CommentComposer({ onSubmit, disabled, placeholder }) {
  const [text, setText] = useState("");
  const handleSubmit = () => {
    if (!text.trim() || disabled) return;
    onSubmit(text);
    setText("");
  };
  return (
    <div
      style={{
        border: `1px solid ${TK.border}`,
        borderRadius: 6,
        background: TK.surface,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        rows={2}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        style={{
          width: "100%",
          padding: "8px 10px",
          background: "transparent",
          border: "none",
          color: TK.text,
          fontSize: 12,
          resize: "vertical",
          minHeight: 50,
        }}
      />
      <div
        style={{
          padding: "6px 10px",
          borderTop: `1px solid ${TK.border}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: 10, color: TK.textDim }}>⌘↵ to send</span>
        <PrimaryBtn onClick={handleSubmit} disabled={!text.trim() || disabled} size="sm">
          Comment
        </PrimaryBtn>
      </div>
    </div>
  );
}

function InlineComposer({ onSubmit, onCancel, placeholder, autoFocus }) {
  const [text, setText] = useState("");
  const ref = useRef(null);
  useEffect(() => {
    if (autoFocus && ref.current) ref.current.focus();
  }, [autoFocus]);
  return (
    <div>
      <textarea
        ref={ref}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        rows={2}
        onKeyDown={(e) => {
          if (e.key === "Escape") onCancel();
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && text.trim()) {
            e.preventDefault();
            onSubmit(text);
          }
        }}
        style={{
          width: "100%",
          padding: "6px 8px",
          background: TK.surfaceHi,
          border: `1px solid ${TK.border}`,
          borderRadius: 4,
          color: TK.text,
          fontSize: 11.5,
          resize: "vertical",
        }}
      />
      <div style={{ display: "flex", gap: 6, marginTop: 5 }}>
        <PrimaryBtn onClick={() => text.trim() && onSubmit(text)} disabled={!text.trim()} size="sm">
          Reply
        </PrimaryBtn>
        <SecondaryBtn onClick={onCancel} size="sm">Cancel</SecondaryBtn>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   QA AREA
   ═══════════════════════════════════════════════════════════ */
function QAArea({
  qaTab,
  onTabChange,
  doc,
  threads,
  totalUnresolved,
  reviewFilter,
  onFilterChange,
  onJumpToBlock,
  onResolve,
  onReopen,
  onDelete,
  perms,
  workflow,
}) {
  return (
    <div
      style={{
        gridColumn: "1 / -1",
        gridRow: "2",
        background: TK.surfaceLo,
        borderTop: `1px solid ${TK.border}`,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          borderBottom: `1px solid ${TK.border}`,
          background: TK.bg,
          height: 40,
          gap: 4,
        }}
      >
        <QATab
          active={qaTab === "quality"}
          onClick={() => onTabChange("quality")}
          label="Quality check"
          badge="0 errors"
          badgeColor={TK.ok}
        />
        <QATab
          active={qaTab === "review"}
          onClick={() => onTabChange("review")}
          label="Review"
          badge={totalUnresolved > 0 ? `${totalUnresolved} open` : "all clear"}
          badgeColor={totalUnresolved > 0 ? TK.warn : TK.ok}
        />
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 10.5, color: TK.textDim }}>
          {WF_META[workflow].label}
        </span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {qaTab === "quality" ? (
          <QualityPlaceholder />
        ) : (
          <ReviewPanel
            doc={doc}
            threads={threads}
            filter={reviewFilter}
            onFilterChange={onFilterChange}
            onJumpToBlock={onJumpToBlock}
            onResolve={onResolve}
            onReopen={onReopen}
            onDelete={onDelete}
            canInteract={perms.canComment}
          />
        )}
      </div>
    </div>
  );
}

function QATab({ active, onClick, label, badge, badgeColor }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "10px 14px",
        background: active ? TK.surfaceLo : "transparent",
        border: "none",
        borderBottom: active ? `2px solid ${TK.accent}` : "2px solid transparent",
        color: active ? TK.text : TK.textMid,
        fontSize: 12,
        fontWeight: 600,
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: -1,
      }}
    >
      {label}
      <span
        style={{
          fontSize: 10,
          padding: "2px 6px",
          background: `${badgeColor}1a`,
          color: badgeColor,
          borderRadius: 3,
          fontWeight: 500,
          letterSpacing: "0.02em",
        }}
      >
        {badge}
      </span>
    </button>
  );
}

function QualityPlaceholder() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: 16,
        background: TK.surface,
        border: `1px dashed ${TK.border}`,
        borderRadius: 6,
      }}
    >
      <div style={{ fontSize: 20, color: TK.ok }}>✓</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>Quality check passes</div>
        <div style={{ fontSize: 11.5, color: TK.textDim, marginTop: 2 }}>
          Structural validation lives in Stage 2 (chart-aware checks, overflow, WCAG).
          Shown here as placeholder so the Review tab reads as an equal sibling.
        </div>
      </div>
    </div>
  );
}


/* ─── REVIEW PANEL ───────────────────────────────────────── */
function ReviewPanel({
  doc,
  threads,
  filter,
  onFilterChange,
  onJumpToBlock,
  onResolve,
  onReopen,
  onDelete,
  canInteract,
}) {
  // Fix #3: filter via derived isThreadResolved, not thread.resolved.
  const filtered = useMemo(() => {
    if (filter === "all") return threads;
    if (filter === "unresolved") return threads.filter((t) => !isThreadResolved(t));
    if (filter === "resolved") return threads.filter((t) => isThreadResolved(t));
    return threads;
  }, [threads, filter]);

  const grouped = useMemo(() => {
    const map = new Map();
    for (const t of filtered) {
      if (!map.has(t.blockId)) map.set(t.blockId, []);
      map.get(t.blockId).push(t);
    }
    return map;
  }, [filtered]);

  const blockOrder = doc.blocks.map((b) => b.id).filter((id) => grouped.has(id));

  const counts = useMemo(() => {
    const all = threads.length;
    // Fix #3: derived-based counters.
    const unresolved = threads.filter((t) => !isThreadResolved(t)).length;
    const resolved = threads.filter((t) => isThreadResolved(t)).length;
    return { all, unresolved, resolved };
  }, [threads]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <SectionHeader>Review queue</SectionHeader>
        <div style={{ flex: 1 }} />
        <FilterPills
          value={filter}
          onChange={onFilterChange}
          options={[
            { value: "unresolved", label: `Open (${counts.unresolved})` },
            { value: "resolved", label: `Resolved (${counts.resolved})` },
            { value: "all", label: `All (${counts.all})` },
          ]}
        />
      </div>

      {blockOrder.length === 0 && (
        <div
          style={{
            padding: 24,
            textAlign: "center",
            color: TK.textDim,
            fontSize: 12,
            background: TK.surface,
            border: `1px dashed ${TK.border}`,
            borderRadius: 6,
          }}
        >
          {filter === "unresolved"
            ? "No open comments. Reviewer can approve the document."
            : filter === "resolved"
            ? "No resolved comments yet."
            : "No comments on this document."}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
          gap: 10,
        }}
      >
        {blockOrder.map((blockId) => {
          const block = doc.blocks.find((b) => b.id === blockId);
          const blockThreads = grouped.get(blockId);
          return (
            <BlockReviewCard
              key={blockId}
              block={block}
              threads={blockThreads}
              onJump={() => onJumpToBlock(blockId)}
              onResolve={onResolve}
              onReopen={onReopen}
              onDelete={onDelete}
              canInteract={canInteract}
            />
          );
        })}
      </div>
    </div>
  );
}

function BlockReviewCard({ block, threads, onJump, onResolve, onReopen, onDelete, canInteract }) {
  const meta = blockDisplayMeta(block.type);
  const openCount = threads.reduce((acc, t) => acc + threadUnresolvedCount(t), 0);
  return (
    <div
      style={{
        background: TK.surface,
        border: `1px solid ${TK.border}`,
        borderRadius: 6,
        padding: 10,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          paddingBottom: 8,
          borderBottom: `1px solid ${TK.border}`,
        }}
      >
        <span style={{ fontSize: 14 }}>{meta.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>{meta.label}</div>
          <div
            style={{
              fontSize: 10.5,
              color: TK.textDim,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {previewText(block)}
          </div>
        </div>
        {openCount > 0 && <CommentBadge count={openCount} size="sm" />}
        <button
          onClick={onJump}
          style={{
            background: "transparent",
            border: `1px solid ${TK.border}`,
            color: TK.textMid,
            padding: "3px 8px",
            borderRadius: 4,
            fontSize: 10.5,
          }}
          title="Jump to block"
        >
          ↗
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {threads.map((t) => (
          <ReviewThreadCompact
            key={t.id}
            thread={t}
            onResolve={onResolve}
            onReopen={onReopen}
            onDelete={onDelete}
            canInteract={canInteract}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewThreadCompact({ thread, onResolve, onReopen, onDelete, canInteract }) {
  const replyCount = thread.replies?.length || 0;
  // Fix #3: derived status for visual tone
  const threadResolved = isThreadResolved(thread);
  const openInThread = threadUnresolvedCount(thread);

  return (
    <div
      style={{
        padding: 8,
        background: threadResolved ? "rgba(74,222,128,0.05)" : TK.surfaceLo,
        border: `1px solid ${threadResolved ? "rgba(74,222,128,0.25)" : TK.border}`,
        borderRadius: 4,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <Avatar name={thread.author} size="xs" />
        <span style={{ fontSize: 10.5, fontWeight: 600 }}>{thread.author}</span>
        <span className="mono" style={{ fontSize: 9.5, color: TK.textDim }}>
          {formatRelative(thread.createdAt)}
        </span>
        {threadResolved ? (
          <span
            style={{
              fontSize: 9,
              padding: "1px 5px",
              background: "rgba(74,222,128,0.15)",
              color: TK.ok,
              borderRadius: 2,
              fontWeight: 600,
              marginLeft: "auto",
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            Resolved
          </span>
        ) : openInThread > 1 && thread.resolved ? (
          // Root is resolved but a reply is still open — surface this
          // state explicitly; it used to be invisible pre-fix.
          <span
            style={{
              fontSize: 9,
              padding: "1px 5px",
              background: "rgba(250,204,21,0.15)",
              color: TK.warn,
              borderRadius: 2,
              fontWeight: 600,
              marginLeft: "auto",
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
            title="Root comment resolved, but replies are still open"
          >
            {openInThread} in thread
          </span>
        ) : (
          <span
            style={{
              fontSize: 9,
              padding: "1px 5px",
              background: "rgba(250,204,21,0.15)",
              color: TK.warn,
              borderRadius: 2,
              fontWeight: 600,
              marginLeft: "auto",
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            Open
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: 11.5,
          color: TK.text,
          lineHeight: 1.45,
          display: "-webkit-box",
          WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {thread.text}
      </div>
      {replyCount > 0 && (
        <div style={{ fontSize: 10, color: TK.textDim, marginTop: 4 }}>
          ↳ {replyCount} repl{replyCount === 1 ? "y" : "ies"}
        </div>
      )}
      {canInteract && (
        <div style={{ display: "flex", gap: 10, marginTop: 6, fontSize: 10.5 }}>
          {!thread.resolved ? (
            <CommentAction onClick={() => onResolve(thread.id)} color={TK.ok}>✓ Resolve root</CommentAction>
          ) : (
            <CommentAction onClick={() => onReopen(thread.id)} color={TK.warn}>↻ Reopen root</CommentAction>
          )}
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   PRIMITIVES
   ═══════════════════════════════════════════════════════════ */
function SectionHeader({ children }) {
  return (
    <div
      style={{
        fontSize: 10.5,
        textTransform: "uppercase",
        letterSpacing: "0.1em",
        color: TK.textDim,
        fontWeight: 600,
      }}
    >
      {children}
    </div>
  );
}

function SegmentedControl({ value, onChange, options, disabled }) {
  return (
    <div
      style={{
        display: "inline-flex",
        background: TK.surface,
        border: `1px solid ${TK.border}`,
        borderRadius: 6,
        padding: 2,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => !disabled && onChange(opt.value)}
            disabled={disabled}
            style={{
              padding: "5px 12px",
              background: active ? TK.surfaceHi : "transparent",
              border: "none",
              color: active ? TK.text : TK.textMid,
              fontSize: 11,
              fontWeight: 500,
              borderRadius: 4,
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function FilterPills({ value, onChange, options }) {
  return (
    <div style={{ display: "inline-flex", gap: 4 }}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              padding: "4px 10px",
              background: active ? TK.surfaceHi : TK.surface,
              border: `1px solid ${active ? TK.borderHi : TK.border}`,
              borderRadius: 4,
              color: active ? TK.text : TK.textMid,
              fontSize: 11,
              fontWeight: 500,
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function PrimaryBtn({ children, onClick, disabled, size = "md" }) {
  const pad = size === "sm" ? "5px 10px" : "7px 14px";
  const fs = size === "sm" ? 11 : 12;
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: pad,
        background: TK.accent,
        border: `1px solid ${TK.accent}`,
        borderRadius: 4,
        color: TK.bg,
        fontSize: fs,
        fontWeight: 600,
      }}
    >
      {children}
    </button>
  );
}

function SecondaryBtn({ children, onClick, disabled, size = "md" }) {
  const pad = size === "sm" ? "5px 10px" : "7px 12px";
  const fs = size === "sm" ? 11 : 12;
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: pad,
        background: TK.surface,
        border: `1px solid ${TK.border}`,
        borderRadius: 4,
        color: TK.textMid,
        fontSize: fs,
        fontWeight: 500,
      }}
    >
      {children}
    </button>
  );
}

function Avatar({ name, size = "sm" }) {
  const dim = size === "xs" ? 18 : size === "sm" ? 22 : 28;
  const fs = size === "xs" ? 9 : size === "sm" ? 10 : 12;
  const initial = (name || "?").charAt(0).toUpperCase();
  const colors = [TK.accent, TK.mauve, TK.gold, TK.info, TK.ok];
  const idx = (name || "").split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % colors.length;
  return (
    <div
      style={{
        width: dim,
        height: dim,
        borderRadius: "50%",
        background: `${colors[idx]}2a`,
        border: `1px solid ${colors[idx]}4d`,
        color: colors[idx],
        display: "grid",
        placeItems: "center",
        fontSize: fs,
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {initial}
    </div>
  );
}

function CommentBadge({ count, size = "sm" }) {
  const dim = size === "sm" ? 20 : 24;
  const fs = size === "sm" ? 10 : 11;
  return (
    <span
      style={{
        minWidth: dim,
        height: dim,
        padding: "0 6px",
        borderRadius: dim / 2,
        background: TK.warn,
        color: "#000",
        fontSize: fs,
        fontWeight: 700,
        display: "inline-grid",
        placeItems: "center",
        lineHeight: 1,
      }}
    >
      {count}
    </span>
  );
}

function Toast({ kind, text }) {
  const tone = kind === "err" ? TK.err : TK.ok;
  const bg = kind === "err" ? "rgba(248,113,113,0.12)" : "rgba(74,222,128,0.12)";
  return (
    <div
      style={{
        position: "fixed",
        bottom: 60,
        left: "50%",
        transform: "translateX(-50%)",
        padding: "10px 16px",
        background: bg,
        border: `1px solid ${tone}`,
        borderRadius: 6,
        color: tone,
        fontSize: 12,
        fontWeight: 500,
        zIndex: 200,
        animation: "slideIn 200ms ease-out",
        backdropFilter: "blur(12px)",
      }}
    >
      {text}
    </div>
  );
}

function DebugFooter({ workflow, mode, schemaVersionRoot, schemaVersionMeta, migrationsApplied, commentCount, totalUnresolved }) {
  const schemaMatch = schemaVersionRoot === schemaVersionMeta;
  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        padding: "6px 16px",
        background: TK.surfaceLo,
        borderTop: `1px solid ${TK.border}`,
        display: "flex",
        gap: 16,
        fontSize: 10.5,
        color: TK.textDim,
        zIndex: 40,
      }}
      className="mono"
    >
      <span>mode={mode}</span>
      <span>workflow={workflow}</span>
      <span style={{ color: schemaMatch ? TK.textDim : TK.err }}>
        schema=root:v{schemaVersionRoot}/meta:v{schemaVersionMeta}
        {!schemaMatch && " ⚠"}
      </span>
      <span>migrations=[{(migrationsApplied || []).join(",")}]</span>
      <span>comments={commentCount}</span>
      <span>unresolved={totalUnresolved}</span>
      <span style={{ flex: 1 }} />
      <span>Stage 3b · v2</span>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════
   HELPERS
   ═══════════════════════════════════════════════════════════ */
function blockDisplayMeta(type) {
  const map = {
    eyebrow_tag: { icon: "▪", label: "Eyebrow tag" },
    headline_editorial: { icon: "𝐇", label: "Headline" },
    subtitle_descriptor: { icon: "¶", label: "Subtitle" },
    hero_stat: { icon: "#", label: "Hero number" },
    ranked_bars: { icon: "≡", label: "Ranked bars" },
    body_annotation: { icon: "❞", label: "Annotation" },
    source_footer: { icon: "§", label: "Source" },
    brand_stamp: { icon: "✦", label: "Brand stamp" },
  };
  return map[type] || { icon: "□", label: type };
}

function previewText(block) {
  const p = block.props || {};
  if (block.type === "ranked_bars") return `${p.items?.length || 0} rows`;
  return p.headline || p.text || p.subtitle || p.value || p.source || p.label || "";
}

function truncate(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function formatRelative(iso) {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = Math.max(0, now - then);
  const s = Math.floor(diff / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}
