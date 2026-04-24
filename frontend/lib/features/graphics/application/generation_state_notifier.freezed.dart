// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'generation_state_notifier.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

/// @nodoc
mixin _$ChartGenerationState {
  GenerationPhase get phase => throw _privateConstructorUsedError;
  String? get jobId => throw _privateConstructorUsedError;
  GenerationResult? get result => throw _privateConstructorUsedError;
  String? get errorMessage => throw _privateConstructorUsedError;
  String? get errorCode => throw _privateConstructorUsedError;
  int get pollCount => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $ChartGenerationStateCopyWith<ChartGenerationState> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ChartGenerationStateCopyWith<$Res> {
  factory $ChartGenerationStateCopyWith(
    ChartGenerationState value,
    $Res Function(ChartGenerationState) then,
  ) = _$ChartGenerationStateCopyWithImpl<$Res, ChartGenerationState>;
  @useResult
  $Res call({
    GenerationPhase phase,
    String? jobId,
    GenerationResult? result,
    String? errorMessage,
    String? errorCode,
    int pollCount,
  });
}

/// @nodoc
class _$ChartGenerationStateCopyWithImpl<$Res,
        $Val extends ChartGenerationState>
    implements $ChartGenerationStateCopyWith<$Res> {
  _$ChartGenerationStateCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? phase = null,
    Object? jobId = freezed,
    Object? result = freezed,
    Object? errorMessage = freezed,
    Object? errorCode = freezed,
    Object? pollCount = null,
  }) {
    return _then(
      _value.copyWith(
            phase: null == phase
                ? _value.phase
                : phase as GenerationPhase,
            jobId: freezed == jobId
                ? _value.jobId
                : jobId as String?,
            result: freezed == result
                ? _value.result
                : result as GenerationResult?,
            errorMessage: freezed == errorMessage
                ? _value.errorMessage
                : errorMessage as String?,
            errorCode: freezed == errorCode
                ? _value.errorCode
                : errorCode as String?,
            pollCount: null == pollCount
                ? _value.pollCount
                : pollCount as int,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ChartGenerationStateImplCopyWith<$Res>
    implements $ChartGenerationStateCopyWith<$Res> {
  factory _$$ChartGenerationStateImplCopyWith(
    _$ChartGenerationStateImpl value,
    $Res Function(_$ChartGenerationStateImpl) then,
  ) = __$$ChartGenerationStateImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    GenerationPhase phase,
    String? jobId,
    GenerationResult? result,
    String? errorMessage,
    String? errorCode,
    int pollCount,
  });
}

/// @nodoc
class __$$ChartGenerationStateImplCopyWithImpl<$Res>
    extends _$ChartGenerationStateCopyWithImpl<$Res,
        _$ChartGenerationStateImpl>
    implements _$$ChartGenerationStateImplCopyWith<$Res> {
  __$$ChartGenerationStateImplCopyWithImpl(
    _$ChartGenerationStateImpl _value,
    $Res Function(_$ChartGenerationStateImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? phase = null,
    Object? jobId = freezed,
    Object? result = freezed,
    Object? errorMessage = freezed,
    Object? errorCode = freezed,
    Object? pollCount = null,
  }) {
    return _then(
      _$ChartGenerationStateImpl(
        phase: null == phase
            ? _value.phase
            : phase as GenerationPhase,
        jobId: freezed == jobId
            ? _value.jobId
            : jobId as String?,
        result: freezed == result
            ? _value.result
            : result as GenerationResult?,
        errorMessage: freezed == errorMessage
            ? _value.errorMessage
            : errorMessage as String?,
        errorCode: freezed == errorCode
            ? _value.errorCode
            : errorCode as String?,
        pollCount: null == pollCount
            ? _value.pollCount
            : pollCount as int,
      ),
    );
  }
}

/// @nodoc
class _$ChartGenerationStateImpl implements _ChartGenerationState {
  const _$ChartGenerationStateImpl({
    this.phase = GenerationPhase.idle,
    this.jobId,
    this.result,
    this.errorMessage,
    this.errorCode,
    this.pollCount = 0,
  });

  @override
  @JsonKey()
  final GenerationPhase phase;
  @override
  final String? jobId;
  @override
  final GenerationResult? result;
  @override
  final String? errorMessage;
  @override
  final String? errorCode;
  @override
  @JsonKey()
  final int pollCount;

  @override
  String toString() {
    return 'ChartGenerationState(phase: $phase, jobId: $jobId, result: $result, errorMessage: $errorMessage, errorCode: $errorCode, pollCount: $pollCount)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ChartGenerationStateImpl &&
            (identical(other.phase, phase) || other.phase == phase) &&
            (identical(other.jobId, jobId) || other.jobId == jobId) &&
            (identical(other.result, result) || other.result == result) &&
            (identical(other.errorMessage, errorMessage) ||
                other.errorMessage == errorMessage) &&
            (identical(other.errorCode, errorCode) ||
                other.errorCode == errorCode) &&
            (identical(other.pollCount, pollCount) ||
                other.pollCount == pollCount));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType, phase, jobId, result, errorMessage, errorCode, pollCount);

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ChartGenerationStateImplCopyWith<_$ChartGenerationStateImpl>
      get copyWith =>
          __$$ChartGenerationStateImplCopyWithImpl<_$ChartGenerationStateImpl>(
              this, _$identity);
}

abstract class _ChartGenerationState implements ChartGenerationState {
  const factory _ChartGenerationState({
    final GenerationPhase phase,
    final String? jobId,
    final GenerationResult? result,
    final String? errorMessage,
    final String? errorCode,
    final int pollCount,
  }) = _$ChartGenerationStateImpl;

  @override
  GenerationPhase get phase;
  @override
  String? get jobId;
  @override
  GenerationResult? get result;
  @override
  String? get errorMessage;
  @override
  String? get errorCode;
  @override
  int get pollCount;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ChartGenerationStateImplCopyWith<_$ChartGenerationStateImpl>
      get copyWith => throw _privateConstructorUsedError;
}
