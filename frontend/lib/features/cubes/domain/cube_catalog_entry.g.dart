// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cube_catalog_entry.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CubeCatalogEntryImpl _$$CubeCatalogEntryImplFromJson(
  Map<String, dynamic> json,
) =>
    _$CubeCatalogEntryImpl(
      productId: json['product_id'] as String,
      titleEn: json['title_en'] as String,
      titleFr: json['title_fr'] as String?,
      subjectCode: json['subject_code'] as String,
      subjectEn: json['subject_en'] as String,
      surveyEn: json['survey_en'] as String?,
      frequency: json['frequency'] as String,
      startDate: json['start_date'] as String?,
      endDate: json['end_date'] as String?,
      archiveStatus: json['archive_status'] as bool? ?? false,
    );

Map<String, dynamic> _$$CubeCatalogEntryImplToJson(
  _$CubeCatalogEntryImpl instance,
) =>
    <String, dynamic>{
      'product_id': instance.productId,
      'title_en': instance.titleEn,
      'title_fr': instance.titleFr,
      'subject_code': instance.subjectCode,
      'subject_en': instance.subjectEn,
      'survey_en': instance.surveyEn,
      'frequency': instance.frequency,
      'start_date': instance.startDate,
      'end_date': instance.endDate,
      'archive_status': instance.archiveStatus,
    };
