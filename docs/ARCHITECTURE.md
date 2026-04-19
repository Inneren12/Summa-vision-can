# Architecture

## System Overview

The current flow is:

```
   Data Sources → ETL Pipeline → Cube Catalog (search) → Data Workbench → Visual Engine → Publication
                                                                                              ↓
                                                                                     Human-in-the-Loop (Admin)
```

### Download Flow (D-2)

```
   User clicks "Download High-Res" → DownloadModal (Turnstile + email)
           ↓
   POST /api/v1/public/leads/capture
           ↓
   Lead saved → Token (SHA-256) stored → Magic Link email sent
           ↓
   User clicks email link → /downloading page (token in URL, cleared immediately)
           ↓
   User clicks "Verify and Download" → GET /api/v1/public/download?token=...
           ↓
   Atomic token activation → 307 redirect to presigned S3 URL → file downloads
```

**Security constraints (R1, R17):** No presigned URLs in emails. No auto-downloads.
Raw tokens never stored in DB (SHA-256 only). Tokens limited to 5 uses, 48h TTL.

### Lead Scoring + Notifications Flow (D-3)

```
   Lead captured (POST /capture)
           ↓ (background task)
   LeadScoringService.score_lead(email)  ← pure sync, ARCH-PURA-001
           ↓
   Update lead: is_b2b, company_domain, category
           ↓
   ┌─ b2b/education → SlackNotifierService.notify_lead() (with dedupe)
   └─ isp/b2c → skip Slack
           ↓
   ESPClient.add_subscriber(email)
   ├─ Success → mark esp_synced=True
   ├─ 4xx → mark esp_sync_failed_permanent=True
   └─ 5xx/timeout → leave esp_synced=False (retried via /admin/leads/resync)
```

**Admin resync:** `POST /api/v1/admin/leads/resync` retries unsynced leads with exponential backoff (3 attempts, delays 1s/2s).

## Infrastructure Layer

- **Docker:** Dockerfile + two compose files
- **Health endpoints:** `/api/health` (liveness), `/api/health/ready` (readiness)
- **Resource semaphores:** data_sem(2), render_sem(2), io_sem(10)
- **Database:** PostgreSQL-only runtime, pool_size=8
- **Storage:** MinIO (dev) / S3 (prod)
  - *Note:* Public gallery API returns `cdn_url` (e.g. `https://cdn.summa.vision/publications/...`) directly from the CDN base URL config rather than generating presigned URLs (per R1).
- **Background Jobs:** persistent DB-backed job system (JobRunner + handler registry)
  - Handlers: `catalog_sync` (A-3), `cube_fetch` (A-5), `graphics_generate` (B-4)

## ETL Pipelines

- **Track A (StatCan)**: Catalog Sync → Search → Fetch → Workbench → Chart.

## Data Engine

- CubeCatalog with bilingual FTS (coming in A-1..A-4)
- DataFetchService with Polars-first pipeline (coming in A-5)
- DataWorkbench pure transforms (coming in A-6)
Note: Polars is primary engine, Pandas only in legacy StatCan code.

## Visual Engine

Plotly SVG + backgrounds + compositor.
Note template backgrounds instead of AI backgrounds for MVP.

### Pipeline data input paths

``GraphicPipeline.generate()`` takes a single ``data_key`` pointing at a
Parquet object in storage. Two paths feed into this contract:

1. **StatCan path** — `POST /api/v1/admin/graphics/generate`. The
   ``data_key`` is a StatCan-origin Parquet written by the ETL /
   Workbench pipeline (Étape A).
2. **Upload path** — `POST /api/v1/admin/graphics/generate-from-data`.
   The endpoint serializes the user-supplied rows into a temporary
   Parquet under ``temp/uploads/{uuid}.parquet`` (via the injected
   ``StorageInterface.upload_bytes``) and enqueues the same
   ``graphics_generate`` job type against that key.

`GraphicPipeline` itself is unchanged — Stage 1 (`_load_data`) can't
tell which path the Parquet came from. Temp Parquet cleanup is tracked
as `DEBT-021` (24 h TTL via ``temp_upload_ttl_hours``).

## Editor (Authoring Workflow)

- Editor document type is `CanonicalDocument` in
  `frontend-public/src/components/editor/types.ts`. Schema version is tracked
  exclusively on `doc.schemaVersion` at the root; `meta.schemaVersion` is
  forbidden.
- `Publication.review` (Stage 3 PR 4) stores the frontend review subtree
  verbatim as a JSON string (Text column, SQLite-compat). Backend does
  not deep-validate nested `history` / `comments` elements; frontend's
  `assertCanonicalDocumentV2Shape` owns that. Workflow state is written
  through both `review.workflow` and `Publication.status` — the latter
  is a derived gallery-visibility flag synced from the former in the
  PATCH / publish / unpublish handlers. `PublicationPublicResponse`
  deliberately omits `review`: workflow, history and comments are
  admin-only.
- Review-related state (workflow, workflow history, comments) lives in
  `doc.review`. Edit history remains in `doc.meta.history` with its own
  `EditHistoryEntry` type — two histories, two purposes, never merged.
- Schema migrations are declarative in `registry/guards.ts#MIGRATIONS`.
  Current version is v2; a single `v1 → v2` step moves root-level `workflow`
  into `doc.review.workflow`. See `docs/modules/editor.md` for the full shape.
- Editor reducer enforces permissions along two orthogonal axes: `mode`
  (template|design) and `workflow` (draft|in_review|approved|exported|
  published). Both must pass for an action to mutate the document. Workflow
  transitions are captured in `store/workflow.ts#TRANSITIONS` and written to
  `doc.review.history` as `WorkflowHistoryEntry` records.
- Comments are first-class review artifacts (`store/comments.ts`, Stage 3
  PR 2b). They mutate `doc.review.comments` directly and do NOT participate
  in the undo/redo history — an UNDO cannot silently restore or obliterate
  another author's note. Comment lifecycle events (add, reply, resolve,
  reopen, delete) are audited via entries in `doc.review.history` alongside
  workflow transitions. A `canComment` flag in `WORKFLOW_PERMISSIONS` gates
  the surface: comments stay open through `draft` and `in_review`, and
  freeze on `approved|exported|published`.
- Editor UI surface (Stage 3 PR 3) — the right rail is tabbed:
  Inspector + Review. Notifications use a single in-app banner with a
  resolution priority (hard error > soft rejection > warnings); there is
  no toast provider. `NoteModal` is the sole modal input for free-text
  user input in the editor (comment composition, transition notes); the
  editor surface contains zero `window.prompt` / `alert` / `confirm`
  call sites. The canvas remains a single `<canvas>` element with no
  overlay; comment indicators live in the LeftPanel block rows and the
  Review panel only. Mode and workflow gates are combined into an
  `effectivePerms` overlay at the parent so disabled buttons never
  silently dispatch into a reducer rejection.
- Workflow transitions carrying a note (`RETURN_TO_DRAFT`,
  `REQUEST_CHANGES`) are always routed through the shared NoteModal,
  regardless of the UI surface initiating them. There is a single
  NoteModal instance in the editor, owned by `index.tsx` and driven by
  a `NoteRequestConfig` callback (`onRequestNote`) passed to every
  surface that needs to collect free-text input. This keeps the audit
  path (`doc.review.history`) identical whether the transition was
  initiated from the Review panel header or the above-canvas read-only
  banner. Direct dispatches from the UI are reserved for transitions
  that carry no note (notably `DUPLICATE_AS_DRAFT`).
- Editor right-rail tabs implement the W3C ARIA Authoring Practices
  tabs pattern: `ArrowLeft`/`ArrowRight` / `Home`/`End` move focus and
  activate tabs; inactive tabs carry `tabIndex={-1}` (roving focus) so
  `Tab` from outside the tablist advances into the active tabpanel
  rather than cycling every tab.

## Admin Surface (Stage 4 Task 0)

- **Routes.** `/admin` (publication list) and `/admin/editor/[id]` (edit
  existing publication). Both live under
  `frontend-public/src/app/admin/` and share `app/admin/layout.tsx`. No
  `/new` route and no creation affordance — Task 0 scope is read/edit
  only. The admin layout sets `metadata.robots = { index: false, follow: false }`.
- **Proxy.** Browser code talks to the same-origin Next.js route handler
  at `src/app/api/admin/publications/[...path]/route.ts`. The handler
  injects the server-only `X-API-KEY` header before forwarding to the
  backend admin API. Supported verbs: `GET`, `POST`, `PATCH`, `DELETE`.
  Any client-supplied `X-API-KEY` is ignored (server always wins). All
  forwards set `cache: 'no-store'`. This is the ONLY path through which
  client code reaches admin endpoints.
- **Server-only helpers.** `src/lib/api/admin-server.ts` is imported by
  server components (the admin page + editor page). It reads
  `ADMIN_API_KEY` directly and throws if imported client-side
  (`typeof window !== 'undefined'` guard at module top). `server-only`
  package not used to avoid adding a dependency.
- **Client helpers.** `src/lib/api/admin.ts` talks only to the
  same-origin proxy (relative URLs). Never reads `ADMIN_API_KEY`.
  Exports `fetchAdminPublication`, `fetchAdminPublicationList`,
  `updateAdminPublication`, and `AdminPublicationNotFoundError`.
- **Hydration flow.** Server page fetches with the key →
  `hydrateDoc(publication)` in `components/editor/utils/persistence.ts`
  maps the admin response onto a `CanonicalDocument` by overlaying the
  default template → page passes the doc to `AdminEditorClient` → which
  passes `initialDoc` and `publicationId` props into `InfographicEditor`.
  `InfographicEditor` validates the doc through `validateImportStrict`
  synchronously; invalid docs fall back to the template and surface the
  error via `NotificationBanner`.
- **Save flow.** Ctrl+S invokes `buildUpdatePayload(doc)` and issues a
  PATCH through the proxy. On success the editor dispatches `SAVED`
  (clears `state.dirty`). On 404 the user is told to reload; on other
  errors the message surfaces via the import-error banner. Autosave is
  deferred to Stage 4 Task 2.
- **Environment variables.** `NEXT_PUBLIC_API_URL` is the only
  client-exposed var (browser uses the proxy at same-origin;
  server-only helpers read it directly). `ADMIN_API_KEY` is
  server-only — it is NEVER placed into `next.config.ts#env`, which
  would bundle it to the browser. `REVALIDATION_SECRET` is unchanged
  from Stage 3. See `frontend-public/.env.example`.
- **Type contract.** `src/lib/types/publication.ts` hosts both
  `PublicationResponse` (public gallery, narrow) and
  `AdminPublicationResponse` (admin, full contract including
  `visual_config` and `review`). Old `PublicationResponse` was kept
  unchanged to minimise churn across existing gallery consumers; admin
  surface uses the new type.

## Technology Summary

| Component | Technology |
|---|---|
| Infrastructure | Docker, PostgreSQL, MinIO |
| Database | PostgreSQL |
| Storage | MinIO |
| Pipeline Engine | Polars, Parquet |

## Module Dependency Graph

```
   backend/src/
   ├── main.py
   ├── core/
   │   ├── config.py
   │   ├── database.py
   │   ├── rate_limit.py
   │   ├── storage.py
   │   ├── scheduler.py
   │   ├── exceptions.py
   │   ├── error_handler.py
   │   ├── logging.py
   │   └── security/
   │       ├── auth.py
   │       └── ip_rate_limiter.py
   ├── api/routers/
   │   ├── health.py              ← (0-1)
   │   ├── admin_graphics.py      ← (B-4: job-based generate + GET /jobs/{id})
   │   ├── admin_leads.py         ← (D-3: ESP resync with exponential backoff)
   │   ├── public_graphics.py
   │   ├── public_leads.py        ← (D-3: scoring + Slack + ESP background tasks)
   │   ├── public_download.py     ← (D-2: token exchange → presigned URL)
   │   ├── public_metr.py         ← (Theme #2: METR calculator — calculate, curve, compare)
   │   └── public_sponsorship.py  ← (D-3: tiered sponsorship inquiry)
   ├── models/
   │   ├── publication.py
   │   ├── lead.py
   │   └── download_token.py  ← (D-0c: SHA-256 token model)
   ├── repositories/
   │   ├── publication_repository.py
   │   ├── lead_repository.py
   │   └── download_token_repository.py  ← (D-2: atomic activate)
   └── services/
       ├── statcan/ (Complete: maintenance guard, HTTP client, schemas, ETL service)
       ├── graphics/ (svg_generator, backgrounds, compositor, pipeline)
       ├── crm/
       │   └── scoring.py         ← (D-3: pure sync lead scoring — ARCH-PURA-001)
       ├── notifications/
       │   └── slack.py           ← (D-3: Slack webhook alerts with dedupe)
       ├── email/
       │   ├── interface.py       ← (D-0a: EmailServiceInterface + ConsoleEmailService)
       │   └── esp_client.py      ← (D-3: Beehiiv ESP client with error classification)
       ├── metr/                  ← (Theme #2: METR calculation engine + card data)
       │   ├── engine.py          ← Pure functions: federal/provincial tax, CPP, EI, CCB, CWB, GST
       │   └── card_data.py       ← Signal card dataset generator (4 cards)
       └── security/ (D-0b: TurnstileValidator)
```
