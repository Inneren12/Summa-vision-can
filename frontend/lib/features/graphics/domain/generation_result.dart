import 'package:freezed_annotation/freezed_annotation.dart';

part 'generation_result.freezed.dart';
part 'generation_result.g.dart';

@freezed
class GenerationResult with _$GenerationResult {
  const factory GenerationResult({
    @JsonKey(name: 'publication_id') required int publicationId,
    @JsonKey(name: 'cdn_url_lowres') required String cdnUrlLowres,
    @JsonKey(name: 's3_key_highres') required String s3KeyHighres,
    required int version,
  }) = _GenerationResult;

  factory GenerationResult.fromJson(Map<String, dynamic> json) =>
      _$GenerationResultFromJson(json);
}
