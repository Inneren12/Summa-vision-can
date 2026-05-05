# Phase 3.1d Frontend Binding Editor — Locked Milestone Recon

**Status:** LOCKED. Source-of-truth for the entire Phase 3.1d frontend milestone.
**Composes:** backend 3.1d recon + Slice 2 recon + Slice 1a/1b shipped + Slices 3a/3b/4a/4b/5/6 plan.
**Discipline:** individual PR prompts reference this file. Do NOT re-decide architecture per-PR. If implementation reveals contradiction, produce a Recon Delta entry, not a new recon doc.

---

## Source-of-truth hierarchy

1. **Backend 3.1d recon** (`docs/recon/phase-3-1d-recon.md` or backend equivalent — verify actual filename at impl time)
   Snapshot table, capture pipeline, `POST /api/v1/admin/publications/{id}/compare`, publish payload extension, staleness service, response shape.

2. **Frontend Slice 2 recon** (`docs/recon/phase-3-1d-slice-2-recon.md`)
   Canonical `Block.binding`, binding union, `validateBinding`, import/export, `DUPLICATE_BLOCK`, no-shim type ownership.

3. **This wrapper**
   Rollout order, HALT gates, carry-forward constraints, recon-delta discipline, milestone close criteria, locked DEBT carry-forward.

---

## PR map (8 named slices, 9 PRs)

Slice 4 splits into 4a/4b because walker correctness and modal/conflict UX have different failure modes.

| PR | Slice | Status | Scope |
|---|---|---|---|
| PR-01 | 1a | DONE | API client + TS types (comparePublication, publishAdminPublication, error codes) |
| PR-02 | 1b | DONE | Compare badge UI + state machine + locale (14 keys + 2 error keys) |
| PR-03 | 2 | RECON LOCKED, IMPL PENDING | Canonical `Block.binding` schema/validation (P3-033 closes) |
| PR-04 | 3a | PENDING | Binding editor picker shell + cube/semantic/dim discovery clients |
| PR-05 | 3b | PENDING | Resolve preview via server-side proxy (Next.js Route Handler) |
| PR-06 | 4a | PENDING | Single-value walker + publish payload adapter (`bound_blocks`) |
| PR-07 | 4b | PENDING | Republish-to-refresh confirm modal + 412 ETag conflict handling |
| PR-08 | 5 | PENDING | Pre-3.1d "Refresh required" CTA for legacy publications |
| PR-09 | 6 | PENDING | Integration / e2e closeout (happy / 412 conflict / pre-3.1d) |

---

## Hard HALT gates

These gates STOP impl work, not just produce warnings. If a gate trips, file Recon Delta and surface to founder before continuing.

### HALT-1 — Slice 3a discovery endpoints

Before implementing Slice 3a, agent must verify:
- Cube list endpoint exists and is callable
- Semantic_key / mapping list endpoint exists and is callable
- Dimension/member metadata endpoint or metadata source exists
- Frontend admin client can call them
- Browser must NOT receive admin API secrets

If any endpoint or client is missing:
- STOP
- Do NOT build mock-only dropdowns
- Do NOT hardcode cube/semantic_key/member lists

Allowed outcomes when discovery endpoints are absent:
- Dispatch backend discovery endpoint work before Slice 3a impl resumes; OR
- Produce a Recon Delta that narrows Slice 3a scope to editing only existing/imported bindings (e.g. bindings already present in the loaded document or in `chart_config` / import metadata) — no free cube/semantic/dim picker UI in this fallback

Forbidden in either outcome:
- Mock-only picker UI (hardcoded cube/semantic/member lists)
- "Temporary" stubs that ship to production

Founder ack required for the fallback path before Slice 3a impl proceeds under reduced scope.

DEBT-073 tracks this dependency.

### HALT-2 — Resolve preview must use server-side proxy

Slice 3b resolve preview requires admin API credentials to call backend. Browser MUST NOT receive admin secrets.

If implementation surfaces credentials in browser context (e.g. `NEXT_PUBLIC_ADMIN_API_KEY`):
- STOP
- Switch to Next.js server-side Route Handler proxy pattern
- Browser calls `/api/admin/resolve` (own origin, cookie-authed); server-side handler proxies to backend with secret

DEBT-078 tracks this constraint.

### HALT-3 — Slice 4a walker emits only single-value bindings

Slice 4a walker MUST emit only `binding.kind === "single"` into backend `bound_blocks`.

Supported v1 block types:
- `hero_stat`
- `delta_badge` (only with precomputed semantic delta values — see Delta badge rule below)

Slice 4a MUST NOT:
- Expand `time_series` bindings
- Expand `categorical_series` bindings
- Expand `multi_metric` bindings
- Expand `tabular` bindings
- Synthesize composite `block_id` values
- Send multiple `bound_blocks` rows for one multi-value block
- Modify backend snapshot contract

For unsupported binding kinds during walk:
- Skip from publish payload
- Collect explicit warning/deferred reason
- Keep document binding intact (don't strip)

Multi-value support is Phase 3.1e (DEBT-071 storage extension + DEBT-072 resolver iteration).

### HALT-4 — Slice 2 recon contract

Frontend Block interface, `Block.binding` shape, `validateBinding` behavior, and `DUPLICATE_BLOCK` clone semantics MUST match Slice 2 recon. Any divergence found during impl:
- STOP
- Produce Recon Delta documenting code reality vs locked recon
- Do NOT silently adapt

### HALT-5 — Backend clone preservation check

Locked decision #7 (split): Slice 2 frontend acceptance does NOT depend on backend clone preserving `binding`. But Slice 4b's clone-then-republish flow does.

Before any clone-then-republish flow is tested or shipped:
- Verify backend clone path (likely `mutate_document_state_for_clone` or equivalent) preserves `Block.binding` as an unknown block sibling field
- If backend clone strips `binding`, file as backend bug AND exclude clone-then-publish from 3.1d milestone close criteria until fixed (frontend code remains correct in either case)

This check is a targeted backend-clone-preservation verification, NOT a dependency on the full Phase 3.1e multi-value backend recon. 3.1d frontend can close once clone preservation is verified, independently of when 3.1e ships.

---

## Delta badge rule (locked)

`delta_badge` block accepts `single` binding ONLY if the bound semantic_key represents a precomputed semantic delta value.

**Allowed:**
- semantic_key like `delta_bps_since_2022`, `yoy_change_pct`, etc. — server-computed delta
- formatter renders pre-signed numeric value verbatim

**Forbidden:**
- Frontend current-vs-baseline subtraction
- Two-point derived delta computation
- Implicit baseline period
- Any client-side semantic delta computation

If precomputed delta semantic keys are not available in cube metadata, `delta_badge` binding editor support must be:
- Disabled (binding editor doesn't offer the block as bindable), OR
- Deferred (no `delta_badge` in v1 binding editor)

Slice 3a recon will pick disabled vs deferred based on backend support availability.

---

## V1 freshness UI scope (locked)

V1 displays **aggregate publication-level status only**:
- Fresh
- Stale
- Unknown
- Partial / check incomplete
- Refresh required

V1 MUST NOT implement:
- Per-block tint
- Inline block annotations
- Block-level drilldown
- Point-level drilldown
- Public viewer stale display
- List-page dynamic live compare badge

Deferred to Phase 3.1e / Phase 3.2 / UX polish:
- DEBT-075 — per-block tint wrapper
- (no DEBT yet) — drilldown
- (no DEBT yet) — public viewer stale display

---

## Refresh required detection (locked)

Frontend shows "Refresh required" CTA when:
- Local document has at least one valid v1 single binding, AND
- Compare response is `unknown` / `info` with `snapshot_missing`, OR
- Compare response has no usable block-level snapshot rows for local bindable blocks

Frontend MUST NOT assume backend can distinguish:
- Pre-3.1d publication
- Cloned publication
- Publish without `bound_blocks`
- Capture failure that wrote zero rows

All four cases collapse to "Refresh required" in v1. Backend may add expected-bindings persistence in Phase 3.1e to disambiguate; until then, single CTA covers all four.

---

## Carry-forward from Slice 1b (locked, do NOT modify)

Slice 1b shipped behavior. Future PRs MUST NOT modify these unless explicitly scoped:

- Manual compare trigger only — no auto-poll, no focus refresh, no hydrate auto-compare
- No polling
- Aggregate status badge only — no per-block, no drilldown
- Retry CTA shows only for `partial` / check-incomplete state
- i18n keys remain under `publication.compare.*` namespace
- Public viewer remains unchanged
- TopBar layout: `[CLONE] [COMPARE button] [COMPARE badge] [EXPORT ZIP]`
- 4-state machine (idle / loading / success / error) — `partial` is severity bucket, not lifecycle state

If a future slice needs to modify Slice 1b behavior, file Recon Delta first.

---

## Recon Delta discipline

Individual PR prompts MUST NOT create new recon docs.

Each PR prompt references:
- Backend 3.1d recon
- Slice 2 recon
- This milestone wrapper
- Previous Recon Delta entries (if any)

If implementation reveals contradiction with locked recon:
- STOP
- Produce a Recon Delta entry at `docs/recon/deltas/phase-3-1d-NN.md` (sequential numbering)
- Format:
  ```
  # Recon Delta NN — <short title>

  ## Discovery
  What was found that contradicts locked recon.

  ## Contradiction
  Which specific section/decision in locked recon this contradicts.

  ## Impacted slices
  Which downstream PRs are affected.

  ## Minimal decision needed
  Smallest decision required to unblock current PR.

  ## Recommended patch
  Concrete change to locked recon (text replacement, new section, etc.).
  ```
- Surface delta to founder before continuing impl
- After founder review, either:
  - Apply patch to locked recon and proceed, OR
  - Revise impl to avoid contradiction

If no contradiction, continue impl without producing delta.

---

## Out of scope for Phase 3.1d frontend milestone

Explicit deferrals — these MUST NOT ship in Phase 3.1d:

- Multi-value publish/capture/compare (DEBT-071, DEBT-072 — Phase 3.1e)
- Backend snapshot-point storage extension (Phase 3.1e)
- Batch resolver endpoint (DEBT-072 — Phase 3.1e)
- Cube/semantic/dim discovery backend endpoints if absent (DEBT-073 — backend)
- Public viewer stale display
- Scheduled / background compare
- Auto compare on hydrate
- Per-block tint / drilldown (DEBT-075)
- Dedicated recapture-snapshots endpoint
- Symbolic `latest` period semantics
- Flutter parity

If a PR implementation would touch any of these, STOP and surface as scope expansion.

---

## Locked backlog / DEBT carry-forward

| DEBT | Scope | Trigger |
|---|---|---|
| DEBT-071 | Multi-value snapshot extension; storage choice (Option B JSONB points OR Option C point table) | Phase 3.1e backend recon |
| DEBT-072 | Multi-value resolver iteration / batch endpoint | Phase 3.1e backend recon |
| DEBT-073 | Discovery endpoints/clients gap | HALT-1 before Slice 3a |
| DEBT-074 | Closed (text glyphs decision; no icon library) | n/a |
| DEBT-075 | Per-block tint wrapper deferred post-v1 | Phase 3.1e or polish |
| DEBT-076 | Conflict modal factoring for publish reuse | Slice 4b impl |
| DEBT-077 | String freeze enforcement | Slice 6 closeout |
| DEBT-078 | Resolve preview must use server-side proxy | HALT-2 before Slice 3b |
| P3-032 | `parseAdminPublicationError` helper extraction | Defer until 3rd caller (Slice 4) |
| P3-033 | `Binding` union split out of `compare.ts` | Closes inline with Slice 2 impl PR merge |
| P3-039 | `cache_miss` locale wording revision | Slice 3b first user-facing consumer |
| P3-040 | Type-only `BackendApiError` import in compareReducer | Trivial 1-line; bundle with closeout batch |

---

## Milestone close criteria

Phase 3.1d frontend milestone is CLOSED only when ALL of:

1. Slice 1b compare badge still works (no regression)
2. `Block.binding` schema survives import/export/ZIP/DUPLICATE_BLOCK (Slice 2 acceptance)
3. Binding editor can create/edit valid `single` bindings for `hero_stat` (and `delta_badge` if precomputed delta keys available)
4. Resolve preview works through server-side proxy — no browser-exposed admin secret
5. Publish/republish sends valid `bound_blocks` for v1 single bindings (single-value only)
6. Republish-to-refresh confirm modal works
7. 412 publish conflict path follows existing autosave conflict UX pattern
8. Pre-3.1d / no-snapshot publications show "Refresh required" CTA
9. Integration / e2e covers:
   - Happy path: bind → publish → compare fresh/stale
   - 412 conflict path: republish with stale ETag → modal → recover
   - Pre-3.1d refresh path (with explicit binding precondition):
     - Legacy publication initially has no snapshots
     - User adds (or already has) at least one valid v1 `single` binding via the binding editor
     - Republish sends `bound_blocks` based on that binding
     - Subsequent compare returns `fresh` / `stale` instead of `snapshot_missing`
     - If no valid local binding exists, the "Refresh required" CTA must explain that adding a binding is a precondition (not promise magic refresh on a doc with no bindable content)
10. NO multi-value binding sent to backend in 3.1d (HALT-3)
11. NO ad-hoc i18n strings outside `publication.compare.*` and `publication.binding.*` namespaces (DEBT-077)

If any criterion fails, milestone is NOT closed; remaining work is a follow-up PR or carry-over to Phase 3.1e / 3.2.

---

## Cross-reference summary (for impl prompts)

When drafting Slice 3a/3b/4a/4b/5/6 impl prompts, reference:

- This wrapper for: PR scope, HALT gates, V1 UI scope, carry-forward, close criteria, DEBT
- Slice 2 recon for: Block.binding shape, validateBinding behavior, type ownership, clone semantics
- Backend 3.1d recon for: snapshot/compare API contract, capture pipeline, response shapes

If an impl prompt needs information NOT in these three sources, that's a signal a Recon Delta is needed — STOP, surface, don't improvise.
