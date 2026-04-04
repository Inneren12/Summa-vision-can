import 'package:freezed_annotation/freezed_annotation.dart';

part 'content_brief.g.dart';
part 'content_brief.freezed.dart';

/// Domain model matching the backend [PublicationResponse] schema.
///
/// Fields must exactly match `/backend/schemas/publication_response.schema.json`.
/// The schema-comparison test in [test/features/queue/domain/content_brief_schema_test.dart]
/// will fail if field names or types drift from the Python backend.
@freezed
class ContentBrief with _$ContentBrief {
  const factory ContentBrief({
    required int id,
    required String headline,
    @JsonKey(name: 'chart_type') required String chartType,
    @JsonKey(name: 'virality_score') required double viralityScore,
    required String status,
    @JsonKey(name: 'created_at') required String createdAt,
  }) = _ContentBrief;

  factory ContentBrief.fromJson(Map<String, dynamic> json) =>
      _$ContentBriefFromJson(json);
}
