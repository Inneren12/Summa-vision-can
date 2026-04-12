// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'data_preview_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$DataPreviewResponseImpl _$$DataPreviewResponseImplFromJson(
  Map<String, dynamic> json,
) =>
    _$DataPreviewResponseImpl(
      storageKey: json['storage_key'] as String,
      rows: (json['rows'] as num).toInt(),
      columns: (json['columns'] as num).toInt(),
      columnNames: (json['column_names'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      data: (json['data'] as List<dynamic>)
          .map((e) => e as Map<String, dynamic>)
          .toList(),
    );

Map<String, dynamic> _$$DataPreviewResponseImplToJson(
  _$DataPreviewResponseImpl instance,
) =>
    <String, dynamic>{
      'storage_key': instance.storageKey,
      'rows': instance.rows,
      'columns': instance.columns,
      'column_names': instance.columnNames,
      'data': instance.data,
    };
