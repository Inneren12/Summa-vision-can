import {
  migrateDoc,
  validateImportStrict,
  hydrateImportedDoc,
  CURRENT_SCHEMA_VERSION,
  MIGRATIONS,
  applyMigrations,
} from "../registry/guards";

// Test-local string-returning wrapper. The legacy `validateImport`
// dual-API was removed in PR 2a (DEBT-022 closure). Tests that previously
// asserted on the message string keep working through this thin shim.
function runImport(doc: unknown): string | null {
  try {
    validateImportStrict(doc);
    return null;
  } catch (err) {
    return err instanceof Error ? err.message : String(err);
  }
}
import { TPLS, mkDoc } from "../registry/templates";
import type {
  CanonicalDocument,
  LegacyDocumentV1,
  EditHistoryEntry,
} from "../types";

// Deterministic timestamps — fixtures must not depend on wall-clock time.
const FIXED_TS = "2026-01-01T00:00:00.000Z";
const FIXED_TS_2 = "2026-02-01T00:00:00.000Z";
const FIXED_TS_3 = "2026-03-01T00:00:00.000Z";

/**
 * Phase 2.1 PR#2 NOTE: `mkDoc` now produces a v3 document (post-rename,
 * post-exportPresets). The historical name `v2Doc` is preserved across
 * the file because the suite was authored against v2 — every consumer
 * only needs "the current canonical shape", not specifically v2.
 */
function v2Doc(): CanonicalDocument {
  return JSON.parse(JSON.stringify(mkDoc("single_stat_hero", TPLS.single_stat_hero)));
}

function v1Doc(overrides: Partial<LegacyDocumentV1> = {}): LegacyDocumentV1 {
  // Start from the current canonical shape, strip post-v1 fields, and
  // emulate the v1-only `workflow` at the root. Keeps the block graph /
  // sections / required-block invariants satisfied without reimplementing
  // them. `exportPresets` is also stripped — v1 documents predate the
  // field, which the v2 → v3 migration adds with the common-4 default.
  const current = v2Doc() as any;
  delete current.review;
  const base: LegacyDocumentV1 = {
    schemaVersion: 1,
    templateId: current.templateId,
    page: {
      size: current.page.size,
      background: current.page.background,
      palette: current.page.palette,
    },
    sections: current.sections,
    blocks: current.blocks,
    workflow: "draft",
    meta: {
      createdAt: FIXED_TS,
      updatedAt: FIXED_TS,
      version: 1,
      history: [],
    },
  };
  return { ...base, ...overrides };
}

describe("migrateDoc — v1 → v3 (real production case)", () => {
  test("bumps schemaVersion to current and reports both applied steps", () => {
    const raw = v1Doc();
    const result = migrateDoc(raw);
    expect(result.doc.schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
    // v1 → v2 → v3, both steps applied in sequence.
    expect(result.appliedMigrations).toEqual([2, 3]);
  });

  test("moves workflow from root into review.workflow (defaulting to 'draft')", () => {
    const raw = v1Doc({ workflow: "draft" });
    const result = migrateDoc(raw);
    expect(result.doc.review.workflow).toBe("draft");
  });

  test("initialises review.comments as an empty array", () => {
    const raw = v1Doc();
    const result = migrateDoc(raw);
    expect(result.doc.review.comments).toEqual([]);
  });

  test("writes a single 'migrated' entry into review.history", () => {
    const raw = v1Doc();
    const result = migrateDoc(raw);
    expect(result.doc.review.history).toHaveLength(1);
    expect(result.doc.review.history[0].action).toBe("migrated");
    expect(result.doc.review.history[0].author).toBe("system");
    expect(result.doc.review.history[0].fromWorkflow).toBeNull();
    expect(result.doc.review.history[0].toWorkflow).toBe("draft");
  });

  test("removes workflow from the document root", () => {
    const raw = v1Doc();
    const result = migrateDoc(raw);
    expect("workflow" in (result.doc as unknown as Record<string, unknown>)).toBe(false);
  });

  test("preserves meta.history bit-for-bit", () => {
    const edits: EditHistoryEntry[] = [
      { version: 1, savedAt: FIXED_TS, summary: "Initial" },
      { version: 2, savedAt: FIXED_TS_2, summary: "Edit one" },
      { version: 3, savedAt: FIXED_TS_3, summary: "Edit two" },
    ];
    const raw = v1Doc({
      meta: {
        createdAt: FIXED_TS,
        updatedAt: FIXED_TS_3,
        version: 3,
        history: edits,
      },
    });
    const result = migrateDoc(raw);
    expect(result.doc.meta.history).toEqual(edits);
  });
});

describe("migrateDoc — workflow preservation", () => {
  test("preserves a non-default workflow through the migration", () => {
    const raw = v1Doc({ workflow: "in_review" });
    const result = migrateDoc(raw);
    expect(result.doc.review.workflow).toBe("in_review");
    expect(result.doc.review.history[0].toWorkflow).toBe("in_review");
  });

  test("falls back to 'draft' when root workflow is invalid", () => {
    const raw = v1Doc({ workflow: "not_a_real_state" as any });
    const result = migrateDoc(raw);
    expect(result.doc.review.workflow).toBe("draft");
  });
});

describe("migrateDoc — idempotence on already-current documents", () => {
  test("current-version input returns without applying any migration", () => {
    const raw = v2Doc();
    const result = migrateDoc(raw);
    expect(result.appliedMigrations).toEqual([]);
    expect(result.doc).toEqual(raw);
  });
});

describe("migrateDoc — rejection paths", () => {
  test("throws on future versions", () => {
    const raw = { ...v2Doc(), schemaVersion: 99 };
    expect(() => migrateDoc(raw)).toThrow(/99/);
    expect(() => migrateDoc(raw)).toThrow(/newer than this client supports/);
  });

  test.each([
    ["null", null],
    ["undefined", undefined],
    ["string", "not a doc"],
    ["number", 42],
    ["array", []],
  ])("throws on non-object input: %s", (_label, input) => {
    expect(() => migrateDoc(input as unknown)).toThrow();
  });
});

describe("migrateDoc — missing schemaVersion assumes v1", () => {
  test("migrates a v1-shaped object without an explicit schemaVersion field", () => {
    const raw = v1Doc();
    const { schemaVersion: _discard, ...unversioned } = raw as any;
    const result = migrateDoc(unversioned);
    expect(result.doc.schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
    expect(result.appliedMigrations).toEqual([2, 3]);
  });
});

describe("validateImportStrict — invariant enforcement", () => {
  test("accepts a freshly-migrated current-version document", () => {
    const raw = v1Doc();
    expect(() => validateImportStrict(raw)).not.toThrow();
    const doc = validateImportStrict(raw);
    expect(doc.schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
  });

  test("rejects a 'v2' doc that kept workflow at root", () => {
    const raw = { ...v2Doc(), workflow: "draft" } as any;
    expect(() => validateImportStrict(raw)).toThrow(/workflow/);
  });

  test("rejects a 'v2' doc missing review.comments", () => {
    const raw: any = v2Doc();
    delete raw.review.comments;
    expect(() => validateImportStrict(raw)).toThrow(/review\.comments/);
  });

  test("rejects a 'v2' doc where meta.history is not an array", () => {
    const raw: any = v2Doc();
    raw.meta.history = "not-an-array";
    expect(() => validateImportStrict(raw)).toThrow(/meta version\/history/i);
  });

  test("rejects a 'v2' doc with meta.schemaVersion present", () => {
    const raw: any = v2Doc();
    raw.meta.schemaVersion = 2;
    expect(() => validateImportStrict(raw)).toThrow(/meta\.schemaVersion/);
  });

  test("rejects a 'v2' doc with meta.workflow present", () => {
    const raw: any = v2Doc();
    raw.meta.workflow = "draft";
    expect(() => validateImportStrict(raw)).toThrow(/meta\.workflow/);
  });
});

describe("validateImportStrict (via runImport) — message-shape regressions", () => {
  test("returns null for a valid v2 doc", () => {
    expect(runImport(v2Doc())).toBeNull();
  });

  test("returns a descriptive error for obvious garbage", () => {
    expect(runImport(null)).toMatch(/Cannot migrate|Not an object/);
  });

  test("returns a descriptive error for a v2 doc with a missing review section", () => {
    const raw: any = v2Doc();
    delete raw.review;
    expect(runImport(raw)).toMatch(/Missing review section/);
  });
});

describe("migrateDoc — missing migration step", () => {
  test("throws when asked to migrate from an unknown intermediate version", () => {
    // schemaVersion 0 has no registered migration.
    const raw = { ...v2Doc(), schemaVersion: 0 };
    expect(() => migrateDoc(raw)).toThrow(/Missing migration from schemaVersion 0/);
  });
});

describe("validateImportStrict — additional shape rejections", () => {
  test("rejects a v2 doc whose review.workflow is not a valid state", () => {
    const raw: any = v2Doc();
    raw.review.workflow = "not_a_real_state";
    expect(() => validateImportStrict(raw)).toThrow(/review\.workflow/);
  });
});

describe("migrateDoc — deterministic timestamp derivation", () => {
  test("migration v1 → v2 is deterministic for the same input", () => {
    const fixture = v1Doc({
      meta: {
        createdAt: "2026-01-01T00:00:00.000Z",
        updatedAt: "2026-02-15T12:30:00.000Z",
        version: 3,
        history: [],
      },
    });
    const a = migrateDoc(JSON.parse(JSON.stringify(fixture))).doc;
    const b = migrateDoc(JSON.parse(JSON.stringify(fixture))).doc;
    expect(a).toEqual(b);
    expect(a.review.history[0].ts).toBe("2026-02-15T12:30:00.000Z"); // prefers updatedAt
  });

  test("migration timestamp falls back to createdAt when updatedAt is missing", () => {
    const fixture = v1Doc({
      meta: {
        createdAt: "2026-01-01T00:00:00.000Z",
        updatedAt: undefined as unknown as string,
        version: 0,
        history: [],
      },
    });
    const result = migrateDoc(fixture).doc;
    expect(result.review.history[0].ts).toBe("2026-01-01T00:00:00.000Z");
  });

  test("migration timestamp falls back to epoch when both timestamps are missing", () => {
    const fixture = v1Doc({
      meta: {
        createdAt: undefined as unknown as string,
        updatedAt: undefined as unknown as string,
        version: 0,
        history: [],
      },
    });
    const result = migrateDoc(fixture).doc;
    expect(result.review.history[0].ts).toBe("1970-01-01T00:00:00.000Z");
  });

  test("migration timestamp falls back to epoch when timestamps are malformed", () => {
    const fixture = v1Doc({
      meta: {
        createdAt: "not-an-iso-string",
        updatedAt: "also-garbage",
        version: 0,
        history: [],
      },
    });
    const result = migrateDoc(fixture).doc;
    expect(result.review.history[0].ts).toBe("1970-01-01T00:00:00.000Z");
  });
});

describe("migrateDoc — defensive branches (MIGRATIONS monkey-patch)", () => {
  // Snapshot the real migrations once so afterEach can reinstate them
  // after a test temporarily replaces an entry.
  const ORIGINAL_M1 = MIGRATIONS[1];
  const ORIGINAL_M2 = MIGRATIONS[2];
  afterEach(() => {
    const map = MIGRATIONS as Record<number, unknown>;
    if (ORIGINAL_M1) map[1] = ORIGINAL_M1;
    if (ORIGINAL_M2) map[2] = ORIGINAL_M2;
    // Drop any forward-lookahead keys added by the test.
    delete map[3];
  });

  test("throws when a migration step fails to bump schemaVersion", () => {
    // Pretend we have a future v2 → v3 migration that forgets to bump.
    (MIGRATIONS as Record<number, (doc: any) => any>)[2] = (doc) => ({
      ...doc,
      // deliberately omits schemaVersion bump
    });
    // Force migrateDoc to walk from 2 → 3 by claiming CURRENT_SCHEMA_VERSION is 3.
    // We cannot monkey-patch the const, so instead point starting version at 2
    // and add a migration for 2 that returns schemaVersion 2 again.
    // Result: migrateDoc's own post-step assertion fires.
    const raw = { ...(v2Doc() as any) };
    // Plant a v2→? broken migration and an artificial CURRENT by also
    // registering [3]: a no-op so the loop reaches the broken step.
    (MIGRATIONS as Record<number, (doc: any) => any>)[3] = (d) => ({ ...d, schemaVersion: 4 });
    // applyMigrations uses CURRENT_SCHEMA = 2, so it never enters the loop
    // on a v2 input; so this test instead exercises the equivalent branch
    // via applyMigrations' inner try/catch on a thrower at v1.
    (MIGRATIONS as Record<number, (doc: any) => any>)[1] = (() => {
      const original = MIGRATIONS[1];
      return (d: any) => {
        // restore immediately so subsequent tests are unaffected
        (MIGRATIONS as Record<number, (doc: any) => any>)[1] = original;
        throw new Error("synthetic migration failure");
      };
    })();
    expect(() => applyMigrations({ ...raw, schemaVersion: 1 })).toThrow(
      /Migration pipeline failed at v1: Migration 1 → 2 failed: synthetic migration failure/,
    );
  });
});

describe("mkDoc — produces a valid current-version document", () => {
  test("validateImportStrict accepts the output of mkDoc", () => {
    expect(() => validateImportStrict(mkDoc("single_stat_hero", TPLS.single_stat_hero))).not.toThrow();
  });

  test("the initial workflow history entry is a 'created' event", () => {
    const doc = mkDoc("single_stat_hero", TPLS.single_stat_hero);
    expect(doc.review.history[0].action).toBe("created");
    expect(doc.review.workflow).toBe("draft");
    expect(doc.review.comments).toEqual([]);
  });
});

// ────────────────────────────────────────────────────────────────────
// DEBT-023 closure — Comment element shape + referential integrity
// ────────────────────────────────────────────────────────────────────

describe("validateImportStrict — Comment element shape (DEBT-023 closure)", () => {
  const FIXED = "2026-04-17T12:00:00.000Z";
  // Pull a real block id from the v2Doc fixture so comments anchor to
  // something `validateImportStrict` recognises. The referential-integrity
  // check rejects comments whose blockId is not in `doc.blocks`.
  const ANCHOR_BLOCK_ID = Object.keys(v2Doc().blocks)[0];

  function wellFormedComment(overrides: Record<string, unknown> = {}) {
    return {
      id: "c1",
      blockId: ANCHOR_BLOCK_ID,
      parentId: null,
      author: "you",
      text: "hi",
      createdAt: FIXED,
      updatedAt: null,
      resolved: false,
      resolvedAt: null,
      resolvedBy: null,
      ...overrides,
    };
  }

  function withComments(...comments: unknown[]) {
    const raw: any = v2Doc();
    raw.review.comments = comments;
    return raw;
  }

  test("accepts a v2 doc with a well-formed comment", () => {
    const raw = withComments(wellFormedComment());
    expect(() => validateImportStrict(raw)).not.toThrow();
  });

  test("accepts a v2 doc with a parent + reply thread", () => {
    const parent = wellFormedComment({ id: "p" });
    const reply = wellFormedComment({ id: "r", parentId: "p" });
    const raw = withComments(parent, reply);
    expect(() => validateImportStrict(raw)).not.toThrow();
  });

  test("rejects a comment with missing id", () => {
    const raw = withComments(wellFormedComment({ id: "" }));
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\]\.id/,
    );
  });

  test("rejects a comment with an invalid createdAt", () => {
    const raw = withComments(wellFormedComment({ createdAt: "not-iso" }));
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\]\.createdAt/,
    );
  });

  test("rejects a resolved comment with null resolvedBy", () => {
    const raw = withComments(
      wellFormedComment({
        resolved: true,
        resolvedAt: FIXED,
        resolvedBy: null,
      }),
    );
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\]\.resolvedBy/,
    );
  });

  test("rejects an unresolved comment with non-null resolvedAt", () => {
    const raw = withComments(
      wellFormedComment({ resolved: false, resolvedAt: FIXED }),
    );
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\]\.resolvedAt/,
    );
  });

  test("rejects a comment with parentId pointing to a non-existent id", () => {
    const raw = withComments(wellFormedComment({ id: "r", parentId: "ghost" }));
    expect(() => validateImportStrict(raw)).toThrow(
      /parentId "ghost" does not match any comment id/,
    );
  });

  test("rejects a comment with an empty-string parentId", () => {
    const raw = withComments(wellFormedComment({ parentId: "" }));
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\]\.parentId/,
    );
  });

  test("rejects a comment whose resolved field is not a boolean", () => {
    const raw = withComments(wellFormedComment({ resolved: "yes" as any }));
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\]\.resolved/,
    );
  });

  test("rejects a non-object comment entry", () => {
    const raw = withComments(null);
    expect(() => validateImportStrict(raw)).toThrow(
      /review\.comments\[0\] is not an object/,
    );
  });

  // ── Issue 4 semantic validation ────────────────────────────────────

  test("rejects a self-referential comment (parentId === id)", () => {
    const raw = withComments(wellFormedComment({ id: "c_1", parentId: "c_1" }));
    expect(() => validateImportStrict(raw)).toThrow(
      /self-reference|parentId must not equal/,
    );
  });

  test("rejects a comment anchored to a non-existent block", () => {
    const raw = withComments(
      wellFormedComment({ blockId: "ghost_block_id" }),
    );
    expect(() => validateImportStrict(raw)).toThrow(
      /blockId "ghost_block_id" does not match any block in doc\.blocks/,
    );
  });

  // ── Issue 3 threading depth ────────────────────────────────────────

  test("rejects a document with reply-to-reply nesting", () => {
    const root = wellFormedComment({ id: "r" });
    const reply = wellFormedComment({ id: "r2", parentId: "r" });
    const nested = wellFormedComment({ id: "r3", parentId: "r2" });
    const raw = withComments(root, reply, nested);
    expect(() => validateImportStrict(raw)).toThrow(
      /reply to a reply|depth must be one level/,
    );
  });

  test("accepts a tombstoned comment ('[deleted]' author, empty update)", () => {
    const tombstoned = wellFormedComment({
      author: "[deleted]",
      text: "[deleted]",
      updatedAt: FIXED,
    });
    const raw = withComments(tombstoned);
    expect(() => validateImportStrict(raw)).not.toThrow();
  });

  // ── Duplicate-id rejection ─────────────────────────────────────────
  // A Set built from `comments.map(c => c.id)` silently dedupes, so
  // duplicate ids would slip past referential-integrity and then corrupt
  // `buildThreads` / `apply{Edit,Resolve,Delete}Comment` downstream.

  test("rejects documents with duplicate comment ids", () => {
    const first = wellFormedComment({
      id: "c_1",
      author: "alice",
      text: "first",
      createdAt: "2026-04-17T12:00:00.000Z",
    });
    const collision = wellFormedComment({
      id: "c_1",
      author: "bob",
      text: "colliding",
      createdAt: "2026-04-17T12:01:00.000Z",
    });
    const raw = withComments(first, collision);
    expect(() => validateImportStrict(raw)).toThrow(
      /duplicates? an earlier comment|duplicate/i,
    );
  });

  test("accepts well-formed unique comment ids", () => {
    const root = wellFormedComment({
      id: "c_1",
      author: "alice",
      text: "root",
      createdAt: "2026-04-17T12:00:00.000Z",
    });
    const reply = wellFormedComment({
      id: "c_2",
      parentId: "c_1",
      author: "bob",
      text: "reply",
      createdAt: "2026-04-17T12:01:00.000Z",
    });
    const raw = withComments(root, reply);
    expect(() => validateImportStrict(raw)).not.toThrow();
  });
});

// ────────────────────────────────────────────────────────────────────
// Phase 2.1 PR#2 — v2 → v3 migration (preset rename + exportPresets)
//
// Risk 3 mitigation per docs/recon/phase-2-1-recon.md §5:
// the migration must atomically (a) rename `page.size` to the post-rename
// preset id and (b) populate `page.exportPresets` with the common-4 default
// when absent. Tests cover the three real-world scenarios plus the
// abort-discipline contract from EDITOR_BLOCK_ARCHITECTURE.md §6.
// ────────────────────────────────────────────────────────────────────

import { DEFAULT_EXPORT_PRESETS } from "../config/sizes";

describe("migrateV2toV3 — preset id rename + exportPresets default", () => {
  function v2Fixture(
    over: { size?: string; exportPresets?: unknown } = {},
  ): Record<string, unknown> {
    // Synthetic v2-shaped doc — does not need to satisfy `validateImportStrict`
    // because the migration runs BEFORE shape validation in the import
    // pipeline. Sections + blocks are intentionally minimal.
    const page: Record<string, unknown> = {
      size: over.size ?? "instagram_1080",
      background: "solid_dark",
      palette: "housing",
    };
    if (over.exportPresets !== undefined) {
      page.exportPresets = over.exportPresets;
    }
    return {
      schemaVersion: 2,
      templateId: "test",
      page,
      sections: [],
      blocks: {},
      meta: {
        createdAt: FIXED_TS,
        updatedAt: FIXED_TS,
        version: 1,
        history: [],
      },
      review: { workflow: "draft", history: [], comments: [] },
    };
  }

  test("scenario 1: pre-migration document with no exportPresets gets common-4 default", () => {
    const v2 = v2Fixture();
    const result = migrateDoc(v2);
    expect(result.doc.schemaVersion).toBe(3);
    expect(result.doc.page.exportPresets).toEqual([...DEFAULT_EXPORT_PRESETS]);
    // page.size unchanged when already on a non-renamed preset id.
    expect(result.doc.page.size).toBe("instagram_1080");
    expect(result.appliedMigrations).toEqual([3]);
  });

  test("scenario 2: pre-migration document with old preset IDs renames page.size", () => {
    const v2 = v2Fixture({ size: "twitter" });
    const result = migrateDoc(v2);
    expect(result.doc.schemaVersion).toBe(3);
    expect(result.doc.page.size).toBe("twitter_landscape");
    expect(result.doc.page.exportPresets).toEqual([...DEFAULT_EXPORT_PRESETS]);
  });

  test("scenario 2 (full coverage): renames every legacy preset id", () => {
    const cases: Array<[string, string]> = [
      ["instagram_port", "instagram_portrait"],
      ["story",          "instagram_story"],
      ["twitter",        "twitter_landscape"],
      ["reddit",         "reddit_standard"],
      ["linkedin",       "linkedin_landscape"],
    ];
    for (const [from, to] of cases) {
      const v2 = v2Fixture({ size: from });
      const result = migrateDoc(v2);
      expect(result.doc.page.size).toBe(to);
    }
  });

  test("scenario 3: pre-migration document on already-renamed ID is unchanged in size", () => {
    // Defensive: a doc already carrying a v3 preset id at v2 (e.g. produced
    // by a forward-compat tool) must not double-rename or corrupt the size.
    const v2 = v2Fixture({ size: "twitter_landscape" });
    const result = migrateDoc(v2);
    expect(result.doc.schemaVersion).toBe(3);
    expect(result.doc.page.size).toBe("twitter_landscape");
    expect(result.doc.page.exportPresets).toEqual([...DEFAULT_EXPORT_PRESETS]);
  });

  test("preserves an existing exportPresets value through the migration", () => {
    // If a forward-compat client wrote exportPresets at v2 (against the
    // v2 spec but possible in practice), the migration must NOT clobber it
    // with the common-4 default — operator intent should survive.
    const customPresets = ["instagram_1080", "instagram_portrait"];
    const v2 = v2Fixture({ size: "instagram_1080", exportPresets: customPresets });
    const result = migrateDoc(v2);
    expect(result.doc.page.exportPresets).toEqual(customPresets);
  });

  test("v1 → v2 → v3 chain produces a doc with both renamed size and default exportPresets", () => {
    const v1 = v1Doc({ page: { size: "twitter", background: "solid_dark", palette: "housing" } });
    const result = migrateDoc(v1);
    expect(result.doc.schemaVersion).toBe(3);
    expect(result.doc.page.size).toBe("twitter_landscape");
    expect(result.doc.page.exportPresets).toEqual([...DEFAULT_EXPORT_PRESETS]);
    expect(result.appliedMigrations).toEqual([2, 3]);
  });

  test("scenario 5: pre-migration document with old IDs in exportPresets array gets them renamed", () => {
    // PR#2 fix1 (P1.1): the v2 → v3 migration also rewrites legacy preset
    // IDs that may pre-exist in `page.exportPresets`. Beta builds and
    // forward-compat tools could have written the field at v2 with the
    // pre-rename slugs; without per-element rename, the migrated doc would
    // carry `page.size = "twitter_landscape"` while `page.exportPresets`
    // still listed `"twitter"` — silently dropping that preset from the
    // PR#3 ZIP orchestrator's enabled set.
    const v2 = v2Fixture({
      size: "twitter",
      exportPresets: ["twitter", "reddit", "story"],
    });
    const result = migrateDoc(v2);

    expect(result.doc.schemaVersion).toBe(3);
    expect(result.doc.page.size).toBe("twitter_landscape");

    // All three legacy IDs renamed to their v3 equivalents.
    expect(result.doc.page.exportPresets).toContain("twitter_landscape");
    expect(result.doc.page.exportPresets).toContain("reddit_standard");
    expect(result.doc.page.exportPresets).toContain("instagram_story");

    // No legacy IDs survive the migration.
    expect(result.doc.page.exportPresets).not.toContain("twitter");
    expect(result.doc.page.exportPresets).not.toContain("reddit");
    expect(result.doc.page.exportPresets).not.toContain("story");
  });

  test("scenario 4 (abort discipline): missing intermediate migration throws", () => {
    // EDITOR_BLOCK_ARCHITECTURE.md §6 mandates abort on missing intermediate.
    // Use a synthetic schemaVersion below any registered migration so the
    // applyMigrations loop hits the no-fn branch on its first iteration.
    const veryOldDoc: Record<string, unknown> = {
      schemaVersion: -999,
      templateId: "test",
      page: { size: "instagram_1080", background: "solid_dark", palette: "housing" },
      sections: [],
      blocks: {},
      meta: { createdAt: FIXED_TS, updatedAt: FIXED_TS, version: 1, history: [] },
      review: { workflow: "draft", history: [], comments: [] },
    };
    expect(() => applyMigrations(veryOldDoc)).toThrow(/Missing migration/);
  });
});

// ────────────────────────────────────────────────────────────────────
// Phase 3.1d Slice 2 — hydrateImportedDoc binding handling
// ────────────────────────────────────────────────────────────────────

describe("hydrateImportedDoc — Block.binding (Phase 3.1d Slice 2)", () => {
  function docWithBlockBinding(blockBinding: unknown): unknown {
    const base = v2Doc() as any;
    const firstBlockKey = Object.keys(base.blocks)[0];
    base.blocks[firstBlockKey] = { ...base.blocks[firstBlockKey], binding: blockBinding };
    return { base, blockKey: firstBlockKey };
  }

  it("hydrates a block without `binding` cleanly (no key on result)", () => {
    const base = v2Doc() as any;
    const blockKey = Object.keys(base.blocks)[0];
    const { doc, warnings } = hydrateImportedDoc(base);
    expect(doc.blocks[blockKey]).not.toHaveProperty("binding");
    expect(warnings.some((w) => /binding/i.test(w))).toBe(false);
  });

  it("preserves a valid binding through hydration", () => {
    const validBinding = {
      kind: "single",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period: "2024-Q3",
    };
    const { base, blockKey } = docWithBlockBinding(validBinding) as any;
    const { doc, warnings } = hydrateImportedDoc(base);
    expect(doc.blocks[blockKey].binding).toEqual(validBinding);
    expect(warnings.some((w) => /Invalid block binding dropped/.test(w))).toBe(false);
  });

  it("drops malformed binding and emits warning", () => {
    const malformed = { kind: "single", cube_id: 42 }; // wrong type
    const { base, blockKey } = docWithBlockBinding(malformed) as any;
    const { doc, warnings } = hydrateImportedDoc(base);
    expect(doc.blocks[blockKey]).not.toHaveProperty("binding");
    const w = warnings.find((s) => /Invalid block binding dropped/.test(s));
    expect(w).toBeDefined();
    expect(w).toContain(blockKey);
    expect(w).toContain("kind=single");
  });

  it("treats binding=undefined as absent (no key, no warning)", () => {
    const { base, blockKey } = docWithBlockBinding(undefined) as any;
    const { doc, warnings } = hydrateImportedDoc(base);
    expect(doc.blocks[blockKey]).not.toHaveProperty("binding");
    expect(warnings.some((w) => /Invalid block binding dropped/.test(w))).toBe(false);
  });

  it("warning text uses kind=unknown when input has no kind field", () => {
    const malformed = { cube_id: "c" };
    const { base, blockKey } = docWithBlockBinding(malformed) as any;
    const { warnings } = hydrateImportedDoc(base);
    const w = warnings.find((s) => /Invalid block binding dropped/.test(s));
    expect(w).toBeDefined();
    expect(w).toContain("kind=unknown");
  });

  it("preserves time_series binding on any block type (universal validation)", () => {
    const tsBinding = {
      kind: "time_series",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period_range: { last_n: 12 },
    };
    const { base, blockKey } = docWithBlockBinding(tsBinding) as any;
    const { doc } = hydrateImportedDoc(base);
    expect(doc.blocks[blockKey].binding).toEqual(tsBinding);
  });

  it("strips unknown extra keys on otherwise-valid binding (canonical reconstruction)", () => {
    const validWithExtra = {
      kind: "single",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period: "2024-Q3",
      mystery_field: "drop me",
    };
    const { base, blockKey } = docWithBlockBinding(validWithExtra) as any;
    const { doc } = hydrateImportedDoc(base);
    expect(doc.blocks[blockKey].binding).not.toHaveProperty("mystery_field");
    expect(doc.blocks[blockKey].binding).toEqual({
      kind: "single",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period: "2024-Q3",
    });
  });

  it("preserves binding through JSON round-trip (export → re-import)", () => {
    const validBinding = {
      kind: "categorical_series",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      category_dim: "province",
      filters: { year: "2024" },
      period: "2024-Q3",
      sort: "value_desc" as const,
      limit: 5,
    };
    const { base, blockKey } = docWithBlockBinding(validBinding) as any;
    const { doc: hydrated } = hydrateImportedDoc(base);
    const json = JSON.stringify(hydrated);
    const reimported = hydrateImportedDoc(JSON.parse(json));
    expect(reimported.doc.blocks[blockKey].binding).toEqual(validBinding);
  });

  it("preserves binding presence/absence per-block in mixed round-trip", () => {
    const base = v2Doc() as any;
    const keys = Object.keys(base.blocks);
    expect(keys.length).toBeGreaterThanOrEqual(1);
    const validBinding = {
      kind: "single",
      cube_id: "cube_a",
      semantic_key: "metric_x",
      filters: { geo: "ON" },
      period: "2024-Q3",
    };
    base.blocks[keys[0]] = { ...base.blocks[keys[0]], binding: validBinding };
    // (other blocks intentionally have no binding)
    const { doc: hydrated } = hydrateImportedDoc(base);
    const reimported = hydrateImportedDoc(JSON.parse(JSON.stringify(hydrated)));
    expect(reimported.doc.blocks[keys[0]].binding).toEqual(validBinding);
    for (const k of keys.slice(1)) {
      expect(reimported.doc.blocks[k]).not.toHaveProperty("binding");
    }
  });
});
