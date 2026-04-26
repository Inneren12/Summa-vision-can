import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/data_preview/application/cube_diff_service.dart';
import 'package:summa_vision_admin/features/data_preview/application/data_preview_providers.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/presentation/data_preview_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

Widget _screen({
  required DataPreviewResponse preview,
  required CubeDiff diff,
}) {
  return ProviderScope(
    overrides: [
      previewStorageKeyProvider.overrideWith((ref) => preview.storageKey),
      dataPreviewProvider.overrideWith((ref) async => preview),
      cubeDiffProvider.overrideWith((ref) async => diff),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: MediaQuery(
        data: const MediaQueryData(size: Size(1200, 800)),
        child: DataPreviewScreen(storageKey: preview.storageKey),
      ),
    ),
  );
}

void main() {
  const preview = DataPreviewResponse(
    storageKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
    rows: 2,
    columns: 2,
    columnNames: ['A', 'B'],
    data: [
      {'A': 1, 'B': 'x'},
      {'A': 2, 'B': 'y'},
    ],
    productId: '13-10-0888-01',
  );

  testWidgets('renders no baseline banner', (tester) async {
    await tester
        .pumpWidget(_screen(preview: preview, diff: const CubeDiff.noBaseline()));
    await tester.pumpAndSettle();

    final element = tester.element(find.byType(DataPreviewScreen));
    final l10n = AppLocalizations.of(element);
    expect(l10n, isNotNull,
        reason: 'Localization harness must provide AppLocalizations');
    expect(
      find.text(l10n!.dataPreviewDiffNoBaseline, skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
  });

  testWidgets('renders schema changed banner', (tester) async {
    await tester.pumpWidget(
        _screen(preview: preview, diff: const CubeDiff.schemaChanged()));
    await tester.pumpAndSettle();

    final element = tester.element(find.byType(DataPreviewScreen));
    final l10n = AppLocalizations.of(element)!;
    expect(
      find.text(l10n.dataPreviewDiffSchemaChanged, skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
  });

  testWidgets('renders changed count and highlights changed cell',
      (tester) async {
    await tester.pumpWidget(
      _screen(
        preview: preview,
        diff: CubeDiff.computed(
          changedCells: <DiffCellKey>{const DiffCellKey(1, 'B')},
        ),
      ),
    );
    await tester.pumpAndSettle();

    final element = tester.element(find.byType(DataPreviewScreen));
    final l10n = AppLocalizations.of(element)!;
    expect(
      find.text(l10n.dataPreviewDiffStatusLabel(1), skipOffstage: false),
      findsAtLeastNWidgets(1),
    );

    final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
    final highlighted = find.byWidgetPredicate(
      (w) => w is Container && w.color == accent,
      description: 'highlight container',
    );
    expect(highlighted, findsAtLeastNWidgets(1));
  });

  testWidgets('renders no product id banner', (tester) async {
    const noProductPreview = DataPreviewResponse(
      storageKey: 'just-one-name',
      rows: 1,
      columns: 1,
      columnNames: ['A'],
      data: [
        {'A': 1}
      ],
      productId: null,
    );
    await tester.pumpWidget(
      _screen(preview: noProductPreview, diff: const CubeDiff.noBaseline()),
    );
    await tester.pumpAndSettle();

    final element = tester.element(find.byType(DataPreviewScreen));
    final l10n = AppLocalizations.of(element)!;
    expect(
      find.text(l10n.dataPreviewDiffNoProductId, skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
  });

  testWidgets(
    'shows no-baseline banner (not no-product-id) when storageKey fallback resolves id',
    (tester) async {
      // Regression guard: round 3 fix.
      // Scenario: productId is null (backend returned null for non-StatCan
      // path), but storageKey contains a parseable second-from-end segment
      // ('abc-123'). resolveDiffProductId returns 'abc-123', so diff
      // tracking IS available — banner must say "first view", not
      // "no diff tracking".
      const preview = DataPreviewResponse(
        storageKey: 'temp/uploads/abc-123/file.parquet',
        rows: 1,
        columns: 1,
        columnNames: ['A'],
        data: [
          {'A': 1}
        ],
        productId: null,
      );

      await tester.pumpWidget(
        _screen(preview: preview, diff: const CubeDiff.noBaseline()),
      );
      await tester.pumpAndSettle();

      final element = tester.element(find.byType(DataPreviewScreen));
      final l10n = AppLocalizations.of(element)!;

      expect(
        find.text(l10n.dataPreviewDiffNoBaseline),
        findsOneWidget,
        reason:
            'storageKey fallback resolves id → diff tracking IS available',
      );
      expect(
        find.text(l10n.dataPreviewDiffNoProductId),
        findsNothing,
        reason: 'Should NOT show no-product-id when fallback succeeds',
      );
    },
  );

  testWidgets(
    'shows no-product-id banner when storageKey has insufficient segments',
    (tester) async {
      // Companion test: when fallback ALSO can't resolve, banner SHOULD
      // say "no diff tracking".
      const preview = DataPreviewResponse(
        storageKey: 'singleword',
        rows: 1,
        columns: 1,
        columnNames: ['A'],
        data: [
          {'A': 1}
        ],
        productId: null,
      );

      await tester.pumpWidget(
        _screen(preview: preview, diff: const CubeDiff.noBaseline()),
      );
      await tester.pumpAndSettle();

      final element = tester.element(find.byType(DataPreviewScreen));
      final l10n = AppLocalizations.of(element)!;

      expect(find.text(l10n.dataPreviewDiffNoProductId), findsOneWidget);
      expect(find.text(l10n.dataPreviewDiffNoBaseline), findsNothing);
    },
  );

  testWidgets(
    'highlight stays on correct business row after sort (regression for index mismatch)',
    (tester) async {
      const sortablePreview = DataPreviewResponse(
        storageKey: 'k',
        rows: 3,
        columns: 1,
        columnNames: ['VALUE'],
        data: [
          {'VALUE': 100},
          {'VALUE': 999},
          {'VALUE': 300},
        ],
        productId: 'X',
      );

      await tester.pumpWidget(
        _screen(
          preview: sortablePreview,
          diff: CubeDiff.computed(
            changedCells: <DiffCellKey>{const DiffCellKey(1, 'VALUE')},
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('VALUE'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('VALUE'));
      await tester.pumpAndSettle();

      final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
      final highlight999 = find.ancestor(
        of: find.text('999'),
        matching: find.byWidgetPredicate((w) => w is Container && w.color == accent),
      );
      final highlight300 = find.ancestor(
        of: find.text('300'),
        matching: find.byWidgetPredicate((w) => w is Container && w.color == accent),
      );
      final highlight100 = find.ancestor(
        of: find.text('100'),
        matching: find.byWidgetPredicate((w) => w is Container && w.color == accent),
      );

      expect(highlight999, findsAtLeastNWidgets(1));
      expect(highlight300, findsNothing);
      expect(highlight100, findsNothing);
    },
  );
}
