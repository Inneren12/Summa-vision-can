// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'cube_catalog_entry.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

CubeCatalogEntry _$CubeCatalogEntryFromJson(Map<String, dynamic> json) {
  return _CubeCatalogEntry.fromJson(json);
}

/// @nodoc
mixin _$CubeCatalogEntry {
  @JsonKey(name: 'product_id')
  String get productId => throw _privateConstructorUsedError;
  @JsonKey(name: 'title_en')
  String get titleEn => throw _privateConstructorUsedError;
  @JsonKey(name: 'title_fr')
  String? get titleFr => throw _privateConstructorUsedError;
  @JsonKey(name: 'subject_code')
  String get subjectCode => throw _privateConstructorUsedError;
  @JsonKey(name: 'subject_en')
  String get subjectEn => throw _privateConstructorUsedError;
  @JsonKey(name: 'survey_en')
  String? get surveyEn => throw _privateConstructorUsedError;
  String get frequency => throw _privateConstructorUsedError;
  @JsonKey(name: 'start_date')
  String? get startDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'end_date')
  String? get endDate => throw _privateConstructorUsedError;
  @JsonKey(name: 'archive_status')
  bool get archiveStatus => throw _privateConstructorUsedError;

  /// Serializes this CubeCatalogEntry to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CubeCatalogEntry
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CubeCatalogEntryCopyWith<CubeCatalogEntry> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CubeCatalogEntryCopyWith<$Res> {
  factory $CubeCatalogEntryCopyWith(
    CubeCatalogEntry value,
    $Res Function(CubeCatalogEntry) then,
  ) = _$CubeCatalogEntryCopyWithImpl<$Res, CubeCatalogEntry>;
  @useResult
  $Res call({
    @JsonKey(name: 'product_id') String productId,
    @JsonKey(name: 'title_en') String titleEn,
    @JsonKey(name: 'title_fr') String? titleFr,
    @JsonKey(name: 'subject_code') String subjectCode,
    @JsonKey(name: 'subject_en') String subjectEn,
    @JsonKey(name: 'survey_en') String? surveyEn,
    String frequency,
    @JsonKey(name: 'start_date') String? startDate,
    @JsonKey(name: 'end_date') String? endDate,
    @JsonKey(name: 'archive_status') bool archiveStatus,
  });
}

/// @nodoc
class _$CubeCatalogEntryCopyWithImpl<$Res, $Val extends CubeCatalogEntry>
    implements $CubeCatalogEntryCopyWith<$Res> {
  _$CubeCatalogEntryCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CubeCatalogEntry
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? productId = null,
    Object? titleEn = null,
    Object? titleFr = freezed,
    Object? subjectCode = null,
    Object? subjectEn = null,
    Object? surveyEn = freezed,
    Object? frequency = null,
    Object? startDate = freezed,
    Object? endDate = freezed,
    Object? archiveStatus = null,
  }) {
    return _then(
      _value.copyWith(
            productId: null == productId
                ? _value.productId
                : productId // ignore: cast_nullable_to_non_nullable
                      as String,
            titleEn: null == titleEn
                ? _value.titleEn
                : titleEn // ignore: cast_nullable_to_non_nullable
                      as String,
            titleFr: freezed == titleFr
                ? _value.titleFr
                : titleFr // ignore: cast_nullable_to_non_nullable
                      as String?,
            subjectCode: null == subjectCode
                ? _value.subjectCode
                : subjectCode // ignore: cast_nullable_to_non_nullable
                      as String,
            subjectEn: null == subjectEn
                ? _value.subjectEn
                : subjectEn // ignore: cast_nullable_to_non_nullable
                      as String,
            surveyEn: freezed == surveyEn
                ? _value.surveyEn
                : surveyEn // ignore: cast_nullable_to_non_nullable
                      as String?,
            frequency: null == frequency
                ? _value.frequency
                : frequency // ignore: cast_nullable_to_non_nullable
                      as String,
            startDate: freezed == startDate
                ? _value.startDate
                : startDate // ignore: cast_nullable_to_non_nullable
                      as String?,
            endDate: freezed == endDate
                ? _value.endDate
                : endDate // ignore: cast_nullable_to_non_nullable
                      as String?,
            archiveStatus: null == archiveStatus
                ? _value.archiveStatus
                : archiveStatus // ignore: cast_nullable_to_non_nullable
                      as bool,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$CubeCatalogEntryImplCopyWith<$Res>
    implements $CubeCatalogEntryCopyWith<$Res> {
  factory _$$CubeCatalogEntryImplCopyWith(
    _$CubeCatalogEntryImpl value,
    $Res Function(_$CubeCatalogEntryImpl) then,
  ) = __$$CubeCatalogEntryImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'product_id') String productId,
    @JsonKey(name: 'title_en') String titleEn,
    @JsonKey(name: 'title_fr') String? titleFr,
    @JsonKey(name: 'subject_code') String subjectCode,
    @JsonKey(name: 'subject_en') String subjectEn,
    @JsonKey(name: 'survey_en') String? surveyEn,
    String frequency,
    @JsonKey(name: 'start_date') String? startDate,
    @JsonKey(name: 'end_date') String? endDate,
    @JsonKey(name: 'archive_status') bool archiveStatus,
  });
}

/// @nodoc
class __$$CubeCatalogEntryImplCopyWithImpl<$Res>
    extends _$CubeCatalogEntryCopyWithImpl<$Res, _$CubeCatalogEntryImpl>
    implements _$$CubeCatalogEntryImplCopyWith<$Res> {
  __$$CubeCatalogEntryImplCopyWithImpl(
    _$CubeCatalogEntryImpl _value,
    $Res Function(_$CubeCatalogEntryImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of CubeCatalogEntry
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? productId = null,
    Object? titleEn = null,
    Object? titleFr = freezed,
    Object? subjectCode = null,
    Object? subjectEn = null,
    Object? surveyEn = freezed,
    Object? frequency = null,
    Object? startDate = freezed,
    Object? endDate = freezed,
    Object? archiveStatus = null,
  }) {
    return _then(
      _$CubeCatalogEntryImpl(
        productId: null == productId
            ? _value.productId
            : productId // ignore: cast_nullable_to_non_nullable
                  as String,
        titleEn: null == titleEn
            ? _value.titleEn
            : titleEn // ignore: cast_nullable_to_non_nullable
                  as String,
        titleFr: freezed == titleFr
            ? _value.titleFr
            : titleFr // ignore: cast_nullable_to_non_nullable
                  as String?,
        subjectCode: null == subjectCode
            ? _value.subjectCode
            : subjectCode // ignore: cast_nullable_to_non_nullable
                  as String,
        subjectEn: null == subjectEn
            ? _value.subjectEn
            : subjectEn // ignore: cast_nullable_to_non_nullable
                  as String,
        surveyEn: freezed == surveyEn
            ? _value.surveyEn
            : surveyEn // ignore: cast_nullable_to_non_nullable
                  as String?,
        frequency: null == frequency
            ? _value.frequency
            : frequency // ignore: cast_nullable_to_non_nullable
                  as String,
        startDate: freezed == startDate
            ? _value.startDate
            : startDate // ignore: cast_nullable_to_non_nullable
                  as String?,
        endDate: freezed == endDate
            ? _value.endDate
            : endDate // ignore: cast_nullable_to_non_nullable
                  as String?,
        archiveStatus: null == archiveStatus
            ? _value.archiveStatus
            : archiveStatus // ignore: cast_nullable_to_non_nullable
                  as bool,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$CubeCatalogEntryImpl implements _CubeCatalogEntry {
  const _$CubeCatalogEntryImpl({
    @JsonKey(name: 'product_id') required this.productId,
    @JsonKey(name: 'title_en') required this.titleEn,
    @JsonKey(name: 'title_fr') this.titleFr,
    @JsonKey(name: 'subject_code') required this.subjectCode,
    @JsonKey(name: 'subject_en') required this.subjectEn,
    @JsonKey(name: 'survey_en') this.surveyEn,
    required this.frequency,
    @JsonKey(name: 'start_date') this.startDate,
    @JsonKey(name: 'end_date') this.endDate,
    @JsonKey(name: 'archive_status') this.archiveStatus = false,
  });

  factory _$CubeCatalogEntryImpl.fromJson(Map<String, dynamic> json) =>
      _$$CubeCatalogEntryImplFromJson(json);

  @override
  @JsonKey(name: 'product_id')
  final String productId;
  @override
  @JsonKey(name: 'title_en')
  final String titleEn;
  @override
  @JsonKey(name: 'title_fr')
  final String? titleFr;
  @override
  @JsonKey(name: 'subject_code')
  final String subjectCode;
  @override
  @JsonKey(name: 'subject_en')
  final String subjectEn;
  @override
  @JsonKey(name: 'survey_en')
  final String? surveyEn;
  @override
  final String frequency;
  @override
  @JsonKey(name: 'start_date')
  final String? startDate;
  @override
  @JsonKey(name: 'end_date')
  final String? endDate;
  @override
  @JsonKey(name: 'archive_status')
  final bool archiveStatus;

  @override
  String toString() {
    return 'CubeCatalogEntry(productId: $productId, titleEn: $titleEn, titleFr: $titleFr, subjectCode: $subjectCode, subjectEn: $subjectEn, surveyEn: $surveyEn, frequency: $frequency, startDate: $startDate, endDate: $endDate, archiveStatus: $archiveStatus)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CubeCatalogEntryImpl &&
            (identical(other.productId, productId) ||
                other.productId == productId) &&
            (identical(other.titleEn, titleEn) || other.titleEn == titleEn) &&
            (identical(other.titleFr, titleFr) || other.titleFr == titleFr) &&
            (identical(other.subjectCode, subjectCode) ||
                other.subjectCode == subjectCode) &&
            (identical(other.subjectEn, subjectEn) ||
                other.subjectEn == subjectEn) &&
            (identical(other.surveyEn, surveyEn) ||
                other.surveyEn == surveyEn) &&
            (identical(other.frequency, frequency) ||
                other.frequency == frequency) &&
            (identical(other.startDate, startDate) ||
                other.startDate == startDate) &&
            (identical(other.endDate, endDate) || other.endDate == endDate) &&
            (identical(other.archiveStatus, archiveStatus) ||
                other.archiveStatus == archiveStatus));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    productId,
    titleEn,
    titleFr,
    subjectCode,
    subjectEn,
    surveyEn,
    frequency,
    startDate,
    endDate,
    archiveStatus,
  );

  /// Create a copy of CubeCatalogEntry
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CubeCatalogEntryImplCopyWith<_$CubeCatalogEntryImpl> get copyWith =>
      __$$CubeCatalogEntryImplCopyWithImpl<_$CubeCatalogEntryImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$CubeCatalogEntryImplToJson(this);
  }
}

abstract class _CubeCatalogEntry implements CubeCatalogEntry {
  const factory _CubeCatalogEntry({
    @JsonKey(name: 'product_id') required final String productId,
    @JsonKey(name: 'title_en') required final String titleEn,
    @JsonKey(name: 'title_fr') final String? titleFr,
    @JsonKey(name: 'subject_code') required final String subjectCode,
    @JsonKey(name: 'subject_en') required final String subjectEn,
    @JsonKey(name: 'survey_en') final String? surveyEn,
    required final String frequency,
    @JsonKey(name: 'start_date') final String? startDate,
    @JsonKey(name: 'end_date') final String? endDate,
    @JsonKey(name: 'archive_status') final bool archiveStatus,
  }) = _$CubeCatalogEntryImpl;

  factory _CubeCatalogEntry.fromJson(Map<String, dynamic> json) =
      _$CubeCatalogEntryImpl.fromJson;

  @override
  @JsonKey(name: 'product_id')
  String get productId;
  @override
  @JsonKey(name: 'title_en')
  String get titleEn;
  @override
  @JsonKey(name: 'title_fr')
  String? get titleFr;
  @override
  @JsonKey(name: 'subject_code')
  String get subjectCode;
  @override
  @JsonKey(name: 'subject_en')
  String get subjectEn;
  @override
  @JsonKey(name: 'survey_en')
  String? get surveyEn;
  @override
  String get frequency;
  @override
  @JsonKey(name: 'start_date')
  String? get startDate;
  @override
  @JsonKey(name: 'end_date')
  String? get endDate;
  @override
  @JsonKey(name: 'archive_status')
  bool get archiveStatus;

  /// Create a copy of CubeCatalogEntry
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CubeCatalogEntryImplCopyWith<_$CubeCatalogEntryImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
