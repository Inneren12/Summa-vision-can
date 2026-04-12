// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'job.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$JobImpl _$$JobImplFromJson(Map<String, dynamic> json) => _$JobImpl(
      id: json['id'] as String,
      jobType: json['job_type'] as String,
      status: json['status'] as String,
      payloadJson: json['payload_json'] as String?,
      resultJson: json['result_json'] as String?,
      errorCode: json['error_code'] as String?,
      errorMessage: json['error_message'] as String?,
      attemptCount: (json['attempt_count'] as num).toInt(),
      maxAttempts: (json['max_attempts'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      startedAt: json['started_at'] == null
          ? null
          : DateTime.parse(json['started_at'] as String),
      finishedAt: json['finished_at'] == null
          ? null
          : DateTime.parse(json['finished_at'] as String),
      createdBy: json['created_by'] as String?,
      dedupeKey: json['dedupe_key'] as String?,
    );

Map<String, dynamic> _$$JobImplToJson(_$JobImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'job_type': instance.jobType,
      'status': instance.status,
      'payload_json': instance.payloadJson,
      'result_json': instance.resultJson,
      'error_code': instance.errorCode,
      'error_message': instance.errorMessage,
      'attempt_count': instance.attemptCount,
      'max_attempts': instance.maxAttempts,
      'created_at': instance.createdAt.toIso8601String(),
      'started_at': instance.startedAt?.toIso8601String(),
      'finished_at': instance.finishedAt?.toIso8601String(),
      'created_by': instance.createdBy,
      'dedupe_key': instance.dedupeKey,
    };
