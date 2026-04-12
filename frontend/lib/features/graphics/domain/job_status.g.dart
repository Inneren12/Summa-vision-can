// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'job_status.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$JobStatusImpl _$$JobStatusImplFromJson(Map<String, dynamic> json) =>
    _$JobStatusImpl(
      id: json['id'] as String,
      status: json['status'] as String,
      resultJson: json['result_json'] as String?,
      errorMessage: json['error_message'] as String?,
    );

Map<String, dynamic> _$$JobStatusImplToJson(_$JobStatusImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'status': instance.status,
      'result_json': instance.resultJson,
      'error_message': instance.errorMessage,
    };
