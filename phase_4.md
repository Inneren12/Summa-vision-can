# Phase 4: Public Site & B2C Lead Capture (Next.js & FastAPI)
Здесь мы строим публичное лицо Summa Vision. Эндпоинты отделены от админки, не требуют API-ключей, но жестко защищены Rate Limiter'ами по IP.

## PR-29: Next.js Init & Pragmatic Client Boundaries

```
Role: Expert Frontend Engineer.
Task: Execute PR-29 for the "Summa Vision" project.
Context (Human): Base setup for the public-facing Next.js application, ensuring SEO performance and strict adherence to the App Router paradigm.
```

<ac-block id="Ph4-PR29-AC1">
**Acceptance Criteria for PR-29 (Next.js Base):**
- [ ] Initialize Next.js 14+ (App Router) with TailwindCSS and TypeScript.
- [ ] Configure global CSS variables for dark theme (`#141414` background, neon blue/green accents).
- [ ] CRITICAL ARCHITECTURE: Use strict Server Components by default. Apply `'use client'` pragmatically at the semantic component boundary (e.g., wrap the interactive Modal, but keep the layout server-side).
- [ ] **[FIX]** Configure `next.config.js` with `NEXT_PUBLIC_API_URL` environment variable pointing to the FastAPI backend. In production this will be `https://api.summa.vision`, in dev `http://localhost:8000`.
- [ ] Component Tests: Test the root layout rendering and theme provider initialization.
- [ ] File location: `/frontend-public/src/app/layout.tsx`, `/frontend-public/tailwind.config.ts`
- [ ] Test location: `/frontend-public/tests/components/layout.test.tsx`
</ac-block>

---

## PR-31: Secure Lead API & Persistence

```
Role: Expert Python Backend Engineer.
Task: Execute PR-31 for the "Summa Vision" project.
Context (Human): The endpoint where users trade their email for high-res graphics. It must be protected against bots and immediately save data locally before talking to any external services.
```

<ac-block id="Ph4-PR31-AC1">
**Acceptance Criteria for PR-31 (Secure Lead API):**
- [ ] **[FIX]** Create `InMemoryRateLimiter(max_requests: int, window_seconds: int)` — a configurable sliding window rate limiter per IP, strictly separate from the StatCan token bucket. It MUST be reusable across multiple endpoints with different limits (e.g., 3/min for leads, 30/min for gallery, 1/5min for sponsorship).
- [ ] Create public router `POST /api/v1/public/leads/capture` accepting `email` and `asset_id`.
- [ ] CRITICAL ARCHITECTURE: 1) Enforce Rate Limit (e.g., 3 req/min per IP). 2) Save the lead to the database (`LeadRepository.create`) IMMEDIATELY to prevent data loss. 3) Return a generated S3 presigned URL for the requested `asset_id` (using `StorageInterface.generate_presigned_url(ttl=900)`).
- [ ] **[FIX]** BEFORE generating the presigned URL, validate that `asset_id` exists in `PublicationRepository` with `status=PUBLISHED`. If not found, return `HTTP 404 Not Found` with message `"Asset not found or not yet published"`. This prevents URL generation for non-existent or draft assets.
- [ ] **[FIX]** Configure FastAPI CORS middleware to allow origins: `summa.vision`, `www.summa.vision`, `localhost:3000` (Next.js dev). Block all other origins. This was missing from Phase 4 after the sprint restructuring.
- [ ] Unit Tests: Trigger the Rate Limit to assert `HTTP 429`. Assert the lead is successfully saved to the DB via the mock repository. **[FIX]** Test with a non-existent `asset_id`, assert `HTTP 404`.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/api/routers/public_leads.py`, `/backend/src/core/security/ip_rate_limiter.py`
</ac-block>

---

## PR-33: Next.js Gallery & Gated Content Modal

```
Role: Expert Frontend Engineer.
Task: Execute PR-33 for the "Summa Vision" project.
Context (Human): The main gallery fetching approved graphics and the lead-capture modal blocking high-res downloads.
```

<ac-block id="Ph4-PR33-AC1">
**Acceptance Criteria for PR-33 (Gallery & Modal UI):**
- [ ] Create Server Component `InfographicFeed` fetching from `GET /api/v1/public/graphics` (created in PR-41). Use Next.js ISR (`revalidate: 3600`).
- [ ] Create Client Component `DownloadModal` accepting `assetId` as a prop.
- [ ] Use `react-hook-form` + `zod` for client-side email validation.
- [ ] CRITICAL ARCHITECTURE: Upon successful form submission to `/api/v1/public/leads/capture`, DO NOT open the returned presigned URL in a new tab (this causes popup-blocker issues). Instead, update the modal state to show a prominent "Download Now" `<a>` button containing the URL.
- [ ] Component Tests: Simulate typing an invalid email (assert Zod error appears). Simulate a successful fetch and assert the "Download Now" button renders.
- [ ] File location: `/frontend-public/src/components/gallery/InfographicFeed.tsx`, `/frontend-public/src/components/forms/DownloadModal.tsx`
</ac-block>
