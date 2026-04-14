// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'raw_data_upload.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

RawDataColumn _$RawDataColumnFromJson(Map<String, dynamic> json) {
  return _RawDataColumn.fromJson(json);
}

/// @nodoc
mixin _$RawDataColumn {
  String get name => throw _privateConstructorUsedError;
  String get dtype => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $RawDataColumnCopyWith<RawDataColumn> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RawDataColumnCopyWith<$Res> {
  factory $RawDataColumnCopyWith(
    RawDataColumn value,
    $Res Function(RawDataColumn) then,
  ) = _$RawDataColumnCopyWithImpl<$Res, RawDataColumn>;
  @useResult
  $Res call({String name, String dtype});
}

/// @nodoc
class _$RawDataColumnCopyWithImpl<$Res, $Val extends RawDataColumn>
    implements $RawDataColumnCopyWith<$Res> {
  _$RawDataColumnCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? name = null,
    Object? dtype = null,
  }) {
    return _then(
      _value.copyWith(
            name: null == name ? _value.name : name as String,
            dtype: null == dtype ? _value.dtype : dtype as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$RawDataColumnImplCopyWith<$Res>
    implements $RawDataColumnCopyWith<$Res> {
  factory _$$RawDataColumnImplCopyWith(
    _$RawDataColumnImpl value,
    $Res Function(_$RawDataColumnImpl) then,
  ) = __$$RawDataColumnImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String name, String dtype});
}

/// @nodoc
class __$$RawDataColumnImplCopyWithImpl<$Res>
    extends _$RawDataColumnCopyWithImpl<$Res, _$RawDataColumnImpl>
    implements _$$RawDataColumnImplCopyWith<$Res> {
  __$$RawDataColumnImplCopyWithImpl(
    _$RawDataColumnImpl _value,
    $Res Function(_$RawDataColumnImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? name = null,
    Object? dtype = null,
  }) {
    return _then(
      _$RawDataColumnImpl(
        name: null == name ? _value.name : name as String,
        dtype: null == dtype ? _value.dtype : dtype as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$RawDataColumnImpl implements _RawDataColumn {
  const _$RawDataColumnImpl({required this.name, this.dtype = 'str'});

  factory _$RawDataColumnImpl.fromJson(Map<String, dynamic> json) =>
      _$$RawDataColumnImplFromJson(json);

  @override
  final String name;
  @override
  @JsonKey()
  final String dtype;

  @override
  String toString() {
    return 'RawDataColumn(name: $name, dtype: $dtype)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RawDataColumnImpl &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.dtype, dtype) || other.dtype == dtype));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, name, dtype);

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RawDataColumnImplCopyWith<_$RawDataColumnImpl> get copyWith =>
      __$$RawDataColumnImplCopyWithImpl<_$RawDataColumnImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RawDataColumnImplToJson(this);
  }
}

abstract class _RawDataColumn implements RawDataColumn {
  const factory _RawDataColumn({
    required final String name,
    final String dtype,
  }) = _$RawDataColumnImpl;

  factory _RawDataColumn.fromJson(Map<String, dynamic> json) =
      _$RawDataColumnImpl.fromJson;

  @override
  String get name;
  @override
  String get dtype;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RawDataColumnImplCopyWith<_$RawDataColumnImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

GenerateFromDataRequest _$GenerateFromDataRequestFromJson(
    Map<String, dynamic> json) {
  return _GenerateFromDataRequest.fromJson(json);
}

/// @nodoc
mixin _$GenerateFromDataRequest {
  List<Map<String, dynamic>> get data => throw _privateConstructorUsedError;
  List<RawDataColumn> get columns => throw _privateConstructorUsedError;
  @JsonKey(name: 'chart_type')
  String get chartType => throw _privateConstructorUsedError;
  String get title => throw _privateConstructorUsedError;
  List<int> get size => throw _privateConstructorUsedError;
  String get category => throw _privateConstructorUsedError;
  @JsonKey(name: 'source_label')
  String get sourceLabel => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $GenerateFromDataRequestCopyWith<GenerateFromDataRequest> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $GenerateFromDataRequestCopyWith<$Res> {
  factory $GenerateFromDataRequestCopyWith(
    GenerateFromDataRequest value,
    $Res Function(GenerateFromDataRequest) then,
  ) = _$GenerateFromDataRequestCopyWithImpl<$Res, GenerateFromDataRequest>;
  @useResult
  $Res call({
    List<Map<String, dynamic>> data,
    List<RawDataColumn> columns,
    @JsonKey(name: 'chart_type') String chartType,
    String title,
    List<int> size,
    String category,
    @JsonKey(name: 'source_label') String sourceLabel,
  });
}

/// @nodoc
class _$GenerateFromDataRequestCopyWithImpl<$Res,
        $Val extends GenerateFromDataRequest>
    implements $GenerateFromDataRequestCopyWith<$Res> {
  _$GenerateFromDataRequestCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? data = null,
    Object? columns = null,
    Object? chartType = null,
    Object? title = null,
    Object? size = null,
    Object? category = null,
    Object? sourceLabel = null,
  }) {
    return _then(
      _value.copyWith(
            data: null == data
                ? _value.data
                : data as List<Map<String, dynamic>>,
            columns: null == columns
                ? _value.columns
                : columns as List<RawDataColumn>,
            chartType:
                null == chartType ? _value.chartType : chartType as String,
            title: null == title ? _value.title : title as String,
            size: null == size ? _value.size : size as List<int>,
            category: null == category ? _value.category : category as String,
            sourceLabel: null == sourceLabel
                ? _value.sourceLabel
                : sourceLabel as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$GenerateFromDataRequestImplCopyWith<$Res>
    implements $GenerateFromDataRequestCopyWith<$Res> {
  factory _$$GenerateFromDataRequestImplCopyWith(
    _$GenerateFromDataRequestImpl value,
    $Res Function(_$GenerateFromDataRequestImpl) then,
  ) = __$$GenerateFromDataRequestImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    List<Map<String, dynamic>> data,
    List<RawDataColumn> columns,
    @JsonKey(name: 'chart_type') String chartType,
    String title,
    List<int> size,
    String category,
    @JsonKey(name: 'source_label') String sourceLabel,
  });
}

/// @nodoc
class __$$GenerateFromDataRequestImplCopyWithImpl<$Res>
    extends _$GenerateFromDataRequestCopyWithImpl<$Res,
        _$GenerateFromDataRequestImpl>
    implements _$$GenerateFromDataRequestImplCopyWith<$Res> {
  __$$GenerateFromDataRequestImplCopyWithImpl(
    _$GenerateFromDataRequestImpl _value,
    $Res Function(_$GenerateFromDataRequestImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? data = null,
    Object? columns = null,
    Object? chartType = null,
    Object? title = null,
    Object? size = null,
    Object? category = null,
    Object? sourceLabel = null,
  }) {
    return _then(
      _$GenerateFromDataRequestImpl(
        data: null == data
            ? _value._data
            : data as List<Map<String, dynamic>>,
        columns: null == columns
            ? _value._columns
            : columns as List<RawDataColumn>,
        chartType:
            null == chartType ? _value.chartType : chartType as String,
        title: null == title ? _value.title : title as String,
        size: null == size ? _value._size : size as List<int>,
        category: null == category ? _value.category : category as String,
        sourceLabel: null == sourceLabel
            ? _value.sourceLabel
            : sourceLabel as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$GenerateFromDataRequestImpl implements _GenerateFromDataRequest {
  const _$GenerateFromDataRequestImpl({
    required final List<Map<String, dynamic>> data,
    required final List<RawDataColumn> columns,
    @JsonKey(name: 'chart_type') required this.chartType,
    required this.title,
    final List<int> size = const <int>[1200, 900],
    required this.category,
    @JsonKey(name: 'source_label') this.sourceLabel = 'custom',
  })  : _data = data,
        _columns = columns,
        _size = size;

  factory _$GenerateFromDataRequestImpl.fromJson(Map<String, dynamic> json) =>
      _$$GenerateFromDataRequestImplFromJson(json);

  final List<Map<String, dynamic>> _data;
  @override
  List<Map<String, dynamic>> get data {
    return List.unmodifiable(_data);
  }

  final List<RawDataColumn> _columns;
  @override
  List<RawDataColumn> get columns {
    return List.unmodifiable(_columns);
  }

  @override
  @JsonKey(name: 'chart_type')
  final String chartType;
  @override
  final String title;
  final List<int> _size;
  @override
  @JsonKey()
  List<int> get size {
    return List.unmodifiable(_size);
  }

  @override
  final String category;
  @override
  @JsonKey(name: 'source_label')
  final String sourceLabel;

  @override
  String toString() {
    return 'GenerateFromDataRequest(data: $data, columns: $columns, chartType: $chartType, title: $title, size: $size, category: $category, sourceLabel: $sourceLabel)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$GenerateFromDataRequestImpl &&
            const DeepCollectionEquality().equals(other._data, _data) &&
            const DeepCollectionEquality().equals(other._columns, _columns) &&
            (identical(other.chartType, chartType) ||
                other.chartType == chartType) &&
            (identical(other.title, title) || other.title == title) &&
            const DeepCollectionEquality().equals(other._size, _size) &&
            (identical(other.category, category) ||
                other.category == category) &&
            (identical(other.sourceLabel, sourceLabel) ||
                other.sourceLabel == sourceLabel));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
        runtimeType,
        const DeepCollectionEquality().hash(_data),
        const DeepCollectionEquality().hash(_columns),
        chartType,
        title,
        const DeepCollectionEquality().hash(_size),
        category,
        sourceLabel,
      );

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$GenerateFromDataRequestImplCopyWith<_$GenerateFromDataRequestImpl>
      get copyWith => __$$GenerateFromDataRequestImplCopyWithImpl<
          _$GenerateFromDataRequestImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$GenerateFromDataRequestImplToJson(this);
  }
}

abstract class _GenerateFromDataRequest implements GenerateFromDataRequest {
  const factory _GenerateFromDataRequest({
    required final List<Map<String, dynamic>> data,
    required final List<RawDataColumn> columns,
    @JsonKey(name: 'chart_type') required final String chartType,
    required final String title,
    final List<int> size,
    required final String category,
    @JsonKey(name: 'source_label') final String sourceLabel,
  }) = _$GenerateFromDataRequestImpl;

  factory _GenerateFromDataRequest.fromJson(Map<String, dynamic> json) =
      _$GenerateFromDataRequestImpl.fromJson;

  @override
  List<Map<String, dynamic>> get data;
  @override
  List<RawDataColumn> get columns;
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
  @JsonKey(name: 'source_label')
  String get sourceLabel;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$GenerateFromDataRequestImplCopyWith<_$GenerateFromDataRequestImpl>
      get copyWith => throw _privateConstructorUsedError;
}
