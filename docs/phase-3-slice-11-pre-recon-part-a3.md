# Phase 3 Slice 3.11 — Pre-Recon Part A3 (Switcher + Smokes + Scripts)

> Read-only inventory covering §4 (language switcher), §5 (locale-switch smoke tests),
> §6 (scripts directory). Prerequisites `docs/phase-3-slice-11-pre-recon-part-a1.md`
> (26 579 B, 357 L) and `docs/phase-3-slice-11-pre-recon-part-a2.md` (17 178 B, 180 L)
> confirmed on disk.

## Section 4 — Language switcher inventory

### 4.1 — Full file content

`frontend/lib/core/shell/language_switcher.dart` (80 lines, 2 213 bytes):

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

/// Compact language switcher for the app shell.
///
/// Renders two pill buttons (EN / RU). Tapping a button changes the active
/// locale via AppBootstrapNotifier, which persists to SharedPreferences.
class LanguageSwitcher extends ConsumerWidget {
  const LanguageSwitcher({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = AppLocalizations.of(context)!;
    final currentLocale =
        ref.watch(appBootstrapProvider).valueOrNull?.locale ??
        const Locale('en');
    final currentCode = currentLocale.languageCode;

    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 4,
      runSpacing: 4,
      children: [
        Padding(
          padding: const EdgeInsets.only(right: 4),
          child: Text(
            loc.languageLabel,
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ),
        _LanguageButton(
          label: loc.languageEnglish,
          code: 'en',
          active: currentCode == 'en',
        ),
        _LanguageButton(
          label: loc.languageRussian,
          code: 'ru',
          active: currentCode == 'ru',
        ),
      ],
    );
  }
}

class _LanguageButton extends ConsumerWidget {
  final String label;
  final String code;
  final bool active;

  const _LanguageButton({
    required this.label,
    required this.code,
    required this.active,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return TextButton(
      onPressed: active
          ? null
          : () => ref.read(appBootstrapProvider.notifier).setLocale(
                Locale(code),
              ),
      style: TextButton.styleFrom(
        minimumSize: const Size(40, 32),
        padding: const EdgeInsets.symmetric(horizontal: 10),
        backgroundColor:
            active ? theme.colorScheme.secondaryContainer : Colors.transparent,
        foregroundColor: active
            ? theme.colorScheme.onSecondaryContainer
            : theme.colorScheme.onSurfaceVariant,
      ),
      child: Text(label),
    );
  }
}
```

### 4.2 — Analysis

| Attribute | Value |
|-----------|-------|
| Line count | 80 |
| Public widget | `LanguageSwitcher` — `ConsumerWidget` (Riverpod) |
| Private widget | `_LanguageButton` — `ConsumerWidget` (Riverpod) |
| UX pattern | "segmented TextButton pair" — `Wrap` of `[labelText, TextButton('English'), TextButton('Russian')]`; no dropdown, no popup, no radio |
| Gesture mechanism | `TextButton.onPressed` — set to `null` when button is already active (disabling taps on the current locale), otherwise calls `ref.read(appBootstrapProvider.notifier).setLocale(Locale(code))` |
| Current-locale visual indicator | Background/foreground color swap via `TextButton.styleFrom(backgroundColor: theme.colorScheme.secondaryContainer if active else Colors.transparent, foregroundColor: onSecondaryContainer if active else onSurfaceVariant)` + disabled tap. **No checkmark, no bold, no border, no icon/flag.** |
| `Semantics` widget | ❌ absent |
| `semanticsLabel` on any `Text` | ❌ absent (both `Text(loc.languageEnglish)` and `Text(loc.languageRussian)` have no `semanticsLabel`) |
| `Tooltip` | ❌ absent |
| `ExcludeSemantics` | ❌ absent |
| Keyboard focus handling | Default Flutter `TextButton` focus only — no explicit `FocusNode`, no `Focus` wrapper, no `Shortcuts`, no `Actions`, no `autofocus` parameter |
| Icons / flags / images | ❌ none (`Icon`, `Image.asset`, emoji all absent) |
| State read | `ref.watch(appBootstrapProvider).valueOrNull?.locale ?? const Locale('en')` (`AsyncValue` unwrap with EN fallback) |
| State write | `ref.read(appBootstrapProvider.notifier).setLocale(Locale(code))` on inner `_LanguageButton` tap |
| Comments / TODOs | Class-level `///` doc comment (lines 6–9). No `TODO` / `FIXME` / `HACK` markers anywhere in file. |

### 4.3 — Import / instantiation sites

Grep: `grep -rn "language_switcher\|LanguageSwitcher" frontend/{lib,test}/ | grep -v "language_switcher.dart:"`

| File | Line | Kind |
|------|-----:|------|
| `frontend/lib/core/routing/app_drawer.dart` | 3 | `import` |
| `frontend/lib/core/routing/app_drawer.dart` | 40 | Instantiation: `const LanguageSwitcher()` inside drawer header `Column` |
| `frontend/test/l10n/queue_locale_switch_smoke_test.dart` | 8 | `import` |
| `frontend/test/l10n/queue_locale_switch_smoke_test.dart` | 76 | `find.byType(LanguageSwitcher)` assertion |
| `frontend/test/l10n/editor_locale_switch_smoke_test.dart` | 7 | `import` |
| `frontend/test/l10n/editor_locale_switch_smoke_test.dart` | 35 | Instantiation: `AppBar(actions: const [LanguageSwitcher()])` |
| `frontend/test/l10n/graphics_locale_switch_smoke_test.dart` | 6 | `import` |
| `frontend/test/l10n/graphics_locale_switch_smoke_test.dart` | 67 | Instantiation: `AppBar(actions: const [LanguageSwitcher()])` |

- **Production instantiations:** 1 (`app_drawer.dart:40`).
- **Test instantiations:** 3 (queue via drawer mount, editor + graphics via direct `AppBar.actions`).
- **Production imports:** 1. **Test imports:** 3. All 4 call sites reach the same widget constructor.

## Section 5 — Locale-switch smoke test inventory

### 5.1 — Directory listing

`ls -la frontend/test/l10n/` — 6 files present:

| File | Bytes | Lines | Relevant to §5? |
|------|-----:|-----:|:---------------:|
| `backend_errors_test.dart` | 4 237 | 124 | no (unit tests for `mapBackendErrorCode`) |
| `drawer_localization_test.dart` | 3 542 | 100 | no (drawer-specific localization, no switch action) |
| `queue_locale_switch_smoke_test.dart` | 3 488 | 96 | **yes** (expected) |
| `editor_locale_switch_smoke_test.dart` | 2 960 | 84 | **yes** (expected) |
| `graphics_locale_switch_smoke_test.dart` | 3 433 | 96 | **yes** (expected) |
| `locale_switch_smoke_test.dart` | 4 765 | 154 | **yes** (additional — not listed in spec's "expected 3") |

`find frontend/test -name "*smoke*" -o -name "*locale*"` also surfaces three `*_denied_en_smoke_test.dart` files under `frontend/test/features/{editor,queue,graphics}/` — those are not locale-switch tests (they verify EN-only fallback when locale cannot resolve); noted for completeness, excluded from §5 scope.

### 5.2 — Per-file report

#### 5.2.1 — `queue_locale_switch_smoke_test.dart` (96 L)

- `testWidgets` blocks: **1**
- Test description: _"Queue strings rerender after EN -> RU switch"_
- Coverage: mounts `QueueScreen` with `queueProvider` overridden to a single `DRAFT` brief, asserts EN strings (`Brief Queue`, `Reject`, `Approve`) are visible, opens the drawer via the hamburger icon, taps the English/Russian switcher's `Russian` `TextButton`, re-asserts RU strings (`Очередь брифов`, `Отклонить`, `Одобрить`) plus absence of EN.
- Router / app pattern: inline `MaterialApp.router` with an ad-hoc `GoRouter` exposing only `AppRoutes.queue` → `QueueScreen`. No helper.
- Language switcher entry point: reached via drawer (`find.byIcon(Icons.menu)` → `Scaffold.drawer` → `AppDrawer` → `LanguageSwitcher`).
- Assertion style: **hardcoded strings** (both EN and RU literals). No `l10n.<key>` lookup. Uses `findsOneWidget` + `findsAtLeastNWidgets(1)` mix (documented in an in-file comment about the `queueTitle`≡`navQueue` duplicate value).

#### 5.2.2 — `editor_locale_switch_smoke_test.dart` (84 L)

- `testWidgets` blocks: **1**
- Test description: _"Editor strings rerender after EN -> RU switch"_
- Coverage: mounts `EditorScreen(briefId: '42')` with `queueProvider` overridden (brief 42), asserts EN strings (`Headline`, `Chart Type`, `Generate Graphic`), taps `Russian` button inside `AppBar.actions` `LanguageSwitcher`, re-asserts RU (`Заголовок`, `Тип графика`, `Сгенерировать графику`).
- Router / app pattern: inline `MaterialApp.router` + `GoRouter` with a single `/editor/:briefId` route whose builder returns `Scaffold(appBar: AppBar(actions: const [LanguageSwitcher()]), body: EditorScreen(...))`.
- Language switcher entry point: direct `AppBar.actions` (bypasses drawer).
- Assertion style: **hardcoded strings**. Uses `skipOffstage: false` on the `Russian` finder to reach the switcher inside the AppBar action menu regardless of layout.

#### 5.2.3 — `graphics_locale_switch_smoke_test.dart` (96 L)

- `testWidgets` blocks: **1**
- Test description: _"ChartConfigScreen chrome rerenders after EN -> RU switch"_
- Coverage: mounts `ChartConfigScreen(storageKey: 'statcan/…/data.parquet')` under mocked `chartConfigNotifierProvider` + `chartGenerationNotifierProvider` (two inline mock `Notifier` subclasses in-file), asserts EN (`Chart Configuration`, `Dataset`, `Background Category`), taps `Russian` in `AppBar.actions`, re-asserts RU (`Настройка графика`, `Набор данных`, `Категория фона`).
- Router / app pattern: inline **`MaterialApp`** (non-router) with `home: Scaffold(appBar: AppBar(actions: const [LanguageSwitcher()]), body: ChartConfigScreen(...))`.
- Language switcher entry point: direct `AppBar.actions`.
- Assertion style: **hardcoded strings**. Same `skipOffstage: false` trick.

#### 5.2.4 — `locale_switch_smoke_test.dart` (154 L, **not in spec's expected 3**)

- `testWidgets` blocks: **6** across 2 `group` blocks.
- Group _"Locale-switch smoke"_ (2 tests):
  - _"EN → RU switches at least 3 visible strings"_ — opens drawer, asserts EN (`Language`, `Brief Queue`, `Jobs`), taps `Russian`, reopens drawer, asserts RU (`Язык`, `Очередь брифов`, `Задания`).
  - _"locale change persists to SharedPreferences"_ — taps `Russian`, asserts `SharedPreferences.getString(kLocaleStorageKey) == 'ru'`.
- Group _"Bootstrap locale resolution"_ (4 tests):
  - _"boots with persisted ru"_ — prefs seeded with `ru`, asserts `Язык`.
  - _"boots with persisted en"_ — prefs seeded with `en`, asserts `Language`.
  - _"unsupported persisted locale falls back to EN"_ — prefs seeded with `fr`, asserts `Language`.
  - _"empty prefs + default device locale boots EN in test env"_ — empty prefs, asserts `Language`.
- Router / app pattern: `_TestShell` ConsumerWidget helper (file-local, not exported) wrapping `MaterialApp.router` with a single `AppRoutes.queue` route whose builder shows `Scaffold(drawer: AppDrawer(), body: hamburger IconButton)` — effectively tests the shell + drawer, not any feature screen body.
- Language switcher entry point: drawer (`AppDrawer` embeds `LanguageSwitcher`).
- Assertion style: **hardcoded strings** + one `SharedPreferences` key read (`kLocaleStorageKey`).

### 5.3 — Pattern consistency assessment

**Mixed.** Three variance axes:

| Axis | Queue (5.2.1) | Editor (5.2.2) | Graphics (5.2.3) | locale_switch (5.2.4) |
|------|---------------|----------------|------------------|------------------------|
| `MaterialApp` variant | `.router` + ad-hoc GoRouter | `.router` + ad-hoc GoRouter | **non-router** (`home:`) | `.router` + ad-hoc GoRouter via `_TestShell` |
| Switcher mount | Drawer | `AppBar.actions` (inline) | `AppBar.actions` (inline) | Drawer (via `AppDrawer`) |
| Shared helper | none | none | none | `_TestShell` (file-local only) |
| ProviderScope overrides | `queueProvider` | `queueProvider` | `chartConfigNotifierProvider`, `chartGenerationNotifierProvider` | none |

No `pumpLocalizedRouter` or similar shared helper exists — each file duplicates the `MaterialApp(.router)` + `appBootstrapProvider` locale-plumbing scaffolding inline (18–25 lines per test). Assertion style is uniform (hardcoded literals).

### 5.4 — Aggregator smoke presence

**No.** No test file navigates across multiple feature screens (queue → editor → graphics) in a single `testWidgets` run. The closest candidate is `locale_switch_smoke_test.dart`, but it stays on the shell/drawer level and never visits `QueueScreen` / `EditorScreen` / `ChartConfigScreen` bodies.

## Section 6 — Existing scripts directory inventory

### 6.1 — Directory presence

| Path | Status |
|------|--------|
| `scripts/` (repo root) | ✅ exists — 14 `.ps1` files + `lib/` subdir |
| `frontend/scripts/` | ❌ absent |
| `frontend/tool/` | ❌ absent |
| `bin/` | ❌ absent |
| `.ai/tools/` | ✅ exists (spec-workflow helpers, already in CLAUDE.md) |
| `backend/scripts/` | ✅ exists (one Python utility + `__init__.py`) |

### 6.2 — `scripts/` contents (repo root, PowerShell-centric)

| File | Bytes | Purpose (from first-line comment or `. common.ps1` pattern) |
|------|-----:|-------------------------------------------------------------|
| `scripts/bootstrap.ps1` | 4 036 | "Facade: bootstrap everything" — param-driven dispatcher to `bootstrap-{backend,frontend,flutter}.ps1` |
| `scripts/bootstrap-backend.ps1` | 4 036 | "Bootstrap backend: Python 3.12 venv + Poetry deps + .env" (`-Lite` / `-Full` switches) |
| `scripts/bootstrap-flutter.ps1` | 1 419 | Flutter SDK bootstrap (no header comment; sources `lib/common.ps1`, uses `Get-ProjectRoot`) |
| `scripts/bootstrap-frontend.ps1` | 929 | Bootstrap `frontend-public` directory (React/Node, separate tree from Flutter `frontend/`) |
| `scripts/doctor.ps1` | 2 691 | "Full environment diagnostic — answers 'why isn't it working?' in 5 seconds" |
| `scripts/smoke-backend.ps1` | 2 344 | Backend smoke test runner |
| `scripts/start.ps1` | 3 202 | "Facade: start services" — param-driven dispatcher |
| `scripts/start-backend.ps1` | 1 236 | Start uvicorn backend using detected venv Python |
| `scripts/start-flutter.ps1` | 600 | Start Flutter web on port 8082 |
| `scripts/start-frontend.ps1` | 383 | Start `frontend-public` dev server |
| `scripts/test.ps1` | 1 033 | "Facade: run all tests" — param-driven dispatcher |
| `scripts/test-backend.ps1` | 238 | `pytest` the `backend/` dir |
| `scripts/test-flutter.ps1` | 218 | `flutter test` the `frontend/` dir |
| `scripts/test-frontend.ps1` | 218 | Run `frontend-public` tests (Node-based) |
| `scripts/lib/common.ps1` | 3 832 | "Shared functions for all Summa Vision scripts" — `Get-ProjectRoot`, `Get-BackendPython`, `Get-FlutterCmd`, `Write-Fail`, `Assert-FileExists`, etc. |

**Pattern.** All 14 top-level scripts are PowerShell (`.ps1`), each sources `lib/common.ps1` for shared helpers. No POSIX (`.sh`) or Python (`.py`) scripts exist under `scripts/`. No i18n-specific script exists (no `check_arb*`, `verify_arb*`, `arb_parity*`, `l10n_*`).

### 6.3 — Other utility script locations (out-of-tree from `scripts/`)

```
./verify_debt.py                       (repo root, Python)
./backend/entrypoint.sh                (Docker/container entrypoint)
./backend/scripts/__init__.py          (empty module marker)
./backend/scripts/export_schemas.py    (Pydantic → JSON schema exporter)
./.ai/tools/get_ac_content.sh          (spec-driven workflow helper)
./.ai/tools/resolve_scope.sh           (spec-driven workflow helper)
./.ai/tools/get_ac_content.ps1         (Windows twin of .sh)
./.ai/tools/resolve_scope.ps1          (Windows twin of .sh)
./.ai/tools/hash_ac_blocks.ps1         (AC-block hash regenerator)
```

First-line summaries:

| Path | Size | Purpose |
|------|-----:|---------|
| `verify_debt.py` | — | `"""DEBT.md structural validator."""` — validates `DEBT.md` entry format |
| `backend/entrypoint.sh` | — | `#!/bin/bash` + `set -e`; no comment (container start shim) |
| `backend/scripts/export_schemas.py` | — | `"""Export Pydantic JSON schemas for frontend drift detection."""` |
| `.ai/tools/get_ac_content.sh` | 903 B | `# Usage: get_ac_content.sh <AC_ID> [task_file]` — extract AC block from sprint spec |
| `.ai/tools/resolve_scope.sh` | 317 B | `# Usage: resolve_scope.sh <TASK_FILE>` — resolve sprint/task scope |
| `.ai/tools/hash_ac_blocks.ps1` | — | `param([string]$SprintFile = 'specs/sprints/sprint-1.md')` — AC-block hash regen |
| `.ai/tools/get_ac_content.ps1` | 1 404 B | Windows twin of `get_ac_content.sh` |
| `.ai/tools/resolve_scope.ps1` | 550 B | Windows twin of `resolve_scope.sh` |

Note: `find -maxdepth 3` also surfaces `backend/migrations/env.py`, `backend/src/__init__.py`, `backend/src/main.py`, `backend/tests/*.py` — all are application source, not utility scripts; excluded from §6.

### 6.4 — Observations relevant to future parity-script placement

- **`scripts/` is PowerShell-only**; adding a Python or POSIX sibling would be the first mixed-runtime script in that tree.
- **`backend/scripts/` is Python-only**; `export_schemas.py` is the only occupant and it already operates on cross-tree artifacts (generates JSON consumed by the frontend), demonstrating the tree is not strictly backend-scoped.
- **No `frontend/tool/` or `frontend/scripts/` exists**; creating one would be a new top-level convention for the Flutter tree.
- **`.ai/tools/` is reserved** for spec-workflow helpers (CLAUDE.md §Spec-Driven Workflow); mixing general tooling there would overload the dir's semantic.
- The recon (Part B) decision on parity-script placement has three plausible landing zones: extend `scripts/` with a `.py`/`.sh` sibling, repurpose `backend/scripts/` for any Python-based ARB checker, or introduce a new `frontend/tool/` following Dart package convention. **No recommendation given here — Part B scope.**
