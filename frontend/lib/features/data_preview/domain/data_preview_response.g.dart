// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'data_preview_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ColumnSchemaImpl _$$ColumnSchemaImplFromJson(Map<String, dynamic> json) =>
    _$ColumnSchemaImpl(
      name: json['name'] as String,
      dtype: json['dtype'] as String,
    );

Map<String, dynamic> _$$ColumnSchemaImplToJson(_$ColumnSchemaImpl instance) =>
    <String, dynamic>{
      'name': instance.name,
      'dtype': instance.dtype,
    };

_$DataPreviewResponseImpl _$$DataPreviewResponseImplFromJson(
  Map<String, dynamic> json,
) =>
    _$DataPreviewResponseImpl(
      columns: (json['columns'] as List<dynamic>)
          .map((e) => ColumnSchema.fromJson(e as Map<String, dynamic>))
          .toList(),
      rows: (json['rows'] as List<dynamic>)
          .map((e) => e as Map<String, dynamic>)
          .toList(),
      totalRows: (json['total_rows'] as num).toInt(),
      returnedRows: (json['returned_rows'] as num).toInt(),
    );

Map<String, dynamic> _$$DataPreviewResponseImplToJson(
  _$DataPreviewResponseImpl instance,
) =>
    <String, dynamic>{
      'columns': instance.columns,
      'rows': instance.rows,
      'total_rows': instance.totalRows,
      'returned_rows': instance.returnedRows,
    };
