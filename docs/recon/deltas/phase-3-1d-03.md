# Recon Delta 03 — Phase 3.1d concurrency on publish + auto-refresh

**File path on commit:** `docs/recon/deltas/phase-3-1d-03.md`
**Status:** **ACKED** by founder 2026-05-07
**Affects:** Slice 4b (PR-07), milestone wrapper, BACKEND_API_INVENTORY.md, FRONTEND_AUTOSAVE_ARCHITECTURE.md
**Discovered by:** preflight inventory `claude/preflight-inventory-review-FEl1b` (2026-05-07)

---

## Surfaced

Phase 3.1d preflight inventory (Slice 4b/5/6 closeout) revealed two gaps against locked recon §2.3:

1. **412 on publish is unimplemented end-to-end.** Frontend `usePublishAction.confirm` does not forward `ifMatch`; backend `publish_publication` does not honor `If-Match`; response does not declare 412. Locked recon §2.3 Q5 said "explicit refresh = republish via POST /publish" but did not lock concurrency semantics on that POST. Phase 1.3 ETag invariants were scoped to PATCH only (DEBT-042, DEBT-043).

2. **Manual-trigger-only compare invariant blocks UX after publish.** Recon §2.3 LOCK: "compare is operator-triggered, never automatic." After successful publish, badge keeps showing prior severity until operator clicks Compare again. Founder decision (2026-05-07): compare auto-fires after publish-success.

Both fall inside Slice 4b scope (locked title: "Republish-to-refresh confirm modal + 412 ETag conflict handling"). Single PR-07 ships both.

---

## Change

### Concurrency invariant on publish (extends §2.3)

**Before:** ETag concurrency check applies to PATCH `/api/v1/admin/publications/{id}` only. POST `/api/v1/admin/publications/{id}/publish` accepts no `If-Match`, returns no 412.

**After:**
- `POST /publish` reads optional `If-Match` header.
- If header present and ETag mismatches current row state → respond 412 Precondition Failed with same envelope shape as PATCH 412 (`{ error: { code: "PRECONDITION_FAILED", message: <i18n key>, current_etag: <strong-etag> } }`).
- If header absent → proceed (v1 tolerance), emit `Deprecation: true` response header + warn-log entry (mirror DEBT-042 pattern).
- Successful publish (200) returns response header `ETag: <new-strong-etag>` derived from post-publish row tuple `(id, updated_at, config_hash OR "")` per Phase 1.3 §K.

**Frontend:**
- `usePublishAction.confirm` calls `publishAdminPublication(publicationId, payload, { ifMatch: etagRef.current })`.
- `publishAdminPublication` already supports `opts.ifMatch` (admin.ts:250) — no signature change.
- 412 response → `setPreconditionFailedModal({ open: true, serverEtag: <from response> })`. Modal mounts at editor/index.tsx:1486 (existing).
- Modal copy distinct from PATCH path: new i18n keys `publication.precondition_failed.body_publish` EN+RU.

### Compare auto-trigger after publish (relaxes §2.3)

**Before:** `useCompareState` lives in `TopBar.tsx:110`. Compare invoked only by `CompareButton onClick` or `compare-error-retry` button. No shared seam.

**After:**
- `useCompareState` lifted to `editor/index.tsx` (editor root). Hook output (`compareState`, `compare`, `reset`) flows to `TopBar` via props.
- `compare` callback also passed to `usePublishAction({ onPublishSuccess })`.
- On publish 200: `onPublishSuccess` invokes `compare()` **first**, then dispatches `MARK_PUBLISHED`. Order rationale: badge transitions to "Comparing…" UI immediately; workflow transition is orthogonal and dispatches synchronously.
- On publish 412 / 404 / generic error: `compare()` NOT invoked. Modal or toast handles error UX.
- Compare auto-trigger does NOT fire on initial mount (preserves recon §2.3 explicit-trigger invariant for the no-publish case).

---

## Affects

| File | Change |
|---|---|
| `docs/architecture/BACKEND_API_INVENTORY.md` | Publish endpoint declares optional `If-Match`, response `ETag` header, 412 status code |
| `docs/architecture/FRONTEND_AUTOSAVE_ARCHITECTURE.md` §7 | PreconditionFailedModal mount points list publish path; compare auto-trigger sequencing diagram |
| `docs/recon/phase-3-1d-recon.md` §2.3 | Q5 LOCK extension noted with reference to this delta |
| `docs/recon/phase-3-1d-milestone-wrapper.md` PR-07 row | Scope expanded to include auto-refresh; status PENDING → IN PROGRESS when impl prompt dispatched |
| `polish.md` | No new entries (P3-038 → P3-043 already lands separately) |
| `DEBT.md` | New entry DEBT-NN8: publish endpoint tolerates missing If-Match for v1 deploy compat (mirrors DEBT-042 for PATCH) |

DEBT-076 (modal factoring for publish reuse) → CLOSED by PR-07 (modal reused via existing `setPreconditionFailedModal({open, serverEtag})` state, no factoring required — was overscoped at recon time).

---

## DEBT-NN8 entry (founder pastes into DEBT.md, agent re-greps max ID first)

```markdown
### DEBT-NN8: POST /publish tolerates missing If-Match for v1 deploy compat

- **Source:** Phase 3.1d Recon Delta 03 (Slice 4b implementation, founder lock 2026-05-07)
- **Added:** 2026-05-07
- **Severity:** low
- **Category:** architecture
- **Status:** active
- **Description:** v1 server tolerates an absent If-Match header on POST /publish (warn-log, proceed without ETag check, response includes `Deprecation: true` header) to avoid breaking any external/scripted publish caller mid-deploy. Frontend public + Flutter admin both forward If-Match starting from PR-07; only ad-hoc curl/script callers are exposed to tolerance window.
- **Impact:** Operator-visible warn-log noise during the rollout window if any external publish callers exist. Tolerance-period publishes do not get optimistic-concurrency protection.
- **Resolution:** after two weeks of clean deploy (frontend + Flutter rolled out everywhere AND no warn-log entries for the missing-If-Match codepath on POST /publish for 7 consecutive days), change the handler to require If-Match and return 428 Precondition Required if absent. Update `docs/architecture/BACKEND_API_INVENTORY.md` to reflect the new strictness. Remove the warn-log emitter and the `Deprecation: true` header.
- **Target:** Phase 4 (after 2026-06-04 if clean-window criteria met)
```

---

## Resolved

Status flips to **RESOLVED** when:
1. PR-07 merged into `main`
2. BACKEND_API_INVENTORY.md publish row updated (this delta lists the exact diff in PR-07 spec)
3. FRONTEND_AUTOSAVE_ARCHITECTURE.md §7 references publish path PreconditionFailedModal
4. DEBT-NN8 entered in DEBT.md (whatever the actual next free ID is on merge day)

---

## Open questions — none

All four locks resolved by founder 2026-05-07:
- Lift target = Option A (editor root), prop drilling acceptable
- Auto-refresh sequencing = `compare()` first, then `MARK_PUBLISHED`
- `If-Match` requirement = optional v1 with `Deprecation: true` header
- 412 modal copy = publish-specific i18n keys

---

**End of Recon Delta 03.**
