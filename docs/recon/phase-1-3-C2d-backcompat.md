# Phase 1.3 — Part C2d — Backwards Compatibility Policy & Deploy Order

**Type:** DESIGN (4 of 4 micro-splits of original Part C2)
**Scope:** Section E only — backcompat policy for missing `If-Match` and deploy order.
**Date:** 2026-04-27
**Branch:** `claude/backcompat-policy-design-CKQ4k`
**Git remote:** `http://local_proxy@127.0.0.1:44571/git/Inneren12/Summa-vision-can`

**Cited references:**
- Part C1 (`docs/recon/phase-1-3-C1-etag.md`) — ETag/`If-Match` wire contract.
- Part C2a (`docs/recon/phase-1-3-C2a-r16.md`) — R16 idempotency tension; uniform 412 client treatment.
- Part C2b (`docs/recon/phase-1-3-C2b-envelope.md`) — `PRECONDITION_FAILED` envelope.
- Part C2c (`docs/recon/phase-1-3-C2c-frontend.md`) — autosave path, modal handling.

---

## Section E — Backwards Compatibility Policy & Deploy Order

### E.1 The compatibility hazard

The Part C1 contract introduces two coupled changes to `PATCH /publications/{id}`:

1. **Backend** starts emitting an `ETag` header on `GET` and accepting `If-Match` on `PATCH`.
2. **Frontend** starts reading the `ETag` from the GET response and echoing it back as
   `If-Match` on every autosave PATCH.

These two changes ship in different artefacts (backend image vs. SPA bundle) and therefore
land at different wall-clock moments. During the gap — and for the lifetime of any browser
tab opened *before* the frontend rollout reaches that user — clients will issue PATCHes
**without** an `If-Match` header. With autosave firing every few seconds (Part C2c §D.1),
even a short gap touches a non-trivial fleet of in-flight tabs.

If the new backend treated a missing `If-Match` as a hard precondition violation
(e.g., responded `428 Precondition Required` from day 1), every one of those open tabs
would 412/428-fail on its next autosave tick. The Part C2c modal would fire across the
entire user base simultaneously, with no genuine concurrent edit to resolve — purely a
rollout artefact.

### E.2 Policy: tolerate missing `If-Match` for v1

**Decision:** the v1 backend handler tolerates an absent `If-Match` header on
`PATCH /publications/{id}`. (Confirmed by founder Q3.)

| Condition                                 | v1 behavior                                                        |
|-------------------------------------------|--------------------------------------------------------------------|
| `If-Match` present **and** matches server ETag | Apply mutation; return new ETag. (Normal path.)                |
| `If-Match` present **and** mismatches     | `412 Precondition Failed` with `PRECONDITION_FAILED` envelope (Part C2b). |
| `If-Match` **absent**                     | Warn-log; **accept** the request; proceed without precondition check; return new ETag. |

The "absent" branch is the backcompat affordance. It is intentionally narrow:

- The check only short-circuits on **header absence**. An empty-string `If-Match: ""` or a
  malformed value still falls into the "mismatch" branch and 412s — only a wholly missing
  header is tolerated.
- The warn-log is mandatory, not optional. It is the operator's signal that pre-rollout
  tabs are still in the field; once the warn-log volume drops to zero (or to negligible
  background noise from automation/curl users), the hardening step in E.5 becomes safe.
- Toleration does **not** bypass any other invariant — auth, validation, ownership checks,
  and the publication-state machine all still apply.

Why "warn" and not "info": the absence is a deviation from the documented contract that
will become an error in a future release (E.5). Logging at `warn` keeps it visible in
default log filters without polluting `error` rates / SLO alarms.

### E.3 DEBT entry

> **DEBT-038 (proposed):** *"PATCH publications tolerates missing `If-Match` for v1 deploy compat"*
>
> - **Severity:** Low
> - **Category:** tech-debt-hardening
> - **Symptom:** A `PATCH /publications/{id}` request omitting the `If-Match` header is
>   accepted and applied without a precondition check, instead of being rejected as a
>   protocol violation. The handler emits a `warn`-level log line on every such request.
> - **Cause:** Intentional v1 backcompat shim to absorb in-flight browser tabs that pre-date
>   the frontend rollout of `If-Match` echo (Part C2c §D.1).
> - **Resolution path:** After **two weeks of clean deploy** (frontend rolled out
>   everywhere; pre-rollout tab population has refreshed naturally; `warn`-log volume for
>   "missing If-Match on PATCH publications" has dropped to negligible), change the handler
>   to **require** `If-Match` and return **`428 Precondition Required`** if absent.
>   Update `docs/modules/api.md` to document `If-Match` as a required header on
>   `PATCH /publications/{id}` and to enumerate the `428` response. Remove the warn-log
>   branch.
> - **Verification before flipping:** read the warn-log metric for the trailing 7 days
>   prior to the flip; if non-negligible, extend the toleration window rather than
>   breaking active clients.
> - **Out of scope for v1:** any change to the `If-Match` mismatch branch (still `412`),
>   any change to the GET-side `ETag` emission, any change to the Part C2c modal.

DEBT number rationale: DEBT-037 is reserved by Part C2a for the idempotency-key
short-circuit work; DEBT-038 is the next sequential identifier (highest existing in
`docs/` is 037 per `grep -roh "DEBT-[0-9]+" docs/`).

### E.4 Deploy order

The toleration policy makes the deploy order one-directional and uncoordinated:

1. **Backend first.**
   - Ships `ETag` on GET, `If-Match` acceptance on PATCH, and the warn-log + tolerate-
     absent branch.
   - From this moment, both old frontends (no `If-Match` echo) and new frontends
     (echoing `If-Match`) are served correctly.
   - Old frontend behavior is unchanged from the user's perspective; the only side effect
     is a stream of `warn` log entries that the operator expects and monitors.

2. **Frontend second.**
   - Ships `ETag` capture on GET, `If-Match` echo on PATCH, the `PRECONDITION_FAILED`
     branch in `performSave` (Part C2c §D.1), and the `PreconditionFailedModal` (Part C2c
     §D.5).
   - As CDN cache invalidates and users refresh, the warn-log volume falls.

**No coordinated rollback is needed.** Each direction degrades safely:

| Scenario                                  | Behavior                                                            |
|-------------------------------------------|---------------------------------------------------------------------|
| Backend rolled back, frontend new         | New frontend sends `If-Match`; old backend ignores unknown header (RFC 7230 §3.2.4 — unknown request headers are not an error). PATCH proceeds without precondition check, identical to pre-1.3 behavior. |
| Backend new, frontend rolled back         | Old frontend sends no `If-Match`; new backend takes the tolerate-absent branch. Warn-log fires; PATCH proceeds. (This is exactly the steady-state rollout window.) |
| Both rolled back                          | Pre-1.3 baseline. No regression.                                    |
| Both rolled forward                       | Full ETag-guarded path; 412 surfaces only on real concurrent edits / lost-response retries (Part C2a §B). |

The contract is therefore **forward-compatible from the moment the backend ships**, which
is the only ordering constraint the v1 design imposes.

### E.5 Hardening: why not 428 from day 1

A "strict" alternative was considered: have the v1 backend reject a missing `If-Match`
with `428 Precondition Required` (RFC 6585 §3) immediately. It is rejected for v1 for
three reasons:

1. **Fleet-wide instantaneous failure.** Per Part C2c §D.1, autosave fires every few
   seconds inside `performSave`. An old tab that has been open across the deploy boundary
   would 428-fail on its very next tick. Multiplied across the open-tab population at
   deploy time, this is a synchronized failure event with no genuine conflict driving any
   of it — purely a rollout artefact.
2. **Modal cannot distinguish rollout from conflict.** The Part C2c modal is designed for
   the conflict case (Reload vs. Save-as-new-draft). Surfacing it to a user whose only
   "sin" is having an open tab from before the deploy degrades the modal's signal: users
   trained on rollout-noise modals will dismiss real conflict modals reflexively.
3. **428 is a one-way door at the wrong moment.** Once the strict handler is live, every
   pre-deploy tab is broken until manually reloaded. Users do not reload tabs on a
   schedule; some sit open for days. There is no operator lever to "soften" the
   transition once 428 is shipped — only a backend rollback, which throws away the new
   ETag emission too.

Tolerate-then-harden is the operator-friendlier path: ship the contract, let the tab
population refresh naturally, **then** flip to 428 when the warn-log says it is safe
(E.3 resolution path). The eventual end-state is identical to the strict alternative;
only the transition is gentler.

### E.6 What the policy does **not** change

- **412 behavior is unchanged.** A *mismatched* `If-Match` still returns the
  `PRECONDITION_FAILED` envelope from Part C2b and triggers the Part C2c modal. The
  toleration applies only to *absent* `If-Match`.
- **R16 decision is unchanged.** Per Part C2a, there is no idempotency-key short-circuit
  in v1. The tolerate-absent branch is **not** a backdoor for retried-after-lost-response
  PATCHes; clients still send `If-Match` on retries, and a stale `If-Match` still 412s.
- **Frontend has no toleration logic to write.** All toleration lives server-side. The
  Part C2c `performSave` branch is unconditional: it always sends `If-Match` once the new
  frontend is loaded.
- **`docs/modules/api.md` is not updated to mark `If-Match` "required" in v1.** It is
  documented as **recommended**, with a forward-pointer to DEBT-038's flip date. The
  "required + 428" wording lands when DEBT-038 resolves.

### E.7 Boundaries with C2a / C2b / C2c

- **C2a (R16):** orthogonal. R16 is about retries with stale `If-Match`; E is about
  requests with no `If-Match`. Both branches coexist in the handler: (no header → tolerate
  + warn-log) is checked before (header → ETag compare → 412 on mismatch).
- **C2b (envelope):** the tolerate-absent branch returns the normal success envelope, not
  a `PRECONDITION_FAILED` envelope. The `PRECONDITION_FAILED` envelope is reserved for
  real mismatch.
- **C2c (frontend):** the modal never fires from the toleration branch (no error envelope
  is ever produced). The new frontend is unaware of the toleration policy; from its
  perspective, every PATCH it sends carries `If-Match`, so the toleration code is dead
  code on the new-frontend / new-backend path.

---

## Summary Report

```
DOC PATH: docs/recon/phase-1-3-C2d-backcompat.md
Policy: tolerate missing If-Match in v1 (warn-log, accept, no ETag check)
DEBT logged: DEBT-038 (next free; DEBT-037 reserved by C2a)
Deploy order: backend first, frontend second; no coordinated rollback
Hardening: flip to 428 Precondition Required after 2 weeks clean (api.md updated then)
Boundary: 412 on mismatch unchanged; toleration applies to absent header only
VERDICT: COMPLETE
```

---

**End of Part C2d.**
