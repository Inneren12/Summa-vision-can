import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'cube_diff_service.dart';

import '../data/data_preview_repository.dart';
import '../domain/data_preview_response.dart';
import '../domain/preview_filter.dart';

/// Currently selected storage key for preview.
///
/// Set when navigating to the preview screen via route query parameter
/// or after a fetch job completes.
final previewStorageKeyProvider = StateProvider<String?>((ref) => null);

/// Preview data fetched from backend.
///
/// Automatically re-fetches when [previewStorageKeyProvider] changes.
/// Returns `null` when no key is selected.
final dataPreviewProvider =
    FutureProvider.autoDispose<DataPreviewResponse?>((ref) async {
  final key = ref.watch(previewStorageKeyProvider);
  if (key == null) return null;
  final repo = ref.read(dataPreviewRepositoryProvider);
  return repo.getPreview(key);
});

/// Client-side filter state for the preview rows.
final previewFilterProvider = StateProvider<PreviewFilter>(
  (ref) => const PreviewFilter(),
);

/// Sort column name (null = no sort).
final previewSortColumnProvider = StateProvider<String?>((ref) => null);

/// Sort direction — `true` = ascending, `false` = descending.
final previewSortAscendingProvider = StateProvider<bool>((ref) => true);

/// Derived provider that applies client-side filters and sorting to preview rows.
///
/// Filtering max 100 rows in-memory is negligible, so no debounce needed.
final filteredPreviewRowsProvider =
    Provider<List<({int originalIndex, Map<String, dynamic> data})>>((ref) {
  final preview = ref.watch(dataPreviewProvider).valueOrNull;
  final filter = ref.watch(previewFilterProvider);
  if (preview == null) return const [];

  final indexedRows = [
    for (var i = 0; i < preview.data.length; i++)
      (originalIndex: i, data: preview.data[i]),
  ];

  var rows = indexedRows.where((entry) {
    final row = entry.data;

    if (filter.geoFilter != null && filter.geoFilter!.isNotEmpty) {
      final geo = row['GEO']?.toString() ?? '';
      if (geo != filter.geoFilter) return false;
    }

    if (filter.dateFromFilter != null && filter.dateFromFilter!.isNotEmpty) {
      final refDate = row['REF_DATE']?.toString() ?? '';
      if (refDate.compareTo(filter.dateFromFilter!) < 0) return false;
    }
    if (filter.dateToFilter != null && filter.dateToFilter!.isNotEmpty) {
      final refDate = row['REF_DATE']?.toString() ?? '';
      if (refDate.compareTo(filter.dateToFilter!) > 0) return false;
    }

    if (filter.searchText != null && filter.searchText!.isNotEmpty) {
      final needle = filter.searchText!.toLowerCase();
      final match = row.values.any((v) {
        if (v == null) return false;
        return v.toString().toLowerCase().contains(needle);
      });
      if (!match) return false;
    }

    return true;
  }).toList();

  final sortCol = ref.watch(previewSortColumnProvider);
  final sortAsc = ref.watch(previewSortAscendingProvider);
  if (sortCol != null) {
    rows.sort((a, b) {
      final aVal = a.data[sortCol];
      final bVal = b.data[sortCol];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortAsc ? 1 : -1;
      if (bVal == null) return sortAsc ? -1 : 1;
      final cmp = (aVal is num && bVal is num)
          ? aVal.compareTo(bVal)
          : aVal.toString().compareTo(bVal.toString());
      return sortAsc ? cmp : -cmp;
    });
  }

  return rows;
});


/// Hive box holding cube diff snapshots, keyed by product_id.
/// Initialized in main bootstrap; tests override with in-memory box.
final cubeDiffSnapshotsBoxProvider = Provider<Box>((ref) {
  throw UnimplementedError(
    'cubeDiffSnapshotsBoxProvider must be overridden via '
    'ProviderScope.overrides in main bootstrap',
  );
});

final cubeDiffServiceProvider = Provider<CubeDiffService>((ref) {
  final box = ref.watch(cubeDiffSnapshotsBoxProvider);
  return CubeDiffService(box);
});

/// Computes the diff for the current preview.
final cubeDiffProvider = FutureProvider.autoDispose<CubeDiff>((ref) async {
  final preview = await ref.watch(dataPreviewProvider.future);
  if (preview == null) return const CubeDiff.noBaseline();

  final productId = preview.productId;
  if (productId == null) return const CubeDiff.noBaseline();

  final service = ref.read(cubeDiffServiceProvider);
  final baseline = service.loadSnapshot(productId);
  final diff = service.computeDiff(baseline, preview);

  await service.saveSnapshot(productId, preview);
  return diff;
});
