import 'package:freezed_annotation/freezed_annotation.dart';

part 'job_status.freezed.dart';
part 'job_status.g.dart';

@freezed
class JobStatus with _$JobStatus {
  const factory JobStatus({
    required String id,
    required String status,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_message') String? errorMessage,
  }) = _JobStatus;

  factory JobStatus.fromJson(Map<String, dynamic> json) =>
      _$JobStatusFromJson(json);
}

extension JobStatusExt on JobStatus {
  bool get isSuccess => status.toLowerCase() == 'success';
  bool get isFailed  => status.toLowerCase() == 'failed';
  bool get isRunning => status.toLowerCase() == 'running';
  bool get isQueued  => status.toLowerCase() == 'queued';
}
