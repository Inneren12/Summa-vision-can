# Phase 3: Flutter Command Center (Sprint 3 + Pack G)
Переходим к фронтенду. Агент должен собрать чистую, тестируемую архитектуру на Riverpod.

## PR-20 & 42b: Flutter Init, Theme & Auth Interceptor

```
Role: Expert Flutter Developer.
Task: Execute PR-20 for the "Summa Vision" project.
Context (Human): Initialize the Flutter project, set up the design system (WCAG compliant), and configure the Dio HTTP client to automatically inject our Admin API key.
```

<ac-block id="Ph3-PR20-AC1">
**Acceptance Criteria for PR-20 (Flutter Init & Dio):**
- [ ] Initialize Flutter Web/Desktop project.
- [ ] Configure `AppTheme` with `ThemeData.dark()`. Ensure the `#141414` background and neon accents pass WCAG AA contrast ratios.
- [ ] Set up `dio` HTTP client. Create `AuthInterceptor` that appends the `X-API-KEY` header (loaded via `flutter_dotenv`) to every request.
- [ ] CRITICAL ARCHITECTURE: Create a `MockInterceptor` that can be toggled via env variables. It should return local JSON fixtures for the Queue endpoint to unblock UI development without running the backend.
- [ ] **[FIX]** `MockInterceptor` MUST simulate realistic network delay using `Future.delayed(Duration(seconds: 1))` before returning fixtures. Without this, `AsyncValue.loading` states flash for milliseconds and loading-related UI bugs are invisible during development.
- [ ] Widget Tests: Ensure `MaterialApp` boots. Test Dio initialization.
- [ ] File location: `/frontend/lib/core/theme/app_theme.dart`, `/frontend/lib/core/network/dio_client.dart`, `/frontend/lib/core/network/auth_interceptor.dart`
- [ ] Test location: `/frontend/test/core/theme_test.dart`
</ac-block>

---

## PR-46: GoRouter Navigation Setup

```
Role: Expert Flutter Developer.
Task: Execute PR-46 for the "Summa Vision" project.
Context (Human): Implement declarative routing to prevent `Navigator.push` spaghetti code and enable deep-linking on Flutter Web.
```

<ac-block id="Ph3-PR46-AC1">
**Acceptance Criteria for PR-46 (GoRouter):**
- [ ] Install `go_router`.
- [ ] Define routes: `/queue` (QueueScreen), `/editor/:briefId` (EditorScreen), `/preview/:taskId` (PreviewScreen).
- [ ] CRITICAL ARCHITECTURE: Inject the router via Riverpod (`Provider<GoRouter>`). Set the initial location (redirect) to `/queue`.
- [ ] Widget Tests: Test navigation between dummy placeholder screens. Assert invalid paths redirect to `/queue`.
- [ ] File location: `/frontend/lib/core/routing/app_router.dart`
- [ ] Test location: `/frontend/test/core/routing/app_router_test.dart`
</ac-block>

---

## PR-22: Models & Queue Screen (Refresh Flow)

```
Role: Expert Flutter Developer.
Task: Execute PR-22 for the "Summa Vision" project.
Context (Human): The Queue UI where the journalist reviews the LLM's suggested viral topics.
```

<ac-block id="Ph3-PR22-AC1">
**Acceptance Criteria for PR-22 (Queue UI):**
- [ ] Create `ContentBrief` model using `freezed` and `json_serializable`.
- [ ] **[FIX]** Write a schema-comparison test: Export the Pydantic `ContentBrief.model_json_schema()` from the Python backend into a static JSON file (`/backend/schemas/content_brief.schema.json`). In the Dart test, load this file and compare field names and types against the Dart model's `toJson()` output. This catches frontend/backend model drift without needing a running server.
- [ ] Build `QueueScreen`. Display the virality score (green if >8), headline, and chart type. Add "Approve" (navigates to Editor) and "Reject" buttons.
- [ ] CRITICAL ARCHITECTURE: Add a "Refresh / Request More" button that invalidates the Riverpod `FutureProvider` and triggers a new LLM generation request. Handle `AsyncValue` loading/error states.
- [ ] Widget Tests: Pump widget with mock state, assert refresh button triggers the repository call.
- [ ] File location: `/frontend/lib/features/queue/presentation/queue_screen.dart`, `/frontend/lib/features/queue/domain/content_brief.dart`
</ac-block>

---

## PR-23: Editor Screen UI & Form State

```
Role: Expert Flutter Developer.
Task: Execute PR-23 for the "Summa Vision" project.
Context (Human): A form allowing the journalist to tweak the LLM's headline or change the chart type before sending it to the rendering engine.
```

<ac-block id="Ph3-PR23-AC1">
**Acceptance Criteria for PR-23 (Editor UI):**
- [ ] Build `EditorScreen`. Extract the `briefId` from `go_router` state.
- [ ] Add `TextFormField` for `headline` and `bg_prompt`.
- [ ] Add a `DropdownButton` (or segmented control) to allow editing the `chart_type` (e.g., changing BAR to SCATTER).
- [ ] CRITICAL ARCHITECTURE: Use a Riverpod `Notifier` to manage the local form state without mutating the original immutable `ContentBrief` object directly.
- [ ] Add a visual placeholder button for "Preview Background" (stub for future use).
- [ ] Widget Tests: Modify form fields and assert the Riverpod state updates correctly.
- [ ] File location: `/frontend/lib/features/editor/presentation/editor_screen.dart`
</ac-block>

---

## PR-24 & 44: Graphic Generation & Polling (Preview Screen)

```
Role: Expert Flutter Developer.
Task: Execute PR-24 for the "Summa Vision" project.
Context (Human): The final screen. It submits the task, polls the backend (since rendering takes 20s), and displays the final downloaded image.
```

<ac-block id="Ph3-PR24-44-AC1">
**Acceptance Criteria for PR-24 (Preview & Polling):**
- [ ] Implement `GraphicRepository.generateGraphic()`. It MUST handle the `202 Accepted` response from the backend, extract the `task_id`, and start a polling loop hitting `GET /api/v1/admin/tasks/{task_id}` every 2 seconds.
- [ ] **[FIX]** Implement a maximum polling limit of 60 attempts (= 2 minutes). If the task is still not COMPLETED after 60 polls, stop polling and show an error state with a "Generation timed out. Try again?" message and a Retry button. Do NOT leave the user staring at an infinite spinner.
- [ ] Build `PreviewScreen`. Show a `CircularProgressIndicator` or Skeleton loader during the polling phase.
- [ ] Once polling returns `COMPLETED` and the `result_url` (S3 presigned URL), display the image using `Image.network` (or download bytes for `Image.memory`).
- [ ] CRITICAL ARCHITECTURE: Cache the image state in Riverpod so navigating back and forth doesn't restart the 20-second generation.
- [ ] **[FIX]** Add a "Download/Save" button. For Flutter Web: implement using `html.AnchorElement` with `download` attribute. For Flutter Desktop: use `file_picker` or `path_provider` to let the user choose a save directory. Both platforms must be handled.
- [ ] Widget Tests: Mock the polling repository. Assert UI transitions from loading -> success image. **[FIX]** Test the timeout scenario: mock 60 failed polls, assert the error/retry UI is shown.
- [ ] File location: `/frontend/lib/features/graphics/presentation/preview_screen.dart`, `/frontend/lib/features/graphics/data/graphic_repository.dart`
</ac-block>
