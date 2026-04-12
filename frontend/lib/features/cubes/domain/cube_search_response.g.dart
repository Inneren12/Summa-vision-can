// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cube_search_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CubeSearchResponseImpl _$$CubeSearchResponseImplFromJson(
  Map<String, dynamic> json,
) =>
    _$CubeSearchResponseImpl(
      items: (json['items'] as List<dynamic>)
          .map((e) => CubeCatalogEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: (json['total'] as num).toInt(),
    );

Map<String, dynamic> _$$CubeSearchResponseImplToJson(
  _$CubeSearchResponseImpl instance,
) =>
    <String, dynamic>{
      'items': instance.items.map((e) => e.toJson()).toList(),
      'total': instance.total,
    };
