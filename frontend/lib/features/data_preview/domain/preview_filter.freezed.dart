// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'preview_filter.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

/// @nodoc
mixin _$PreviewFilter {
  String? get geoFilter => throw _privateConstructorUsedError;
  String? get dateFromFilter => throw _privateConstructorUsedError;
  String? get dateToFilter => throw _privateConstructorUsedError;
  String? get searchText => throw _privateConstructorUsedError;

  /// Create a copy of PreviewFilter
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $PreviewFilterCopyWith<PreviewFilter> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $PreviewFilterCopyWith<$Res> {
  factory $PreviewFilterCopyWith(
    PreviewFilter value,
    $Res Function(PreviewFilter) then,
  ) = _$PreviewFilterCopyWithImpl<$Res, PreviewFilter>;
  @useResult
  $Res call({
    String? geoFilter,
    String? dateFromFilter,
    String? dateToFilter,
    String? searchText,
  });
}

/// @nodoc
class _$PreviewFilterCopyWithImpl<$Res, $Val extends PreviewFilter>
    implements $PreviewFilterCopyWith<$Res> {
  _$PreviewFilterCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of PreviewFilter
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? geoFilter = freezed,
    Object? dateFromFilter = freezed,
    Object? dateToFilter = freezed,
    Object? searchText = freezed,
  }) {
    return _then(
      _value.copyWith(
            geoFilter: freezed == geoFilter
                ? _value.geoFilter
                : geoFilter // ignore: cast_nullable_to_non_nullable
                      as String?,
            dateFromFilter: freezed == dateFromFilter
                ? _value.dateFromFilter
                : dateFromFilter // ignore: cast_nullable_to_non_nullable
                      as String?,
            dateToFilter: freezed == dateToFilter
                ? _value.dateToFilter
                : dateToFilter // ignore: cast_nullable_to_non_nullable
                      as String?,
            searchText: freezed == searchText
                ? _value.searchText
                : searchText // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$PreviewFilterImplCopyWith<$Res>
    implements $PreviewFilterCopyWith<$Res> {
  factory _$$PreviewFilterImplCopyWith(
    _$PreviewFilterImpl value,
    $Res Function(_$PreviewFilterImpl) then,
  ) = __$$PreviewFilterImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    String? geoFilter,
    String? dateFromFilter,
    String? dateToFilter,
    String? searchText,
  });
}

/// @nodoc
class __$$PreviewFilterImplCopyWithImpl<$Res>
    extends _$PreviewFilterCopyWithImpl<$Res, _$PreviewFilterImpl>
    implements _$$PreviewFilterImplCopyWith<$Res> {
  __$$PreviewFilterImplCopyWithImpl(
    _$PreviewFilterImpl _value,
    $Res Function(_$PreviewFilterImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of PreviewFilter
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? geoFilter = freezed,
    Object? dateFromFilter = freezed,
    Object? dateToFilter = freezed,
    Object? searchText = freezed,
  }) {
    return _then(
      _$PreviewFilterImpl(
        geoFilter: freezed == geoFilter
            ? _value.geoFilter
            : geoFilter // ignore: cast_nullable_to_non_nullable
                  as String?,
        dateFromFilter: freezed == dateFromFilter
            ? _value.dateFromFilter
            : dateFromFilter // ignore: cast_nullable_to_non_nullable
                  as String?,
        dateToFilter: freezed == dateToFilter
            ? _value.dateToFilter
            : dateToFilter // ignore: cast_nullable_to_non_nullable
                  as String?,
        searchText: freezed == searchText
            ? _value.searchText
            : searchText // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc

class _$PreviewFilterImpl implements _PreviewFilter {
  const _$PreviewFilterImpl({
    this.geoFilter,
    this.dateFromFilter,
    this.dateToFilter,
    this.searchText,
  });

  @override
  final String? geoFilter;
  @override
  final String? dateFromFilter;
  @override
  final String? dateToFilter;
  @override
  final String? searchText;

  @override
  String toString() {
    return 'PreviewFilter(geoFilter: $geoFilter, dateFromFilter: $dateFromFilter, dateToFilter: $dateToFilter, searchText: $searchText)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$PreviewFilterImpl &&
            (identical(other.geoFilter, geoFilter) ||
                other.geoFilter == geoFilter) &&
            (identical(other.dateFromFilter, dateFromFilter) ||
                other.dateFromFilter == dateFromFilter) &&
            (identical(other.dateToFilter, dateToFilter) ||
                other.dateToFilter == dateToFilter) &&
            (identical(other.searchText, searchText) ||
                other.searchText == searchText));
  }

  @override
  int get hashCode => Object.hash(
    runtimeType,
    geoFilter,
    dateFromFilter,
    dateToFilter,
    searchText,
  );

  /// Create a copy of PreviewFilter
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$PreviewFilterImplCopyWith<_$PreviewFilterImpl> get copyWith =>
      __$$PreviewFilterImplCopyWithImpl<_$PreviewFilterImpl>(
        this,
        _$identity,
      );
}

abstract class _PreviewFilter implements PreviewFilter {
  const factory _PreviewFilter({
    final String? geoFilter,
    final String? dateFromFilter,
    final String? dateToFilter,
    final String? searchText,
  }) = _$PreviewFilterImpl;

  @override
  String? get geoFilter;
  @override
  String? get dateFromFilter;
  @override
  String? get dateToFilter;
  @override
  String? get searchText;

  /// Create a copy of PreviewFilter
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$PreviewFilterImplCopyWith<_$PreviewFilterImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
