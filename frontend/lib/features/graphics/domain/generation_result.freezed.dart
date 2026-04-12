// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'generation_result.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

GenerationResult _$GenerationResultFromJson(Map<String, dynamic> json) {
  return _GenerationResult.fromJson(json);
}

/// @nodoc
mixin _$GenerationResult {
  @JsonKey(name: 'publication_id')
  int get publicationId => throw _privateConstructorUsedError;
  @JsonKey(name: 'cdn_url_lowres')
  String get cdnUrlLowres => throw _privateConstructorUsedError;
  @JsonKey(name: 's3_key_highres')
  String get s3KeyHighres => throw _privateConstructorUsedError;
  int get version => throw _privateConstructorUsedError;

  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  @JsonKey(includeFromJson: false, includeToJson: false)
  $GenerationResultCopyWith<GenerationResult> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $GenerationResultCopyWith<$Res> {
  factory $GenerationResultCopyWith(
    GenerationResult value,
    $Res Function(GenerationResult) then,
  ) = _$GenerationResultCopyWithImpl<$Res, GenerationResult>;
  @useResult
  $Res call({
    @JsonKey(name: 'publication_id') int publicationId,
    @JsonKey(name: 'cdn_url_lowres') String cdnUrlLowres,
    @JsonKey(name: 's3_key_highres') String s3KeyHighres,
    int version,
  });
}

/// @nodoc
class _$GenerationResultCopyWithImpl<$Res, $Val extends GenerationResult>
    implements $GenerationResultCopyWith<$Res> {
  _$GenerationResultCopyWithImpl(this._value, this._then);

  final $Val _value;
  final $Res Function($Val) _then;

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? publicationId = null,
    Object? cdnUrlLowres = null,
    Object? s3KeyHighres = null,
    Object? version = null,
  }) {
    return _then(
      _value.copyWith(
            publicationId: null == publicationId
                ? _value.publicationId
                : publicationId as int,
            cdnUrlLowres: null == cdnUrlLowres
                ? _value.cdnUrlLowres
                : cdnUrlLowres as String,
            s3KeyHighres: null == s3KeyHighres
                ? _value.s3KeyHighres
                : s3KeyHighres as String,
            version:
                null == version ? _value.version : version as int,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$GenerationResultImplCopyWith<$Res>
    implements $GenerationResultCopyWith<$Res> {
  factory _$$GenerationResultImplCopyWith(
    _$GenerationResultImpl value,
    $Res Function(_$GenerationResultImpl) then,
  ) = __$$GenerationResultImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'publication_id') int publicationId,
    @JsonKey(name: 'cdn_url_lowres') String cdnUrlLowres,
    @JsonKey(name: 's3_key_highres') String s3KeyHighres,
    int version,
  });
}

/// @nodoc
class __$$GenerationResultImplCopyWithImpl<$Res>
    extends _$GenerationResultCopyWithImpl<$Res, _$GenerationResultImpl>
    implements _$$GenerationResultImplCopyWith<$Res> {
  __$$GenerationResultImplCopyWithImpl(
    _$GenerationResultImpl _value,
    $Res Function(_$GenerationResultImpl) _then,
  ) : super(_value, _then);

  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? publicationId = null,
    Object? cdnUrlLowres = null,
    Object? s3KeyHighres = null,
    Object? version = null,
  }) {
    return _then(
      _$GenerationResultImpl(
        publicationId: null == publicationId
            ? _value.publicationId
            : publicationId as int,
        cdnUrlLowres: null == cdnUrlLowres
            ? _value.cdnUrlLowres
            : cdnUrlLowres as String,
        s3KeyHighres: null == s3KeyHighres
            ? _value.s3KeyHighres
            : s3KeyHighres as String,
        version:
            null == version ? _value.version : version as int,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$GenerationResultImpl implements _GenerationResult {
  const _$GenerationResultImpl({
    @JsonKey(name: 'publication_id') required this.publicationId,
    @JsonKey(name: 'cdn_url_lowres') required this.cdnUrlLowres,
    @JsonKey(name: 's3_key_highres') required this.s3KeyHighres,
    required this.version,
  });

  factory _$GenerationResultImpl.fromJson(Map<String, dynamic> json) =>
      _$$GenerationResultImplFromJson(json);

  @override
  @JsonKey(name: 'publication_id')
  final int publicationId;
  @override
  @JsonKey(name: 'cdn_url_lowres')
  final String cdnUrlLowres;
  @override
  @JsonKey(name: 's3_key_highres')
  final String s3KeyHighres;
  @override
  final int version;

  @override
  String toString() {
    return 'GenerationResult(publicationId: $publicationId, cdnUrlLowres: $cdnUrlLowres, s3KeyHighres: $s3KeyHighres, version: $version)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$GenerationResultImpl &&
            (identical(other.publicationId, publicationId) ||
                other.publicationId == publicationId) &&
            (identical(other.cdnUrlLowres, cdnUrlLowres) ||
                other.cdnUrlLowres == cdnUrlLowres) &&
            (identical(other.s3KeyHighres, s3KeyHighres) ||
                other.s3KeyHighres == s3KeyHighres) &&
            (identical(other.version, version) ||
                other.version == version));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode =>
      Object.hash(runtimeType, publicationId, cdnUrlLowres, s3KeyHighres, version);

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$GenerationResultImplCopyWith<_$GenerationResultImpl> get copyWith =>
      __$$GenerationResultImplCopyWithImpl<_$GenerationResultImpl>(
          this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$GenerationResultImplToJson(this);
  }
}

abstract class _GenerationResult implements GenerationResult {
  const factory _GenerationResult({
    @JsonKey(name: 'publication_id') required final int publicationId,
    @JsonKey(name: 'cdn_url_lowres') required final String cdnUrlLowres,
    @JsonKey(name: 's3_key_highres') required final String s3KeyHighres,
    required final int version,
  }) = _$GenerationResultImpl;

  factory _GenerationResult.fromJson(Map<String, dynamic> json) =
      _$GenerationResultImpl.fromJson;

  @override
  @JsonKey(name: 'publication_id')
  int get publicationId;
  @override
  @JsonKey(name: 'cdn_url_lowres')
  String get cdnUrlLowres;
  @override
  @JsonKey(name: 's3_key_highres')
  String get s3KeyHighres;
  @override
  int get version;

  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$GenerationResultImplCopyWith<_$GenerationResultImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
