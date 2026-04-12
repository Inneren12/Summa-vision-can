// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'job_filter.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

/// @nodoc
mixin _$JobFilter {
  String? get jobType => throw _privateConstructorUsedError;
  String? get status => throw _privateConstructorUsedError;
  int get limit => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $JobFilterCopyWith<JobFilter> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $JobFilterCopyWith<$Res> {
  factory $JobFilterCopyWith(
    JobFilter value,
    $Res Function(JobFilter) then,
  ) = _$JobFilterCopyWithImpl<$Res, JobFilter>;
  @useResult
  $Res call({String? jobType, String? status, int limit});
}

/// @nodoc
class _$JobFilterCopyWithImpl<$Res, $Val extends JobFilter>
    implements $JobFilterCopyWith<$Res> {
  _$JobFilterCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? jobType = freezed,
    Object? status = freezed,
    Object? limit = null,
  }) {
    return _then(
      _value.copyWith(
            jobType: freezed == jobType
                ? _value.jobType
                : jobType as String?,
            status: freezed == status
                ? _value.status
                : status as String?,
            limit: null == limit ? _value.limit : limit as int,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$JobFilterImplCopyWith<$Res>
    implements $JobFilterCopyWith<$Res> {
  factory _$$JobFilterImplCopyWith(
    _$JobFilterImpl value,
    $Res Function(_$JobFilterImpl) then,
  ) = __$$JobFilterImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String? jobType, String? status, int limit});
}

/// @nodoc
class __$$JobFilterImplCopyWithImpl<$Res>
    extends _$JobFilterCopyWithImpl<$Res, _$JobFilterImpl>
    implements _$$JobFilterImplCopyWith<$Res> {
  __$$JobFilterImplCopyWithImpl(
    _$JobFilterImpl _value,
    $Res Function(_$JobFilterImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? jobType = freezed,
    Object? status = freezed,
    Object? limit = null,
  }) {
    return _then(
      _$JobFilterImpl(
        jobType: freezed == jobType
            ? _value.jobType
            : jobType as String?,
        status: freezed == status
            ? _value.status
            : status as String?,
        limit: null == limit ? _value.limit : limit as int,
      ),
    );
  }
}

/// @nodoc

class _$JobFilterImpl implements _JobFilter {
  const _$JobFilterImpl({this.jobType, this.status, this.limit = 50});

  @override
  final String? jobType;
  @override
  final String? status;
  @override
  @JsonKey()
  final int limit;

  @override
  String toString() {
    return 'JobFilter(jobType: $jobType, status: $status, limit: $limit)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$JobFilterImpl &&
            (identical(other.jobType, jobType) ||
                other.jobType == jobType) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.limit, limit) || other.limit == limit));
  }

  @override
  int get hashCode => Object.hash(runtimeType, jobType, status, limit);

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$JobFilterImplCopyWith<_$JobFilterImpl> get copyWith =>
      __$$JobFilterImplCopyWithImpl<_$JobFilterImpl>(this, _$identity);
}

abstract class _JobFilter implements JobFilter {
  const factory _JobFilter({
    final String? jobType,
    final String? status,
    final int limit,
  }) = _$JobFilterImpl;

  @override
  String? get jobType;
  @override
  String? get status;
  @override
  int get limit;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$JobFilterImplCopyWith<_$JobFilterImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
