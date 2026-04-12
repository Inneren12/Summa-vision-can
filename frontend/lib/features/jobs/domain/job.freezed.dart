// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'job.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

Job _$JobFromJson(Map<String, dynamic> json) {
  return _Job.fromJson(json);
}

/// @nodoc
mixin _$Job {
  String get id => throw _privateConstructorUsedError;
  @JsonKey(name: 'job_type')
  String get jobType => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'payload_json')
  String? get payloadJson => throw _privateConstructorUsedError;
  @JsonKey(name: 'result_json')
  String? get resultJson => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_code')
  String? get errorCode => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_message')
  String? get errorMessage => throw _privateConstructorUsedError;
  @JsonKey(name: 'attempt_count')
  int get attemptCount => throw _privateConstructorUsedError;
  @JsonKey(name: 'max_attempts')
  int get maxAttempts => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  DateTime get createdAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'started_at')
  DateTime? get startedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'finished_at')
  DateTime? get finishedAt => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_by')
  String? get createdBy => throw _privateConstructorUsedError;
  @JsonKey(name: 'dedupe_key')
  String? get dedupeKey => throw _privateConstructorUsedError;

  /// Serializes this Job to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of Job
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $JobCopyWith<Job> get copyWith => throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $JobCopyWith<$Res> {
  factory $JobCopyWith(Job value, $Res Function(Job) then) =
      _$JobCopyWithImpl<$Res, Job>;
  @useResult
  $Res call({
    String id,
    @JsonKey(name: 'job_type') String jobType,
    String status,
    @JsonKey(name: 'payload_json') String? payloadJson,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_code') String? errorCode,
    @JsonKey(name: 'error_message') String? errorMessage,
    @JsonKey(name: 'attempt_count') int attemptCount,
    @JsonKey(name: 'max_attempts') int maxAttempts,
    @JsonKey(name: 'created_at') DateTime createdAt,
    @JsonKey(name: 'started_at') DateTime? startedAt,
    @JsonKey(name: 'finished_at') DateTime? finishedAt,
    @JsonKey(name: 'created_by') String? createdBy,
    @JsonKey(name: 'dedupe_key') String? dedupeKey,
  });
}

/// @nodoc
class _$JobCopyWithImpl<$Res, $Val extends Job> implements $JobCopyWith<$Res> {
  _$JobCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of Job
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? jobType = null,
    Object? status = null,
    Object? payloadJson = freezed,
    Object? resultJson = freezed,
    Object? errorCode = freezed,
    Object? errorMessage = freezed,
    Object? attemptCount = null,
    Object? maxAttempts = null,
    Object? createdAt = null,
    Object? startedAt = freezed,
    Object? finishedAt = freezed,
    Object? createdBy = freezed,
    Object? dedupeKey = freezed,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as String,
            jobType: null == jobType
                ? _value.jobType
                : jobType // ignore: cast_nullable_to_non_nullable
                      as String,
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            payloadJson: freezed == payloadJson
                ? _value.payloadJson
                : payloadJson // ignore: cast_nullable_to_non_nullable
                      as String?,
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
            attemptCount: null == attemptCount
                ? _value.attemptCount
                : attemptCount // ignore: cast_nullable_to_non_nullable
                      as int,
            maxAttempts: null == maxAttempts
                ? _value.maxAttempts
                : maxAttempts // ignore: cast_nullable_to_non_nullable
                      as int,
            createdAt: null == createdAt
                ? _value.createdAt
                : createdAt // ignore: cast_nullable_to_non_nullable
                      as DateTime,
            startedAt: freezed == startedAt
                ? _value.startedAt
                : startedAt // ignore: cast_nullable_to_non_nullable
                      as DateTime?,
            finishedAt: freezed == finishedAt
                ? _value.finishedAt
                : finishedAt // ignore: cast_nullable_to_non_nullable
                      as DateTime?,
            createdBy: freezed == createdBy
                ? _value.createdBy
                : createdBy // ignore: cast_nullable_to_non_nullable
                      as String?,
            dedupeKey: freezed == dedupeKey
                ? _value.dedupeKey
                : dedupeKey // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$JobImplCopyWith<$Res> implements $JobCopyWith<$Res> {
  factory _$$JobImplCopyWith(_$JobImpl value, $Res Function(_$JobImpl) then) =
      __$$JobImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String id,
    @JsonKey(name: 'job_type') String jobType,
    String status,
    @JsonKey(name: 'payload_json') String? payloadJson,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_code') String? errorCode,
    @JsonKey(name: 'error_message') String? errorMessage,
    @JsonKey(name: 'attempt_count') int attemptCount,
    @JsonKey(name: 'max_attempts') int maxAttempts,
    @JsonKey(name: 'created_at') DateTime createdAt,
    @JsonKey(name: 'started_at') DateTime? startedAt,
    @JsonKey(name: 'finished_at') DateTime? finishedAt,
    @JsonKey(name: 'created_by') String? createdBy,
    @JsonKey(name: 'dedupe_key') String? dedupeKey,
  });
}

/// @nodoc
class __$$JobImplCopyWithImpl<$Res> extends _$JobCopyWithImpl<$Res, _$JobImpl>
    implements _$$JobImplCopyWith<$Res> {
  __$$JobImplCopyWithImpl(_$JobImpl _value, $Res Function(_$JobImpl) _then)
    : super(_value, _then);

  /// Create a copy of Job
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? jobType = null,
    Object? status = null,
    Object? payloadJson = freezed,
    Object? resultJson = freezed,
    Object? errorCode = freezed,
    Object? errorMessage = freezed,
    Object? attemptCount = null,
    Object? maxAttempts = null,
    Object? createdAt = null,
    Object? startedAt = freezed,
    Object? finishedAt = freezed,
    Object? createdBy = freezed,
    Object? dedupeKey = freezed,
  }) {
    return _then(
      _$JobImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as String,
        jobType: null == jobType
            ? _value.jobType
            : jobType // ignore: cast_nullable_to_non_nullable
                  as String,
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        payloadJson: freezed == payloadJson
            ? _value.payloadJson
            : payloadJson // ignore: cast_nullable_to_non_nullable
                  as String?,
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
        attemptCount: null == attemptCount
            ? _value.attemptCount
            : attemptCount // ignore: cast_nullable_to_non_nullable
                  as int,
        maxAttempts: null == maxAttempts
            ? _value.maxAttempts
            : maxAttempts // ignore: cast_nullable_to_non_nullable
                  as int,
        createdAt: null == createdAt
            ? _value.createdAt
            : createdAt // ignore: cast_nullable_to_non_nullable
                  as DateTime,
        startedAt: freezed == startedAt
            ? _value.startedAt
            : startedAt // ignore: cast_nullable_to_non_nullable
                  as DateTime?,
        finishedAt: freezed == finishedAt
            ? _value.finishedAt
            : finishedAt // ignore: cast_nullable_to_non_nullable
                  as DateTime?,
        createdBy: freezed == createdBy
            ? _value.createdBy
            : createdBy // ignore: cast_nullable_to_non_nullable
                  as String?,
        dedupeKey: freezed == dedupeKey
            ? _value.dedupeKey
            : dedupeKey // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$JobImpl implements _Job {
  const _$JobImpl({
    required this.id,
    @JsonKey(name: 'job_type') required this.jobType,
    required this.status,
    @JsonKey(name: 'payload_json') this.payloadJson,
    @JsonKey(name: 'result_json') this.resultJson,
    @JsonKey(name: 'error_code') this.errorCode,
    @JsonKey(name: 'error_message') this.errorMessage,
    @JsonKey(name: 'attempt_count') required this.attemptCount,
    @JsonKey(name: 'max_attempts') required this.maxAttempts,
    @JsonKey(name: 'created_at') required this.createdAt,
    @JsonKey(name: 'started_at') this.startedAt,
    @JsonKey(name: 'finished_at') this.finishedAt,
    @JsonKey(name: 'created_by') this.createdBy,
    @JsonKey(name: 'dedupe_key') this.dedupeKey,
  });

  factory _$JobImpl.fromJson(Map<String, dynamic> json) =>
      _$$JobImplFromJson(json);

  @override
  final String id;
  @override
  @JsonKey(name: 'job_type')
  final String jobType;
  @override
  final String status;
  @override
  @JsonKey(name: 'payload_json')
  final String? payloadJson;
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
  @JsonKey(name: 'attempt_count')
  final int attemptCount;
  @override
  @JsonKey(name: 'max_attempts')
  final int maxAttempts;
  @override
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @override
  @JsonKey(name: 'started_at')
  final DateTime? startedAt;
  @override
  @JsonKey(name: 'finished_at')
  final DateTime? finishedAt;
  @override
  @JsonKey(name: 'created_by')
  final String? createdBy;
  @override
  @JsonKey(name: 'dedupe_key')
  final String? dedupeKey;

  @override
  String toString() {
    return 'Job(id: $id, jobType: $jobType, status: $status, payloadJson: $payloadJson, resultJson: $resultJson, errorCode: $errorCode, errorMessage: $errorMessage, attemptCount: $attemptCount, maxAttempts: $maxAttempts, createdAt: $createdAt, startedAt: $startedAt, finishedAt: $finishedAt, createdBy: $createdBy, dedupeKey: $dedupeKey)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$JobImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.jobType, jobType) || other.jobType == jobType) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.payloadJson, payloadJson) ||
                other.payloadJson == payloadJson) &&
            (identical(other.resultJson, resultJson) ||
                other.resultJson == resultJson) &&
            (identical(other.errorCode, errorCode) ||
                other.errorCode == errorCode) &&
            (identical(other.errorMessage, errorMessage) ||
                other.errorMessage == errorMessage) &&
            (identical(other.attemptCount, attemptCount) ||
                other.attemptCount == attemptCount) &&
            (identical(other.maxAttempts, maxAttempts) ||
                other.maxAttempts == maxAttempts) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt) &&
            (identical(other.startedAt, startedAt) ||
                other.startedAt == startedAt) &&
            (identical(other.finishedAt, finishedAt) ||
                other.finishedAt == finishedAt) &&
            (identical(other.createdBy, createdBy) ||
                other.createdBy == createdBy) &&
            (identical(other.dedupeKey, dedupeKey) ||
                other.dedupeKey == dedupeKey));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    jobType,
    status,
    payloadJson,
    resultJson,
    errorCode,
    errorMessage,
    attemptCount,
    maxAttempts,
    createdAt,
    startedAt,
    finishedAt,
    createdBy,
    dedupeKey,
  );

  /// Create a copy of Job
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$JobImplCopyWith<_$JobImpl> get copyWith =>
      __$$JobImplCopyWithImpl<_$JobImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$JobImplToJson(this);
  }
}

abstract class _Job implements Job {
  const factory _Job({
    required final String id,
    @JsonKey(name: 'job_type') required final String jobType,
    required final String status,
    @JsonKey(name: 'payload_json') final String? payloadJson,
    @JsonKey(name: 'result_json') final String? resultJson,
    @JsonKey(name: 'error_code') final String? errorCode,
    @JsonKey(name: 'error_message') final String? errorMessage,
    @JsonKey(name: 'attempt_count') required final int attemptCount,
    @JsonKey(name: 'max_attempts') required final int maxAttempts,
    @JsonKey(name: 'created_at') required final DateTime createdAt,
    @JsonKey(name: 'started_at') final DateTime? startedAt,
    @JsonKey(name: 'finished_at') final DateTime? finishedAt,
    @JsonKey(name: 'created_by') final String? createdBy,
    @JsonKey(name: 'dedupe_key') final String? dedupeKey,
  }) = _$JobImpl;

  factory _Job.fromJson(Map<String, dynamic> json) = _$JobImpl.fromJson;

  @override
  String get id;
  @override
  @JsonKey(name: 'job_type')
  String get jobType;
  @override
  String get status;
  @override
  @JsonKey(name: 'payload_json')
  String? get payloadJson;
  @override
  @JsonKey(name: 'result_json')
  String? get resultJson;
  @override
  @JsonKey(name: 'error_code')
  String? get errorCode;
  @override
  @JsonKey(name: 'error_message')
  String? get errorMessage;
  @override
  @JsonKey(name: 'attempt_count')
  int get attemptCount;
  @override
  @JsonKey(name: 'max_attempts')
  int get maxAttempts;
  @override
  @JsonKey(name: 'created_at')
  DateTime get createdAt;
  @override
  @JsonKey(name: 'started_at')
  DateTime? get startedAt;
  @override
  @JsonKey(name: 'finished_at')
  DateTime? get finishedAt;
  @override
  @JsonKey(name: 'created_by')
  String? get createdBy;
  @override
  @JsonKey(name: 'dedupe_key')
  String? get dedupeKey;

  /// Create a copy of Job
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$JobImplCopyWith<_$JobImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
