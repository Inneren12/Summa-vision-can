# i18n Recon — Slice 1: Editor Core

Date: 2026-04-22
Scope: frontend-public editor core files
Status: RECON COMPLETE

## 1. Files audited

| File | Found | Hardcoded strings | Notes |
|---|---|---|---|
| frontend-public/src/components/editor/index.tsx | yes | 6 | Core editor container; several error/banner strings. |
| frontend-public/src/components/editor/EditorShell.tsx | no | 0 | not found |
| frontend-public/src/components/editor/Toolbar.tsx | no | 0 | not found |
| frontend-public/src/components/editor/Canvas.tsx | no | 0 | not found |
| frontend-public/src/app/admin/editor/[id]/page.tsx | yes | 0 | Server page; no user-visible literals in rendered JSX. |
| frontend-public/src/app/admin/editor/[id]/layout.tsx | no | 0 | not found |
| frontend-public/src/app/admin/layout.tsx | yes | 3 | Admin chrome contains visible labels. |
| frontend-public/src/app/admin/page.tsx | yes | 3 | Admin index headings/empty state contain visible labels. |
| frontend-public/src/app/admin/editor/[id]/AdminEditorClient.tsx | yes (discovered) | 0 | Discovered additional top-level editor file; wrapper only. |
| frontend-public/src/components/editor/components/Canvas.tsx | yes (discovered) | 0 | Discovered additional editor canvas file; no user-visible text literals. |

## 2. Hardcoded strings inventory

For each file with hardcoded strings:

### frontend-public/src/components/editor/index.tsx

| # | String (EN) | Location (line ~N) | Context | Suggested key | Canonical RU |
|---|---|---|---|---|---|
| 1 | "Failed to load publication — using template defaults. ${initialValidationError}" | ~217 | Import/init fallback error shown in notification banner | publication.load_failed.fallback | TBD |
| 2 | "Publication not found — reload the page" | ~571 | Save failure message stored in state and surfaced via banner | publication.not_found.reload | TBD |
| 3 | "Invalid JSON file" | ~856 | Import validation error shown to user | import.invalid_json | TBD |
| 4 | "Import error: ${hydrationErr?.message ?? 'hydration failed'}" | ~864 | Import hydration failure surfaced to user | import.error.hydration | TBD |
| 5 | "Import error: ${validationErr?.message ?? 'validation failed'}" | ~872 | Import schema validation failure surfaced to user | import.error.validation | TBD |
| 6 | "hydration failed" / "validation failed" | ~864, ~872 | Fallback fragments shown when nested error message is absent | import.hydration_failed / import.validation_failed | TBD |

### frontend-public/src/app/admin/layout.tsx

| # | String (EN) | Location (line ~N) | Context | Suggested key | Canonical RU |
|---|---|---|---|---|---|
| 1 | "Admin — Summa Vision" | ~5 | Page metadata title | admin.meta.title | TBD |
| 2 | "Summa Vision · Admin" | ~19 | Header brand label/link text | admin.header.brand | TBD |
| 3 | "Internal tool" | ~21 | Header helper label | admin.header.internal_tool | TBD |

### frontend-public/src/app/admin/page.tsx

| # | String (EN) | Location (line ~N) | Context | Suggested key | Canonical RU |
|---|---|---|---|---|---|
| 1 | "Publications" | ~12 | Admin index heading (empty state branch) | publications.title | публикация (base term in glossary; plural UI form TBD) |
| 2 | "No publications yet." | ~13 | Empty state message | publications.empty | No publications yet. → TBD |
| 3 | "Publications" | ~20 | Admin index heading (non-empty branch) | publications.title | публикация (base term in glossary; plural UI form TBD) |

## 3. Existing i18n infrastructure

| Item | Found | Notes |
|---|---|---|
| next-intl in package.json | no | `frontend-public/package.json` has no `next-intl` dependency. |
| messages/ directory | no | `frontend-public/messages` not found. |
| middleware.ts locale logic | no | No `frontend-public/middleware.ts` or `frontend-public/src/middleware.ts` present. |
| useTranslations calls | no | No `useTranslations` / `getTranslations` usage found under `frontend-public/src`. |
| locale routing in next.config.ts | no | `frontend-public/next.config.ts` has no i18n locale config/routing block. |

## 4. Shared components risk

| Component | Shared with public site | Risk | Notes |
|---|---|---|---|
| frontend-public/src/components/editor/index.tsx | no | low | Imported only by admin editor client route. |
| frontend-public/src/app/admin/editor/[id]/AdminEditorClient.tsx | no | low | Located under admin route only. |
| frontend-public/src/components/editor/components/Canvas.tsx | no | low | No imports from public app routes found. |

## 5. Summary

- Total files audited: 10
- Files with hardcoded strings: 3
- Total hardcoded strings found: 12
- Existing i18n infrastructure: none (no package, messages, middleware locale logic, translation hooks, or locale routing)
- Shared component risk: none (0 components flagged as shared with public site)
- Blockers for implementation: none in this slice; main prerequisite is introducing i18n infrastructure from scratch

## 6. Recommended implementation order (within Slice 1)

1. `frontend-public/src/app/admin/layout.tsx` — small, isolated labels (metadata/header), low-risk first migration.
2. `frontend-public/src/app/admin/page.tsx` — simple heading/empty-state strings; establishes admin list namespace (`publications.*`).
3. `frontend-public/src/components/editor/index.tsx` — higher-risk because strings are tied to save/import error pathways and should be migrated after base i18n wiring is stable.
4. `frontend-public/src/app/admin/editor/[id]/AdminEditorClient.tsx` and `frontend-public/src/components/editor/components/Canvas.tsx` — no current strings, but keep in migration pass for future regressions and consistency checks.
