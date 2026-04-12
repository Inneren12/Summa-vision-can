import 'package:freezed_annotation/freezed_annotation.dart';

part 'job_filter.freezed.dart';

@freezed
class JobFilter with _$JobFilter {
  const factory JobFilter({
    String? jobType,
    String? status,
    @Default(50) int limit,
  }) = _JobFilter;
}
