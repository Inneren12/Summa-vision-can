import 'package:freezed_annotation/freezed_annotation.dart';

part 'graphics_generate_request.freezed.dart';
part 'graphics_generate_request.g.dart';

@freezed
class GraphicsGenerateRequest with _$GraphicsGenerateRequest {
  const factory GraphicsGenerateRequest({
    @JsonKey(name: 'data_key') required String dataKey,
    @JsonKey(name: 'chart_type') required String chartType,
    required String title,
    required List<int> size,
    required String category,
    @JsonKey(name: 'source_product_id') String? sourceProductId,
  }) = _GraphicsGenerateRequest;

  factory GraphicsGenerateRequest.fromJson(Map<String, dynamic> json) =>
      _$GraphicsGenerateRequestFromJson(json);
}
