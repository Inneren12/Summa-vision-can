# Phase 1.3 Pre-Recon — RECONCILIATION (Part 2 of 3)

**Type:** RECONCILIATION (cross-Part contradiction resolution)
**Scope:** Sections §6–§8 — separator choice, i18n key, TOCTOU DEBT-039.
**Other parts:** Part 1 covers §1–§5; Part 3 covers §9–§11.
**Date:** 2026-04-27
**Branch:** `claude/phase-1-3-reconciliation`
**Continuation:** front matter, inputs, contradictions index, and §3–§5 are in `[phase-1-3-RECONCILIATION-1.md](http://phase-1-3-RECONCILIATION-1.md)`. Part 2 inherits all definitions and conventions from Part 1 without restating them.

---

## §6 ETag separator — `|` (pipe)

### §6.1 Drift

- **C1 §A.2** defines the derivation function with a literal pipe separator:

  ```python
  raw = f"{[pub.id](http://pub.id)}|{timestamp}|{config}"
  digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
  return f'W/"{digest}"'
  ```

  The separator is `|` (ASCII 0x7C), used twice between the three components
  `(id, timestamp, config_hash)`.

- **D4 §J Q1** proposes a different separator:

  > "Recon-proper recommendation (Part C1): `W/"sha256(id || '' || updated_at_iso || '' || config_hash)"`
  > with a fixed `\x1F` (US, ASCII 0x1F) separator to avoid collision risk
  > from naïve concatenation."

  D4 attributes the `\x1F` separator to Part C1, but C1 §A.2 uses `|`. The
  attribution is incorrect; D4's `\x1F` is a *new* proposal floated at the
  founder-question stage, not a carry-forward of a C1 decision.

### §6.2 Resolution: keep `|` per C1 §A.2

Canonical separator: **`|` (ASCII 0x7C)**, exactly as C1 §A.2 specifies.

| Aspect              | Canonical value                                   |
|---------------------|---------------------------------------------------|
| Separator literal   | `|` (single ASCII pipe, 0x7C)                     |
| Position            | Between `id`/`timestamp` and between `timestamp`/`config_hash` (two occurrences) |
| Source              | C1 §A.2 verbatim                                  |
| Reference impl      | `f"{[pub.id](http://pub.id)}|{timestamp}|{config}"`                |

### §6.3 Why not `\x1F`

D4's `\x1F` (US, ASCII 0x1F) carries a colourable theoretical motivation —
"avoid collision risk from naïve concatenation" — but in this specific input
domain the motivation does not apply:

1. **`id` is an integer.** `[pub.id](http://pub.id)` serialises as `"1"`, `"42"`, `"12345"` —
   ASCII digits, no separator characters of any kind.
2. **`timestamp` is `datetime.isoformat()` output.** ISO-8601 strings contain
   `-`, `:`, `T`, `+`, `.`, and digits. Crucially they do **not** contain `|`.
3. **`config_hash` is a 64-char hex string** (per Part A §1.2 line 90:
   `String(64)`). Hex strings contain only `0-9a-f` — no `|`.

There is no input where any field can contain the literal `|`, so a
`(a, b, c)` tuple with pipe separators is unambiguous: the parse `a|b|c` is
injective on this domain. The only collision attack vector for naïve
concatenation is when one field's representation can contain the separator;
none of the three fields here can. `\x1F` would be defensible if e.g.
`config_hash` were ever changed to free-form text — but D2 §G.1 confirms the
`String(64)` hex constraint is unchanged in 1.3.

Adopting `\x1F` would be a protocol-level change for a non-existent risk and
would diverge from the C1 reference implementation that recon-proper / impl
test scaffolding will copy verbatim.

### §6.4 Q1 status

Q1 (founder-side question on derivation formula) is **PENDING** — the founder
still confirms the overall tuple `(id, updated_at_iso, config_hash)` and the
weak-vs-strong choice. This reconciliation only resolves the **separator**
sub-question inside Q1: separator = `|` (pipe), per C1 §A.2.

If the founder answers Q1 with a counter-proposal that changes the tuple
composition (e.g., "include `version_counter` instead of `config_hash`"),
recon-proper repeats §6 against the new tuple. The separator decision is stable
across tuple changes because the same domain analysis (§6.3) applies to any
tuple of `(int, ISO-8601, hex)` shapes.

---

## §7 412 i18n key — `errors.backend.precondition_failed`

### §7.1 Drift

- **C2b §C.4** specifies the i18n key namespace and casing definitively:

  > "**Key:** `errors.backend.precondition_failed`
  >
  > **Justification:** Part B §1.2 confirmed the DEBT-030 hybrid (Option C) at
  > `frontend-public/src/lib/api/errorCodes.ts:108` — publication-specific UX
  > messages live under `publication.*`; cross-cutting / protocol-level codes
  > live under `errors.backend.*`. A 412 precondition failure is a
  > **protocol-level** concurrency signal, not a publication-domain UX event
  > (the same code would apply to any future ETag-guarded resource), so it
  > belongs under `errors.backend.*`."

  C2b also pins `snake_case` for the leaf (`precondition_failed`), citing the
  three existing `errors.backend.*` snake_case leaves in B §1.4
  (`auth_api_key_missing`, `auth_api_key_invalid`, `auth_admin_rate_limited`)
  as the precedent.

- **D1 §T-1.3-F-INT-01 footnote** softens this into an open question:

  > "namespace. Both `publication.precondition_failed.*` and
  > `errors.backend.precondition_failed` would be defensible; the prompt
  > specifies `errors.backend.precondition_failed`, so this test asserts that..."

  D1 frames the namespace as "either is defensible" — but C2b §C.4 already
  resolved the question with a non-trivial reason (protocol-level vs
  publication-domain). The C2b reasoning is what makes the choice
  *non-defensibly-either*: a future ETag-guarded resource that is not a
  publication would still emit `PRECONDITION_FAILED`, and surfacing that under
  `publication.*` would be incorrect.

The D1 footnote's hedge is authoring drift; C2b §C.4 is the source of truth.

### §7.2 Resolution

Canonical i18n key for the 412 modal copy: **`errors.backend.precondition_failed`**.

| Aspect                            | Canonical value                          |
|-----------------------------------|------------------------------------------|
| Full key                          | `errors.backend.precondition_failed`     |
| Namespace                         | `errors.backend.*` (cross-cutting / protocol) |
| Leaf casing                       | `snake_case` (precedent: 3 existing peer keys per B §1.4) |
| Source-of-truth part              | C2b §C.4                                 |
| Where the EN string lives         | `frontend-public/messages/en.json`       |
| Where the RU string lives         | `frontend-public/messages/ru.json` (value pending Q5) |

### §7.3 Why `errors.backend.*`, not `publication.*`

The substantive reason from C2b §C.4 stands and bears repeating because the D1
footnote misclassified it:

- `publication.*` keys are **domain-specific UX** for publications: load
  failure, payload-invalid copy, not-found-reload prompt, serialization-error
  copy. Each is a UX framing of a publication-level event.
- `errors.backend.*` keys are **protocol-level** signals that are not tied to
  any single domain: auth failure, rate limiting, and now precondition failure.
  Each could arise on any backend resource the same way.

A 412 from a (hypothetical, future) ETag-guarded `/admin/cubes/{id}` PATCH
would emit the same `PRECONDITION_FAILED` code with the same UX semantics;
filing the i18n key under `publication.*` would force either (a) duplicating
the key under `cube.*`, (b) cross-referencing across domains, or (c)
namespace migration when the second resource ships. None of these are paid
costs in v1; using `errors.backend.*` from day 1 avoids them.

### §7.4 Carry-forward fix list

D1 §T-1.3-F-INT-01 footnote MUST be removed in recon-proper — there is no open
namespace question. The test assertion itself
(`errors.backend.precondition_failed` resolves to the EN translation) is
correct and stays.

D1 §T-1.3-F-INT-01 modal-name reference is fixed under §4 of Part 1
(`StaleVersionModal` → `PreconditionFailedModal`); the i18n-key fix here is
strictly to the footnote text, not the assertion.

---

## §8 TOCTOU window — DEBT-039 to be created

### §8.1 The C1 hardening note

C1 §A.6 records a real but bounded concurrency concern:

> "The TOCTOU concern: if we (a) read the row, (b) compute its ETag, (c)
> compare to `If-Match`, (d) commit-and-release the session, then later open a
> new tx to UPDATE — a concurrent writer could land between (c) and (d). To
> avoid this:
> - Use the existing per-request session pattern. ... All three operations
>   execute on the same `AsyncSession`, in the same transaction, before the
>   dependency's `await session.commit()` runs.
> - Two concurrent PATCHes on the same row will serialize at the database
>   level when the second one tries to UPDATE (PostgreSQL row-level lock
>   acquired implicitly by UPDATE) ...
> - **Stronger guarantee available if needed:** add `.with_for_update()` to
>   the `get_by_id` SELECT used by PATCH. That converts the read into a row
>   lock. For v1, the implicit UPDATE-side serialization is sufficient; flag
>   `with_for_update()` as a hardening option in C2/Part D if telemetry shows
>   lost-update races."

The note explicitly defers the `.with_for_update()` hardening to "C2/Part D"
on a telemetry trigger.

### §8.2 The gap

Part D3 §H tracks DEBT additions for the 1.3 impl PR:

- DEBT-037 — no idempotency-key short-circuit (from C2a §B)
- DEBT-038 — tolerate-missing-`If-Match` (from C2d §E.3, conditional on Q3)

Neither D3 nor any other Part D split allocates a DEBT for the C1 §A.6
hardening note. The note exists as a "flag in C2/Part D if telemetry shows
lost-update races" forward-pointer, but no Part D actually creates the entry.
Without an entry, the hardening trigger is unowned: there is no DEBT to consult
when telemetry surfaces a race.

### §8.3 Resolution: create DEBT-039

A new DEBT entry MUST be added to the impl-PR DEBT bundle, sequenced after
DEBT-038. Drafted here for review; will be appended to `[DEBT.md](http://DEBT.md)` in the same
commit as the 1.3 implementation PR (matching the D3 §H.4 cadence: not in
pre-recon, not in recon-proper).

#### DEBT-039 (drafted) — "PATCH publications has narrow TOCTOU window between ETag check and UPDATE"

- **Status:** Active
- **Severity:** Low
- **Category:** concurrency-hardening
- **Source:** Phase 1.3 recon, hardening note in Part C1 §A.6.
- **Description:** v1 of optimistic concurrency relies on PostgreSQL's
  implicit row-level UPDATE serialization to defend against the narrow
  TOCTOU window between (a) the `get_by_id` SELECT, (b) the
  `If-Match`-vs-server-ETag comparison, and (c) the `update_fields` UPDATE.
  Both reads-then-writes execute on the same per-request `AsyncSession`
  inside the same transaction (per Part A §1.6), and the UPDATE acquires a
  row-level lock implicitly — so a second concurrent writer's UPDATE
  serialises behind the first and produces a stale ETag on its own
  flush-side comparison. This is sufficient correctness for v1.
  However, the SELECT in step (a) is **not** itself locked, so a window
  exists where a concurrent writer could observe the same `If-Match`-valid
  state before either UPDATE runs. The defence is "second UPDATE produces
  a stale ETag", not "second UPDATE is rejected at SELECT time". For v1
  this is acceptable; under sustained concurrent-write load on the same
  row the lost-update probability rises.
- **Resolution:** if telemetry surfaces lost-update races on
  `PATCH /publications/{id}` (operationally: increased rate of `412`s
  attributed to this code path, or audit-log evidence of overlapping
  successful PATCHes that should have conflicted), promote the
  `get_by_id` SELECT to `.with_for_update()`. That converts step (a)
  into a row lock, eliminating the TOCTOU window at the cost of one
  Postgres row lock per PATCH. Update Part C1 §A.6 to record the
  promotion, and add a regression test under
  `backend/tests/integration/` that exercises two concurrent PATCHes on
  the same row and asserts at most one succeeds.
- **Verification before flipping:** the `with_for_update()` change must
  pass under load test on a multi-connection pool to confirm the lock is
  scoped per-row (not per-table) — a misconfigured Postgres `lock_timeout`
  or unintended `FOR UPDATE OF ALL TABLES` hint would serialise the entire
  publications surface.
- **Out of scope for v1:** any change to the SELECT inside `get_by_id`,
  any change to the PATCH handler's transaction boundaries, any change to
  the C2c modal behaviour. v1 ships the implicit-serialisation defence
  exactly as C1 §A.6 designs it.

### §8.4 DEBT numbering check

Per D3 §H.0, the highest existing DEBT number was DEBT-036 (read 2026-04-27).
D3 allocated DEBT-037 (idempotency) and DEBT-038 (tolerate-`If-Match`).
DEBT-039 is therefore the next sequential identifier and is reserved for the
TOCTOU hardening above.

D3 §H.4's bundling rule applies unchanged: all three DEBT entries (037, 038
conditional on Q3, and 039) land in the same commit as the 1.3 impl PR — not
in pre-recon, not in recon-proper. This reconciliation does not append
DEBT-039 to `[DEBT.md](http://DEBT.md)` directly; it only commits the entry's authored text to
the impl-prompt input pile.

### §8.5 Carry-forward to Part 3

§9 (Part 3) lists the architecture-MD updates Phase 1.3 must ship; one of
those updates is `ARCHITECTURE_[INVARIANTS.md](http://INVARIANTS.md)` §7 placeholder for the TOCTOU
hardening trigger, cross-referencing DEBT-039. That cross-reference is the
hand-off point between this section and §9.

---

End of Part 2. Sections §6–§8 added by Part 2; §9–§11 follow in Part 3.
