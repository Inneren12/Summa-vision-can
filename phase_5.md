# Phase 5: B2B Funnel, Email Automation & Media Kit (Pack J)
Здесь мы превращаем сырой трафик в деньги. Отсеиваем зевак, находим корпоративных клиентов и оповещаем команду продаж.

## PR-35: B2B Lead Scoring Engine

```
Role: Python Data Engineer.
Task: Execute PR-35 for the "Summa Vision" project.
Context (Human): We need to identify high-value B2B leads by analyzing their email domains.
```

<ac-block id="Ph5-PR35-AC1">
**Acceptance Criteria for PR-35 (B2B Lead Scorer):**
- [ ] Create Pydantic model `LeadScore(is_b2b: bool, company_domain: str | None, category: str)`. Categories: `b2b`, `education`, `isp`, `b2c`.
- [ ] Create `LeadScoringService`. Maintain static lists for:
      - Free email domains: `gmail.com`, `yahoo.com`, `outlook.com`, `hotmail.com`, `protonmail.com`, etc.
      - Canadian ISP domains: `shaw.ca`, `rogers.com`, `bell.net`, `telus.net`, `videotron.ca`, `sasktel.net`, etc.
      - **[FIX]** Top-20 Canadian university domains (hardcoded): `utoronto.ca`, `ubc.ca`, `mcgill.ca`, `uwaterloo.ca`, `ualberta.ca`, `queensu.ca`, `sfu.ca`, `yorku.ca`, `ucalgary.ca`, `uottawa.ca`, `dal.ca`, `uvic.ca`, `usask.ca`, `umanitoba.ca`, `concordia.ca`, `wlu.ca`, `torontomu.ca`, `carleton.ca`, `uoguelph.ca`, `unb.ca`.
- [ ] **[FIX]** Domain classification priority rules:
      1. All `.edu` domains → `education`.
      2. Domains matching the Top-20 university list → `education`.
      3. `.ca` domains containing `uni`, `college`, `school`, `academy`, `institut` → `education`.
      4. Domains in the ISP list → `isp` (not B2B, not B2C — separate category for nuanced handling).
      5. Domains in the free email list → `b2c`.
      6. Everything else → `b2b`.
- [ ] Implement `score_lead(email: str) -> LeadScore`.
- [ ] CRITICAL ARCHITECTURE: This must be a pure, synchronous function decoupled from any database or network operations for blazing-fast execution.
- [ ] Unit Tests: Test `john@rogers.com` -> `isp`. Test `sarah@utoronto.ca` -> `education`. Test `ceo@tdbank.ca` -> `b2b`. Test `me@gmail.com` -> `b2c`. **[FIX]** Test `admin@college-ontario.ca` -> `education` (pattern match). Test `info@unknowncompany.ca` -> `b2b` (default).
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/crm/scoring.py`
</ac-block>

---

## PR-34 & 49: ESP Client, Background Sync & Failsafe

```
Role: Python Backend Engineer.
Task: Execute PR-34 and PR-49 for the "Summa Vision" project.
Context (Human): Push captured leads to our Email Service Provider (ESP) without making the user wait. Ensure no leads are lost if the ESP API goes down.
```

<ac-block id="Ph5-PR34-49-AC1">
**Acceptance Criteria for ESP Sync & Failsafe:**
- [ ] Define `EmailServiceInterface` with `async_add_subscriber` and `async_add_tag`. Implement ESP client (e.g., Beehiiv) satisfying the interface.
- [ ] Update `/api/v1/public/leads/capture`: After saving to the local DB (from PR-31), use `fastapi.BackgroundTasks` to trigger the ESP sync in the background so the HTTP response is instant.
- [ ] CRITICAL ARCHITECTURE (Failsafe): In the background task, handle ESP errors as follows:
      - **[FIX]** If ESP returns `5xx` (server error / timeout): set `esp_synced=False` on the Lead in our DB. These are retryable.
      - **[FIX]** If ESP returns `4xx` (client error, e.g., invalid email on Beehiiv side, duplicate rejection): set `esp_sync_failed_permanent=True`. These are NOT retryable — the ESP has explicitly rejected this lead.
- [ ] Create endpoint `POST /api/v1/admin/leads/resync` that fetches all leads where `esp_synced=False AND esp_sync_failed_permanent=False` and retries sending them to the ESP.
- [ ] **[FIX]** Resync MUST implement exponential backoff (1s, 2s, 4s) between retries for each lead, with a max of 3 attempts per resync run. If a lead fails 3 times in one resync run, skip it and move to the next (it will be retried on the next resync invocation).
- [ ] Unit Tests: Mock an ESP 500 error -> assert Lead remains in DB with `esp_synced=False`. **[FIX]** Mock an ESP 400 error -> assert Lead is marked `esp_sync_failed_permanent=True` and is excluded from `get_unsynced()` query.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/services/email/esp_client.py`, `/backend/src/services/email/resync.py`
</ac-block>

---

## PR-36: Next.js Media Kit ("Partner with Us")

```
Role: Expert Frontend Engineer.
Task: Execute PR-36 for the "Summa Vision" project.
Context (Human): A static landing page explaining our sponsorship tiers and a form for B2B inquiries.
```

<ac-block id="Ph5-PR36-AC1">
**Acceptance Criteria for PR-36 (Media Kit UI):**
- [ ] Create static page `/partner-with-us`.
- [ ] Build 3 sections: "Our Audience" (metrics), "Sponsorship Tiers" (pricing table, e.g., $75 CPM), and "Custom Content".
- [ ] **[FIX]** Extract all pricing data and tier descriptions into a separate constants file (`/frontend-public/src/lib/constants/pricing.ts`). Do NOT inline pricing values in JSX. When pricing changes, only one file needs updating — no component code changes, no risk of missing a hardcoded value.
- [ ] Add an Inquiry Form (Name, Company Email, Budget, Message) using `react-hook-form` + `zod`.
- [ ] **[FIX]** Zod validation for Company Email MUST reject known free email domains (gmail.com, yahoo.com, etc.) and Canadian ISP domains (shaw.ca, rogers.com, etc.) on the client side, showing the message: "Please use your corporate email address." Maintain a shared domain list in `/frontend-public/src/lib/constants/free_domains.ts`.
- [ ] CRITICAL ARCHITECTURE: Hardcode static text for now (no CMS needed for MVP) to optimize page speed. The form MUST submit to `POST /api/v1/public/sponsorship/inquire`.
- [ ] Component Tests: Assert the page renders the 3 main pricing tiers. Assert form validation triggers on empty fields. **[FIX]** Assert that entering `test@gmail.com` shows the corporate email error.
- [ ] File location: `/frontend-public/src/app/partner-with-us/page.tsx`, `/frontend-public/src/lib/constants/pricing.ts`
</ac-block>

---

## PR-37 & 38: B2B Inquiry API & Slack Notifications

```
Role: Python Backend Engineer.
Task: Execute PR-37 for the "Summa Vision" project.
Context (Human): Process sponsorship inquiries, filter out spam/B2C emails, and immediately alert the sales team.
```

<ac-block id="Ph5-PR37-38-AC1">
**Acceptance Criteria for PR-37 (Inquiry API & Notifications):**
- [ ] Create router `POST /api/v1/public/sponsorship/inquire`.
- [ ] Apply a strict Rate Limit (e.g., 1 request per 5 minutes per IP) using the `InMemoryRateLimiter`.
- [ ] **[FIX]** CRITICAL ARCHITECTURE: Use the `LeadScoringService` to classify the email, then apply tiered handling:
      - **`b2b`** category: Accept the inquiry. Send full details to Slack via `SlackNotifierService`. Return `HTTP 200`.
      - **`education`** category: Accept the inquiry. Send to Slack with a `[EDUCATION]` tag. Return `HTTP 200`.
      - **`isp`** category: Accept the inquiry (a Rogers employee using personal ISP email could be a real lead). Save to DB but do NOT send to Slack. Tag as `low_priority` in the database. Return `HTTP 200`.
      - **`b2c`** category (gmail, yahoo, etc.): Reject with `HTTP 422 Unprocessable Entity` and message `"Please use your corporate email address for sponsorship inquiries."`.
      Note: Hard reject only B2C free email. ISP emails are accepted silently to avoid losing edge-case leads (e.g., a bank VP who uses their home ISP email).
- [ ] Implement `SlackNotifierService` to push the validated lead's details (Budget, Company Domain, Message, Category) to an internal Slack webhook.
- [ ] Unit Tests: Test `user@gmail.com` rejection (assert 422). Test `user@rogers.com` acceptance without Slack call. Test `ceo@tdbank.ca` acceptance WITH Slack call. Mock the Slack webhook and assert correct payload formatting.
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/api/routers/public_sponsorship.py`, `/backend/src/services/notifications/slack.py`
</ac-block>
