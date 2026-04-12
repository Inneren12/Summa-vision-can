// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'cube_search_response.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

CubeSearchResponse _$CubeSearchResponseFromJson(Map<String, dynamic> json) {
  return _CubeSearchResponse.fromJson(json);
}

/// @nodoc
mixin _$CubeSearchResponse {
  List<CubeCatalogEntry> get items => throw _privateConstructorUsedError;
  int get total => throw _privateConstructorUsedError;

  /// Serializes this CubeSearchResponse to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CubeSearchResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CubeSearchResponseCopyWith<CubeSearchResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CubeSearchResponseCopyWith<$Res> {
  factory $CubeSearchResponseCopyWith(
    CubeSearchResponse value,
    $Res Function(CubeSearchResponse) then,
  ) = _$CubeSearchResponseCopyWithImpl<$Res, CubeSearchResponse>;
  @useResult
  $Res call({List<CubeCatalogEntry> items, int total});
}

/// @nodoc
class _$CubeSearchResponseCopyWithImpl<$Res, $Val extends CubeSearchResponse>
    implements $CubeSearchResponseCopyWith<$Res> {
  _$CubeSearchResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CubeSearchResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
  }) {
    return _then(
      _value.copyWith(
            items: null == items
                ? _value.items
                : items // ignore: cast_nullable_to_non_nullable
                      as List<CubeCatalogEntry>,
            total: null == total
                ? _value.total
                : total // ignore: cast_nullable_to_non_nullable
                      as int,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$CubeSearchResponseImplCopyWith<$Res>
    implements $CubeSearchResponseCopyWith<$Res> {
  factory _$$CubeSearchResponseImplCopyWith(
    _$CubeSearchResponseImpl value,
    $Res Function(_$CubeSearchResponseImpl) then,
  ) = __$$CubeSearchResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({List<CubeCatalogEntry> items, int total});
}

/// @nodoc
class __$$CubeSearchResponseImplCopyWithImpl<$Res>
    extends _$CubeSearchResponseCopyWithImpl<$Res, _$CubeSearchResponseImpl>
    implements _$$CubeSearchResponseImplCopyWith<$Res> {
  __$$CubeSearchResponseImplCopyWithImpl(
    _$CubeSearchResponseImpl _value,
    $Res Function(_$CubeSearchResponseImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of CubeSearchResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? items = null,
    Object? total = null,
  }) {
    return _then(
      _$CubeSearchResponseImpl(
        items: null == items
            ? _value._items
            : items // ignore: cast_nullable_to_non_nullable
                  as List<CubeCatalogEntry>,
        total: null == total
            ? _value.total
            : total // ignore: cast_nullable_to_non_nullable
                  as int,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$CubeSearchResponseImpl implements _CubeSearchResponse {
  const _$CubeSearchResponseImpl({
    required final List<CubeCatalogEntry> items,
    required this.total,
  }) : _items = items;

  factory _$CubeSearchResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$CubeSearchResponseImplFromJson(json);

  final List<CubeCatalogEntry> _items;
  @override
  List<CubeCatalogEntry> get items {
    if (_items is EqualUnmodifiableListView) return _items;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_items);
  }

  @override
  final int total;

  @override
  String toString() {
    return 'CubeSearchResponse(items: $items, total: $total)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CubeSearchResponseImpl &&
            const DeepCollectionEquality().equals(other._items, _items) &&
            (identical(other.total, total) || other.total == total));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    const DeepCollectionEquality().hash(_items),
    total,
  );

  /// Create a copy of CubeSearchResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CubeSearchResponseImplCopyWith<_$CubeSearchResponseImpl> get copyWith =>
      __$$CubeSearchResponseImplCopyWithImpl<_$CubeSearchResponseImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$CubeSearchResponseImplToJson(this);
  }
}

abstract class _CubeSearchResponse implements CubeSearchResponse {
  const factory _CubeSearchResponse({
    required final List<CubeCatalogEntry> items,
    required final int total,
  }) = _$CubeSearchResponseImpl;

  factory _CubeSearchResponse.fromJson(Map<String, dynamic> json) =
      _$CubeSearchResponseImpl.fromJson;

  @override
  List<CubeCatalogEntry> get items;
  @override
  int get total;

  /// Create a copy of CubeSearchResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CubeSearchResponseImplCopyWith<_$CubeSearchResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
