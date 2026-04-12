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
  String get id => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'result_json')
  String? get resultJson => throw _privateConstructorUsedError;
  @JsonKey(name: 'error_message')
  String? get errorMessage => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

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
    String id,
    String status,
    @JsonKey(name: 'result_json') String? resultJson,
    @JsonKey(name: 'error_message') String? errorMessage,
  });
}

/// @nodoc
class _$JobStatusCopyWithImpl<$Res, $Val extends JobStatus>
    implements $JobStatusCopyWith<$Res> {
  _$JobStatusCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? status = null,
    Object? resultJson = freezed,
    Object? errorMessage = freezed,
  }) {
    return _then(
      _value.copyWith(
            id: null == id ? _value.id : id as String,
            status:
                null == status ? _value.status : status as String,
            resultJson: freezed == resultJson
                ? _value.resultJson
                : resultJson as String?,
            errorMessage: freezed == errorMessage
                ? _value.errorMessage
                : errorMessage as String?,
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
    String id,
    String status,
    @JsonKey(name: 'result_json') String? resultJson,
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

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? status = null,
    Object? resultJson = freezed,
    Object? errorMessage = freezed,
  }) {
    return _then(
      _$JobStatusImpl(
        id: null == id ? _value.id : id as String,
        status:
            null == status ? _value.status : status as String,
        resultJson: freezed == resultJson
            ? _value.resultJson
            : resultJson as String?,
        errorMessage: freezed == errorMessage
            ? _value.errorMessage
            : errorMessage as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$JobStatusImpl implements _JobStatus {
  const _$JobStatusImpl({
    required this.id,
    required this.status,
    @JsonKey(name: 'result_json') this.resultJson,
    @JsonKey(name: 'error_message') this.errorMessage,
  });

  factory _$JobStatusImpl.fromJson(Map<String, dynamic> json) =>
      _$$JobStatusImplFromJson(json);

  @override
  final String id;
  @override
  final String status;
  @override
  @JsonKey(name: 'result_json')
  final String? resultJson;
  @override
  @JsonKey(name: 'error_message')
  final String? errorMessage;

  @override
  String toString() {
    return 'JobStatus(id: $id, status: $status, resultJson: $resultJson, errorMessage: $errorMessage)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$JobStatusImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.resultJson, resultJson) ||
                other.resultJson == resultJson) &&
            (identical(other.errorMessage, errorMessage) ||
                other.errorMessage == errorMessage));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, id, status, resultJson, errorMessage);

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
    required final String id,
    required final String status,
    @JsonKey(name: 'result_json') final String? resultJson,
    @JsonKey(name: 'error_message') final String? errorMessage,
  }) = _$JobStatusImpl;

  factory _JobStatus.fromJson(Map<String, dynamic> json) =
      _$JobStatusImpl.fromJson;

  @override
  String get id;
  @override
  String get status;
  @override
  @JsonKey(name: 'result_json')
  String? get resultJson;
  @override
  @JsonKey(name: 'error_message')
  String? get errorMessage;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$JobStatusImplCopyWith<_$JobStatusImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
