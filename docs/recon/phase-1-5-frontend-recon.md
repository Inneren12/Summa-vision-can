# Phase 1.5 Frontend Recon (PR 2/2): Visual Data Diffing

Date: 2026-04-26  
Mode: strict, plan-only with embedded verification reads  
Target branch: `claude/phase-1-5-frontend-recon`

## §A. Decisions reference (founder-locked D1–D7, 2026-04-26)

### D1. Baseline key — product_id from PreviewResponse

**Adjusted from original storage_key.** Storage key includes `{date}` segment changing per sync (Case 2 in original halt). Backend PR 1 parses `product_id` from storage_key and exposes in `PreviewResponse.product_id`. Frontend uses `product_id` as Hive key — stable across sync runs of same cube.

**Edge case:** `product_id == null` (non-StatCan storage paths, e.g., temp uploads, transformed outputs). Frontend treats this as "no diff baseline available" — graceful degradation. Banner: "No baseline" message, no Hive interaction.

### D2. Client-side diff (Path A)

Hive box stores last-seen state per product_id. No backend changes in this PR (backend already shipped in PR 1).

### D3. Cell-level comparison

Pairwise compare `current.data[rowIndex][col]` with `baseline.data[rowIndex][col]`. If values differ → highlight cell.

Edge cases:
- New row (rowIndex >= baseline.length): NOT highlighted
- Removed row: not shown (physically absent)
- Schema change: see D5

`==` semantics; no epsilon tolerance (StatCan uses fixed-precision decimals — actual numeric change SHOULD highlight).

### D4. Visual style — `accentMuted` cell background

Highlight = `SummaTheme.accentMuted` background on `DataCell`. No border, no tooltip-with-previous-value. Subtle background only.

### D5. Schema change → bail-out

If `Set(current.columnNames) != Set(baseline.columnNames)` → skip diff, banner: "Schema changed since last view — diff unavailable".
Background: still save current snapshot (overwrites baseline with new schema). Next view diffs correctly against new baseline.

### D6. Single Hive box `cube_diff_snapshots`, key = product_id

Schema (freezed):

```dart
@freezed
class CubeDiffSnapshot with _$CubeDiffSnapshot {
  const factory CubeDiffSnapshot({
    required List<String> columnNames,
    required List<Map<String, dynamic>> data,
    required int savedAtMillis,
  }) = _CubeDiffSnapshot;

  factory CubeDiffSnapshot.fromJson(Map<String, dynamic> json) =>
      _$CubeDiffSnapshotFromJson(json);
}
```

Stored as JSON string via `jsonEncode`. On read, `jsonDecode` then freezed `fromJson`. **TTL: 30 days.** Auto-purge at app boot.

### D7. ARB i18n with RU plurals (CLDR)

| Key | EN | RU |
|---|---|---|
| `dataPreviewDiffStatusLabel` | `{count, plural, =0 {No cells changed since last view} =1 {1 cell changed since last view} other {# cells changed since last view}}` | `{count, plural, =0 {Ничего не изменилось с прошлого раза} =1 {1 ячейка изменилась с прошлого раза} few {# ячейки изменились с прошлого раза} many {# ячеек изменилось с прошлого раза} other {# ячеек изменилось с прошлого раза}}` |
| `dataPreviewDiffNoBaseline` | First view — no comparison available | Первый просмотр — сравнение недоступно |
| `dataPreviewDiffSchemaChanged` | Schema changed since last view — diff unavailable | Структура данных изменилась — сравнение недоступно |
| `dataPreviewDiffNoProductId` | This data has no diff tracking | Для этих данных отслеживание изменений недоступно |

Last key handles `product_id == null` case from D1 edge case.

## §V. Verification log (read-only)

### §V.1 DataPreviewResponse Dart type current shape

`frontend/lib/features/data_preview/domain/data_preview_response.dart` currently has snake_case JSON keys for `storage_key` and `column_names`, and **does not yet include `productId`**:

```dart
@freezed
class DataPreviewResponse with _$DataPreviewResponse {
  const factory DataPreviewResponse({
    @JsonKey(name: 'storage_key') required String storageKey,
    required int rows,
    required int columns,
    @JsonKey(name: 'column_names') required List<String> columnNames,
    required List<Map<String, dynamic>> data,
  }) = _DataPreviewResponse;

  factory DataPreviewResponse.fromJson(Map<String, dynamic> json) =>
      _$DataPreviewResponseFromJson(json);
}
```

Conclusion: PR 2 must add nullable `@JsonKey(name: 'product_id') String? productId` and run codegen.

### §V.2 Hive bootstrap status

- `frontend/lib/main.dart`: no `Hive.initFlutter`, `Hive.init`, or `hive_flutter` usage found.
- `frontend/pubspec.yaml`: no `hive`/`Hive` entries found.

Conclusion: Hive is not initialized yet; PR 2 must add dependency + boot wiring.

### §V.3 SummaTheme accentMuted token confirmed

`frontend/lib/core/theme/app_theme.dart` confirms:
- `accentMuted` token exists.
- Assignment is `Color(0x26FBBF24)` (15% opacity amber).

Conclusion: D4 can use existing token directly.

### §V.4 appBootstrapProvider pattern

`frontend/lib/core/app_bootstrap/app_bootstrap_provider.dart` shows `AppBootstrapNotifier` as centralized async bootstrap owner with SharedPreferences locale resolution/persistence and `appBootstrapProvider` AsyncNotifierProvider.

Conclusion: TTL purge and/or box initialization integration should align with this bootstrap ownership pattern.

### §V.5 pumpLocalizedRouter helper path

Confirmed helper exists at:
- `frontend/test/helpers/pump_localized_router.dart`

(Also found `frontend/test/helpers/localized_pump.dart`.)

### §V.6 ARB plural pattern style sample

`rg -n 'plural,' frontend/lib/l10n/app_en.arb frontend/lib/l10n/app_ru.arb` returned no current plural messages.

Conclusion: there is no in-repo plural exemplar; PR 2 should introduce standard ICU plural syntax and include RU CLDR categories (`one`, `few`, `many`, `other`) for `dataPreviewDiffStatusLabel`.

### §V.7 DataPreviewScreen `_buildDataTable` + `_buildCell` verbatim

From `frontend/lib/features/data_preview/presentation/data_preview_screen.dart`:

```dart
  Widget _buildDataTable(
    List<String> columnNames,
    List<Map<String, dynamic>> rows,
    String? sortCol,
    bool sortAsc,
    DataPreviewResponse preview,
  ) {
    // Infer dtypes from first row for numeric detection
    final firstRow =
        preview.data.isNotEmpty ? preview.data.first : <String, dynamic>{};

    return SingleChildScrollView(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          sortColumnIndex:
              sortCol != null
                  ? columnNames.indexOf(sortCol)
                  : null,
          sortAscending: sortAsc,
          headingRowColor: WidgetStateProperty.all(_theme.bgSurface),
          dataRowColor: WidgetStateProperty.resolveWith((states) {
            return null; // handled by row striping below
          }),
          columnSpacing: 24,
          columns: columnNames.map((name) {
            final sampleVal = firstRow[name];
            final isNumeric = sampleVal is num;
            return DataColumn(
              label: Text(
                name,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _theme.textPrimary,
                ),
              ),
              numeric: isNumeric,
              onSort: (_, __) => _onSort(name),
            );
          }).toList(),
          rows: List.generate(rows.length, (index) {
            final row = rows[index];
            final isEven = index % 2 == 0;
            return DataRow(
              color: WidgetStateProperty.all(
                isEven
                    ? Colors.transparent
                    : _theme.bgSurface.withOpacity(0.5),
              ),
              cells: columnNames.map((name) {
                final value = row[name];
                final isNumeric = firstRow[name] is num;
                return DataCell(_buildCell(value, isNumeric));
              }).toList(),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildCell(dynamic value, bool isNumeric) {
    if (value == null) {
      return Text(
        '\u2014', // em dash
        style: TextStyle(color: _theme.textSecondary),
      );
    }

    final text = isNumeric ? _formatNumber(value) : value.toString();

    return Tooltip(
      message: value.toString(),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 200),
        child: Text(
          text,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(color: _theme.textPrimary, fontSize: 13),
        ),
      ),
    );
  }
```

### §V.8 Riverpod chain confirmed

`frontend/lib/features/data_preview/application/data_preview_providers.dart` confirms existing chain is unchanged:

`previewStorageKeyProvider` → `dataPreviewProvider` → `filteredPreviewRowsProvider`.

## §B. Frontend specification

### B.1 Update DataPreviewResponse to include productId

Modify `frontend/lib/features/data_preview/domain/data_preview_response.dart`:

```dart
@freezed
class DataPreviewResponse with _$DataPreviewResponse {
  const factory DataPreviewResponse({
    required String storageKey,
    required int rows,
    required int columns,
    required List<String> columnNames,
    required List<Map<String, dynamic>> data,
    @JsonKey(name: 'product_id') String? productId,
  }) = _DataPreviewResponse;

  factory DataPreviewResponse.fromJson(Map<String, dynamic> json) =>
      _$DataPreviewResponseFromJson(json);
}
```

Keep existing snake_case JSON key style (`storage_key`, `column_names`, `product_id`) consistent with current convention.

**Codegen required:** `dart run build_runner build`, then verify regenerated `.freezed.dart` and `.g.dart` files.

### B.2 Add pubspec dependency for hive_flutter

In `frontend/pubspec.yaml` add:

```yaml
dependencies:
  hive_flutter: ^1.1.0
```

Then run `flutter pub get`.

### B.3 Hive bootstrap in main.dart

Add Hive initialization before widget tree and open box:

```dart
import 'package:hive_flutter/hive_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  // ... existing bootstrap (locale, etc.) ...
  final cubeDiffBox = await Hive.openBox('cube_diff_snapshots');

  runApp(
    ProviderScope(
      overrides: [
        cubeDiffSnapshotsBoxProvider.overrideWithValue(cubeDiffBox),
      ],
      child: const SummaApp(),
    ),
  );
}
```

If `main.dart` shape differs during implementation, preserve existing order constraints; Hive init must remain pre-runApp.

### B.4 New CubeDiffSnapshot freezed model

Create `frontend/lib/features/data_preview/domain/cube_diff_snapshot.dart`:

```dart
@freezed
class CubeDiffSnapshot with _$CubeDiffSnapshot {
  const factory CubeDiffSnapshot({
    required List<String> columnNames,
    required List<Map<String, dynamic>> data,
    required int savedAtMillis,
  }) = _CubeDiffSnapshot;

  factory CubeDiffSnapshot.fromJson(Map<String, dynamic> json) =>
      _$CubeDiffSnapshotFromJson(json);
}
```

Run codegen for `.freezed.dart` + `.g.dart`.

### B.5 New CubeDiffService

Create `frontend/lib/features/data_preview/application/cube_diff_service.dart` implementing:

- `loadSnapshot(productId)` (safe decode + log on parse failure)
- `saveSnapshot(productId, current)`
- `purgeExpired()` with 30-day TTL and corrupt-entry eviction
- `computeDiff(baseline, current)` with schema check + cell-level changed set
- `CubeDiff` union (`noBaseline`, `schemaChanged`, `computed`)
- `DiffCellKey` with `==` + `hashCode` for Set semantics

(Use D3/D5/D6 semantics exactly.)

### B.6 Riverpod wiring

Extend `frontend/lib/features/data_preview/application/data_preview_providers.dart` with:

- `cubeDiffSnapshotsBoxProvider`
- `cubeDiffServiceProvider`
- `cubeDiffProvider`

Provider flow:
1. Await preview via `dataPreviewProvider.future`
2. If null → noBaseline
3. If `preview.productId == null` → noBaseline/no-tracking path
4. Load baseline → compute diff
5. Save current snapshot **after** diffing
6. Return diff

### B.7 DataPreviewScreen render integration

Modify `frontend/lib/features/data_preview/presentation/data_preview_screen.dart`:

1. Watch `cubeDiffProvider`
2. Render diff banner above table:
   - `NoBaselineCubeDiff`: first-view banner or no-product-id banner
   - `SchemaChangedCubeDiff`: schema changed banner
   - `ComputedCubeDiff`: pluralized changed-cell count
3. In each cell, apply highlight when `(rowIndex, columnName)` exists in `changedCells`
4. Highlight style: wrap cell content in `Container(color: _theme.accentMuted, ...)`

### B.8 TTL purge at boot

After opening Hive box, run purge asynchronously with logged failure path:

```dart
unawaited(CubeDiffService(box).purgeExpired().catchError((e, st) {
  developer.log('Hive TTL purge failed', error: e, stackTrace: st);
  return 0;
}));
```

### B.9 Tests

#### B.9.1 Unit — `CubeDiffService.computeDiff`

Add `frontend/test/features/data_preview/cube_diff_service_test.dart` with 10 cases:
- noBaseline returns `NoBaselineCubeDiff`
- schema added column → `SchemaChangedCubeDiff`
- schema removed column → `SchemaChangedCubeDiff`
- schema renamed column → `SchemaChangedCubeDiff`
- no changes → empty `changedCells`
- single cell change detected
- multiple cells in row detected independently
- new row not highlighted
- removed row ignored
- numeric/string type mismatch highlights (`1` vs `"1"`)

#### B.9.2 Unit — TTL purge

In same/new test file, add 5 TTL cases:
- removes entries older than 30 days
- keeps entries within 30 days
- removes corrupt entries gracefully
- returns removed count
- uses in-memory test Hive directory

#### B.9.3 Widget — diff rendering

Add `frontend/test/features/data_preview/data_preview_diff_widget_test.dart`:
- use `pumpLocalizedRouter`
- override `cubeDiffProvider` with synthetic diff states
- assert first-view/schema-changed/no-tracking banners
- assert changed count banner (e.g., 3)
- assert exact count of highlighted cells using `accentMuted`

#### B.9.4 Pipeline — HTTP → state → UI

Add `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart` with single E2E scenario:
1. mock preview #1 (`product_id = X`) → first-view banner
2. mock preview #2 (`product_id = X`) one changed cell
3. trigger refresh/re-fetch
4. assert "1 cell changed" + expected highlighted cell

### B.10 i18n keys

Add 4 keys in both `frontend/lib/l10n/app_en.arb` and `frontend/lib/l10n/app_ru.arb`:
- `dataPreviewDiffStatusLabel` (plural)
- `dataPreviewDiffNoBaseline`
- `dataPreviewDiffSchemaChanged`
- `dataPreviewDiffNoProductId`

Run `flutter gen-l10n` and verify generated `app_localizations*.dart` include all keys.

## §C. Backend specification

No backend changes in this PR. Backend PR 1 already shipped `product_id` in preview response.

## §D. Documentation updates

- If `docs/EDITOR_ARCHITECTURE.md` has Flutter persistence section, add brief note for Hive box `cube_diff_snapshots`.
- Update `DEBT.md` only if recon during implementation identifies new out-of-scope debt.

## §E. Implementation execution gates

1. Frontend bundle delta acceptable.
2. New tests pass first run.
3. `flutter analyze` clean.
4. **Codegen verification gate**:
   ```bash
   ls frontend/lib/features/data_preview/domain/cube_diff_snapshot.dart \
      frontend/lib/features/data_preview/domain/cube_diff_snapshot.freezed.dart \
      frontend/lib/features/data_preview/domain/cube_diff_snapshot.g.dart
   ```
   All three must exist.
5. **Backend untouched gate:**
   ```bash
   git diff --name-only | rg '^backend'
   ```
   must return empty.
6. **Whitelist exact match (~21 files):**
   - `frontend/lib/features/data_preview/domain/data_preview_response.dart`
   - `frontend/lib/features/data_preview/domain/data_preview_response.freezed.dart`
   - `frontend/lib/features/data_preview/domain/data_preview_response.g.dart`
   - `frontend/lib/features/data_preview/domain/cube_diff_snapshot.dart`
   - `frontend/lib/features/data_preview/domain/cube_diff_snapshot.freezed.dart`
   - `frontend/lib/features/data_preview/domain/cube_diff_snapshot.g.dart`
   - `frontend/lib/features/data_preview/application/cube_diff_service.dart`
   - `frontend/lib/features/data_preview/application/data_preview_providers.dart`
   - `frontend/lib/features/data_preview/presentation/data_preview_screen.dart`
   - `frontend/lib/core/app_bootstrap/app_bootstrap_provider.dart`
   - `frontend/lib/main.dart`
   - `frontend/lib/l10n/app_en.arb`
   - `frontend/lib/l10n/app_ru.arb`
   - `frontend/lib/l10n/generated/app_localizations.dart`
   - `frontend/lib/l10n/generated/app_localizations_en.dart`
   - `frontend/lib/l10n/generated/app_localizations_ru.dart`
   - `frontend/test/features/data_preview/cube_diff_service_test.dart`
   - `frontend/test/features/data_preview/data_preview_diff_widget_test.dart`
   - `frontend/test/features/data_preview/data_preview_diff_pipeline_test.dart`
   - `frontend/pubspec.yaml`
   - `frontend/pubspec.lock`

   Anything outside list → stop.
7. **i18n coverage gate:** `flutter gen-l10n` succeeds and all 4 keys are present in EN and RU outputs.

## §F. Open follow-ups (not scope)

- Epsilon tolerance for float comparison (v1 strict equality).
- Multi-device baseline sync (v1 is per-device only).
- Previous-value tooltip enhancement.
- New/removed row delta reporting.
- Hive box size cap observability.

## Verification command ledger

Executed during recon:

```bash
git status --short
git remote -v
git branch --show-current
git checkout main
if [ -n "$(git remote -v)" ]; then git pull --ff-only origin main 2>&1 | tail -3 || true; fi
git checkout -b claude/phase-1-5-frontend-recon
mkdir -p docs/recon
rg -n "product_id" backend/src/schemas/transform.py
test -f backend/src/services/statcan/key_parser.py && echo "PARSER_OK" || echo "PARSER_MISSING"
rg -n "extract_product_id_from_storage_key|product_id\s*=|product_id:" backend/src/api/routers/admin_data.py backend/src/api/routers -g '*.py'
sed -n '1,80p' frontend/lib/features/data_preview/domain/data_preview_response.dart
ls frontend/lib/features/data_preview/domain/
rg -n "Hive\.initFlutter|Hive\.init|hive_flutter" frontend/lib/main.dart
rg -n "hive|Hive" frontend/pubspec.yaml | head -10
rg -n "accentMuted|rawAmber400" frontend/lib/core/theme/app_theme.dart
sed -n '1,120p' frontend/lib/core/app_bootstrap/app_bootstrap_provider.dart
rg -l "pumpLocalizedRouter" frontend/test/ | head -3
rg -n 'plural,' frontend/lib/l10n/app_en.arb frontend/lib/l10n/app_ru.arb
sed -n '444,580p' frontend/lib/features/data_preview/presentation/data_preview_screen.dart
sed -n '1,120p' frontend/lib/features/data_preview/application/data_preview_providers.dart
```
