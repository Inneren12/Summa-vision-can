// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'graphics_generate_request.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$GraphicsGenerateRequestImpl _$$GraphicsGenerateRequestImplFromJson(
        Map<String, dynamic> json) =>
    _$GraphicsGenerateRequestImpl(
      dataKey: json['data_key'] as String,
      chartType: json['chart_type'] as String,
      title: json['title'] as String,
      size: (json['size'] as List<dynamic>).map((e) => (e as num).toInt()).toList(),
      category: json['category'] as String,
      sourceProductId: json['source_product_id'] as String?,
    );

Map<String, dynamic> _$$GraphicsGenerateRequestImplToJson(
        _$GraphicsGenerateRequestImpl instance) =>
    <String, dynamic>{
      'data_key': instance.dataKey,
      'chart_type': instance.chartType,
      'title': instance.title,
      'size': instance.size,
      'category': instance.category,
      'source_product_id': instance.sourceProductId,
    };
