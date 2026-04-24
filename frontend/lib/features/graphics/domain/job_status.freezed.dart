// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'job_status.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

JobStatus _$JobStatusFromJson(Map<String, dynamic> json) {
  return _JobStatus.fromJson(json);
}

/// @nodoc
mixin _$JobStatus {
  @JsonKey(name: 'job_id')
  String get jobId => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'result_json')
  String? get resultJson => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_code')
  String? get errorCode => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_message')
  String? get errorMessage => throw _privateConstructorUsedError;

  /// Serializes this JobStatus to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of JobStatus
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $JobStatusCopyWith<JobStatus> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $JobStatusCopyWith<$Res> {
  factory $JobStatusCopyWith(
    JobStatus value,
    $Res Function(JobStatus) then,
  ) = _$JobStatusCopyWithImpl<$Res, JobStatus>;
  @useResult
  $Res call({
    @JsonKey(name: 'job_id') String jobId,
    String status,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_code') String? errorCode,
    @JsonKey(name: 'error_message') String? errorMessage,
  });
}

/// @nodoc
class _$JobStatusCopyWithImpl<$Res, $Val extends JobStatus>
    implements $JobStatusCopyWith<$Res> {
  _$JobStatusCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of JobStatus
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? jobId = null,
    Object? status = null,
    Object? resultJson = freezed,
    Object? errorCode = freezed,
    Object? errorMessage = freezed,
  }) {
    return _then(
      _value.copyWith(
            jobId: null == jobId
                ? _value.jobId
                : jobId // ignore: cast_nullable_to_non_nullable
                      as String,
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            resultJson: freezed == resultJson
                ? _value.resultJson
                : resultJson // ignore: cast_nullable_to_non_nullable
                      as String?,
            errorCode: freezed == errorCode
                ? _value.errorCode
                : errorCode // ignore: cast_nullable_to_non_nullable
                      as String?,
            errorMessage: freezed == errorMessage
                ? _value.errorMessage
                : errorMessage // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$JobStatusImplCopyWith<$Res>
    implements $JobStatusCopyWith<$Res> {
  factory _$$JobStatusImplCopyWith(
    _$JobStatusImpl value,
    $Res Function(_$JobStatusImpl) then,
  ) = __$$JobStatusImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'job_id') String jobId,
    String status,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_code') String? errorCode,
    @JsonKey(name: 'error_message') String? errorMessage,
  });
}

/// @nodoc
class __$$JobStatusImplCopyWithImpl<$Res>
    extends _$JobStatusCopyWithImpl<$Res, _$JobStatusImpl>
    implements _$$JobStatusImplCopyWith<$Res> {
  __$$JobStatusImplCopyWithImpl(
    _$JobStatusImpl _value,
    $Res Function(_$JobStatusImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of JobStatus
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? jobId = null,
    Object? status = null,
    Object? resultJson = freezed,
    Object? errorCode = freezed,
    Object? errorMessage = freezed,
  }) {
    return _then(
      _$JobStatusImpl(
        jobId: null == jobId
            ? _value.jobId
            : jobId // ignore: cast_nullable_to_non_nullable
                  as String,
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        resultJson: freezed == resultJson
            ? _value.resultJson
            : resultJson // ignore: cast_nullable_to_non_nullable
                  as String?,
        errorCode: freezed == errorCode
            ? _value.errorCode
            : errorCode // ignore: cast_nullable_to_non_nullable
                  as String?,
        errorMessage: freezed == errorMessage
            ? _value.errorMessage
            : errorMessage // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$JobStatusImpl implements _JobStatus {
  const _$JobStatusImpl({
    @JsonKey(name: 'job_id') required this.jobId,
    required this.status,
    @JsonKey(name: 'result_json') this.resultJson,
    @JsonKey(name: 'error_code') this.errorCode,
    @JsonKey(name: 'error_message') this.errorMessage,
  });

  factory _$JobStatusImpl.fromJson(Map<String, dynamic> json) =>
      _$$JobStatusImplFromJson(json);

  @override
  @JsonKey(name: 'job_id')
  final String jobId;
  @override
  final String status;
  @override
  @JsonKey(name: 'result_json')
  final String? resultJson;
  @override
  @JsonKey(name: 'error_code')
  final String? errorCode;
  @override
  @JsonKey(name: 'error_message')
  final String? errorMessage;

  @override
  String toString() {
    return 'JobStatus(jobId: $jobId, status: $status, resultJson: $resultJson, errorCode: $errorCode, errorMessage: $errorMessage)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$JobStatusImpl &&
            (identical(other.jobId, jobId) || other.jobId == jobId) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.resultJson, resultJson) ||
                other.resultJson == resultJson) &&
            (identical(other.errorCode, errorCode) ||
                other.errorCode == errorCode) &&
            (identical(other.errorMessage, errorMessage) ||
                other.errorMessage == errorMessage));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    jobId,
    status,
    resultJson,
    errorCode,
    errorMessage,
  );

  /// Create a copy of JobStatus
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$JobStatusImplCopyWith<_$JobStatusImpl> get copyWith =>
      __$$JobStatusImplCopyWithImpl<_$JobStatusImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$JobStatusImplToJson(this);
  }
}

abstract class _JobStatus implements JobStatus {
  const factory _JobStatus({
    @JsonKey(name: 'job_id') required final String jobId,
    required final String status,
    @JsonKey(name: 'result_json') final String? resultJson,
    @JsonKey(name: 'error_code') final String? errorCode,
    @JsonKey(name: 'error_message') final String? errorMessage,
  }) = _$JobStatusImpl;

  factory _JobStatus.fromJson(Map<String, dynamic> json) =
      _$JobStatusImpl.fromJson;

  @override
  @JsonKey(name: 'job_id')
  String get jobId;
  @override
  String get status;
  @override
  @JsonKey(name: 'result_json')
  String? get resultJson;
  @override
  @JsonKey(name: 'error_code')
  String? get errorCode;
  @override
  @JsonKey(name: 'error_message')
  String? get errorMessage;

  /// Create a copy of JobStatus
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$JobStatusImplCopyWith<_$JobStatusImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
