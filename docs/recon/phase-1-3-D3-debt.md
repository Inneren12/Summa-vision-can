# Phase 1.3 Pre-Recon Part D3 — DEBT Additions (Section H)

**Type:** RECON FINALIZATION (3 of 4 micro-splits of original Part D)
**Scope:** Section H only — DEBT entries to be added in 1.3 impl PR.
**Other splits:** D1 (test plan), D2 (migration & rollout), D4 (polish + founder questions).
**Date:** 2026-04-27
**Branch:** `claude/add-debt-section-h-CRfsZ`
**Git remote:** `http://local_proxy@127.0.0.1:44945/git/Inneren12/Summa-vision-can`

**Prereqs read:**
- Part C2a — `docs/recon/phase-1-3-C2a-r16.md` (idempotency-key short-circuit decision).
- Part C2d — `docs/recon/phase-1-3-C2d-backcompat.md` (tolerate-missing `If-Match` policy).

This document is **READ-ONLY**. The two DEBT entries are **drafted** here for
review only. They are NOT appended to `DEBT.md` in this recon PR. The impl
prompt for 1.3 will append both entries to `DEBT.md` in the SAME commit as the
1.3 implementation PR (not in pre-recon, not in recon-proper).

---

## Section H — DEBT additions

### H.0 Fresh `DEBT.md` numbering grep

Command (verbatim from prompt §1):

```bash
grep -E '^### DEBT-[0-9]+:' DEBT.md | tail -3
```

Output (executed 2026-04-27 against `DEBT.md` at HEAD of branch
`claude/add-debt-section-h-CRfsZ`):

```
### DEBT-026: Lossy round-trip between CanonicalDocument and AdminPublicationResponse
### DEBT-035: Parallel config_hash computation in pipeline + lineage helper
### DEBT-036: Verify crop zone dimensions against current platform layouts
```

**Highest existing DEBT number:** `DEBT-036`.

Therefore for the impl prompt:
- `N`   → **DEBT-037** (the no-idempotency-short-circuit entry, §H.1).
- `N+1` → **DEBT-038** (the tolerate-missing-`If-Match` entry, §H.2; conditional
  on Q3 = "tolerate" — see Part D4 founder-question summary).

> Cross-ref note: Part D2 §G already references `DEBT-038` for the tolerate-missing
> policy; that reference was authored against the same DEBT-036 high-water-mark
> and remains consistent with this fresh grep.

---

### H.1 DEBT-037 (drafted) — "PATCH publications has no idempotency-key short-circuit"

- **Status:** Active
- **Severity:** Low
- **Category:** api-correctness-edge-case
- **Source:** Phase 1.3 recon, decision in Part C2a.
- **Description:** v1 of optimistic concurrency applies the ETag check
  unconditionally on every PATCH. A legitimate retry of an already-successful
  PATCH (e.g. network drop on the response leg) will return `412 Precondition
  Failed` because the server's stored ETag has advanced past the client's
  `If-Match`. The client then treats the 412 as "reload and retry" — which is
  correct behaviour for both a genuine concurrent edit AND for the rare network
  retry, but it adds one extra round trip per dropped response.
- **Resolution:** when HTTP idempotency-key infrastructure lands project-wide,
  integrate a cache-hit short-circuit before the ETag check. **Memory snapshot
  of recon decision (Part C2a):** cache hit MUST short-circuit BEFORE the ETag
  check, returning the cached `200 OK`; the ETag check applies only on cache
  miss. This ordering is load-bearing — reversing it re-introduces the spurious
  412 on retry.

---

### H.2 DEBT-038 (drafted, **conditional on Q3 = tolerate**) — "PATCH publications tolerates missing If-Match for v1 deploy compat"

- **Status:** Active
- **Severity:** Low
- **Category:** tech-debt-hardening
- **Source:** Phase 1.3 recon, decision in Part C2d.
- **Description:** v1 server tolerates an absent `If-Match` header on PATCH
  (warn-log, proceed without ETag check) to avoid breaking old browser tabs
  mid-deploy. Without this tolerance, every open tab still running the old
  frontend would `412`-fail on its next autosave the moment the new backend
  rolls out, producing a thundering herd of "reload and retry" prompts during
  the deploy window.
- **Resolution:** after 2 weeks of clean deploy (frontend rolled out
  everywhere, AND no `warn`-log entries for the missing-`If-Match` codepath
  for 7 consecutive days), change the handler to require `If-Match` and
  return `428 Precondition Required` if the header is absent. Update
  `docs/modules/api.md` to reflect the new strictness, and remove the
  warn-log emitter.

---

### H.3 DO NOT bundle

- **DEBT-034** ("Admin/publication backend envelopes are not yet unified") —
  separate scope, owned by a future envelope-unification sprint. Do **NOT**
  touch DEBT-034 in the 1.3 impl PR. The 1.3 impl PR may reference DEBT-034
  in commit-message context but must not modify the DEBT-034 entry's status,
  description, or resolution plan.

---

### H.4 Note for the 1.3 impl prompt

Both DEBT entries (DEBT-037 and DEBT-038, conditional on Q3) are to be
appended to `DEBT.md` in the **same commit** as the 1.3 impl PR. They are
explicitly **not** to be appended in:

- the pre-recon PR (this PR), or
- the recon-proper PR (the next one),

because the resolution wording is calibrated against shipped v1 behaviour and
should land atomically with that behaviour.

---

## Summary Report

```
DOC PATH: docs/recon/phase-1-3-D3-debt.md
Highest existing DEBT (from grep): DEBT-036
DEBT-N drafted (no idempotency short-circuit): yes (= DEBT-037)
DEBT-N+1 drafted (If-Match tolerance, conditional Q3): yes (= DEBT-038)
Bundle DEBT-034: no
VERDICT: COMPLETE
```

**End of Part D3.**
