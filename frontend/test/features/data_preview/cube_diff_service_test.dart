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
      expect(CubeDiffService(box).computeDiff(baseline, current), isA<SchemaChangedCubeDiff>());
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
      final diff = CubeDiffService(box).computeDiff(baseline, current) as ComputedCubeDiff;
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
        savedAtMillis: DateTime.now().subtract(const Duration(days: 31)).millisecondsSinceEpoch,
      );
      await box.put('old', jsonEncode(old.toJson()));
      await box.put('corrupt', 'not valid json {{{');
      final removed = await svc.purgeExpired();
      expect(removed, 2);
      expect(box.get('old'), isNull);
      expect(box.get('corrupt'), isNull);
    });
  });
}
