import 'package:freezed_annotation/freezed_annotation.dart';

part 'cube_catalog_entry.g.dart';
part 'cube_catalog_entry.freezed.dart';

/// Domain model for a StatCan cube catalog entry.
///
/// Maps snake_case API fields to camelCase Dart fields via [JsonKey].
@freezed
class CubeCatalogEntry with _$CubeCatalogEntry {
  const factory CubeCatalogEntry({
    @JsonKey(name: 'product_id') required String productId,
    @JsonKey(name: 'title_en') required String titleEn,
    @JsonKey(name: 'title_fr') String? titleFr,
    @JsonKey(name: 'subject_code') required String subjectCode,
    @JsonKey(name: 'subject_en') required String subjectEn,
    @JsonKey(name: 'survey_en') String? surveyEn,
    required String frequency,
    @JsonKey(name: 'start_date') String? startDate,
    @JsonKey(name: 'end_date') String? endDate,
    @Default(false) @JsonKey(name: 'archive_status') bool archiveStatus,
  }) = _CubeCatalogEntry;

  factory CubeCatalogEntry.fromJson(Map<String, dynamic> json) =>
      _$CubeCatalogEntryFromJson(json);
}
