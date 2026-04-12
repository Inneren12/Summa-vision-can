import 'package:flutter_riverpod/flutter_riverpod.dart';

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
    Provider<List<Map<String, dynamic>>>((ref) {
  final preview = ref.watch(dataPreviewProvider).valueOrNull;
  final filter = ref.watch(previewFilterProvider);
  if (preview == null) return [];

  var rows = preview.data.where((row) {
    // GEO filter
    if (filter.geoFilter != null && filter.geoFilter!.isNotEmpty) {
      final geo = row['GEO']?.toString() ?? '';
      if (geo != filter.geoFilter) return false;
    }

    // Date range filters (string comparison works for ISO/YYYY-MM format)
    if (filter.dateFromFilter != null && filter.dateFromFilter!.isNotEmpty) {
      final refDate = row['REF_DATE']?.toString() ?? '';
      if (refDate.compareTo(filter.dateFromFilter!) < 0) return false;
    }
    if (filter.dateToFilter != null && filter.dateToFilter!.isNotEmpty) {
      final refDate = row['REF_DATE']?.toString() ?? '';
      if (refDate.compareTo(filter.dateToFilter!) > 0) return false;
    }

    // Free-text search across all columns
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

  // Client-side sorting
  final sortCol = ref.watch(previewSortColumnProvider);
  final sortAsc = ref.watch(previewSortAscendingProvider);
  if (sortCol != null) {
    rows.sort((a, b) {
      final aVal = a[sortCol];
      final bVal = b[sortCol];
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
