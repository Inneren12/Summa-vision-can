// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'job_list_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$JobListResponseImpl _$$JobListResponseImplFromJson(
  Map<String, dynamic> json,
) => _$JobListResponseImpl(
  items: (json['items'] as List<dynamic>)
      .map((e) => Job.fromJson(e as Map<String, dynamic>))
      .toList(),
  total: (json['total'] as num).toInt(),
);

Map<String, dynamic> _$$JobListResponseImplToJson(
  _$JobListResponseImpl instance,
) => <String, dynamic>{'items': instance.items, 'total': instance.total};
