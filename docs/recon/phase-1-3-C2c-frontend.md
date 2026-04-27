# Phase 1.3 — Part C2c — Frontend Handling

**Type:** DESIGN (3 of 4 micro-splits of original Part C2)
**Scope:** Section D only — frontend 412 handling + modal.
**Date:** 2026-04-27
**Branch:** `claude/frontend-412-error-modal-BK4eq`
**Git remote:** `http://local_proxy@127.0.0.1:34059/git/Inneren12/Summa-vision-can`

---

## Section D — Frontend 412 Handling

### D.1 Autosave path — where the 412 branch lives

Per **Part B §1.3** (`docs/recon/phase-1-3-B-frontend-inventory.md`), the single autosave
consumer is:

```
frontend-public/src/components/editor/index.tsx:568   (performSave useCallback)
```

The terminal-vs-retry split happens inside `performSave`'s `.catch` block at
`frontend-public/src/components/editor/index.tsx:584–623`. The new 412 branch is added
there, **before** the existing "transient / unknown failure — retry with backoff" fallthrough.

Sketch (illustrative — not a code change in this doc):

```ts
.catch((err: unknown) => {
  if (err instanceof AdminPublicationNotFoundError) { /* existing terminal branch */ return; }

  // NEW: 412 terminal branch — must NOT enter the auto-retry path below.
  if (err instanceof BackendApiError && err.code === 'PRECONDITION_FAILED') {
    const serverEtag = typeof err.details?.server_etag === 'string'
      ? err.details.server_etag
      : null;
    setPreconditionFailedModal({ open: true, serverEtag });
    setSaveStatus('error');
    return; // terminal — no setSaveFailureGen bump, no auto-retry
  }

  // ...existing transient/unknown auto-retry branch (lines 599–622)
})
```

Key properties of this placement:

- **Single chokepoint.** All autosave traffic flows through `performSave`; no other call
  site needs the 412 handler.
- **Terminal, not retryable.** The branch must `return` early so it bypasses
  `setSaveFailureGen((n) => n + 1)` and the `canAutoRetry: true` dispatch. Auto-retry on
  412 would loop indefinitely (the server ETag never magically matches the client's
  stale version).
- **Distinct from `NotificationBanner`.** The existing banner UX is for transient errors
  with auto-retry; 412 needs explicit user choice, so it surfaces as a modal instead.

### D.2 `BackendApiError` integration — no refactor needed

Confirmed against **Part B §1.1** (`admin.ts:34–51` verbatim):

```ts
export class BackendApiError extends Error {
  public readonly status: number;
  public readonly code: string | null;
  public readonly details: Record<string, unknown> | null;
  // ...
}
```

For the 412 branch, the autosave handler reads:

| Field                            | Source (Part B §1.1, Part C2b §C)             | Use in modal              |
|----------------------------------|-----------------------------------------------|---------------------------|
| `error.code === 'PRECONDITION_FAILED'` | Discriminator (matches Part C2b error_code) | Branch trigger            |
| `error.details?.server_etag`     | Optional string carrying server's current ETag | Passed to refetch logic   |
| `error.message`                  | Backend message                               | Fallback if i18n key absent |

**No changes to `BackendApiError`, `extractBackendErrorPayload`, or the admin.ts error
branch are required.** The class already exposes `code` and `details` as read-only
public fields; the 412 envelope from Part C2b populates both via the existing
`extractBackendErrorPayload(body)` plumbing at `admin.ts:139`. The only additive change
is registering `'PRECONDITION_FAILED'` in `KNOWN_BACKEND_ERROR_CODES` (errorCodes.ts:17)
when an i18n key for the modal copy is mapped — that's an i18n-key concern (out of scope
for this part; covered in C2d/i18n work), not a class refactor.

### D.3 v1 UX — modal with two buttons

A **modal dialog** with exactly two action buttons:

| Button                          | Effect                                             |
|---------------------------------|----------------------------------------------------|
| **Reload (lose my changes)**    | Discards local autosave buffer, refetches the publication, replaces editor state. *Default focus.* |
| **Save as new draft**           | Calls existing clone endpoint (`cloneAdminPublication` at `admin.ts:169`) with current editor state; user continues on the new (forked) publication; the original remains untouched (and continues to belong to whichever writer advanced its ETag). |

**Default focus on "Reload."** Reload is the safer choice: it simply re-syncs to the
server's truth and the user only loses unsaved local changes since the last successful
save (typically seconds, given autosave cadence). "Save as new draft" requires more
deliberation — the user is choosing to fork — so it should not be the default.

**No silent dismissal.** Closing the modal via `Esc` or backdrop click leaves the modal
in a re-openable state; autosave **remains broken** until the user picks Reload or Save-
as-new-draft. This is intentional: silently letting the editor continue would either
keep generating 412s on every autosave tick or, worse, mask the conflict and let the
user keep typing into a doomed buffer. Cancel/dismiss is therefore non-resolving — see
D.6.

### D.4 Out of scope for v1

Explicitly NOT shipping in v1:

- **Full diff/merge UI.** No side-by-side view of "my changes" vs "their changes". The
  user picks Reload or Save-as-new-draft; that's the entire interaction surface.
- **Automatic conflict resolution.** No server-side or client-side merge attempt. The
  client never silently picks a winner.
- **Three-way merge** of (autosave buffer) ⊕ (server state) ⊕ (cloned draft). The clone
  in "Save as new draft" is a one-way fork of the local state; it does not attempt to
  reconcile with what the server now holds.

These are deferred to a future phase (likely contingent on actual operational data on
how often 412 fires and how disruptive the binary Reload/Fork choice feels).

### D.5 Modal component location

**Proposed:** `frontend-public/src/components/editor/components/PreconditionFailedModal.tsx`

Convention reconciliation against **Part B inventory**:

- **Location.** Part B §1.3 surveyed existing modals and identifies the editor-local
  convention `frontend-public/src/components/editor/components/<Concept>Modal.tsx`
  (e.g., `NoteModal.tsx` at that path). The new file MUST live alongside `NoteModal.tsx`
  and `NotificationBanner.tsx`, not at `components/editor/PreconditionFailedModal.tsx`.
- **Name.** `PreconditionFailedModal` mirrors the backend `error_code`
  (`PRECONDITION_FAILED`, per Part C2b §C) one-for-one. This keeps the discriminator
  (the string the `.catch` branch tests) and the component name aligned, which makes
  grep across the boundary trivial. (Part B §1.3 used the working name
  `StaleVersionModal.tsx`; we adopt `PreconditionFailedModal.tsx` instead because the
  contract code is the stable artifact and the user-facing copy lives in i18n, not in
  the type/file name.)
- **Lifted state.** `preconditionFailedModalState` (or equivalent) lives in `index.tsx`
  next to `setSaveStatus` / `setSaveFailureGen` — same module that owns `performSave`.
  Avoids prop-drilling; the modal renders as a peer of `NotificationBanner` and reads/
  writes that local state.

### D.6 Modal behavior — full state matrix

| User action               | Effect on local autosave buffer | Effect on server state | Effect on editor pubId | Modal state after          |
|---------------------------|---------------------------------|------------------------|------------------------|----------------------------|
| Click **Reload**          | Discarded                       | Untouched              | Same id, refreshed body & ETag | Closed                |
| Click **Save as new draft** | Cloned to new publication; local link to original severed | Original untouched; new publication created via clone endpoint | New id (the clone's id) | Closed |
| `Esc` / backdrop click / X | Preserved (not discarded)      | Untouched              | Unchanged              | Closed, but **autosave remains broken**; the modal is re-shown on the next autosave tick (which will 412 again) |

**Reload — implementation note.**
Reload re-runs the same fetch path the editor uses on initial mount (Part B §1.3 shows
the consumer is `frontend-public/src/components/editor/index.tsx`; the publication-load
path lives in the same module). The new ETag returned by that refetch becomes the
client's `If-Match` value for the next PATCH, so subsequent autosaves succeed.

**Save as new draft — implementation note.**
Reuses the **existing** clone endpoint via the existing client function
`cloneAdminPublication` (Part B §1.1 / Phase 1.1 contract). The endpoint is *not*
new in 1.3. The flow:

1. Snapshot current editor state (the buffer that just failed to save).
2. Call `cloneAdminPublication(originalId)`.
3. Apply the snapshot to the clone via a fresh `updateAdminPublication(cloneId, ...)`
   PATCH using the clone's initial ETag (which the GET-after-clone returns).
4. Navigate / swap editor state to the clone's id.
5. Discard link to the original publication's pubId.

The clone's own ETag from step 3 is fresh, so the PATCH cannot 412 against itself.
(There is a vanishingly rare edge case where another writer simultaneously edits the
just-created clone — but the clone was just created by *this* user; no other writer
holds its id yet. Safe.)

**Cancel/dismiss — non-resolving by design.**
Per D.3, dismissing the modal does not "fix" anything. The 412 condition lives on the
server (the server's ETag is ahead of the client's), and only Reload or Save-as-new-
draft mutate local state in a way that can resolve the mismatch. Continuing to autosave
without resolution would 412 again on the very next tick. The modal therefore re-opens
automatically on the next failed autosave, restoring the user's two-button choice.

### D.7 Boundaries with C2a / C2b / C2d

- **C2a (R16):** `PRECONDITION_FAILED` is treated uniformly — the same modal and the
  same Reload/Fork choice apply whether the underlying cause is a genuine concurrent
  edit or a lost-response retry whose server-side mutation already succeeded. Reload-
  then-retry is a no-op in the lost-response case (the user's prior write is already
  the server's truth), which is the correct outcome.
- **C2b (envelope):** Modal reads `err.code === 'PRECONDITION_FAILED'` and
  `err.details.server_etag` exactly as defined in the C2b envelope. No client-side
  awareness of the `jsonable_encoder` wrapping requirement is needed (that's a server
  concern); the client just sees the parsed JSON envelope.
- **C2d (i18n keys for modal copy):** Out of scope for this part. The button labels
  ("Reload (lose my changes)", "Save as new draft"), modal title, and body copy are
  named here as English strings for design clarity; their i18n keys (under
  `publication.*` per Part B §1.4 hybrid convention) are the C2d/i18n deliverable.

---

## Summary Report

```
DOC PATH: docs/recon/phase-1-3-C2c-frontend.md
Modal location: frontend-public/src/components/editor/components/PreconditionFailedModal.tsx
v1 UX: Reload + Save-as-draft (default focus Reload)
BackendApiError refactor needed: no
Existing clone endpoint reused: yes (1.1)
VERDICT: COMPLETE
```

---

**End of Part C2c.**
