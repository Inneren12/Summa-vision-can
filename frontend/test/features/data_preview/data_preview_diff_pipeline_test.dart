import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
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
    await tester.pumpAndSettle();

    expect(find.textContaining('First view', skipOffstage: false), findsAtLeastNWidgets(1));

    container.invalidate(dataPreviewProvider);
    container.invalidate(cubeDiffProvider);
    await tester.pumpAndSettle();

    expect(find.textContaining('1 cell changed', skipOffstage: false), findsAtLeastNWidgets(1));
    final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
    final highlighted = find.byWidgetPredicate((w) => w is Container && w.color == accent);
    expect(highlighted, findsAtLeastNWidgets(1));
  });
}
