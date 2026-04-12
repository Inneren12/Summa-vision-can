import 'package:freezed_annotation/freezed_annotation.dart';

part 'preview_filter.freezed.dart';

/// Client-side filter state applied to the already-loaded preview rows.
///
/// All filtering happens on the max-100 rows already in memory —
/// no additional API calls are made.
@freezed
class PreviewFilter with _$PreviewFilter {
  const factory PreviewFilter({
    String? geoFilter,
    String? dateFromFilter,
    String? dateToFilter,
    String? searchText,
  }) = _PreviewFilter;
}
