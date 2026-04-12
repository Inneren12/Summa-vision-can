import 'package:freezed_annotation/freezed_annotation.dart';

part 'job.freezed.dart';
part 'job.g.dart';

@freezed
class Job with _$Job {
  const factory Job({
    required String id,
    @JsonKey(name: 'job_type') required String jobType,
    required String status,
    @JsonKey(name: 'payload_json') String? payloadJson,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_code') String? errorCode,
    @JsonKey(name: 'error_message') String? errorMessage,
    @JsonKey(name: 'attempt_count') required int attemptCount,
    @JsonKey(name: 'max_attempts') required int maxAttempts,
    @JsonKey(name: 'created_at') required DateTime createdAt,
    @JsonKey(name: 'started_at') DateTime? startedAt,
    @JsonKey(name: 'finished_at') DateTime? finishedAt,
    @JsonKey(name: 'created_by') String? createdBy,
    @JsonKey(name: 'dedupe_key') String? dedupeKey,
  }) = _Job;

  factory Job.fromJson(Map<String, dynamic> json) => _$JobFromJson(json);
}

extension JobHelpers on Job {
  bool get isRetryable =>
      status == 'failed' && attemptCount < maxAttempts;

  bool get isStale =>
      status == 'running' &&
      startedAt != null &&
      DateTime.now().difference(startedAt!).inMinutes > 10;

  Duration? get duration =>
      (startedAt != null && finishedAt != null)
          ? finishedAt!.difference(startedAt!)
          : null;

  String get jobTypeDisplay {
    switch (jobType) {
      case 'catalog_sync':
        return 'Catalog Sync';
      case 'cube_fetch':
        return 'Data Fetch';
      case 'graphics_generate':
        return 'Chart Generation';
      default:
        return jobType;
    }
  }

  String get statusDisplay =>
      status[0].toUpperCase() + status.substring(1);
}
