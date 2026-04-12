import 'package:freezed_annotation/freezed_annotation.dart';

import 'job.dart';

part 'job_list_response.freezed.dart';
part 'job_list_response.g.dart';

@freezed
class JobListResponse with _$JobListResponse {
  const factory JobListResponse({
    required List<Job> items,
    required int total,
  }) = _JobListResponse;

  factory JobListResponse.fromJson(Map<String, dynamic> json) =>
      _$JobListResponseFromJson(json);
}
