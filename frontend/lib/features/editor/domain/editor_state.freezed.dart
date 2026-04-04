// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'editor_state.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

/// @nodoc
mixin _$EditorState {
  int get briefId => throw _privateConstructorUsedError;
  String get headline => throw _privateConstructorUsedError;
  String get bgPrompt => throw _privateConstructorUsedError;
  ChartType get chartType => throw _privateConstructorUsedError;
  bool get isDirty => throw _privateConstructorUsedError;

  /// Create a copy of EditorState
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $EditorStateCopyWith<EditorState> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $EditorStateCopyWith<$Res> {
  factory $EditorStateCopyWith(
    EditorState value,
    $Res Function(EditorState) then,
  ) = _$EditorStateCopyWithImpl<$Res, EditorState>;
  @useResult
  $Res call({
    int briefId,
    String headline,
    String bgPrompt,
    ChartType chartType,
    bool isDirty,
  });
}

/// @nodoc
class _$EditorStateCopyWithImpl<$Res, $Val extends EditorState>
    implements $EditorStateCopyWith<$Res> {
  _$EditorStateCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of EditorState
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? briefId = null,
    Object? headline = null,
    Object? bgPrompt = null,
    Object? chartType = null,
    Object? isDirty = null,
  }) {
    return _then(
      _value.copyWith(
            briefId: null == briefId
                ? _value.briefId
                : briefId // ignore: cast_nullable_to_non_nullable
                      as int,
            headline: null == headline
                ? _value.headline
                : headline // ignore: cast_nullable_to_non_nullable
                      as String,
            bgPrompt: null == bgPrompt
                ? _value.bgPrompt
                : bgPrompt // ignore: cast_nullable_to_non_nullable
                      as String,
            chartType: null == chartType
                ? _value.chartType
                : chartType // ignore: cast_nullable_to_non_nullable
                      as ChartType,
            isDirty: null == isDirty
                ? _value.isDirty
                : isDirty // ignore: cast_nullable_to_non_nullable
                      as bool,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$EditorStateImplCopyWith<$Res>
    implements $EditorStateCopyWith<$Res> {
  factory _$$EditorStateImplCopyWith(
    _$EditorStateImpl value,
    $Res Function(_$EditorStateImpl) then,
  ) = __$$EditorStateImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int briefId,
    String headline,
    String bgPrompt,
    ChartType chartType,
    bool isDirty,
  });
}

/// @nodoc
class __$$EditorStateImplCopyWithImpl<$Res>
    extends _$EditorStateCopyWithImpl<$Res, _$EditorStateImpl>
    implements _$$EditorStateImplCopyWith<$Res> {
  __$$EditorStateImplCopyWithImpl(
    _$EditorStateImpl _value,
    $Res Function(_$EditorStateImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of EditorState
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? briefId = null,
    Object? headline = null,
    Object? bgPrompt = null,
    Object? chartType = null,
    Object? isDirty = null,
  }) {
    return _then(
      _$EditorStateImpl(
        briefId: null == briefId
            ? _value.briefId
            : briefId // ignore: cast_nullable_to_non_nullable
                  as int,
        headline: null == headline
            ? _value.headline
            : headline // ignore: cast_nullable_to_non_nullable
                  as String,
        bgPrompt: null == bgPrompt
            ? _value.bgPrompt
            : bgPrompt // ignore: cast_nullable_to_non_nullable
                  as String,
        chartType: null == chartType
            ? _value.chartType
            : chartType // ignore: cast_nullable_to_non_nullable
                  as ChartType,
        isDirty: null == isDirty
            ? _value.isDirty
            : isDirty // ignore: cast_nullable_to_non_nullable
                  as bool,
      ),
    );
  }
}

/// @nodoc

class _$EditorStateImpl implements _EditorState {
  const _$EditorStateImpl({
    required this.briefId,
    required this.headline,
    required this.bgPrompt,
    required this.chartType,
    this.isDirty = false,
  });

  @override
  final int briefId;
  @override
  final String headline;
  @override
  final String bgPrompt;
  @override
  final ChartType chartType;
  @override
  @JsonKey()
  final bool isDirty;

  @override
  String toString() {
    return 'EditorState(briefId: $briefId, headline: $headline, bgPrompt: $bgPrompt, chartType: $chartType, isDirty: $isDirty)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$EditorStateImpl &&
            (identical(other.briefId, briefId) || other.briefId == briefId) &&
            (identical(other.headline, headline) ||
                other.headline == headline) &&
            (identical(other.bgPrompt, bgPrompt) ||
                other.bgPrompt == bgPrompt) &&
            (identical(other.chartType, chartType) ||
                other.chartType == chartType) &&
            (identical(other.isDirty, isDirty) || other.isDirty == isDirty));
  }

  @override
  int get hashCode =>
      Object.hash(runtimeType, briefId, headline, bgPrompt, chartType, isDirty);

  /// Create a copy of EditorState
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$EditorStateImplCopyWith<_$EditorStateImpl> get copyWith =>
      __$$EditorStateImplCopyWithImpl<_$EditorStateImpl>(this, _$identity);
}

abstract class _EditorState implements EditorState {
  const factory _EditorState({
    required final int briefId,
    required final String headline,
    required final String bgPrompt,
    required final ChartType chartType,
    final bool isDirty,
  }) = _$EditorStateImpl;

  @override
  int get briefId;
  @override
  String get headline;
  @override
  String get bgPrompt;
  @override
  ChartType get chartType;
  @override
  bool get isDirty;

  /// Create a copy of EditorState
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$EditorStateImplCopyWith<_$EditorStateImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
