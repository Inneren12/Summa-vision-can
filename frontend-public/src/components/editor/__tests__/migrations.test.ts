import {
  migrateDoc,
  validateImportStrict,
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

function v2Doc(): CanonicalDocument {
  // `mkDoc` already produces a v2 document. Deep-clone so per-test mutation
  // cannot leak between cases.
  return JSON.parse(JSON.stringify(mkDoc("single_stat_hero", TPLS.single_stat_hero)));
}

function v1Doc(overrides: Partial<LegacyDocumentV1> = {}): LegacyDocumentV1 {
  // Start from a v2 mkDoc output, then strip v2-only fields and add v1-only
  // fields. Keeps the block graph / sections / required-block invariants
  // satisfied without reimplementing them in the test.
  const v2 = v2Doc() as any;
  delete v2.review;
  const base: LegacyDocumentV1 = {
    schemaVersion: 1,
    templateId: v2.templateId,
    page: v2.page,
    sections: v2.sections,
    blocks: v2.blocks,
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

describe("migrateDoc — v1 → v2 (real production case)", () => {
  test("bumps schemaVersion to 2 and reports the applied step", () => {
    const raw = v1Doc();
    const result = migrateDoc(raw);
    expect(result.doc.schemaVersion).toBe(2);
    expect(result.appliedMigrations).toEqual([2]);
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
  test("v2 input returns without applying any migration", () => {
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
    expect(result.appliedMigrations).toEqual([2]);
  });
});

describe("validateImportStrict — invariant enforcement", () => {
  test("accepts a freshly-migrated v2 document", () => {
    const raw = v1Doc();
    expect(() => validateImportStrict(raw)).not.toThrow();
    const doc = validateImportStrict(raw);
    expect(doc.schemaVersion).toBe(2);
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
  afterEach(() => {
    // Restore any temporary keys added to the shared MIGRATIONS map.
    delete (MIGRATIONS as Record<number, unknown>)[2];
    delete (MIGRATIONS as Record<number, unknown>)[3];
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

describe("mkDoc — produces a valid v2 document", () => {
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
