# CHANGELOG: Phase Updates (Review Fixes)

Все изменения помечены `[FIX]` в файлах фаз. Ниже — полный список что добавлено и где.

---

## Phase 0
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-00b | `alembic upgrade head` шаг в CI pipeline | После PR-39 тесты зависят от миграций БД |

## Phase 1
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-07 | Метод `upload_json()` в StorageInterface | Нужен для сохранения метаданных и HTML снапшотов |
| PR-11 | TODO-комментарий о миграции на Redis/DB store | In-memory state теряется при рестарте |
| PR-12 | `SCHEDULER_DB_URL` в BaseSettings (отдельно от DATABASE_URL) | Job store должен мигрировать на PostgreSQL вместе с основной БД |

## Phase 1.5
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-39 | `esp_synced: bool` и `esp_sync_failed_permanent: bool` в Lead модели | Требуется Phase 5 для ESP failsafe и resync |
| PR-40 | `get_drafts(limit)` в PublicationRepository | Phase 2 `GET /api/v1/admin/queue` зависит от этого метода |
| PR-40 | `get_unsynced()`, `mark_synced()`, `mark_permanently_failed()` в LeadRepository | Phase 5 resync механизм |
| PR-41 | `Cache-Control: public, max-age=3600` header | Совпадение с Next.js ISR revalidate=3600 |

## Phase 2
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-14/47 | Cache key = `prompt_hash + data_hash` | Инвалидация кэша при обновлении данных StatCan |
| PR-17 | Size presets: `SIZE_INSTAGRAM`, `SIZE_TWITTER`, `SIZE_REDDIT` | Три основных канала дистрибуции |
| PR-18 | `size` параметр в AIImageClient, DPI по умолчанию 150 (не 300) | 300 DPI для соцсетей = тяжёлые файлы, 150 достаточно |

## Phase 2.5
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-42 | Вторичный rate limit 10 req/min для admin endpoints | Защита бюджета при утечке API key |

## Phase 3
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-20 | `Future.delayed(1s)` в MockInterceptor | Loading states невидимы без задержки |
| PR-22 | Schema comparison test (Pydantic JSON Schema → Dart model) | Ловит frontend/backend drift без запущенного сервера |
| PR-24 | Max 60 polling attempts (2 мин таймаут) | Бесконечный спиннер при зависшей генерации |
| PR-24 | Desktop file save через `file_picker`/`path_provider` | `html.AnchorElement` работает только на Web |
| PR-24 | Тест timeout-сценария | Покрытие error/retry UI |

## Phase 4
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-29 | `NEXT_PUBLIC_API_URL` env variable | Конфигурация API URL для dev/prod |
| PR-31 | `InMemoryRateLimiter` конфигурируемый (`max_requests`, `window_seconds`) | Переиспользование в gallery, leads, sponsorship |
| PR-31 | Валидация `asset_id` через PublicationRepository | Предотвращает presigned URL для несуществующих объектов |
| PR-31 | CORS конфигурация `summa.vision` + `localhost:3000` | Потерялась при рефакторинге из спринтов в фазы |

## Phase 5
| PR | Что добавлено | Зачем |
|----|--------------|-------|
| PR-35 | Категория `isp` отдельно от `b2c` | Rogers/Shaw ≠ Gmail. ISP-пользователь может быть реальным B2B |
| PR-35 | Top-20 канадских университетов + паттерн-матчинг | `.ca` домены с `uni/college/school` → education |
| PR-34/49 | Разделение 4xx/5xx ошибок ESP | 4xx = permanent fail (не ретраить), 5xx = temporary (ретраить) |
| PR-34/49 | Exponential backoff в resync (max 3 попытки) | Не спамить ESP при массовом resync |
| PR-36 | `pricing.ts` вынесен в constants | Изменение цен без правки компонентов |
| PR-36 | Zod-валидация email на клиенте (free + ISP домены) | UX: ошибка до отправки формы |
| PR-37/38 | Tiered handling: b2b→Slack, education→Slack+tag, isp→DB only, b2c→reject | Не теряем edge-case лиды (ISP), не спамим Slack шумом |
