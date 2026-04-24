import 'package:freezed_annotation/freezed_annotation.dart';

part 'task_status.freezed.dart';
part 'task_status.g.dart';

enum TaskStatusValue { pending, running, completed, failed }

@freezed
class TaskStatus with _$TaskStatus {
  const factory TaskStatus({
    @JsonKey(name: 'task_id') required String taskId,
    required String status,
    @JsonKey(name: 'result_url') String? resultUrl,
    @JsonKey(name: 'error_code') String? errorCode,
    String? detail,
  }) = _TaskStatus;

  factory TaskStatus.fromJson(Map<String, dynamic> json) =>
      _$TaskStatusFromJson(json);
}

extension TaskStatusExt on TaskStatus {
  bool get isCompleted => status.toUpperCase() == 'COMPLETED';
  bool get isFailed    => status.toUpperCase() == 'FAILED';
  bool get isPending   => status.toUpperCase() == 'PENDING';
  bool get isRunning   => status.toUpperCase() == 'RUNNING';
}
