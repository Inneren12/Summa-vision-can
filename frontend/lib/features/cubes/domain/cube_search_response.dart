import 'package:freezed_annotation/freezed_annotation.dart';

import 'cube_catalog_entry.dart';

part 'cube_search_response.g.dart';
part 'cube_search_response.freezed.dart';

/// Wraps paginated cube search results from the backend.
@freezed
class CubeSearchResponse with _$CubeSearchResponse {
  const factory CubeSearchResponse({
    required List<CubeCatalogEntry> items,
    required int total,
  }) = _CubeSearchResponse;

  factory CubeSearchResponse.fromJson(Map<String, dynamic> json) =>
      _$CubeSearchResponseFromJson(json);
}
