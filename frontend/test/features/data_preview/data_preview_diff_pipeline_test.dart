import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/data_preview/application/cube_diff_service.dart';
import 'package:summa_vision_admin/features/data_preview/application/data_preview_providers.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/presentation/data_preview_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

void main() {
  testWidgets('first view no baseline, refresh shows 1 change and highlight',
      (tester) async {
    final tempDir = await Directory.systemTemp.createTemp('cube_diff_pipeline_');

    // Defensive: absorb any leaked Hive state from prior tests in same isolate.
    await Hive.close();
    Hive.init(tempDir.path);

    final box = await Hive.openBox(
        'cube_diff_pipeline_${DateTime.now().microsecondsSinceEpoch}');
    addTearDown(() async {
      await box.deleteFromDisk();
      await Hive.close();
      await tempDir.delete(recursive: true);
    });

    const storageKey = 'statcan/processed/13-10-0888-01/2024-12-15.parquet';
    const firstResponse = DataPreviewResponse(
      storageKey: storageKey,
      rows: 2,
      columns: 2,
      columnNames: ['A', 'B'],
      data: [
        {'A': 1, 'B': 'x'},
        {'A': 2, 'B': 'y'},
      ],
      productId: '13-10-0888-01',
    );
    const secondResponse = DataPreviewResponse(
      storageKey: storageKey,
      rows: 2,
      columns: 2,
      columnNames: ['A', 'B'],
      data: [
        {'A': 1, 'B': 'x'},
        {'A': 2, 'B': 'z'},
      ],
      productId: '13-10-0888-01',
    );

    // Stateful counter that the override reads on each rebuild.
    var fetchCount = 0;
    DataPreviewResponse currentResponse() =>
        fetchCount++ == 0 ? firstResponse : secondResponse;

    final container = ProviderContainer(
      overrides: [
        cubeDiffSnapshotsBoxProvider.overrideWithValue(box),
        previewStorageKeyProvider.overrideWith((ref) => storageKey),
        // Override at the FutureProvider level — bypasses the repository
        // and Dio entirely. This is the same override pattern that the
        // sister widget tests (data_preview_diff_widget_test.dart) use.
        dataPreviewProvider.overrideWith((ref) async {
          // ref.watch the storage key so re-fetch can be triggered by
          // invalidating dataPreviewProvider (which re-runs this body).
          ref.watch(previewStorageKeyProvider);
          return currentResponse();
        }),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: AppTheme.dark,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: MediaQuery(
            data: const MediaQueryData(size: Size(1200, 800)),
            child: DataPreviewScreen(storageKey: storageKey),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle(const Duration(seconds: 2));

    // First view — no baseline (fetchCount == 1 after first read)
    final element1 = tester.element(find.byType(DataPreviewScreen));
    final l10n1 = AppLocalizations.of(element1)!;
    expect(
      find.text(l10n1.dataPreviewDiffNoBaseline, skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
    expect(fetchCount, 1, reason: 'First fetch must have run exactly once');

    // Force refetch to get second response.
    container.invalidate(dataPreviewProvider);
    container.invalidate(cubeDiffProvider);
    await tester.pumpAndSettle(const Duration(seconds: 2));

    expect(fetchCount, 2, reason: 'Second fetch must have run after invalidate');

    final element2 = tester.element(find.byType(DataPreviewScreen));
    final l10n2 = AppLocalizations.of(element2)!;
    expect(
      find.text(l10n2.dataPreviewDiffStatusLabel(1), skipOffstage: false),
      findsAtLeastNWidgets(1),
    );

    final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
    final highlighted =
        find.byWidgetPredicate((w) => w is Container && w.color == accent);
    expect(highlighted, findsAtLeastNWidgets(1));
  });
}
