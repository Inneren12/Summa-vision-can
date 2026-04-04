// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'content_brief.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ContentBriefImpl _$$ContentBriefImplFromJson(Map<String, dynamic> json) =>
    _$ContentBriefImpl(
      id: (json['id'] as num).toInt(),
      headline: json['headline'] as String,
      chartType: json['chart_type'] as String,
      viralityScore: (json['virality_score'] as num).toDouble(),
      status: json['status'] as String,
      createdAt: json['created_at'] as String,
    );

Map<String, dynamic> _$$ContentBriefImplToJson(_$ContentBriefImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'headline': instance.headline,
      'chart_type': instance.chartType,
      'virality_score': instance.viralityScore,
      'status': instance.status,
      'created_at': instance.createdAt,
    };
