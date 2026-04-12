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

ColumnSchema _$ColumnSchemaFromJson(Map<String, dynamic> json) {
  return _ColumnSchema.fromJson(json);
}

/// @nodoc
mixin _$ColumnSchema {
  String get name => throw _privateConstructorUsedError;
  String get dtype => throw _privateConstructorUsedError;

  /// Serializes this ColumnSchema to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of ColumnSchema
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $ColumnSchemaCopyWith<ColumnSchema> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $ColumnSchemaCopyWith<$Res> {
  factory $ColumnSchemaCopyWith(
    ColumnSchema value,
    $Res Function(ColumnSchema) then,
  ) = _$ColumnSchemaCopyWithImpl<$Res, ColumnSchema>;
  @useResult
  $Res call({String name, String dtype});
}

/// @nodoc
class _$ColumnSchemaCopyWithImpl<$Res, $Val extends ColumnSchema>
    implements $ColumnSchemaCopyWith<$Res> {
  _$ColumnSchemaCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of ColumnSchema
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? name = null,
    Object? dtype = null,
  }) {
    return _then(
      _value.copyWith(
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            dtype: null == dtype
                ? _value.dtype
                : dtype // ignore: cast_nullable_to_non_nullable
                      as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$ColumnSchemaImplCopyWith<$Res>
    implements $ColumnSchemaCopyWith<$Res> {
  factory _$$ColumnSchemaImplCopyWith(
    _$ColumnSchemaImpl value,
    $Res Function(_$ColumnSchemaImpl) then,
  ) = __$$ColumnSchemaImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String name, String dtype});
}

/// @nodoc
class __$$ColumnSchemaImplCopyWithImpl<$Res>
    extends _$ColumnSchemaCopyWithImpl<$Res, _$ColumnSchemaImpl>
    implements _$$ColumnSchemaImplCopyWith<$Res> {
  __$$ColumnSchemaImplCopyWithImpl(
    _$ColumnSchemaImpl _value,
    $Res Function(_$ColumnSchemaImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of ColumnSchema
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? name = null,
    Object? dtype = null,
  }) {
    return _then(
      _$ColumnSchemaImpl(
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        dtype: null == dtype
            ? _value.dtype
            : dtype // ignore: cast_nullable_to_non_nullable
                  as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$ColumnSchemaImpl implements _ColumnSchema {
  const _$ColumnSchemaImpl({required this.name, required this.dtype});

  factory _$ColumnSchemaImpl.fromJson(Map<String, dynamic> json) =>
      _$$ColumnSchemaImplFromJson(json);

  @override
  final String name;
  @override
  final String dtype;

  @override
  String toString() {
    return 'ColumnSchema(name: $name, dtype: $dtype)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$ColumnSchemaImpl &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.dtype, dtype) || other.dtype == dtype));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, name, dtype);

  /// Create a copy of ColumnSchema
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$ColumnSchemaImplCopyWith<_$ColumnSchemaImpl> get copyWith =>
      __$$ColumnSchemaImplCopyWithImpl<_$ColumnSchemaImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$ColumnSchemaImplToJson(this);
  }
}

abstract class _ColumnSchema implements ColumnSchema {
  const factory _ColumnSchema({
    required final String name,
    required final String dtype,
  }) = _$ColumnSchemaImpl;

  factory _ColumnSchema.fromJson(Map<String, dynamic> json) =
      _$ColumnSchemaImpl.fromJson;

  @override
  String get name;
  @override
  String get dtype;

  /// Create a copy of ColumnSchema
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$ColumnSchemaImplCopyWith<_$ColumnSchemaImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

DataPreviewResponse _$DataPreviewResponseFromJson(Map<String, dynamic> json) {
  return _DataPreviewResponse.fromJson(json);
}

/// @nodoc
mixin _$DataPreviewResponse {
  List<ColumnSchema> get columns => throw _privateConstructorUsedError;
  List<Map<String, dynamic>> get rows => throw _privateConstructorUsedError;
  @JsonKey(name: 'total_rows')
  int get totalRows => throw _privateConstructorUsedError;
  @JsonKey(name: 'returned_rows')
  int get returnedRows => throw _privateConstructorUsedError;

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
    List<ColumnSchema> columns,
    List<Map<String, dynamic>> rows,
    @JsonKey(name: 'total_rows') int totalRows,
    @JsonKey(name: 'returned_rows') int returnedRows,
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
    Object? columns = null,
    Object? rows = null,
    Object? totalRows = null,
    Object? returnedRows = null,
  }) {
    return _then(
      _value.copyWith(
            columns: null == columns
                ? _value.columns
                : columns // ignore: cast_nullable_to_non_nullable
                      as List<ColumnSchema>,
            rows: null == rows
                ? _value.rows
                : rows // ignore: cast_nullable_to_non_nullable
                      as List<Map<String, dynamic>>,
            totalRows: null == totalRows
                ? _value.totalRows
                : totalRows // ignore: cast_nullable_to_non_nullable
                      as int,
            returnedRows: null == returnedRows
                ? _value.returnedRows
                : returnedRows // ignore: cast_nullable_to_non_nullable
                      as int,
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
    List<ColumnSchema> columns,
    List<Map<String, dynamic>> rows,
    @JsonKey(name: 'total_rows') int totalRows,
    @JsonKey(name: 'returned_rows') int returnedRows,
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
    Object? columns = null,
    Object? rows = null,
    Object? totalRows = null,
    Object? returnedRows = null,
  }) {
    return _then(
      _$DataPreviewResponseImpl(
        columns: null == columns
            ? _value._columns
            : columns // ignore: cast_nullable_to_non_nullable
                  as List<ColumnSchema>,
        rows: null == rows
            ? _value._rows
            : rows // ignore: cast_nullable_to_non_nullable
                  as List<Map<String, dynamic>>,
        totalRows: null == totalRows
            ? _value.totalRows
            : totalRows // ignore: cast_nullable_to_non_nullable
                  as int,
        returnedRows: null == returnedRows
            ? _value.returnedRows
            : returnedRows // ignore: cast_nullable_to_non_nullable
                  as int,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$DataPreviewResponseImpl implements _DataPreviewResponse {
  const _$DataPreviewResponseImpl({
    required final List<ColumnSchema> columns,
    required final List<Map<String, dynamic>> rows,
    @JsonKey(name: 'total_rows') required this.totalRows,
    @JsonKey(name: 'returned_rows') required this.returnedRows,
  })  : _columns = columns,
        _rows = rows;

  factory _$DataPreviewResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$DataPreviewResponseImplFromJson(json);

  final List<ColumnSchema> _columns;
  @override
  List<ColumnSchema> get columns {
    if (_columns is EqualUnmodifiableListView) return _columns;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_columns);
  }

  final List<Map<String, dynamic>> _rows;
  @override
  List<Map<String, dynamic>> get rows {
    if (_rows is EqualUnmodifiableListView) return _rows;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_rows);
  }

  @override
  @JsonKey(name: 'total_rows')
  final int totalRows;
  @override
  @JsonKey(name: 'returned_rows')
  final int returnedRows;

  @override
  String toString() {
    return 'DataPreviewResponse(columns: $columns, rows: $rows, totalRows: $totalRows, returnedRows: $returnedRows)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$DataPreviewResponseImpl &&
            const DeepCollectionEquality().equals(other._columns, _columns) &&
            const DeepCollectionEquality().equals(other._rows, _rows) &&
            (identical(other.totalRows, totalRows) ||
                other.totalRows == totalRows) &&
            (identical(other.returnedRows, returnedRows) ||
                other.returnedRows == returnedRows));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    const DeepCollectionEquality().hash(_columns),
    const DeepCollectionEquality().hash(_rows),
    totalRows,
    returnedRows,
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
    required final List<ColumnSchema> columns,
    required final List<Map<String, dynamic>> rows,
    @JsonKey(name: 'total_rows') required final int totalRows,
    @JsonKey(name: 'returned_rows') required final int returnedRows,
  }) = _$DataPreviewResponseImpl;

  factory _DataPreviewResponse.fromJson(Map<String, dynamic> json) =
      _$DataPreviewResponseImpl.fromJson;

  @override
  List<ColumnSchema> get columns;
  @override
  List<Map<String, dynamic>> get rows;
  @override
  @JsonKey(name: 'total_rows')
  int get totalRows;
  @override
  @JsonKey(name: 'returned_rows')
  int get returnedRows;

  /// Create a copy of DataPreviewResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$DataPreviewResponseImplCopyWith<_$DataPreviewResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
