import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/data_preview/application/cube_diff_service.dart';
import 'package:summa_vision_admin/features/data_preview/application/data_preview_providers.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/presentation/data_preview_screen.dart';

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
    await tester.pumpWidget(_screen(preview: preview, diff: const CubeDiff.noBaseline()));
    await tester.pumpAndSettle();

    expect(
      find.text('First view — no comparison available', skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
  });

  testWidgets('renders schema changed banner', (tester) async {
    await tester.pumpWidget(_screen(preview: preview, diff: const CubeDiff.schemaChanged()));
    await tester.pumpAndSettle();

    expect(find.textContaining('Schema changed', skipOffstage: false), findsAtLeastNWidgets(1));
  });

  testWidgets('renders changed count and highlights changed cell', (tester) async {
    await tester.pumpWidget(
      _screen(
        preview: preview,
        diff: const CubeDiff.computed(changedCells: {DiffCellKey(1, 'B')}),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('1 cell changed', skipOffstage: false), findsAtLeastNWidgets(1));

    final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
    final highlighted = find.byWidgetPredicate(
      (w) => w is Container && w.color == accent,
      description: 'highlight container',
    );
    expect(highlighted, findsAtLeastNWidgets(1));
  });

  testWidgets('renders no product id banner', (tester) async {
    const noProductPreview = DataPreviewResponse(
      storageKey: 'custom/path/file.parquet',
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

    expect(find.textContaining('no diff tracking', skipOffstage: false), findsAtLeastNWidgets(1));
  });
}
