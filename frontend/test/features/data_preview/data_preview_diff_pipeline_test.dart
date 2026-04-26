import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/data_preview/application/cube_diff_service.dart';
import 'package:summa_vision_admin/features/data_preview/application/data_preview_providers.dart';
import 'package:summa_vision_admin/features/data_preview/data/data_preview_repository.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/presentation/data_preview_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

class _SequencedRepo extends DataPreviewRepository {
  _SequencedRepo(this._responses) : super(Dio());

  final List<DataPreviewResponse> _responses;
  int _idx = 0;

  @override
  Future<DataPreviewResponse> getPreview(String storageKey,
      {int limit = 100}) async {
    final value =
        _responses[_idx < _responses.length ? _idx : _responses.length - 1];
    _idx++;
    return value;
  }
}

void main() {
  testWidgets('first view no baseline, refresh shows 1 change and highlight',
      (tester) async {
    final tempDir = await Directory.systemTemp.createTemp('cube_diff_pipeline_');

    // Defensive: if a prior test in the same isolate left Hive open at a
    // different path, close it before re-initializing. Hive.close() is a
    // no-op when nothing is open. Without this guard, Hive.openBox below
    // can deadlock on internal locks held by the leaked state, hanging
    // pumpAndSettle for its full timeout.
    await Hive.close();

    Hive.init(tempDir.path);
    final box = await Hive.openBox(
        'cube_diff_pipeline_${DateTime.now().microsecondsSinceEpoch}');
    addTearDown(() async {
      await box.deleteFromDisk();
      // Symmetric with setUp: close Hive so subsequent tests in the same
      // isolate get a clean global state.
      await Hive.close();
      await tempDir.delete(recursive: true);
    });

    const storageKey = 'statcan/processed/13-10-0888-01/2024-12-15.parquet';
    final repo = _SequencedRepo([
      const DataPreviewResponse(
        storageKey: storageKey,
        rows: 2,
        columns: 2,
        columnNames: ['A', 'B'],
        data: [
          {'A': 1, 'B': 'x'},
          {'A': 2, 'B': 'y'},
        ],
        productId: '13-10-0888-01',
      ),
      const DataPreviewResponse(
        storageKey: storageKey,
        rows: 2,
        columns: 2,
        columnNames: ['A', 'B'],
        data: [
          {'A': 1, 'B': 'x'},
          {'A': 2, 'B': 'z'},
        ],
        productId: '13-10-0888-01',
      ),
    ]);

    // Use an explicit ProviderContainer so we can drive provider rebuilds
    // deterministically with `await container.read(provider.future)` instead
    // of relying on widget-tree subscription timing during `pumpAndSettle`.
    final container = ProviderContainer(
      overrides: [
        dataPreviewRepositoryProvider.overrideWithValue(repo),
        cubeDiffSnapshotsBoxProvider.overrideWithValue(box),
      ],
    );
    addTearDown(container.dispose);

    // Set the storage key up front so dataPreviewProvider can fire immediately,
    // bypassing the Future.microtask race in DataPreviewScreen.initState.
    container.read(previewStorageKeyProvider.notifier).state = storageKey;

    // Pre-warm permanent listeners on both providers so autoDispose never
    // collects them between invalidate() and the next frame. Without these,
    // a brief gap with zero listeners disposes the provider state and the
    // subsequent rebuild may never get scheduled, causing pumpAndSettle to
    // hang until its 10-minute timeout.
    final previewSub = container.listen<AsyncValue<DataPreviewResponse?>>(
      dataPreviewProvider,
      (_, __) {},
      fireImmediately: true,
    );
    addTearDown(previewSub.close);
    final diffSub = container.listen<AsyncValue<CubeDiff>>(
      cubeDiffProvider,
      (_, __) {},
      fireImmediately: true,
    );
    addTearDown(diffSub.close);

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

    // Drive the first fetch deterministically.
    await container.read(dataPreviewProvider.future);
    await container.read(cubeDiffProvider.future);
    await tester.pumpAndSettle(const Duration(seconds: 2));

    final element1 = tester.element(find.byType(DataPreviewScreen));
    final l10n1 = AppLocalizations.of(element1)!;
    expect(
      find.text(l10n1.dataPreviewDiffNoBaseline, skipOffstage: false),
      findsAtLeastNWidgets(1),
    );

    // Force re-fetch with explicit await chain. Awaiting the new future after
    // each invalidate eliminates dependence on widget-tree timing and
    // guarantees _SequencedRepo._idx advances before assertions run.
    container.invalidate(dataPreviewProvider);
    await container.read(dataPreviewProvider.future);
    container.invalidate(cubeDiffProvider);
    await container.read(cubeDiffProvider.future);
    await tester.pumpAndSettle(const Duration(seconds: 2));

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
