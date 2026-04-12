// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'generation_result.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$GenerationResultImpl _$$GenerationResultImplFromJson(
        Map<String, dynamic> json) =>
    _$GenerationResultImpl(
      publicationId: (json['publication_id'] as num).toInt(),
      cdnUrlLowres: json['cdn_url_lowres'] as String,
      s3KeyHighres: json['s3_key_highres'] as String,
      version: (json['version'] as num).toInt(),
    );

Map<String, dynamic> _$$GenerationResultImplToJson(
        _$GenerationResultImpl instance) =>
    <String, dynamic>{
      'publication_id': instance.publicationId,
      'cdn_url_lowres': instance.cdnUrlLowres,
      's3_key_highres': instance.s3KeyHighres,
      'version': instance.version,
    };
