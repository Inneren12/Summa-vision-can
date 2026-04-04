// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'content_brief.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

ContentBrief _$ContentBriefFromJson(Map<String, dynamic> json) {
  return _ContentBrief.fromJson(json);
}

/// @nodoc
mixin _$ContentBrief {
  int get id => throw _privateConstructorUsedError;
  String get headline => throw _privateConstructorUsedError;
  @JsonKey(name: 'chart_type')
  String get chartType => throw _privateConstructorUsedError;
  @JsonKey(name: 'virality_score')
  double get viralityScore => throw _privateConstructorUsedError;
  String get status => throw _privateConstructorUsedError;
  @JsonKey(name: 'created_at')
  String get createdAt => throw _privateConstructorUsedError;

  /// Serializes this ContentBrief to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of ContentBrief
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ContentBriefCopyWith<ContentBrief> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ContentBriefCopyWith<$Res> {
  factory $ContentBriefCopyWith(
    ContentBrief value,
    $Res Function(ContentBrief) then,
  ) = _$ContentBriefCopyWithImpl<$Res, ContentBrief>;
  @useResult
  $Res call({
    int id,
    String headline,
    @JsonKey(name: 'chart_type') String chartType,
    @JsonKey(name: 'virality_score') double viralityScore,
    String status,
    @JsonKey(name: 'created_at') String createdAt,
  });
}

/// @nodoc
class _$ContentBriefCopyWithImpl<$Res, $Val extends ContentBrief>
    implements $ContentBriefCopyWith<$Res> {
  _$ContentBriefCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of ContentBrief
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? headline = null,
    Object? chartType = null,
    Object? viralityScore = null,
    Object? status = null,
    Object? createdAt = null,
  }) {
    return _then(
      _value.copyWith(
            id: null == id
                ? _value.id
                : id // ignore: cast_nullable_to_non_nullable
                      as int,
            headline: null == headline
                ? _value.headline
                : headline // ignore: cast_nullable_to_non_nullable
                      as String,
            chartType: null == chartType
                ? _value.chartType
                : chartType // ignore: cast_nullable_to_non_nullable
                      as String,
            viralityScore: null == viralityScore
                ? _value.viralityScore
                : viralityScore // ignore: cast_nullable_to_non_nullable
                      as double,
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            createdAt: null == createdAt
                ? _value.createdAt
                : createdAt // ignore: cast_nullable_to_non_nullable
                      as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ContentBriefImplCopyWith<$Res>
    implements $ContentBriefCopyWith<$Res> {
  factory _$$ContentBriefImplCopyWith(
    _$ContentBriefImpl value,
    $Res Function(_$ContentBriefImpl) then,
  ) = __$$ContentBriefImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int id,
    String headline,
    @JsonKey(name: 'chart_type') String chartType,
    @JsonKey(name: 'virality_score') double viralityScore,
    String status,
    @JsonKey(name: 'created_at') String createdAt,
  });
}

/// @nodoc
class __$$ContentBriefImplCopyWithImpl<$Res>
    extends _$ContentBriefCopyWithImpl<$Res, _$ContentBriefImpl>
    implements _$$ContentBriefImplCopyWith<$Res> {
  __$$ContentBriefImplCopyWithImpl(
    _$ContentBriefImpl _value,
    $Res Function(_$ContentBriefImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of ContentBrief
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? id = null,
    Object? headline = null,
    Object? chartType = null,
    Object? viralityScore = null,
    Object? status = null,
    Object? createdAt = null,
  }) {
    return _then(
      _$ContentBriefImpl(
        id: null == id
            ? _value.id
            : id // ignore: cast_nullable_to_non_nullable
                  as int,
        headline: null == headline
            ? _value.headline
            : headline // ignore: cast_nullable_to_non_nullable
                  as String,
        chartType: null == chartType
            ? _value.chartType
            : chartType // ignore: cast_nullable_to_non_nullable
                  as String,
        viralityScore: null == viralityScore
            ? _value.viralityScore
            : viralityScore // ignore: cast_nullable_to_non_nullable
                  as double,
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        createdAt: null == createdAt
            ? _value.createdAt
            : createdAt // ignore: cast_nullable_to_non_nullable
                  as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$ContentBriefImpl implements _ContentBrief {
  const _$ContentBriefImpl({
    required this.id,
    required this.headline,
    @JsonKey(name: 'chart_type') required this.chartType,
    @JsonKey(name: 'virality_score') required this.viralityScore,
    required this.status,
    @JsonKey(name: 'created_at') required this.createdAt,
  });

  factory _$ContentBriefImpl.fromJson(Map<String, dynamic> json) =>
      _$$ContentBriefImplFromJson(json);

  @override
  final int id;
  @override
  final String headline;
  @override
  @JsonKey(name: 'chart_type')
  final String chartType;
  @override
  @JsonKey(name: 'virality_score')
  final double viralityScore;
  @override
  final String status;
  @override
  @JsonKey(name: 'created_at')
  final String createdAt;

  @override
  String toString() {
    return 'ContentBrief(id: $id, headline: $headline, chartType: $chartType, viralityScore: $viralityScore, status: $status, createdAt: $createdAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ContentBriefImpl &&
            (identical(other.id, id) || other.id == id) &&
            (identical(other.headline, headline) ||
                other.headline == headline) &&
            (identical(other.chartType, chartType) ||
                other.chartType == chartType) &&
            (identical(other.viralityScore, viralityScore) ||
                other.viralityScore == viralityScore) &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.createdAt, createdAt) ||
                other.createdAt == createdAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    id,
    headline,
    chartType,
    viralityScore,
    status,
    createdAt,
  );

  /// Create a copy of ContentBrief
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ContentBriefImplCopyWith<_$ContentBriefImpl> get copyWith =>
      __$$ContentBriefImplCopyWithImpl<_$ContentBriefImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ContentBriefImplToJson(this);
  }
}

abstract class _ContentBrief implements ContentBrief {
  const factory _ContentBrief({
    required final int id,
    required final String headline,
    @JsonKey(name: 'chart_type') required final String chartType,
    @JsonKey(name: 'virality_score') required final double viralityScore,
    required final String status,
    @JsonKey(name: 'created_at') required final String createdAt,
  }) = _$ContentBriefImpl;

  factory _ContentBrief.fromJson(Map<String, dynamic> json) =
      _$ContentBriefImpl.fromJson;

  @override
  int get id;
  @override
  String get headline;
  @override
  @JsonKey(name: 'chart_type')
  String get chartType;
  @override
  @JsonKey(name: 'virality_score')
  double get viralityScore;
  @override
  String get status;
  @override
  @JsonKey(name: 'created_at')
  String get createdAt;

  /// Create a copy of ContentBrief
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ContentBriefImplCopyWith<_$ContentBriefImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
