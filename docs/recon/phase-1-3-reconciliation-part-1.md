# Phase 1.3 Pre-Recon — RECONCILIATION (Part 1 of 3)

**Type:** RECONCILIATION (cross-Part contradiction resolution)
**Scope:** Sections §1–§5 — front matter, inputs, contradictions index, §3 Q3 status, §4 modal name, §5 Q4 scope.
**Other parts:** Part 2 covers §6–§8; Part 3 covers §9–§11.
**Date:** 2026-04-27
**Branch:** `claude/phase-1-3-reconciliation`
**Output:** READ-ONLY reconciliation document — does NOT modify any pre-recon part; resolves cross-Part drift before recon-proper.

---

## §1 Inputs consumed

All 11 Phase 1.3 pre-recon parts read in full before this reconciliation:

| Part  | Path                                            | Role in reconciliation                            |
|-------|-------------------------------------------------|----------------------------------------------------|
| A     | `docs/recon/[phase-1-3-A-backend-inventory.md](http://phase-1-3-A-backend-inventory.md)`   | column ground-truth (referenced for §3, §6, §8)    |
| B     | `docs/recon/[phase-1-3-B-frontend-inventory.md](http://phase-1-3-B-frontend-inventory.md)`  | i18n + modal-location convention (§4, §7)          |
| C1    | `docs/recon/[phase-1-3-C1-etag.md](http://phase-1-3-C1-etag.md)`               | ETag derivation, separator, TOCTOU note (§6, §8)   |
| C2a   | `docs/recon/[phase-1-3-C2a-r16.md](http://phase-1-3-C2a-r16.md)`               | Q7 dropped, DEBT-037 source                        |
| C2b   | `docs/recon/[phase-1-3-C2b-envelope.md](http://phase-1-3-C2b-envelope.md)`          | error_code + i18n key (§7)                         |
| C2c   | `docs/recon/[phase-1-3-C2c-frontend.md](http://phase-1-3-C2c-frontend.md)`          | modal name (`PreconditionFailedModal`) (§4)        |
| C2d   | `docs/recon/[phase-1-3-C2d-backcompat.md](http://phase-1-3-C2d-backcompat.md)`        | DEBT-038, deploy order, Q3 status source (§3)      |
| D1    | `docs/recon/[phase-1-3-D1-tests.md](http://phase-1-3-D1-tests.md)`              | drifted modal name, drifted i18n key (§4, §7)      |
| D2    | `docs/recon/[phase-1-3-D2-migration.md](http://phase-1-3-D2-migration.md)`          | migration audit (no drift)                         |
| D3    | `docs/recon/[phase-1-3-D3-debt.md](http://phase-1-3-D3-debt.md)`               | DEBT numbering (DEBT-039 follow-up, §8)            |
| D4    | `docs/recon/[phase-1-3-D4-polish-questions.md](http://phase-1-3-D4-polish-questions.md)`   | Q1 separator drift, Q3/Q4 founder copy (§5, §6)    |

---

## §2 Contradictions index

Seven cross-Part discrepancies were found between the 11 parts. Each is resolved
in the indicated section across Parts 1–3 of this reconciliation. **No previously
agreed decision is reopened**; the reconciliation only fixes drift where two parts
recorded incompatible derivations of the same fact.

| #   | Topic                                | First part         | Drift in            | Resolution location |
|-----|--------------------------------------|--------------------|---------------------|---------------------|
| §3  | Q3 backcompat status (pending/Confirmed) | D4 §J Q3        | C2d §E.2            | Part 1 — §3         |
| §4  | Modal component name                 | C2c §D.5           | D1 §T-1.3-F-INT-01  | Part 1 — §4         |
| §5  | Q4 v1 conflict UX scope (modal vs reload-only) | C2c §D.3 | D4 §J Q4            | Part 1 — §5         |
| §6  | ETag separator (`|` vs `\x1F`)       | C1 §A.2            | D4 §J Q1            | Part 2 — §6         |
| §7  | 412 i18n key namespace               | C2b §C.4           | D1 footnote on T-1.3-F-INT-01 | Part 2 — §7 |
| §8  | TOCTOU hardening — DEBT not yet allocated | C1 §A.6       | D3 §H (only -037/-038) | Part 2 — §8      |
| §9  | Architecture-MD updates required     | aggregate          | none — gap rather than drift | Part 3 — §9    |

§9 is a "gap not drift": no part contradicts another, but five architecture
documents under `docs/architecture/` need to be updated to reflect Phase 1.3 — the
recon prompt would be incomplete without enumerating them.

§10 (founder action items) and §11 (reconciliation log) are summary sections, not
contradiction resolutions.

---

## §3 Q3 backcompat status — pending, not "Confirmed"

### §3.1 Drift

- **D4 §J Q3** lists Q3 as an **open** founder question with two options: (a)
  tolerate missing `If-Match` (warn-log, accept), (b) hard-require with `428` from
  day 1. D4 explicitly notes: *"choice here directly gates whether DEBT-038 ...
  is appended to `[DEBT.md](http://DEBT.md)` in the impl PR."* Q3 is therefore **not yet
  answered** at the pre-recon stage.

- **C2d §E.2** is written as: *"**Decision:** the v1 backend handler tolerates an
  absent `If-Match` header on `PATCH /publications/{id}`. (Confirmed by founder Q3.)"*
  The parenthetical "Confirmed by founder Q3" is incorrect — Q3 is the question
  itself; C2d cannot have it pre-confirmed.

### §3.2 Resolution

Q3 status is **PENDING founder decision**. The "(Confirmed by founder Q3)"
parenthetical in C2d §E.2 is an authoring artefact and must be read as
"recommended pending Q3" until the founder answers.

The recon-proper prompt MUST list Q3 in the founder-questions block alongside
Q1, Q2, Q4, Q5 with status `PENDING`. Recon-proper MUST NOT proceed to impl
phase until Q3 is answered explicitly in the chat (not assumed from C2d §E.2).

### §3.3 Conditional artefacts gated by Q3

The following artefacts are **provisional** and ship only on Q3 = (a) tolerate:

| Artefact                                                         | Source       | Ships if Q3 = (a) | Ships if Q3 = (b) |
|------------------------------------------------------------------|--------------|-------------------|-------------------|
| Tolerate-absent + warn-log branch in PATCH handler               | C2d §E.2     | yes               | no — replaced by `428 Precondition Required` branch |
| `DEBT-038` entry in `[DEBT.md](http://DEBT.md)`                                    | D3 §H.2      | yes               | no — drop entirely |
| [api.md](http://api.md) "If-Match recommended in v1 + DEBT-038 forward-pointer" wording | C2d §E.6 | yes               | replaced by "If-Match required + 428 documented from day 1" |
| Test T-1.3-B-INT-02 *("PATCH without If-Match warn-logs and accepts")* | D1   | yes               | replaced by 428-asserting test |

D3 §H.2 already flags DEBT-038 as **conditional on Q3**; this reconciliation
ratifies that the conditionality is real and not a residual draft note.

### §3.4 Recommendation (carry-forward, not new)

The pre-recon recommendation remains **(a) tolerate** per C2d §E.5
("fleet-wide instantaneous failure") and D4 §J Q3 ("recon-proper recommendation
... (a) tolerate"). This reconciliation does NOT pick a side — it only restores
the open-question status that C2d §E.2's "Confirmed" parenthetical erased.

---

## §4 Modal component name — `PreconditionFailedModal`

### §4.1 Drift

- **C2c §D.5** explicitly renames the modal:
  *"**Proposed:** `frontend-public/src/components/editor/components/PreconditionFailedModal.tsx` ...
  Part B §1.3 used the working name `StaleVersionModal.tsx`; we adopt
  `PreconditionFailedModal.tsx` instead because the contract code is the stable
  artifact and the user-facing copy lives in i18n, not in the type/file name."*

- **D1 §T-1.3-F-INT-01** still references the pre-rename name: *"Assert: (a) the
  new `StaleVersionModal` (proposed location
  `frontend-public/src/components/editor/components/StaleVersionModal.tsx`,
  Part B §1.3) appears in the DOM..."*

D1 was authored against Part B's working name and did not pick up C2c's rename.
This is a forward-reference drift, not a re-decision.

### §4.2 Resolution

Canonical name across the entire 1.3 contract: **`PreconditionFailedModal`**.

| Aspect                  | Canonical value                                                       |
|-------------------------|-----------------------------------------------------------------------|
| Component class name    | `PreconditionFailedModal`                                             |
| File path               | `frontend-public/src/components/editor/components/PreconditionFailedModal.tsx` |
| Source-of-truth part    | C2c §D.5                                                              |
| Trigger discriminator   | `err instanceof BackendApiError && err.code === 'PRECONDITION_FAILED'` |

Rationale (carry-forward from C2c §D.5): the component name mirrors the backend
`error_code` so the discriminator the `.catch` branch tests and the React
component name are 1:1 greppable across the boundary. "StaleVersion" is UX
framing; the stable artefact is the wire contract code.

### §4.3 Carry-forward fix list (for recon-proper / impl prompt)

The recon-proper prompt MUST replace `StaleVersionModal` with
`PreconditionFailedModal` in every test name, file path, and assertion derived
from D1:

- D1 §T-1.3-F-INT-01 — modal name, file path, DOM-presence assertion
- Any other D1/D2/D3/D4 site that imports or asserts the modal symbol

Part B §1.3's working name `StaleVersionModal.tsx` is **explicitly superseded**
by C2c §D.5; recon-proper does not need to update Part B (it is a discovery
document and accurately records what was conjectured at that moment), but every
*forward*-looking artefact (impl prompt, test plan, file scaffolding) uses
`PreconditionFailedModal`.

---

## §5 Q4 v1 conflict UX scope — ESCALATE

### §5.1 Drift

- **C2c §D.3** designs a **two-button modal** as the v1 surface:

  > "A **modal dialog** with exactly two action buttons:
  > | Button | Effect |
  > | **Reload (lose my changes)** | ... *Default focus.* |
  > | **Save as new draft** | Calls existing clone endpoint ... |"

  C2c §D.6 then specifies the full state matrix for both buttons including the
  Save-as-new-draft → `cloneAdminPublication` → fresh-PATCH flow.

- **D4 §J Q4** treats v1 conflict UX as an **open question** and explicitly
  **recommends (b) reload-only**:

  > "Recon-proper recommendation (Part C2c): **(b) reload-only** for v1, since
  > the fork path requires a `POST /publications` from a typed-but-unsaved
  > canonical document, which has its own validation surface ... that has not
  > been recon'd. Defer the fork path until that sub-recon is done."

  D4 attributes the reload-only recommendation to Part C2c, but C2c itself
  designs a two-button modal — D4's attribution is incorrect.

C2c (designed two buttons) and D4 (recommends one button, citing C2c as source)
disagree on the v1 scope.

### §5.2 Why this is an ESCALATION, not a unilateral pick

The two parts diverge on a **scope** question, not a derivation question:

- C2c describes the design *surface area* the founder asked for.
- D4 narrows that surface citing a validation-surface gap (the fork path's
  `POST /publications` from local state has unmapped failure modes — cell-key
  collisions, missing required fields, validator state).

Either is defensible; the choice is a workflow / risk-tolerance call, not a
technical-correctness call. This reconciliation document is not authorised to
collapse a scope question silently.

### §5.3 Resolution: ESCALATE Q4 to founder

Q4 status: **ESCALATED — pending explicit founder decision**.

The founder MUST pick exactly one of:

- **(a) Two-button modal per C2c §D.3 + §D.6** (Reload + Save-as-new-draft).
  Ships full clone-then-PATCH fork path. Implementation cost: higher
  (sub-recon needed on fork-path validation surface).
- **(b) Reload-only per D4 §J Q4 recommendation** (single primary "Reload"
  action; fork path deferred to a follow-up sprint).
  Implementation cost: lower; modal degenerates to an alert with one CTA.

Recon-proper MUST NOT proceed to impl until Q4 is answered. The Q4 entry in the
founder-questions block of recon-proper repeats this dichotomy verbatim.

### §5.4 Conditional artefacts gated by Q4

| Artefact                                                  | Q4 = (a) two-button | Q4 = (b) reload-only |
|-----------------------------------------------------------|---------------------|----------------------|
| `PreconditionFailedModal.tsx` button count                | 2                   | 1                    |
| C2c §D.6 "Save as new draft — implementation note" steps  | ships               | dropped               |
| Sub-recon on fork-path validation surface                 | required before impl | not needed           |
| Q5 RU translation second clause (*"…либо сохраните их как новый черновик."*) | included | dropped (per D4 §J Q5) |
| D1 test for "Save as draft" button DOM presence           | required             | dropped               |

### §5.5 No fallback default

This reconciliation **does not** select a fallback default for Q4. The recon
prompt must block on the founder's answer; choosing silently would either
overship (impl Q4=a when founder wanted b) or underdeliver (impl Q4=b when
founder wanted a) — both costly to reverse.

---

End of Part 1. Sections §1–§5 added by Part 1; §6–§8 follow in Part 2; §9–§11 follow in Part 3.
