Phase 2.5: Security Perimeter (Pack F)
Защищаем наши дорогие эндпоинты с LLM от выгорания бюджета случайными парсерами или ботами.

PR-42: Auth Middleware & Namespace Isolation
Plaintext
Role: Security/Backend Engineer.
Task: Execute PR-42 for the "Summa Vision" project.
Context (Human): Admin endpoints (graphic generation, queue fetching) are exposed. Anyone could burn our LLM tokens. We must isolate namespaces and enforce API Key authentication.

<ac-block id="Ph2.5-PR42-AC1">
Acceptance Criteria for PR-42 (API Key Auth):
- [ ] Create `AuthMiddleware` acting on all routes under `/api/v1/admin/*`.
- [ ] Public routes (`/api/v1/public/*`) MUST bypass this middleware.
- [ ] The middleware MUST check for the `X-API-KEY` header. If missing or invalid, immediately return `HTTP 401 Unauthorized`.
- [ ] CRITICAL ARCHITECTURE: The valid API key MUST be loaded securely via `BaseSettings.ADMIN_API_KEY`. Never hardcode it. Add JWT placeholder comments for future B2B client expansion.
- [ ] Unit Tests: Test a request to a private endpoint without a key (assert 401). Test with a valid key (assert 200). Test a public endpoint without a key (assert 200).
- [ ] Code coverage >90%.
- [ ] File location: `/backend/src/core/security/auth.py`
- [ ] Test location: `/backend/tests/core/security/test_auth.py`
</ac-block>