import 'package:freezed_annotation/freezed_annotation.dart';

part 'data_preview_response.freezed.dart';
part 'data_preview_response.g.dart';

/// Schema descriptor for a single column in the preview dataset.
@freezed
class ColumnSchema with _$ColumnSchema {
  const factory ColumnSchema({
    required String name,
    required String dtype,
  }) = _ColumnSchema;

  factory ColumnSchema.fromJson(Map<String, dynamic> json) =>
      _$ColumnSchemaFromJson(json);
}

/// Response from `GET /api/v1/admin/data/preview/{storage_key}`.
///
/// Contains column metadata, up to [returnedRows] data rows (max 100 per R15),
/// and the [totalRows] count for the full dataset.
@freezed
class DataPreviewResponse with _$DataPreviewResponse {
  const factory DataPreviewResponse({
    required List<ColumnSchema> columns,
    required List<Map<String, dynamic>> rows,
    @JsonKey(name: 'total_rows') required int totalRows,
    @JsonKey(name: 'returned_rows') required int returnedRows,
  }) = _DataPreviewResponse;

  factory DataPreviewResponse.fromJson(Map<String, dynamic> json) =>
      _$DataPreviewResponseFromJson(json);
}
