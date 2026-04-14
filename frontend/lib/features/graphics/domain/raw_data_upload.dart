import 'package:freezed_annotation/freezed_annotation.dart';

part 'raw_data_upload.freezed.dart';
part 'raw_data_upload.g.dart';

/// Column definition sent to ``POST /api/v1/admin/graphics/generate-from-data``.
///
/// ``dtype`` is one of ``"str"``, ``"int"``, ``"float"``, ``"date"`` and maps
/// 1:1 to the backend ``RawDataColumn.dtype`` literal.
@freezed
class RawDataColumn with _$RawDataColumn {
  const factory RawDataColumn({
    required String name,
    @Default('str') String dtype,
  }) = _RawDataColumn;

  factory RawDataColumn.fromJson(Map<String, dynamic> json) =>
      _$RawDataColumnFromJson(json);
}

/// Request body for generating a graphic from user-uploaded JSON/CSV.
///
/// Keys are emitted in snake_case to match the FastAPI schema:
/// ``data``, ``columns``, ``chart_type``, ``title``, ``size``, ``category``,
/// ``source_label``.
@freezed
class GenerateFromDataRequest with _$GenerateFromDataRequest {
  const factory GenerateFromDataRequest({
    required List<Map<String, dynamic>> data,
    required List<RawDataColumn> columns,
    @JsonKey(name: 'chart_type') required String chartType,
    required String title,
    @Default(<int>[1200, 900]) List<int> size,
    required String category,
    @JsonKey(name: 'source_label') @Default('custom') String sourceLabel,
  }) = _GenerateFromDataRequest;

  factory GenerateFromDataRequest.fromJson(Map<String, dynamic> json) =>
      _$GenerateFromDataRequestFromJson(json);
}
