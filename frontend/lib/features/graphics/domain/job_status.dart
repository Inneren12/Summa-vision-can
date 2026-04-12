import 'package:freezed_annotation/freezed_annotation.dart';

part 'job_status.freezed.dart';
part 'job_status.g.dart';

@freezed
class JobStatus with _$JobStatus {
  const factory JobStatus({
    @JsonKey(name: 'job_id') required String jobId,
    required String status,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_message') String? errorMessage,
  }) = _JobStatus;

  factory JobStatus.fromJson(Map<String, dynamic> json) =>
      _$JobStatusFromJson(json);
}
