// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'raw_data_upload.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$RawDataColumnImpl _$$RawDataColumnImplFromJson(Map<String, dynamic> json) =>
    _$RawDataColumnImpl(
      name: json['name'] as String,
      dtype: json['dtype'] as String? ?? 'str',
    );

Map<String, dynamic> _$$RawDataColumnImplToJson(
        _$RawDataColumnImpl instance) =>
    <String, dynamic>{
      'name': instance.name,
      'dtype': instance.dtype,
    };

_$GenerateFromDataRequestImpl _$$GenerateFromDataRequestImplFromJson(
        Map<String, dynamic> json) =>
    _$GenerateFromDataRequestImpl(
      data: (json['data'] as List<dynamic>)
          .map((e) => e as Map<String, dynamic>)
          .toList(),
      columns: (json['columns'] as List<dynamic>)
          .map((e) => RawDataColumn.fromJson(e as Map<String, dynamic>))
          .toList(),
      chartType: json['chart_type'] as String,
      title: json['title'] as String,
      size: (json['size'] as List<dynamic>?)
              ?.map((e) => (e as num).toInt())
              .toList() ??
          const <int>[1200, 900],
      category: json['category'] as String,
      sourceLabel: json['source_label'] as String? ?? 'custom',
    );

Map<String, dynamic> _$$GenerateFromDataRequestImplToJson(
        _$GenerateFromDataRequestImpl instance) =>
    <String, dynamic>{
      'data': instance.data,
      'columns': instance.columns.map((e) => e.toJson()).toList(),
      'chart_type': instance.chartType,
      'title': instance.title,
      'size': instance.size,
      'category': instance.category,
      'source_label': instance.sourceLabel,
    };
