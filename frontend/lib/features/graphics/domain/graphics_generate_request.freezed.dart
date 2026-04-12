// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'graphics_generate_request.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

GraphicsGenerateRequest _$GraphicsGenerateRequestFromJson(
    Map<String, dynamic> json) {
  return _GraphicsGenerateRequest.fromJson(json);
}

/// @nodoc
mixin _$GraphicsGenerateRequest {
  @JsonKey(name: 'data_key')
  String get dataKey => throw _privateConstructorUsedError;
  @JsonKey(name: 'chart_type')
  String get chartType => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  List<int> get size => throw _privateConstructorUsedError;
  String get category => throw _privateConstructorUsedError;
  @JsonKey(name: 'source_product_id')
  String? get sourceProductId => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $GraphicsGenerateRequestCopyWith<GraphicsGenerateRequest> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $GraphicsGenerateRequestCopyWith<$Res> {
  factory $GraphicsGenerateRequestCopyWith(
    GraphicsGenerateRequest value,
    $Res Function(GraphicsGenerateRequest) then,
  ) = _$GraphicsGenerateRequestCopyWithImpl<$Res, GraphicsGenerateRequest>;
  @useResult
  $Res call({
    @JsonKey(name: 'data_key') String dataKey,
    @JsonKey(name: 'chart_type') String chartType,
    String title,
    List<int> size,
    String category,
    @JsonKey(name: 'source_product_id') String? sourceProductId,
  });
}

/// @nodoc
class _$GraphicsGenerateRequestCopyWithImpl<$Res,
        $Val extends GraphicsGenerateRequest>
    implements $GraphicsGenerateRequestCopyWith<$Res> {
  _$GraphicsGenerateRequestCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? dataKey = null,
    Object? chartType = null,
    Object? title = null,
    Object? size = null,
    Object? category = null,
    Object? sourceProductId = freezed,
  }) {
    return _then(
      _value.copyWith(
            dataKey:
                null == dataKey ? _value.dataKey : dataKey as String,
            chartType:
                null == chartType ? _value.chartType : chartType as String,
            title: null == title ? _value.title : title as String,
            size: null == size ? _value.size : size as List<int>,
            category:
                null == category ? _value.category : category as String,
            sourceProductId: freezed == sourceProductId
                ? _value.sourceProductId
                : sourceProductId as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$GraphicsGenerateRequestImplCopyWith<$Res>
    implements $GraphicsGenerateRequestCopyWith<$Res> {
  factory _$$GraphicsGenerateRequestImplCopyWith(
    _$GraphicsGenerateRequestImpl value,
    $Res Function(_$GraphicsGenerateRequestImpl) then,
  ) = __$$GraphicsGenerateRequestImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'data_key') String dataKey,
    @JsonKey(name: 'chart_type') String chartType,
    String title,
    List<int> size,
    String category,
    @JsonKey(name: 'source_product_id') String? sourceProductId,
  });
}

/// @nodoc
class __$$GraphicsGenerateRequestImplCopyWithImpl<$Res>
    extends _$GraphicsGenerateRequestCopyWithImpl<$Res,
        _$GraphicsGenerateRequestImpl>
    implements _$$GraphicsGenerateRequestImplCopyWith<$Res> {
  __$$GraphicsGenerateRequestImplCopyWithImpl(
    _$GraphicsGenerateRequestImpl _value,
    $Res Function(_$GraphicsGenerateRequestImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? dataKey = null,
    Object? chartType = null,
    Object? title = null,
    Object? size = null,
    Object? category = null,
    Object? sourceProductId = freezed,
  }) {
    return _then(
      _$GraphicsGenerateRequestImpl(
        dataKey:
            null == dataKey ? _value.dataKey : dataKey as String,
        chartType:
            null == chartType ? _value.chartType : chartType as String,
        title: null == title ? _value.title : title as String,
        size: null == size
            ? _value._size
            : size as List<int>,
        category:
            null == category ? _value.category : category as String,
        sourceProductId: freezed == sourceProductId
            ? _value.sourceProductId
            : sourceProductId as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$GraphicsGenerateRequestImpl implements _GraphicsGenerateRequest {
  const _$GraphicsGenerateRequestImpl({
    @JsonKey(name: 'data_key') required this.dataKey,
    @JsonKey(name: 'chart_type') required this.chartType,
    required this.title,
    required final List<int> size,
    required this.category,
    @JsonKey(name: 'source_product_id') this.sourceProductId,
  }) : _size = size;

  factory _$GraphicsGenerateRequestImpl.fromJson(Map<String, dynamic> json) =>
      _$$GraphicsGenerateRequestImplFromJson(json);

  @override
  @JsonKey(name: 'data_key')
  final String dataKey;
  @override
  @JsonKey(name: 'chart_type')
  final String chartType;
  @override
  final String title;
  final List<int> _size;
  @override
  List<int> get size {
    return List.unmodifiable(_size);
  }

  @override
  final String category;
  @override
  @JsonKey(name: 'source_product_id')
  final String? sourceProductId;

  @override
  String toString() {
    return 'GraphicsGenerateRequest(dataKey: $dataKey, chartType: $chartType, title: $title, size: $size, category: $category, sourceProductId: $sourceProductId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$GraphicsGenerateRequestImpl &&
            (identical(other.dataKey, dataKey) || other.dataKey == dataKey) &&
            (identical(other.chartType, chartType) ||
                other.chartType == chartType) &&
            (identical(other.title, title) || other.title == title) &&
            const DeepCollectionEquality().equals(other._size, _size) &&
            (identical(other.category, category) ||
                other.category == category) &&
            (identical(other.sourceProductId, sourceProductId) ||
                other.sourceProductId == sourceProductId));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
        runtimeType,
        dataKey,
        chartType,
        title,
        const DeepCollectionEquality().hash(_size),
        category,
        sourceProductId,
      );

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$GraphicsGenerateRequestImplCopyWith<_$GraphicsGenerateRequestImpl>
      get copyWith => __$$GraphicsGenerateRequestImplCopyWithImpl<
          _$GraphicsGenerateRequestImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$GraphicsGenerateRequestImplToJson(this);
  }
}

abstract class _GraphicsGenerateRequest implements GraphicsGenerateRequest {
  const factory _GraphicsGenerateRequest({
    @JsonKey(name: 'data_key') required final String dataKey,
    @JsonKey(name: 'chart_type') required final String chartType,
    required final String title,
    required final List<int> size,
    required final String category,
    @JsonKey(name: 'source_product_id') final String? sourceProductId,
  }) = _$GraphicsGenerateRequestImpl;

  factory _GraphicsGenerateRequest.fromJson(Map<String, dynamic> json) =
      _$GraphicsGenerateRequestImpl.fromJson;

  @override
  @JsonKey(name: 'data_key')
  String get dataKey;
  @override
  @JsonKey(name: 'chart_type')
  String get chartType;
  @override
  String get title;
  @override
  List<int> get size;
  @override
  String get category;
  @override
  @JsonKey(name: 'source_product_id')
  String? get sourceProductId;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$GraphicsGenerateRequestImplCopyWith<_$GraphicsGenerateRequestImpl>
      get copyWith => throw _privateConstructorUsedError;
}
