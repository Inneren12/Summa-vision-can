import 'package:freezed_annotation/freezed_annotation.dart';

part 'data_preview_response.freezed.dart';
part 'data_preview_response.g.dart';

/// Response from `GET /api/v1/admin/data/preview/{storage_key}`.
///
/// Matches the real backend contract:
/// - [storageKey]: S3 key of the Parquet file
/// - [rows]: total row count in the full dataset (integer)
/// - [columns]: number of columns (integer)
/// - [columnNames]: ordered list of column name strings
/// - [data]: actual preview row data (max 100 per R15)
@freezed
class DataPreviewResponse with _$DataPreviewResponse {
  const factory DataPreviewResponse({
    @JsonKey(name: 'storage_key') required String storageKey,
    required int rows,
    required int columns,
    @JsonKey(name: 'column_names') required List<String> columnNames,
    required List<Map<String, dynamic>> data,
  }) = _DataPreviewResponse;

  factory DataPreviewResponse.fromJson(Map<String, dynamic> json) =>
      _$DataPreviewResponseFromJson(json);
}
