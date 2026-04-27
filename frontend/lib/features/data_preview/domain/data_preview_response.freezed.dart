// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'data_preview_response.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

DataPreviewResponse _$DataPreviewResponseFromJson(Map<String, dynamic> json) {
  return _DataPreviewResponse.fromJson(json);
}

/// @nodoc
mixin _$DataPreviewResponse {
  @JsonKey(name: 'storage_key')
  String get storageKey => throw _privateConstructorUsedError;
  int get rows => throw _privateConstructorUsedError;
  int get columns => throw _privateConstructorUsedError;
  @JsonKey(name: 'column_names')
  List<String> get columnNames => throw _privateConstructorUsedError;
  List<Map<String, dynamic>> get data => throw _privateConstructorUsedError;
  @JsonKey(name: 'product_id')
  String? get productId => throw _privateConstructorUsedError;

  /// Serializes this DataPreviewResponse to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of DataPreviewResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $DataPreviewResponseCopyWith<DataPreviewResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $DataPreviewResponseCopyWith<$Res> {
  factory $DataPreviewResponseCopyWith(
    DataPreviewResponse value,
    $Res Function(DataPreviewResponse) then,
  ) = _$DataPreviewResponseCopyWithImpl<$Res, DataPreviewResponse>;
  @useResult
  $Res call({
    @JsonKey(name: 'storage_key') String storageKey,
    int rows,
    int columns,
    @JsonKey(name: 'column_names') List<String> columnNames,
    List<Map<String, dynamic>> data,
    @JsonKey(name: 'product_id') String? productId,
  });
}

/// @nodoc
class _$DataPreviewResponseCopyWithImpl<$Res,
        $Val extends DataPreviewResponse>
    implements $DataPreviewResponseCopyWith<$Res> {
  _$DataPreviewResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of DataPreviewResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? storageKey = null,
    Object? rows = null,
    Object? columns = null,
    Object? columnNames = null,
    Object? data = null,
    Object? productId = freezed,
  }) {
    return _then(
      _value.copyWith(
            storageKey: null == storageKey
                ? _value.storageKey
                : storageKey // ignore: cast_nullable_to_non_nullable
                      as String,
            rows: null == rows
                ? _value.rows
                : rows // ignore: cast_nullable_to_non_nullable
                      as int,
            columns: null == columns
                ? _value.columns
                : columns // ignore: cast_nullable_to_non_nullable
                      as int,
            columnNames: null == columnNames
                ? _value.columnNames
                : columnNames // ignore: cast_nullable_to_non_nullable
                      as List<String>,
            data: null == data
                ? _value.data
                : data // ignore: cast_nullable_to_non_nullable
                      as List<Map<String, dynamic>>,
            productId: freezed == productId
                ? _value.productId
                : productId // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$DataPreviewResponseImplCopyWith<$Res>
    implements $DataPreviewResponseCopyWith<$Res> {
  factory _$$DataPreviewResponseImplCopyWith(
    _$DataPreviewResponseImpl value,
    $Res Function(_$DataPreviewResponseImpl) then,
  ) = __$$DataPreviewResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'storage_key') String storageKey,
    int rows,
    int columns,
    @JsonKey(name: 'column_names') List<String> columnNames,
    List<Map<String, dynamic>> data,
    @JsonKey(name: 'product_id') String? productId,
  });
}

/// @nodoc
class __$$DataPreviewResponseImplCopyWithImpl<$Res>
    extends _$DataPreviewResponseCopyWithImpl<$Res, _$DataPreviewResponseImpl>
    implements _$$DataPreviewResponseImplCopyWith<$Res> {
  __$$DataPreviewResponseImplCopyWithImpl(
    _$DataPreviewResponseImpl _value,
    $Res Function(_$DataPreviewResponseImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of DataPreviewResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? storageKey = null,
    Object? rows = null,
    Object? columns = null,
    Object? columnNames = null,
    Object? data = null,
    Object? productId = freezed,
  }) {
    return _then(
      _$DataPreviewResponseImpl(
        storageKey: null == storageKey
            ? _value.storageKey
            : storageKey // ignore: cast_nullable_to_non_nullable
                  as String,
        rows: null == rows
            ? _value.rows
            : rows // ignore: cast_nullable_to_non_nullable
                  as int,
        columns: null == columns
            ? _value.columns
            : columns // ignore: cast_nullable_to_non_nullable
                  as int,
        columnNames: null == columnNames
            ? _value._columnNames
            : columnNames // ignore: cast_nullable_to_non_nullable
                  as List<String>,
        data: null == data
            ? _value._data
            : data // ignore: cast_nullable_to_non_nullable
                  as List<Map<String, dynamic>>,
        productId: freezed == productId
            ? _value.productId
            : productId // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$DataPreviewResponseImpl implements _DataPreviewResponse {
  const _$DataPreviewResponseImpl({
    @JsonKey(name: 'storage_key') required this.storageKey,
    required this.rows,
    required this.columns,
    @JsonKey(name: 'column_names') required final List<String> columnNames,
    required final List<Map<String, dynamic>> data,
    @JsonKey(name: 'product_id') this.productId,
  })  : _columnNames = columnNames,
        _data = data;

  factory _$DataPreviewResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$DataPreviewResponseImplFromJson(json);

  @override
  @JsonKey(name: 'storage_key')
  final String storageKey;
  @override
  final int rows;
  @override
  final int columns;

  final List<String> _columnNames;
  @override
  @JsonKey(name: 'column_names')
  List<String> get columnNames {
    if (_columnNames is EqualUnmodifiableListView) return _columnNames;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_columnNames);
  }

  final List<Map<String, dynamic>> _data;
  @override
  List<Map<String, dynamic>> get data {
    if (_data is EqualUnmodifiableListView) return _data;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_data);
  }

  @override
  @JsonKey(name: 'product_id')
  final String? productId;

  @override
  String toString() {
    return 'DataPreviewResponse(storageKey: $storageKey, rows: $rows, columns: $columns, columnNames: $columnNames, data: $data, productId: $productId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DataPreviewResponseImpl &&
            (identical(other.storageKey, storageKey) ||
                other.storageKey == storageKey) &&
            (identical(other.rows, rows) || other.rows == rows) &&
            (identical(other.columns, columns) || other.columns == columns) &&
            const DeepCollectionEquality()
                .equals(other._columnNames, _columnNames) &&
            const DeepCollectionEquality().equals(other._data, _data) &&
            (identical(other.productId, productId) ||
                other.productId == productId));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    storageKey,
    rows,
    columns,
    const DeepCollectionEquality().hash(_columnNames),
    const DeepCollectionEquality().hash(_data),
    productId,
  );

  /// Create a copy of DataPreviewResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$DataPreviewResponseImplCopyWith<_$DataPreviewResponseImpl> get copyWith =>
      __$$DataPreviewResponseImplCopyWithImpl<_$DataPreviewResponseImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$DataPreviewResponseImplToJson(this);
  }
}

abstract class _DataPreviewResponse implements DataPreviewResponse {
  const factory _DataPreviewResponse({
    @JsonKey(name: 'storage_key') required final String storageKey,
    required final int rows,
    required final int columns,
    @JsonKey(name: 'column_names') required final List<String> columnNames,
    required final List<Map<String, dynamic>> data,
    @JsonKey(name: 'product_id') final String? productId,
  }) = _$DataPreviewResponseImpl;

  factory _DataPreviewResponse.fromJson(Map<String, dynamic> json) =
      _$DataPreviewResponseImpl.fromJson;

  @override
  @JsonKey(name: 'storage_key')
  String get storageKey;
  @override
  int get rows;
  @override
  int get columns;
  @override
  @JsonKey(name: 'column_names')
  List<String> get columnNames;
  @override
  List<Map<String, dynamic>> get data;
  @override
  @JsonKey(name: 'product_id')
  String? get productId;

  /// Create a copy of DataPreviewResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DataPreviewResponseImplCopyWith<_$DataPreviewResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
