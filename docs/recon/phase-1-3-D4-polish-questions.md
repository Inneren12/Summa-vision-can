# Phase 1.3 Pre-Recon Part D4 — Polish + Founder Questions (Sections I & J)

**Type:** RECON FINALIZATION (4 of 4 micro-splits of original Part D)
**Scope:** Section I (`polish.md` additions) + Section J (founder questions Q1–Q6).
**Other splits:** D1 (test plan), D2 (migration & rollout), D3 (DEBT entries).
**Date:** 2026-04-27
**Branch:** `claude/polish-founder-questions-DNtrj`
**Git remote:** `http://local_proxy@127.0.0.1:41181/git/Inneren12/Summa-vision-can`

This document is **READ-ONLY**. The P3-006 entry is **drafted** here for review
only. It is NOT appended to `polish.md` in this recon PR. The 1.3 impl prompt
will append the entry to `polish.md` in the **same commit** as the 1.3
implementation PR (not in pre-recon, not in recon-proper).

---

## Section I — `polish.md` additions

### I.0 Fresh `polish.md` numbering grep

Command (verbatim from prompt §1):

```bash
grep -E '^## P[0-9]+-[0-9]+ —' polish.md
```

Output (executed 2026-04-27 against `polish.md` at HEAD of branch
`claude/polish-founder-questions-DNtrj`):

```
## P2-001 — TopBar crop toggle: add `aria-pressed`
## P3-001 — PreviewResponse field comment style
## P3-002 — Uppercase .PARQUET extension test for key parser
## P3-003 — Document `limit` query param on preview endpoint
## P3-004 — Tests must use `localizationsDelegates` for any localized UI
## P3-005 — Document Dart `const Set` with custom equality limitation
```

**Last entry:** `P3-005` — Document Dart `const Set` with custom equality limitation.

**Numbering matches expected (P3-005):** **YES**.

Therefore:
- The next entry to append is **P3-006**.
- Q6 (numbering-mismatch fallback) is **NOT raised** — see Section J.

---

### I.1 P3-006 (drafted) — Hive.close() helper for widget tests with isolate cleanup

> **Folds in the earlier draft from the original Part D prompt; no new findings
> beyond the saga-level synthesis already captured there. Centralization is
> motivated by the rounds-4-7 cycle of re-discovering the same two pitfalls
> across separate test files.**

- **Source:** Phase 1.5 frontend rounds 4–7 saga
- **Added:** 2026-04-27 (drafted; will be added in 1.3 impl PR commit)
- **Severity:** P3
- **Category:** test-infrastructure
- **File (proposed):** `frontend/test/test_helpers/hive_temp_box.dart`
- **Description:** Hive box setup inside a `testWidgets` body must be wrapped
  in `tester.runAsync(...)` because the default `testWidgets` fake-async zone
  blocks `dart:io` calls that Hive performs under the hood (path resolution,
  lock-file creation, native lib init). Symmetrically, teardown must call
  `Hive.close()` **before** `box.deleteFromDisk()` — otherwise the still-open
  box holds a file handle on the temp path and `deleteFromDisk` either no-ops
  silently or throws on Windows. Both pitfalls were re-discovered in three
  separate widget test files across rounds 4-7. Centralize to a single helper
  to prevent re-discovery in any future Hive-using widget test.
- **Fix sketch:** helper API roughly:
  ```dart
  // frontend/test/test_helpers/hive_temp_box.dart
  Future<({Box<T> box, Future<void> Function() teardown})> openTempHiveBox<T>(
    String namePrefix,
  ) async {
    // 1. mktemp dir under Directory.systemTemp (must be inside runAsync)
    // 2. Hive.init(tempDir.path)
    // 3. final box = await Hive.openBox<T>('$namePrefix-${uuid()}');
    // 4. teardown closure:
    //      await Hive.close();          // close FIRST
    //      await box.deleteFromDisk();  // then remove files
    //      await tempDir.delete(recursive: true);
    // Return (box, teardown).
  }
  ```
  Caller pattern:
  ```dart
  testWidgets('saves payload to Hive', (tester) async {
    final result = await tester.runAsync(() => openTempHiveBox<Payload>('autosave'));
    addTearDown(result.teardown);
    // ... use result.box ...
  });
  ```
- **Test addition:** a smoke test under `frontend/test/test_helpers/` that
  opens, writes, closes, and asserts the temp dir is gone after teardown.
- **Status:** pending

---

### I.2 Note for the 1.3 impl prompt

Append the P3-006 entry above (verbatim or near-verbatim) to `polish.md` in the
**same commit** as the 1.3 implementation PR. Place it after `P3-005` and
before the `## Batch dispatch policy` section heading at line 167. Update the
"Backend cosmetics batch (1.5)" / "A11y batch" notes only if the founder
explicitly requests bundling P3-006 — otherwise leave the batch dispatch
section untouched (P3-006 is a test-infrastructure item with no current peers,
so it does not yet belong in any batch).

---

## Section J — Open questions for founder

The following are the consolidated open questions blocking the 1.3 impl PR.
Q1–Q5 are always asked. Q6 is conditional on the §I numbering grep result;
since the grep returned `P3-005` (matches expected), **Q6 is NOT raised**.

> Q7 (idempotency-key hard-require vs defer) was dropped after Part C2a
> confirmed v1 has no short-circuit and the deferral was logged as DEBT-037
> in Part D3.

### Q1 — ETag derivation formula

**Question:** Confirm the ETag for `Publication` resources is derived as
weak ETag of SHA-256 over the tuple `(id, updated_at_iso, config_hash)`, or
counter-propose an alternative.

- Recon-proper recommendation (Part C1): `W/"sha256(id || '' || updated_at_iso || '' || config_hash)"`
  with a fixed `` (US, ASCII 0x1F) separator to avoid collision risk
  from naïve concatenation.
- Counter-proposal slot: e.g. include `version_counter` instead of
  `config_hash`, or weak-vs-strong, or a different hash.

### Q2 — Error code for stale `If-Match`

**Question:** Confirm the JSON body `error_code` value returned with HTTP `412`
on a stale `If-Match`. Candidates:

| Candidate              | Pro                                              | Con                                          |
|------------------------|--------------------------------------------------|----------------------------------------------|
| `PRECONDITION_FAILED`  | Mirrors HTTP semantics 1:1; least surprise       | Generic; gives no domain hint                |
| `STALE_VERSION`        | Most descriptive of the user-facing condition    | Doesn't echo the HTTP layer                  |
| `VERSION_MISMATCH`     | Symmetric with frontend's `VersionMismatchError` | Slightly redundant with HTTP status          |
| `IF_MATCH_FAILED`      | Names the specific header that failed            | Leaks transport-layer detail into error body |

Recon-proper recommendation (Part C2b envelope): **`PRECONDITION_FAILED`** for
HTTP-status parity, but the founder may prefer a domain-flavoured alternative.

### Q3 — v1 backwards-compat policy for missing `If-Match`

**Question:** Should v1 PATCH `/publications/{id}`:

- **(a) Tolerate** a missing `If-Match` header (warn-log, proceed) for the
  first 2 weeks post-deploy, then harden to `428 Precondition Required` —
  tracked as DEBT-038. **OR**
- **(b) Hard-require** `If-Match` from day 1 (return `428` immediately if
  absent).

Recon-proper recommendation (Part C2d): **(a) tolerate**, because old browser
tabs running the pre-1.3 frontend will not send `If-Match` and would otherwise
all `412`-fail on their next autosave at the moment of rollout. The 2-week
hardening is the resolution plan in DEBT-038 (drafted in Part D3).

> Note: choice here directly gates whether DEBT-038 (drafted in Part D3) is
> appended to `DEBT.md` in the impl PR. Q3 = (a) → append DEBT-038.
> Q3 = (b) → drop DEBT-038, and remove the tolerate-missing branch from the
> handler scaffold in Part C2c.

### Q4 — v1 conflict UX on `412`

**Question:** When the frontend receives a `412` from a PATCH, should v1
present:

- **(a) Modal with two buttons** — "Reload" (default focus) and "Save as new
  draft", with the latter forking the in-memory edits into a new draft
  publication. **OR**
- **(b) Reload-only** — single primary action "Reload"; the "save as new
  draft" fork option is deferred to a follow-up sprint.

Recon-proper recommendation (Part C2c): **(b) reload-only** for v1, since the
fork path requires a `POST /publications` from a typed-but-unsaved canonical
document, which has its own validation surface (cell-key collisions, missing
required fields) that has not been recon'd. Defer the fork path until that
sub-recon is done.

> If founder picks (a), the impl prompt needs an additional Section in
> recon-proper covering the fork-from-stale-edits flow.

### Q5 — RU translation for the conflict modal

**Question:** Confirm the Russian (RU) translation for the EN string:

> "This publication has changed since you loaded it. Reload and reapply your
> changes, or save as a new draft."

Translator-suggested candidate (to be confirmed or replaced by founder):

> «Эта публикация была изменена с момента загрузки. Перезагрузите её и
> примените изменения заново, либо сохраните их как новый черновик.»

If Q4 = (b) reload-only, the second clause ("…либо сохраните их как новый
черновик.") is dropped, leaving:

> «Эта публикация была изменена с момента загрузки. Перезагрузите её и
> примените изменения заново.»

### Q6 — (CONDITIONAL — NOT RAISED)

**Trigger:** §I numbering grep returns last entry ≠ `P3-005`.
**Status:** **Not raised.** Grep returned `P3-005` (matches expected). The
P3-006 slot is unambiguously the next number; no founder clarification needed.

---

## Summary Report

```
DOC PATH: docs/recon/phase-1-3-D4-polish-questions.md
polish.md last entry from grep: P3-005
Numbering matches expected (P3-005): yes
P3-006 drafted: yes
Founder questions: Q1-Q5 always (5)
Q6 raised (conditional): no
VERDICT: COMPLETE — pre-recon set complete after this part lands
```

**End of Part D4. Pre-recon set 1.3 complete.**
