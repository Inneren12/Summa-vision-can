// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'task_status.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$TaskStatusImpl _$$TaskStatusImplFromJson(Map<String, dynamic> json) =>
    _$TaskStatusImpl(
      taskId: json['task_id'] as String,
      status: json['status'] as String,
      resultUrl: json['result_url'] as String?,
      detail: json['detail'] as String?,
    );

Map<String, dynamic> _$$TaskStatusImplToJson(_$TaskStatusImpl instance) =>
    <String, dynamic>{
      'task_id': instance.taskId,
      'status': instance.status,
      'result_url': instance.resultUrl,
      'detail': instance.detail,
    };
