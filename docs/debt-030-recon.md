# DEBT-030 RECON — Editor endpoint structured `error_code` for localized operator messaging

## 1) Summary
The three editor-action endpoints are defined in `backend/src/api/routers/admin_publications.py` as PATCH `/{publication_id}`, POST `/{publication_id}/publish`, and POST `/{publication_id}/unpublish`.
Current explicit business failures are `404 Publication not found`; middleware contributes `401/429`; request validation contributes `422`.
Frontend editor flow does not yet call these endpoints; localized operator messaging for these actions is not active yet.
Recommended contract: structured `error_code` inside `detail` (Option A), then extend frontend mapper and ARB keys.
Founder decisions (2026-04-26) are reflected in implementation plan and questions section.

## 2) Current state

### Endpoint locations
- `PATCH /api/v1/admin/publications/{publication_id}`: `backend/src/api/routers/admin_publications.py:337`
- `POST /api/v1/admin/publications/{publication_id}/publish`: `backend/src/api/routers/admin_publications.py:470`
- `POST /api/v1/admin/publications/{publication_id}/unpublish`: `backend/src/api/routers/admin_publications.py:524`

### Error path inventory
| Endpoint | Trigger condition | HTTP status | Current response body shape | Current detail/error text | RU operator sees today |
|---|---|---:|---|---|---|
| PATCH | missing row pre-read | 404 | `{"detail": "..."}` | `Publication not found` | not wired yet |
| PATCH | missing row post-update | 404 | `{"detail": "..."}` | `Publication not found` | not wired yet |
| PATCH | invalid payload schema | 422 | FastAPI validation (`detail` array) | framework-generated | raw/unmapped |
| PATCH | missing/invalid API key | 401 | `{"error": "..."}` | middleware text | raw/unmapped |
| PATCH | rate limited | 429 | `{"error": "..."}` | middleware text | raw/unmapped |
| publish | missing row | 404 | `{"detail": "..."}` | `Publication not found` | not wired yet |
| publish | missing/invalid API key | 401 | `{"error": "..."}` | middleware text | raw/unmapped |
| publish | rate limited | 429 | `{"error": "..."}` | middleware text | raw/unmapped |
| unpublish | missing row | 404 | `{"detail": "..."}` | `Publication not found` | not wired yet |
| unpublish | missing/invalid API key | 401 | `{"error": "..."}` | middleware text | raw/unmapped |
| unpublish | rate limited | 429 | `{"error": "..."}` | middleware text | raw/unmapped |

### Frontend handling
- `mapBackendErrorCode(String? errorCode, AppLocalizations l10n)` exists in `frontend/lib/l10n/backend_errors.dart` and currently maps job codes only.
- `editorActionError` exists in ARB but editor notifier comments show save/publish/unpublish backend actions are future work.

## 3) Proposed error_code vocabulary
| Error code | Trigger | Endpoint(s) | Operator action |
|---|---|---|---|
| `PUBLICATION_NOT_FOUND` | publication missing | all 3 | refresh list |
| `PUBLICATION_UPDATE_PAYLOAD_INVALID` | PATCH validation failure | PATCH | fix input and retry |
| `AUTH_API_KEY_MISSING` | header missing | all 3 | re-authenticate |
| `AUTH_API_KEY_INVALID` | bad key | all 3 | re-authenticate |
| `AUTH_ADMIN_RATE_LIMITED` | rate limit exceeded | all 3 | wait and retry |
| `PUBLICATION_INTERNAL_SERIALIZATION_ERROR` | internal repo serialization issue | PATCH | retry/escalate |

## 4) ARB additions (EN + RU)
| ARB key | EN value | RU value | @description |
|---|---|---|---|
| `editorErrorPublicationNotFound` | This publication no longer exists. It may have been deleted. | Эта публикация больше не существует. Возможно, она была удалена. | Missing publication target |
| `editorErrorPublicationUpdatePayloadInvalid` | The submitted changes are invalid. Check required fields and formats. | Отправленные изменения некорректны. Проверьте обязательные поля и формат. | PATCH 422 guidance |
| `editorErrorAuthApiKeyMissing` | Authentication is missing. Please sign in again. | Отсутствуют данные авторизации. Войдите снова. | Missing API key |
| `editorErrorAuthApiKeyInvalid` | Your session is invalid. Please sign in again. | Сессия недействительна. Войдите снова. | Invalid API key |
| `editorErrorAuthAdminRateLimited` | Too many admin requests. Please wait a minute and try again. | Слишком много административных запросов. Подождите минуту и попробуйте снова. | Admin rate limit |
| `editorErrorPublicationInternalSerializationError` | Could not save this publication due to a server data format issue. Try again. | Не удалось сохранить публикацию из-за серверной ошибки формата данных. Повторите попытку. | Internal serialization failure fallback |

## 5) Backend contract
### Current
Current explicit endpoint failures use `HTTPException(detail="...")` -> `{"detail": "Publication not found"}`.

### Proposed convention
Use Option A (`detail` as object):
```json
{
  "detail": {
    "error_code": "PUBLICATION_NOT_FOUND",
    "message": "Publication not found"
  }
}
```

### Pydantic model proposal
```python
class StructuredErrorDetail(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] | None = None

class StructuredErrorResponse(BaseModel):
    detail: StructuredErrorDetail
```

### Exception base proposal
```python
class PublicationApiError(HTTPException):
    status_code_value = 400
    error_code = "PUBLICATION_UNKNOWN_ERROR"
    message = "Publication action failed"

    def __init__(self, *, details: dict | None = None):
        super().__init__(
            status_code=self.status_code_value,
            detail={"error_code": self.error_code, "message": self.message, **({"details": details} if details else {})},
        )
```

## 6) Frontend mapper extension
Add new switch cases in `backend_errors.dart` for the six codes above.
No signature change required now.
Wire into future editor action notifier/UI path when endpoints are integrated.

## 7) Test coverage matrix
| Error code | Backend integration test | Frontend mapper test | Pipeline integration test |
|---|---|---|---|
| `PUBLICATION_NOT_FOUND` | missing id on PATCH/publish/unpublish returns 404 + code | EN/RU mapper assertion | when editor flow exists |
| `PUBLICATION_UPDATE_PAYLOAD_INVALID` | invalid PATCH returns 422 + code | EN/RU mapper assertion | mocked HTTP 422 -> notifier -> UI |
| `AUTH_API_KEY_MISSING` | 401 with code | mapper assertion | optional per UX |
| `AUTH_API_KEY_INVALID` | 401 with code | mapper assertion | optional per UX |
| `AUTH_ADMIN_RATE_LIMITED` | 429 with code | mapper assertion | optional per UX |
| `PUBLICATION_INTERNAL_SERIALIZATION_ERROR` | forced internal error -> structured failure | mapper assertion | mocked failure -> notifier -> UI |

Test homes:
- `backend/tests/api/test_admin_publications.py`
- `frontend/test/l10n/backend_errors_test.dart`
- `frontend/test/features/editor/presentation/editor_screen_test.dart`

## 8) Implementation plan
Recommended: **combined backend + frontend PR** per founder decision.
- Backend: structured errors + endpoint refactor + tests.
- Frontend: ARB keys + mapper extension + editor flow wiring + pipeline tests.
Dependency order remains backend-first logically, but can land in one coordinated PR.

## 9) Founder questions (captured decisions)
Q1 (envelope consistency): Decision A — keep middleware envelope, add sibling `error_code` field (Variant 1).
Q3 (include auth/rate-limit codes): Decision A — include `AUTH_*`/rate-limit codes now.
Q4 (publish/unpublish semantics): Decision A — keep idempotent behavior.
Plan decision: combined backend + frontend implementation PR.

## 10) DEBT.md update draft
> **DEBT-030 — Structured editor endpoint error codes for localized operator messaging**
>
> Scope includes PATCH/publish/unpublish admin publication endpoints with stable `error_code` and frontend EN/RU mapping.
>
> Delivered: backend structured errors, frontend mapper/ARB updates, and integration coverage (backend + frontend mapper + editor pipeline tests).
