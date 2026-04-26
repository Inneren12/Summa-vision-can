import 'dart:convert';
import 'dart:developer' as developer;

import 'package:hive_flutter/hive_flutter.dart';

import '../domain/cube_diff_snapshot.dart';
import '../domain/data_preview_response.dart';

/// Resolve the productId to use as a diff baseline key.
///
/// Backend `extract_product_id_from_storage_key` only matches
/// `statcan/processed/{product_id}/{date}.parquet` keys. For all
/// other storage path families (e.g., user uploads at
/// `temp/uploads/...`, transformed outputs at
/// `statcan/transformed/...`, or custom test keys), the backend
/// returns null.
///
/// To keep diff functional across all path families, we fall back
/// to parsing the storage_key path: if path is `a/b/c/d.parquet`,
/// the segment second-from-end (`c`) is treated as the productId
/// for diffing purposes.
///
/// Returns null only when the storage_key has too few segments to
/// derive any meaningful identifier.
String? resolveDiffProductId(DataPreviewResponse preview) {
  final pid = preview.productId;
  if (pid != null && pid.isNotEmpty) {
    return pid;
  }

  final parts = preview.storageKey.split('/');
  if (parts.length >= 2) {
    final candidate = parts[parts.length - 2];
    if (candidate.isNotEmpty) return candidate;
  }

  return null;
}

class CubeDiffService {
  CubeDiffService(this._box);
  final Box _box;

  static const _ttlMillis = 30 * 24 * 60 * 60 * 1000;

  CubeDiffSnapshot? loadSnapshot(String productId) {
    final raw = _box.get(productId) as String?;
    if (raw == null) return null;
    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      return CubeDiffSnapshot.fromJson(json);
    } catch (e, st) {
      developer.log(
        'Failed to decode snapshot for productId=$productId',
        error: e,
        stackTrace: st,
      );
      return null;
    }
  }

  Future<void> saveSnapshot(String productId, DataPreviewResponse current) async {
    final snapshot = CubeDiffSnapshot(
      columnNames: current.columnNames,
      data: current.data,
      savedAtMillis: DateTime.now().millisecondsSinceEpoch,
    );
    await _box.put(productId, jsonEncode(snapshot.toJson()));
  }

  Future<int> purgeExpired() async {
    final cutoff = DateTime.now().millisecondsSinceEpoch - _ttlMillis;
    final keysToRemove = <dynamic>[];

    for (final key in _box.keys) {
      try {
        final raw = _box.get(key) as String?;
        if (raw == null) {
          keysToRemove.add(key);
          continue;
        }
        final json = jsonDecode(raw) as Map<String, dynamic>;
        final snapshot = CubeDiffSnapshot.fromJson(json);
        if (snapshot.savedAtMillis < cutoff) {
          keysToRemove.add(key);
        }
      } catch (_) {
        keysToRemove.add(key);
      }
    }

    for (final key in keysToRemove) {
      await _box.delete(key);
    }
    return keysToRemove.length;
  }

  /// Compute diff between baseline and current.
  ///
  /// Out of scope (v1):
  /// - Added rows (current.data.length > baseline.data.length): not counted
  /// - Removed rows (baseline.data.length > current.data.length): not counted
  /// Only cell-level changes within the common row range are reported.
  /// Banner count reflects changedCells, not total rows that differ.
  CubeDiff computeDiff(
    CubeDiffSnapshot? baseline,
    DataPreviewResponse current,
  ) {
    if (baseline == null) return const NoBaselineCubeDiff();

    // Dart Set does not have structural equality for ==.
    final baselineColumns = baseline.columnNames.toSet();
    final currentColumns = current.columnNames.toSet();
    final schemaUnchanged =
        baselineColumns.length == currentColumns.length &&
            baselineColumns.containsAll(currentColumns);
    if (!schemaUnchanged) {
      return const SchemaChangedCubeDiff();
    }

    final changedCells = <DiffCellKey>{};
    final commonRows = baseline.data.length < current.data.length
        ? baseline.data.length
        : current.data.length;

    for (var rowIndex = 0; rowIndex < commonRows; rowIndex++) {
      final baselineRow = baseline.data[rowIndex];
      final currentRow = current.data[rowIndex];
      for (final col in current.columnNames) {
        if (baselineRow[col] != currentRow[col]) {
          changedCells.add(DiffCellKey(rowIndex, col));
        }
      }
    }

    return ComputedCubeDiff(changedCells: changedCells);
  }
}

sealed class CubeDiff {
  const CubeDiff();
  const factory CubeDiff.noBaseline() = NoBaselineCubeDiff;
  const factory CubeDiff.schemaChanged() = SchemaChangedCubeDiff;
  const factory CubeDiff.computed({required Set<DiffCellKey> changedCells}) =
      ComputedCubeDiff;
}

final class NoBaselineCubeDiff extends CubeDiff {
  const NoBaselineCubeDiff();
}

final class SchemaChangedCubeDiff extends CubeDiff {
  const SchemaChangedCubeDiff();
}

final class ComputedCubeDiff extends CubeDiff {
  const ComputedCubeDiff({required this.changedCells});

  final Set<DiffCellKey> changedCells;
}

class DiffCellKey {
  const DiffCellKey(this.rowIndex, this.columnName);

  final int rowIndex;
  final String columnName;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DiffCellKey &&
          rowIndex == other.rowIndex &&
          columnName == other.columnName;

  @override
  int get hashCode => Object.hash(rowIndex, columnName);

  @override
  String toString() => 'DiffCellKey($rowIndex, $columnName)';
}
