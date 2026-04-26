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

class _SequencedRepo extends DataPreviewRepository {
  _SequencedRepo(this._responses) : super(Dio());

  final List<DataPreviewResponse> _responses;
  int _idx = 0;

  @override
  Future<DataPreviewResponse> getPreview(String storageKey, {int limit = 100}) async {
    final value = _responses[_idx < _responses.length ? _idx : _responses.length - 1];
    _idx++;
    return value;
  }
}

void main() {
  testWidgets('first view no baseline, refresh shows 1 change and highlight', (tester) async {
    final tempDir = await Directory.systemTemp.createTemp('cube_diff_pipeline_');
    Hive.init(tempDir.path);
    final box = await Hive.openBox('cube_diff_pipeline_${DateTime.now().microsecondsSinceEpoch}');
    addTearDown(() async {
      await box.deleteFromDisk();
      await tempDir.delete(recursive: true);
    });

    final storageKey = 'statcan/processed/13-10-0888-01/2024-12-15.parquet';
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

    late ProviderContainer container;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          dataPreviewRepositoryProvider.overrideWithValue(repo),
          cubeDiffSnapshotsBoxProvider.overrideWithValue(box),
        ],
        child: Consumer(builder: (context, ref, _) {
          container = ProviderScope.containerOf(context);
          return MaterialApp(
            theme: AppTheme.dark,
            home: MediaQuery(
              data: const MediaQueryData(size: Size(1200, 800)),
              child: DataPreviewScreen(storageKey: storageKey),
            ),
          );
        }),
      ),
    );

    // Pre-warm a permanent listener so autoDispose never collects either provider
    // during the invalidate→re-fetch transition. Without this, a brief gap with
    // zero subscribers (between invalidate and the screen's rebuild) would dispose
    // the provider, and the second fetch would never fire — leaving pumpAndSettle
    // waiting on a future that never resolves.
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

    await tester.pumpAndSettle(const Duration(seconds: 2));

    expect(find.textContaining('First view', skipOffstage: false), findsAtLeastNWidgets(1));

    // Force re-fetch with a deterministic await chain. Awaiting `read(...future)`
    // explicitly drives the new fetch through `_SequencedRepo.getPreview` (advancing
    // _idx) and the cubeDiffProvider body (Hive load+diff+save), independent of any
    // widget-tree subscription timing. pumpAndSettle then only has UI rebuild work.
    container.invalidate(dataPreviewProvider);
    await container.read(dataPreviewProvider.future);
    container.invalidate(cubeDiffProvider);
    await container.read(cubeDiffProvider.future);
    await tester.pumpAndSettle(const Duration(seconds: 2));

    expect(find.textContaining('1 cell changed', skipOffstage: false), findsAtLeastNWidgets(1));
    final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
    final highlighted = find.byWidgetPredicate((w) => w is Container && w.color == accent);
    expect(highlighted, findsAtLeastNWidgets(1));
  });
}
