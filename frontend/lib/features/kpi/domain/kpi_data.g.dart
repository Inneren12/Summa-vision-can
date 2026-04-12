// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'kpi_data.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$KPIDataImpl _$$KPIDataImplFromJson(Map<String, dynamic> json) =>
    _$KPIDataImpl(
      totalPublications: (json['total_publications'] as num).toInt(),
      publishedCount: (json['published_count'] as num).toInt(),
      draftCount: (json['draft_count'] as num).toInt(),
      totalLeads: (json['total_leads'] as num).toInt(),
      b2bLeads: (json['b2b_leads'] as num).toInt(),
      educationLeads: (json['education_leads'] as num).toInt(),
      ispLeads: (json['isp_leads'] as num).toInt(),
      b2cLeads: (json['b2c_leads'] as num).toInt(),
      espSyncedCount: (json['esp_synced_count'] as num).toInt(),
      espFailedPermanentCount:
          (json['esp_failed_permanent_count'] as num).toInt(),
      emailsSent: (json['emails_sent'] as num).toInt(),
      tokensCreated: (json['tokens_created'] as num).toInt(),
      tokensActivated: (json['tokens_activated'] as num).toInt(),
      tokensExhausted: (json['tokens_exhausted'] as num).toInt(),
      totalJobs: (json['total_jobs'] as num).toInt(),
      jobsSucceeded: (json['jobs_succeeded'] as num).toInt(),
      jobsFailed: (json['jobs_failed'] as num).toInt(),
      jobsQueued: (json['jobs_queued'] as num).toInt(),
      jobsRunning: (json['jobs_running'] as num).toInt(),
      failedByType: (json['failed_by_type'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, (e as num).toInt()),
      ),
      catalogSyncs: (json['catalog_syncs'] as num).toInt(),
      dataContractViolations:
          (json['data_contract_violations'] as num).toInt(),
      periodStart: DateTime.parse(json['period_start'] as String),
      periodEnd: DateTime.parse(json['period_end'] as String),
    );

Map<String, dynamic> _$$KPIDataImplToJson(_$KPIDataImpl instance) =>
    <String, dynamic>{
      'total_publications': instance.totalPublications,
      'published_count': instance.publishedCount,
      'draft_count': instance.draftCount,
      'total_leads': instance.totalLeads,
      'b2b_leads': instance.b2bLeads,
      'education_leads': instance.educationLeads,
      'isp_leads': instance.ispLeads,
      'b2c_leads': instance.b2cLeads,
      'esp_synced_count': instance.espSyncedCount,
      'esp_failed_permanent_count': instance.espFailedPermanentCount,
      'emails_sent': instance.emailsSent,
      'tokens_created': instance.tokensCreated,
      'tokens_activated': instance.tokensActivated,
      'tokens_exhausted': instance.tokensExhausted,
      'total_jobs': instance.totalJobs,
      'jobs_succeeded': instance.jobsSucceeded,
      'jobs_failed': instance.jobsFailed,
      'jobs_queued': instance.jobsQueued,
      'jobs_running': instance.jobsRunning,
      'failed_by_type': instance.failedByType,
      'catalog_syncs': instance.catalogSyncs,
      'data_contract_violations': instance.dataContractViolations,
      'period_start': instance.periodStart.toIso8601String(),
      'period_end': instance.periodEnd.toIso8601String(),
    };
