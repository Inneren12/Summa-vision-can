// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'chart_config_notifier.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

/// @nodoc
mixin _$ChartConfig {
  String get dataKey => throw _privateConstructorUsedError;
  String? get sourceProductId => throw _privateConstructorUsedError;
  ChartType get chartType => throw _privateConstructorUsedError;
  SizePreset get sizePreset => throw _privateConstructorUsedError;
  BackgroundCategory get category => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $ChartConfigCopyWith<ChartConfig> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ChartConfigCopyWith<$Res> {
  factory $ChartConfigCopyWith(
    ChartConfig value,
    $Res Function(ChartConfig) then,
  ) = _$ChartConfigCopyWithImpl<$Res, ChartConfig>;
  @useResult
  $Res call({
    String dataKey,
    String? sourceProductId,
    ChartType chartType,
    SizePreset sizePreset,
    BackgroundCategory category,
    String title,
  });
}

/// @nodoc
class _$ChartConfigCopyWithImpl<$Res, $Val extends ChartConfig>
    implements $ChartConfigCopyWith<$Res> {
  _$ChartConfigCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? dataKey = null,
    Object? sourceProductId = freezed,
    Object? chartType = null,
    Object? sizePreset = null,
    Object? category = null,
    Object? title = null,
  }) {
    return _then(
      _value.copyWith(
            dataKey:
                null == dataKey ? _value.dataKey : dataKey as String,
            sourceProductId: freezed == sourceProductId
                ? _value.sourceProductId
                : sourceProductId as String?,
            chartType: null == chartType
                ? _value.chartType
                : chartType as ChartType,
            sizePreset: null == sizePreset
                ? _value.sizePreset
                : sizePreset as SizePreset,
            category: null == category
                ? _value.category
                : category as BackgroundCategory,
            title: null == title ? _value.title : title as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ChartConfigImplCopyWith<$Res>
    implements $ChartConfigCopyWith<$Res> {
  factory _$$ChartConfigImplCopyWith(
    _$ChartConfigImpl value,
    $Res Function(_$ChartConfigImpl) then,
  ) = __$$ChartConfigImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String dataKey,
    String? sourceProductId,
    ChartType chartType,
    SizePreset sizePreset,
    BackgroundCategory category,
    String title,
  });
}

/// @nodoc
class __$$ChartConfigImplCopyWithImpl<$Res>
    extends _$ChartConfigCopyWithImpl<$Res, _$ChartConfigImpl>
    implements _$$ChartConfigImplCopyWith<$Res> {
  __$$ChartConfigImplCopyWithImpl(
    _$ChartConfigImpl _value,
    $Res Function(_$ChartConfigImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? dataKey = null,
    Object? sourceProductId = freezed,
    Object? chartType = null,
    Object? sizePreset = null,
    Object? category = null,
    Object? title = null,
  }) {
    return _then(
      _$ChartConfigImpl(
        dataKey:
            null == dataKey ? _value.dataKey : dataKey as String,
        sourceProductId: freezed == sourceProductId
            ? _value.sourceProductId
            : sourceProductId as String?,
        chartType: null == chartType
            ? _value.chartType
            : chartType as ChartType,
        sizePreset: null == sizePreset
            ? _value.sizePreset
            : sizePreset as SizePreset,
        category: null == category
            ? _value.category
            : category as BackgroundCategory,
        title: null == title ? _value.title : title as String,
      ),
    );
  }
}

/// @nodoc
class _$ChartConfigImpl implements _ChartConfig {
  const _$ChartConfigImpl({
    required this.dataKey,
    this.sourceProductId,
    this.chartType = ChartType.line,
    this.sizePreset = SizePreset.instagram,
    this.category = BackgroundCategory.housing,
    this.title = '',
  });

  @override
  final String dataKey;
  @override
  final String? sourceProductId;
  @override
  @JsonKey()
  final ChartType chartType;
  @override
  @JsonKey()
  final SizePreset sizePreset;
  @override
  @JsonKey()
  final BackgroundCategory category;
  @override
  @JsonKey()
  final String title;

  @override
  String toString() {
    return 'ChartConfig(dataKey: $dataKey, sourceProductId: $sourceProductId, chartType: $chartType, sizePreset: $sizePreset, category: $category, title: $title)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ChartConfigImpl &&
            (identical(other.dataKey, dataKey) || other.dataKey == dataKey) &&
            (identical(other.sourceProductId, sourceProductId) ||
                other.sourceProductId == sourceProductId) &&
            (identical(other.chartType, chartType) ||
                other.chartType == chartType) &&
            (identical(other.sizePreset, sizePreset) ||
                other.sizePreset == sizePreset) &&
            (identical(other.category, category) ||
                other.category == category) &&
            (identical(other.title, title) || other.title == title));
  }

  @override
  int get hashCode => Object.hash(
      runtimeType, dataKey, sourceProductId, chartType, sizePreset, category, title);

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ChartConfigImplCopyWith<_$ChartConfigImpl> get copyWith =>
      __$$ChartConfigImplCopyWithImpl<_$ChartConfigImpl>(this, _$identity);
}

abstract class _ChartConfig implements ChartConfig {
  const factory _ChartConfig({
    required final String dataKey,
    final String? sourceProductId,
    final ChartType chartType,
    final SizePreset sizePreset,
    final BackgroundCategory category,
    final String title,
  }) = _$ChartConfigImpl;

  @override
  String get dataKey;
  @override
  String? get sourceProductId;
  @override
  ChartType get chartType;
  @override
  SizePreset get sizePreset;
  @override
  BackgroundCategory get category;
  @override
  String get title;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ChartConfigImplCopyWith<_$ChartConfigImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
