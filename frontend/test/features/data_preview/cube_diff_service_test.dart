import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:summa_vision_admin/features/data_preview/application/cube_diff_service.dart';
import 'package:summa_vision_admin/features/data_preview/domain/cube_diff_snapshot.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';

DataPreviewResponse _resp({
  String? productId = 'X',
  List<String> cols = const ['a', 'b'],
  List<Map<String, dynamic>> rows = const [
    {'a': 1, 'b': 'x'},
  ],
}) {
  return DataPreviewResponse(
    storageKey: 'k',
    rows: rows.length,
    columns: cols.length,
    columnNames: cols,
    data: rows,
    productId: productId,
  );
}

void main() {
  late Directory tempDir;
  late Box box;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('cube_diff_test_');
    Hive.init(tempDir.path);
    box = await Hive.openBox(
      'cube_diff_snapshots_test_${DateTime.now().microsecondsSinceEpoch}',
    );
  });

  tearDown(() async {
    await box.deleteFromDisk();
    // Close Hive so its global state (paths, locks, open-box registry) does
    // not leak into other test files in the same isolate. Without this,
    // alphabetically-later Hive-using tests (e.g. data_preview_diff_pipeline)
    // can hang in Hive.openBox awaiting a never-released internal lock.
    await Hive.close();
    await tempDir.delete(recursive: true);
  });

  group('computeDiff', () {
    test('null baseline returns NoBaselineCubeDiff', () {
      final svc = CubeDiffService(box);
      expect(svc.computeDiff(null, _resp()), isA<NoBaselineCubeDiff>());
    });

    test('same column set returns ComputedCubeDiff (regression for Set != bug)', () {
      final baseline = CubeDiffSnapshot(
        columnNames: ['a', 'b'],
        data: const [
          {'a': 1, 'b': 2}
        ],
        savedAtMillis: 0,
      );
      final current = _resp(cols: ['a', 'b'], rows: const [
        {'a': 1, 'b': 99}
      ]);
      final diff = CubeDiffService(box).computeDiff(baseline, current);
      expect(
        diff,
        isA<ComputedCubeDiff>(),
        reason: 'Same column set should NOT trigger schema-changed bail-out',
      );
      expect((diff as ComputedCubeDiff).changedCells.length, 1);
    });

    test('column reorder still treated as same schema', () {
      final baseline = CubeDiffSnapshot(
        columnNames: ['a', 'b'],
        data: const [
          {'a': 1, 'b': 2}
        ],
        savedAtMillis: 0,
      );
      final current = _resp(cols: ['b', 'a'], rows: const [
        {'a': 1, 'b': 2}
      ]);
      final diff = CubeDiffService(box).computeDiff(baseline, current);
      expect(
        diff,
        isNot(isA<SchemaChangedCubeDiff>()),
        reason: 'Column reorder is not a schema change',
      );
    });

    test('schema change returns SchemaChangedCubeDiff', () {
      final baseline = CubeDiffSnapshot(
        columnNames: ['a'],
        data: const [
          {'a': 1}
        ],
        savedAtMillis: 0,
      );
      final current = _resp(cols: ['a', 'b'], rows: const [
        {'a': 1, 'b': 2}
      ]);
      expect(CubeDiffService(box).computeDiff(baseline, current),
          isA<SchemaChangedCubeDiff>());
    });

    test('single cell change detected', () {
      final baseline = CubeDiffSnapshot(
        columnNames: ['a', 'b'],
        data: const [
          {'a': 1, 'b': 2}
        ],
        savedAtMillis: 0,
      );
      final current = _resp(cols: ['a', 'b'], rows: const [
        {'a': 1, 'b': 99}
      ]);
      final diff =
          CubeDiffService(box).computeDiff(baseline, current) as ComputedCubeDiff;
      expect(diff.changedCells, {const DiffCellKey(0, 'b')});
    });
  });

  group('purgeExpired', () {
    test('removes stale and corrupt entries', () async {
      final svc = CubeDiffService(box);
      final old = CubeDiffSnapshot(
        columnNames: ['a'],
        data: const [
          {'a': 1}
        ],
        savedAtMillis: DateTime.now()
            .subtract(const Duration(days: 31))
            .millisecondsSinceEpoch,
      );
      await box.put('old', jsonEncode(old.toJson()));
      await box.put('corrupt', 'not valid json {{{');
      final removed = await svc.purgeExpired();
      expect(removed, 2);
      expect(box.get('old'), isNull);
      expect(box.get('corrupt'), isNull);
    });
  });

  group('resolveDiffProductId', () {
    test('uses preview.productId when present and non-empty', () {
      final preview = DataPreviewResponse(
        storageKey: 'statcan/processed/18-10-0004-01/2026-04-26.parquet',
        rows: 1,
        columns: 1,
        columnNames: const ['v'],
        data: const [
          {'v': 1}
        ],
        productId: '18-10-0004-01',
      );
      expect(resolveDiffProductId(preview), '18-10-0004-01');
    });

    test('falls back to storageKey parse when productId is null', () {
      final preview = DataPreviewResponse(
        storageKey: 'temp/uploads/abc-123/file.parquet',
        rows: 1,
        columns: 1,
        columnNames: const ['v'],
        data: const [
          {'v': 1}
        ],
        productId: null,
      );
      expect(resolveDiffProductId(preview), 'abc-123');
    });

    test('falls back when productId is empty string', () {
      final preview = DataPreviewResponse(
        storageKey: 'a/b/c/d.parquet',
        rows: 1,
        columns: 1,
        columnNames: const ['v'],
        data: const [
          {'v': 1}
        ],
        productId: '',
      );
      expect(resolveDiffProductId(preview), 'c');
    });

    test('returns null when storageKey has insufficient segments', () {
      final preview = DataPreviewResponse(
        storageKey: 'just-one-name',
        rows: 1,
        columns: 1,
        columnNames: const ['v'],
        data: const [
          {'v': 1}
        ],
        productId: null,
      );
      expect(resolveDiffProductId(preview), null);
    });

    test('returns null when fallback candidate would be empty', () {
      final preview = DataPreviewResponse(
        storageKey: '/file.parquet',
        rows: 1,
        columns: 1,
        columnNames: const ['v'],
        data: const [
          {'v': 1}
        ],
        productId: null,
      );
      expect(resolveDiffProductId(preview), null);
    });
  });
}
