// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'task_status.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

TaskStatus _$TaskStatusFromJson(Map<String, dynamic> json) {
  return _TaskStatus.fromJson(json);
}

/// @nodoc
mixin _$TaskStatus {
  @JsonKey(name: 'task_id')
  String get taskId => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'result_url')
  String? get resultUrl => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_code')
  String? get errorCode => throw _privateConstructorUsedError;
  String? get detail => throw _privateConstructorUsedError;

  /// Serializes this TaskStatus to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of TaskStatus
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $TaskStatusCopyWith<TaskStatus> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TaskStatusCopyWith<$Res> {
  factory $TaskStatusCopyWith(
    TaskStatus value,
    $Res Function(TaskStatus) then,
  ) = _$TaskStatusCopyWithImpl<$Res, TaskStatus>;
  @useResult
  $Res call({
    @JsonKey(name: 'task_id') String taskId,
    String status,
    @JsonKey(name: 'result_url') String? resultUrl,
    @JsonKey(name: 'error_code') String? errorCode,
    String? detail,
  });
}

/// @nodoc
class _$TaskStatusCopyWithImpl<$Res, $Val extends TaskStatus>
    implements $TaskStatusCopyWith<$Res> {
  _$TaskStatusCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of TaskStatus
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? taskId = null,
    Object? status = null,
    Object? resultUrl = freezed,
    Object? errorCode = freezed,
    Object? detail = freezed,
  }) {
    return _then(
      _value.copyWith(
            taskId: null == taskId
                ? _value.taskId
                : taskId // ignore: cast_nullable_to_non_nullable
                      as String,
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            resultUrl: freezed == resultUrl
                ? _value.resultUrl
                : resultUrl // ignore: cast_nullable_to_non_nullable
                      as String?,
            errorCode: freezed == errorCode
                ? _value.errorCode
                : errorCode // ignore: cast_nullable_to_non_nullable
                      as String?,
            detail: freezed == detail
                ? _value.detail
                : detail // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$TaskStatusImplCopyWith<$Res>
    implements $TaskStatusCopyWith<$Res> {
  factory _$$TaskStatusImplCopyWith(
    _$TaskStatusImpl value,
    $Res Function(_$TaskStatusImpl) then,
  ) = __$$TaskStatusImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'task_id') String taskId,
    String status,
    @JsonKey(name: 'result_url') String? resultUrl,
    @JsonKey(name: 'error_code') String? errorCode,
    String? detail,
  });
}

/// @nodoc
class __$$TaskStatusImplCopyWithImpl<$Res>
    extends _$TaskStatusCopyWithImpl<$Res, _$TaskStatusImpl>
    implements _$$TaskStatusImplCopyWith<$Res> {
  __$$TaskStatusImplCopyWithImpl(
    _$TaskStatusImpl _value,
    $Res Function(_$TaskStatusImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of TaskStatus
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? taskId = null,
    Object? status = null,
    Object? resultUrl = freezed,
    Object? errorCode = freezed,
    Object? detail = freezed,
  }) {
    return _then(
      _$TaskStatusImpl(
        taskId: null == taskId
            ? _value.taskId
            : taskId // ignore: cast_nullable_to_non_nullable
                  as String,
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        resultUrl: freezed == resultUrl
            ? _value.resultUrl
            : resultUrl // ignore: cast_nullable_to_non_nullable
                  as String?,
        errorCode: freezed == errorCode
            ? _value.errorCode
            : errorCode // ignore: cast_nullable_to_non_nullable
                  as String?,
        detail: freezed == detail
            ? _value.detail
            : detail // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$TaskStatusImpl implements _TaskStatus {
  const _$TaskStatusImpl({
    @JsonKey(name: 'task_id') required this.taskId,
    required this.status,
    @JsonKey(name: 'result_url') this.resultUrl,
    @JsonKey(name: 'error_code') this.errorCode,
    this.detail,
  });

  factory _$TaskStatusImpl.fromJson(Map<String, dynamic> json) =>
      _$$TaskStatusImplFromJson(json);

  @override
  @JsonKey(name: 'task_id')
  final String taskId;
  @override
  final String status;
  @override
  @JsonKey(name: 'result_url')
  final String? resultUrl;
  @override
  @JsonKey(name: 'error_code')
  final String? errorCode;
  @override
  final String? detail;

  @override
  String toString() {
    return 'TaskStatus(taskId: $taskId, status: $status, resultUrl: $resultUrl, errorCode: $errorCode, detail: $detail)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TaskStatusImpl &&
            (identical(other.taskId, taskId) || other.taskId == taskId) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.resultUrl, resultUrl) ||
                other.resultUrl == resultUrl) &&
            (identical(other.errorCode, errorCode) ||
                other.errorCode == errorCode) &&
            (identical(other.detail, detail) || other.detail == detail));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    taskId,
    status,
    resultUrl,
    errorCode,
    detail,
  );

  /// Create a copy of TaskStatus
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$TaskStatusImplCopyWith<_$TaskStatusImpl> get copyWith =>
      __$$TaskStatusImplCopyWithImpl<_$TaskStatusImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TaskStatusImplToJson(this);
  }
}

abstract class _TaskStatus implements TaskStatus {
  const factory _TaskStatus({
    @JsonKey(name: 'task_id') required final String taskId,
    required final String status,
    @JsonKey(name: 'result_url') final String? resultUrl,
    @JsonKey(name: 'error_code') final String? errorCode,
    final String? detail,
  }) = _$TaskStatusImpl;

  factory _TaskStatus.fromJson(Map<String, dynamic> json) =
      _$TaskStatusImpl.fromJson;

  @override
  @JsonKey(name: 'task_id')
  String get taskId;
  @override
  String get status;
  @override
  @JsonKey(name: 'result_url')
  String? get resultUrl;
  @override
  @JsonKey(name: 'error_code')
  String? get errorCode;
  @override
  String? get detail;

  /// Create a copy of TaskStatus
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$TaskStatusImplCopyWith<_$TaskStatusImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
