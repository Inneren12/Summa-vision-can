# i18n Recon — Slice 4: Admin Shell + Publications

Date: 2026-04-22
Scope: non-editor admin routes + admin components
Status: RECON COMPLETE
Previous slices: 1 merged, 2a merged, 2b in flight
Excluded: /admin/editor/*, /admin/layout.tsx, /admin/page.tsx, LanguageSwitcher.tsx (done)

## 1. Routes audited

| Route | Files | Component type | Hardcoded strings | Notes |
|---|---|---|---|---|
| `/admin/*` (non-editor) | *(none found in repository for this slice scope)* | N/A | 0 | Only excluded files exist under `src/app/admin`: `/admin/layout.tsx`, `/admin/page.tsx`, and `/admin/editor/[id]/*`. |
| `/admin/publications` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/publications/[id]` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/leads` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/leads/[id]` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/jobs` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/settings` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/users` | *(not present)* | N/A | 0 | Route directory not found. |
| `/admin/login` | *(not present)* | N/A | 0 | Route directory not found. |

## 2. Per-file string inventory

No in-scope files were found after exclusions.

Audited glob results:
- `frontend-public/src/app/admin/**/*.tsx` → only excluded files (`layout.tsx`, `page.tsx`, `/editor/[id]/*`)
- `frontend-public/src/app/admin/**/*.ts` → no files
- `frontend-public/src/components/admin/**/*.tsx` → only excluded file (`LanguageSwitcher.tsx`)

## 3. Status badges — reuse existing keys

No in-scope status rendering sites found in this slice.

| Raw status value | Suggested existing key | Source section in glossary |
|---|---|---|
| *(none in scope)* | N/A | N/A |

## 4. Shared admin components

No in-scope shared admin components found in this slice.

| Component | Used in routes | Strings | Notes |
|---|---|---|---|
| *(none in scope)* | N/A | N/A | `src/components/admin` currently contains only `LanguageSwitcher.tsx` (excluded, already done in Slice 1). |

## 5. Date/number formatting sites

No in-scope formatting sites found.

| File | Pattern | Locale-aware replacement |
|---|---|---|
| *(none in scope)* | N/A | N/A |

## 6. Metadata / generateMetadata calls

No in-scope `generateMetadata` calls found.

| File | Current title | Suggested key |
|---|---|---|
| *(none in scope)* | N/A | N/A |

## 7. Summary

- Total routes audited: 0 (non-editor admin routes present in codebase)
- Files with hardcoded strings: 0
- Total hardcoded strings found: 0
- Status badge reuse opportunities: 0
- Shared admin components: 0
- Date/number formatting sites: 0
- Glossary coverage: covered 0 / partial 0 / new 0
- Blockers: **Route surface not yet present in repository** for the expected non-editor admin pages (`publications`, `leads`, `jobs`, `settings`, `users`, `login`)

## 8. New terms requiring translation decisions

None for this slice.

| Key | EN | Suggested RU (TBD) |
|---|---|---|
| *(none)* | N/A | N/A |

## 9. Recommended implementation order

Order suggestion once these routes land:
- Shared admin components first (list/table/filter/pagination primitives)
- High-traffic route next (`/admin/publications` list)
- Remaining routes in daily operator priority (`leads` → `jobs` → `users/settings`)

